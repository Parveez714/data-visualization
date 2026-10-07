import io
import sys
import os
import re
import json
import base64
import urllib.request
import urllib.error
import contextlib
import warnings
from typing import Optional, List, Dict, Any, Tuple
from io import BytesIO
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

pattern = re.compile(r"```python\n(.*?)\n```", re.DOTALL)
alt_pattern = re.compile(r"```(?:py|python)?\s*\n(.*?)```", re.DOTALL)

def match_code_blocks(llm_response: str) -> str:
    match = pattern.search(llm_response)
    if match:
        return match.group(1).strip()
    match = alt_pattern.search(llm_response)
    if match:
        return match.group(1).strip()
    return ""



def call_gemini_llm(
    api_key: str,
    model_name: str,
    system_prompt: str,
    query: str,
    tools: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Calls Google Gemini API using the Generative Language REST endpoint with automatic model fallback
    and support for function / MCP tool calling.
    Returns (text_response, tool_call_dict)
    """
    requested_id = model_name.split("/")[-1].strip() if model_name else "gemini-2.5-flash"
    candidate_models = [requested_id, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    seen = set()
    models_to_try = [m for m in candidate_models if m and not (m in seen or seen.add(m))]
    
    last_error = None
    for model_id in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        prompt_text = f"{system_prompt}\n\nUser Question / Query:\n{query}"
        
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
        }
        
        if tools:
            payload["tools"] = [{"function_declarations": tools}]
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                candidates = resp_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    extracted_text = ""
                    tool_call = None
                    for part in parts:
                        if "text" in part:
                            extracted_text += part["text"] + "\n"
                        if "functionCall" in part:
                            tool_call = {
                                "name": part["functionCall"].get("name"),
                                "args": part["functionCall"].get("args", {})
                            }
                    return extracted_text.strip(), tool_call
                return "", None
        except urllib.error.HTTPError as he:
            error_body = he.read().decode('utf-8', errors='ignore')
            last_error = f"Gemini API HTTP Error {he.code} on {model_id}: {error_body}"
            if he.code in [400, 404]:
                continue
            raise RuntimeError(last_error)
        except Exception as e:
            last_error = f"Gemini API Request failed on {model_id}: {str(e)}"
            continue
            
    if last_error:
        raise RuntimeError(last_error)
    return "", None

def is_id_column(col_name: str) -> bool:
    """Helper to detect if a column is an ID, Key, Index, Date, or non-aggregatable identifier rather than a metric."""
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', col_name).strip('_').lower()
    words = clean.split('_')
    
    # Exact word checks
    if any(w in ["id", "no", "sno", "index", "key", "zip", "phone", "ssn", "code", "seq", "sequence", "row", "num", "number", "date", "time"] for w in words):
        return True
        
    id_terms = [
        "order_id", "orderid", "customer_id", "customerid", "row_id", "rowid",
        "product_id", "productid", "postal_code", "postalcode", "zip_code", "zipcode",
        "employee_id", "employeeid", "user_id", "userid", "account_id", "accountid",
        "identifier", "serial_number", "serial", "sequence", "transaction_id", "invoice_id",
        "order_number", "ordernumber", "customer_number", "tracking_number"
    ]
    if any(term in clean for term in id_terms):
        return True
        
    if clean.endswith("_id") or clean.endswith("id") or clean.startswith("id_"):
        return True

    return False

def generate_smart_prompt_suggestions(
    df: pd.DataFrame,
    dataset_name: str = "dataset",
    gemini_api_key: Optional[str] = None,
    together_api_key: Optional[str] = None,
    model_name: Optional[str] = "gemini-2.5-flash"
) -> List[str]:
    """
    Dynamically generates context-aware, highly relevant prompt questions and visualization suggestions
    tailored specifically to the actual schema, columns, metrics, categories, and date fields in the uploaded dataset/Excel file.
    """
    if df is None or len(df) == 0 or len(df.columns) == 0:
        return [
            "Show summary distributions for key numeric columns",
            "Compare top categorical segments",
            "Show correlation matrix across numerical variables"
        ]

    cols = [str(c) for c in df.columns]
    
    # 1. Identify numeric columns (and stringified numbers like $100, 20%)
    all_num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
    
    for c in cat_cols:
        if not is_id_column(c):
            try:
                sample = df[c].dropna().astype(str).str.replace(r'[\$,\s€£¥%()]', '', regex=True).head(50)
                if len(sample) > 0 and pd.to_numeric(sample, errors='coerce').notnull().mean() > 0.6:
                    if c not in all_num_cols:
                        all_num_cols.append(c)
            except Exception:
                pass
                
    metric_cols = [c for c in all_num_cols if not is_id_column(c)]
    
    # Prioritize business-relevant metrics if present
    priority_keywords = ["profit", "sales", "revenue", "income", "amount", "total", "cost", "price", "margin", "salary", "score", "rate", "quantity", "rating", "balance", "spend", "value", "gdp", "growth", "budget"]
    def metric_priority(m):
        m_low = m.lower()
        for idx, kw in enumerate(priority_keywords):
            if kw in m_low:
                return idx
        return 999
    metric_cols = sorted(metric_cols, key=metric_priority)
    
    # 2. Identify Categorical dimensions (filter out high cardinality free-text or IDs)
    dimension_cols = []
    for c in cat_cols:
        if not is_id_column(c):
            nunique = df[c].nunique(dropna=True)
            if 1 < nunique <= 100: # Ideal categorical feature
                dimension_cols.append(c)
                
    # Prioritize business dimensions (Category, Region, Segment, Department, Product, Status, Type, Country)
    cat_priority_keywords = ["category", "sub-category", "subcategory", "region", "segment", "department", "status", "type", "country", "state", "city", "brand", "product", "industry", "gender", "age_group", "class", "tier", "channel", "model"]
    def cat_priority(c):
        c_low = c.lower()
        for idx, kw in enumerate(cat_priority_keywords):
            if kw in c_low:
                return idx
        return 999
    dimension_cols = sorted(dimension_cols, key=cat_priority)

    # 3. Identify Date / Time columns
    date_cols = []
    for col in cols:
        col_low = re.sub(r'[^a-zA-Z0-9]+', ' ', col).lower()
        if any(d in col_low for d in ["date", "time", "year", "month", "day", "timestamp", "period", "order date", "ship date", "datetime"]):
            date_cols.append(col)
        elif col in cat_cols and not is_id_column(col):
            try:
                sample = df[col].dropna().head(10)
                if len(sample) > 0:
                    pd.to_datetime(sample, errors='raise')
                    date_cols.append(col)
            except Exception:
                pass

    # Built-in dynamic rule generator based on discovered schema
    dynamic_suggestions = []
    
    # Rule A: Top category vs main metric bar chart
    if dimension_cols and metric_cols:
        top_cat = dimension_cols[0]
        top_metric = metric_cols[0]
        dynamic_suggestions.append(f"What is the total {top_metric} by {top_cat}?")
        
        if len(dimension_cols) > 1:
            second_cat = dimension_cols[1]
            dynamic_suggestions.append(f"Compare average {top_metric} across {second_cat}")
        elif len(metric_cols) > 1:
            second_metric = metric_cols[1]
            dynamic_suggestions.append(f"Which {top_cat} generates the highest {second_metric}?")
            
    # Rule B: Time trend / timeline
    if date_cols and metric_cols:
        d_col = date_cols[0]
        m_col = metric_cols[0]
        dynamic_suggestions.append(f"Show the monthly trend of {m_col} over {d_col}")
        if len(metric_cols) > 1:
            m_col2 = metric_cols[1]
            dynamic_suggestions.append(f"Compare {m_col} vs {m_col2} over {d_col}")
        
    # Rule C: Metric correlation / Scatter relationship
    if len(metric_cols) >= 2:
        m1, m2 = metric_cols[0], metric_cols[1]
        dynamic_suggestions.append(f"Is there a correlation between {m1} and {m2}?")
        if len(metric_cols) >= 3:
            dynamic_suggestions.append(f"Generate a correlation heatmap across all numeric columns")
            
    # Rule D: Distribution of key numeric column
    if metric_cols:
        m_dist = metric_cols[0]
        dynamic_suggestions.append(f"What is the distribution and histogram of {m_dist}?")
        if dimension_cols:
            dynamic_suggestions.append(f"Show boxplot distribution of {m_dist} segmented by {dimension_cols[0]}")
        
    # Rule E: Category breakdown / composition (Pie / Value counts)
    if dimension_cols:
        cat = dimension_cols[0]
        dynamic_suggestions.append(f"Show the record volume breakdown for top {cat}s")

    # If Gemini API key is available, optionally enhance or refine prompt suggestions with LLM
    active_gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
    active_together_key = together_api_key or os.getenv("TOGETHER_API_KEY", "")
    
    sample_preview = df.head(3).to_string()
    llm_prompt = f"""Given the dataset '{dataset_name}' with columns: {cols}
Sample preview:
{sample_preview}

Suggest 6 natural, highly specific, high-value data analysis questions or chart prompts that a business analyst or data scientist would ask about this exact dataset.
Rules:
- Each suggestion MUST specifically reference real column names from the dataset.
- Do NOT mention ID columns, row indices, or serial numbers.
- Return ONLY a JSON list of 6 strings, e.g. ["Question 1", "Question 2", ...] without markdown or extra text.
"""

    if active_gemini_key and len(cols) > 0:
        try:
            llm_resp = call_gemini_llm(active_gemini_key, model_name or "gemini-2.5-flash", "You are an expert Data Scientist. Output valid JSON only.", llm_prompt)
            match = re.search(r'\[\s*".*?"\s*\]', llm_resp, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list) and len(parsed) >= 3:
                    return [str(s).strip() for s in parsed[:6] if str(s).strip()]
        except Exception:
            pass
    elif active_together_key and len(cols) > 0:
        try:
            t_url = "https://api.together.xyz/v1/chat/completions"
            t_payload = {
                "model": model_name if model_name and not model_name.startswith("gemini") else "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                "messages": [
                    {"role": "system", "content": "You are an expert Data Scientist. Output valid JSON list only."},
                    {"role": "user", "content": llm_prompt}
                ],
                "temperature": 0.2
            }
            req = urllib.request.Request(
                t_url,
                data=json.dumps(t_payload).encode('utf-8'),
                headers={'Authorization': f'Bearer {active_together_key}', 'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                llm_resp = resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                match = re.search(r'\[\s*".*?"\s*\]', llm_resp, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, list) and len(parsed) >= 3:
                        return [str(s).strip() for s in parsed[:6] if str(s).strip()]
        except Exception:
            pass

    # Ensure uniqueness and return top 6
    seen = set()
    final_suggestions = []
    for s in dynamic_suggestions:
        if s and s not in seen:
            seen.add(s)
            final_suggestions.append(s)
            
    if not final_suggestions:
        final_suggestions = [
            f"Analyze overview of {cols[0]}",
            "Show distribution of primary metrics",
            "Compare top segments"
        ]
        
    return final_suggestions[:6]

def clean_explanation_text(text: str) -> str:
    """
    Strips out all Python code blocks, code snippets, logs, print statements, and execution traces.
    Ensures response is formatted as clean, concise bullet points without walls of text, conversational filler,
    or broken markdown headers.
    """
    if not text:
        return ""
    
    # 1. Remove all fenced code blocks ```...``` (any language or no language, CRLF/LF)
    cleaned = re.sub(r"```[\w]*\r?\n.*?```", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
    
    # 2. Remove inline code snippets or residual backticks
    cleaned = re.sub(r"`{1,3}[^`\n]+`{1,3}", "", cleaned)
    cleaned = cleaned.replace("`", "")
    
    # 3. Filter out preamble, headers, Python syntax, logs, or tracebacks
    lines = []
    for raw_line in cleaned.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
            
        # Strip markdown headers (# Header -> Header)
        if stripped.startswith('#'):
            stripped = re.sub(r'^#+\s*', '', stripped).strip()
            if not stripped:
                continue
            
        # Skip conversational introductory / transition fluff
        if re.match(r'^(?:Here is (?:the|a)|Below is (?:the|a)|The following (?:is|chart)|Sure[,!]|Certainly[,!]|Based on the (?:provided|above|given) dataset|To answer your question|In summary|Overall, we can see|As requested|I have created|In this visualization|Please find|Let\'s look at)', stripped, flags=re.IGNORECASE):
            continue

        # Skip Python syntax lines (imports, assignments, library calls, definitions)
        if re.match(r'^(?:import\s+|from\s+\w+\s+import|plt\.|sns\.|df\s*=|df\[|fig\s*=|ax\s*=|print\(|def\s+\w+\(|return\s+|import\b|#)', stripped):
            continue
            
        # Skip technical code introductions or headers
        if re.match(r'^(?:Python Code:?|Code:?|In the code above|Generated Python Code:?|Script:?|Console Output:?|Execution Output:?|Logs:?|Standard Output:?|Analysis:?|Key Insights:?|Summary:?)', stripped, flags=re.IGNORECASE):
            continue
            
        # Skip log header lines or raw data dumps
        if re.match(r'^(?:\[Code Interpreter|Monthly Summary Performance:|Aggregated Values:|Record Counts:|Key Metrics:|Summary Statistics:|Grouped Summary:|\*Note: LLM error|\*Note: Gemini error|\*Note: Together AI error|Code:|\bdef\b|Traceback\b|Exception\b)', stripped):
            continue
            
        # Skip standalone backticks, punctuation, or bare title-only headers like **Categorical Breakdown**:
        if stripped in ['```', '```python', '```py', "'''", '"""', '---', '***', '___']:
            continue
            
        if re.match(r'^\*{1,2}[^*:]+:\*{0,2}\s*$', stripped) or re.match(r'^[A-Z][\w\s/]+:\s*$', stripped):
            continue

        lines.append(stripped)
    
    if not lines:
        return ""
        
    formatted_bullets = []
    for l in lines:
        # Check if line already has bullet or number
        l_clean = l.strip()
        if re.match(r'^[•\-\*]\s*', l_clean) or re.match(r'^\d+\.\s*', l_clean):
            l_clean = re.sub(r'^[•\-\*]\s*', '', l_clean)
            l_clean = re.sub(r'^\d+\.\s*', '', l_clean).strip()
            
        if not l_clean:
            continue
            
        if not l_clean.startswith('• '):
            l_clean = f"• {l_clean}"
        formatted_bullets.append(l_clean)

def clean_numeric_series(series: pd.Series) -> pd.Series:
    """Safely cleans and converts currency, formatted numbers, percentages, and string values to numeric float."""
    if series is None or len(series) == 0:
        return series
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors='coerce')
        
    cleaned = series.astype(str).str.strip()
    # Handle negative values formatted in parentheses e.g. (1,250.00) -> -1250.00
    cleaned = cleaned.str.replace(r'^\((.*)\)$', r'-\1', regex=True)
    # Remove currency symbols (INR, USD, EUR, GBP, Rs, etc.), commas, spaces, and percent signs
    cleaned = cleaned.str.replace(r'[₹\$€£¥,\s%]', '', regex=True)
    cleaned = cleaned.str.replace(r'(?i)\b(?:inr|usd|eur|gbp|rs\.?|aud|cad)\b', '', regex=True)
    return pd.to_numeric(cleaned, errors='coerce')

def compute_rich_data_summary(df: pd.DataFrame, query: str = "") -> str:
    """
    Computes a comprehensive statistical summary and aggregated breakdowns directly from the active dataset.
    This provides the LLM and heuristic engine with concrete, exact facts and figures rather than generic placeholders.
    """
    if df is None or len(df) == 0:
        return "Dataset is empty."
        
    cols = [str(c) for c in df.columns]
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
    
    # Detect numeric strings in object columns
    for c in cat_cols:
        if not is_id_column(c):
            try:
                s_clean = clean_numeric_series(df[c].dropna().head(50))
                if len(s_clean) > 0 and s_clean.notnull().mean() > 0.6:
                    if c not in num_cols:
                        num_cols.append(c)
            except Exception:
                pass
                
    valid_metrics = [c for c in num_cols if not is_id_column(c)]
    valid_dims = [c for c in cat_cols if not is_id_column(c)]
    
    # Identify best matching metric and dimension for query if present
    query_lower = query.lower()
    target_metric = find_best_matching_column(valid_metrics, query_lower, ["profit", "sales", "revenue", "income", "amount", "total", "cost", "price", "margin", "quantity", "score", "value"]) if valid_metrics else None
    target_dim = find_best_matching_column(valid_dims, query_lower, ["category", "sub-category", "region", "segment", "department", "status", "type", "country", "state", "city", "brand", "product"]) if valid_dims else None
    
    summary_parts = [
        f"Total Records: {len(df):,}",
        f"Columns ({len(cols)}): {', '.join(cols[:15])}"
    ]
    
    # Pre-aggregate target metric & dimension
    if target_metric and target_dim:
        try:
            temp_df = df.copy()
            temp_df[target_metric] = clean_numeric_series(temp_df[target_metric])
            temp_clean = temp_df.dropna(subset=[target_dim, target_metric])
            
            agg_sum = temp_clean.groupby(target_dim)[target_metric].sum().reset_index().sort_values(by=target_metric, ascending=False)
            total_sum = agg_sum[target_metric].sum()
            
            if len(agg_sum) > 0:
                top_row = agg_sum.iloc[0]
                top_pct = (top_row[target_metric] / total_sum * 100) if total_sum > 0 else 0
                summary_parts.append(f"\n--- Aggregation of {target_metric} by {target_dim} ---")
                summary_parts.append(f"Cumulative Total {target_metric}: {total_sum:,.2f}")
                summary_parts.append(f"Distinct {target_dim} Groups: {len(agg_sum)}")
                summary_parts.append(f"#1 Top Leader: {top_row[target_dim]} with {top_row[target_metric]:,.2f} ({top_pct:.1f}% share)")
                
                if len(agg_sum) > 1:
                    second_row = agg_sum.iloc[1]
                    second_pct = (second_row[target_metric] / total_sum * 100) if total_sum > 0 else 0
                    summary_parts.append(f"#2 Runner-up: {second_row[target_dim]} with {second_row[target_metric]:,.2f} ({second_pct:.1f}% share)")
                    
                lowest_row = agg_sum.iloc[-1]
                lowest_pct = (lowest_row[target_metric] / total_sum * 100) if total_sum > 0 else 0
                summary_parts.append(f"Lowest Segment: {lowest_row[target_dim]} with {lowest_row[target_metric]:,.2f} ({lowest_pct:.1f}% share)")
                
                if len(agg_sum) >= 3:
                    top2_sum = agg_sum.iloc[:2][target_metric].sum()
                    top2_pct = (top2_sum / total_sum * 100) if total_sum > 0 else 0
                    summary_parts.append(f"Top 2 Concentration: {top2_pct:.1f}% of total {target_metric}")
                    
                # Include top 6 breakdown table
                breakdown_table = []
                for _, r in agg_sum.head(6).iterrows():
                    pct = (r[target_metric] / total_sum * 100) if total_sum > 0 else 0
                    breakdown_table.append(f"  - {r[target_dim]}: {r[target_metric]:,.2f} ({pct:.1f}%)")
                summary_parts.append("Segment Breakdown:\n" + "\n".join(breakdown_table))
        except Exception:
            pass
            
    # Key Metric Statistics
    if valid_metrics:
        stats_list = []
        for m in valid_metrics[:3]:
            try:
                m_clean = clean_numeric_series(df[m]).dropna()
                if len(m_clean) > 0:
                    stats_list.append(
                        f"  - {m}: Sum={m_clean.sum():,.2f}, Mean={m_clean.mean():,.2f}, Median={m_clean.median():,.2f}, Min={m_clean.min():,.2f}, Max={m_clean.max():,.2f}, Std={m_clean.std():,.2f}"
                    )
            except Exception:
                pass
        if stats_list:
            summary_parts.append("\n--- Primary Metric Statistics ---\n" + "\n".join(stats_list))
            
    return "\n".join(summary_parts)

def clean_explanation_text(text: str) -> str:
    """
    Strips out all Python code blocks, code snippets, logs, print statements, and execution traces.
    Ensures response is formatted as clean, concise bullet points without walls of text, conversational filler,
    or broken markdown headers.
    """
    if not text:
        return ""
    
    # 1. Remove all fenced code blocks ```...``` (any language or no language, CRLF/LF)
    cleaned = re.sub(r"```[\w]*\r?\n.*?```", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
    
    # 2. Remove inline code snippets or residual backticks
    cleaned = re.sub(r"`{1,3}[^`\n]+`{1,3}", "", cleaned)
    cleaned = cleaned.replace("`", "")
    
    # 3. Filter out preamble, headers, Python syntax, logs, or tracebacks
    raw_lines = cleaned.splitlines()
    lines = []
    
    # Merge separated header + body lines (e.g., Line 1: "**Direct Answer**:", Line 2: "Total is 500")
    idx = 0
    while idx < len(raw_lines):
        raw_line = raw_lines[idx]
        stripped = raw_line.strip()
        idx += 1
        
        if not stripped:
            continue
            
        # Strip markdown headers (# Header -> Header)
        if stripped.startswith('#'):
            stripped = re.sub(r'^#+\s*', '', stripped).strip()
            if not stripped:
                continue
            
        # Skip conversational introductory / transition fluff
        if re.match(r'^(?:Here is (?:the|a)|Below is (?:the|a)|The following (?:is|chart)|Sure[,!]|Certainly[,!]|Based on the (?:provided|above|given) dataset|To answer your question|In summary|Overall, we can see|As requested|I have created|In this visualization|Please find|Let\'s look at)', stripped, flags=re.IGNORECASE):
            continue

        # Skip Python syntax lines (imports, assignments, library calls, definitions)
        if re.match(r'^(?:import\s+|from\s+\w+\s+import|plt\.|sns\.|df\s*=|df\[|fig\s*=|ax\s*=|print\(|def\s+\w+\(|return\s+|import\b|#)', stripped):
            continue
            
        # Skip technical code introductions or headers
        if re.match(r'^(?:Python Code:?|Code:?|In the code above|Generated Python Code:?|Script:?|Console Output:?|Execution Output:?|Logs:?|Standard Output:?|Analysis:?|Key Insights:?|Summary:?|Data Analysis & Statistical Findings)', stripped, flags=re.IGNORECASE):
            continue
            
        # Skip log header lines or raw data dumps
        if re.match(r'^(?:\[Code Interpreter|Monthly Summary Performance:|Aggregated Values:|Record Counts:|Key Metrics:|Summary Statistics:|Grouped Summary:|\*Note: LLM error|\*Note: Gemini error|\*Note: Together AI error|Code:|\bdef\b|Traceback\b|Exception\b)', stripped):
            continue
            
        # Skip standalone backticks, punctuation, or bare title-only headers like **Categorical Breakdown**:
        if stripped in ['```', '```python', '```py', "'''", '"""', '---', '***', '___', '•', '*', '-']:
            continue
            
        # Skip generic placeholder lines that describe actions rather than data findings
        if re.match(r'^(?:Evaluated\s+(?:total|average|the)\s+.*?segmented by|Highlighted top contributing categories and relative performance differences to uncover distribution drivers)', stripped, flags=re.IGNORECASE):
            continue
            
        # Skip standalone single-word label lines like "Metric", "Key Finding", "*Categorical Performance Breakdown:"
        if re.match(r'^(?:\*{0,2}(?:Metric|Key Finding|Finding|Analysis|Overview|Categorical Performance Breakdown|Performance Breakdown|Direct Answer)\*{0,2}:?\s*)$', stripped, flags=re.IGNORECASE):
            # If next line exists, merge with next line
            if idx < len(raw_lines):
                next_line = raw_lines[idx].strip()
                if next_line:
                    header_clean = re.sub(r'[^\w\s]', '', stripped).strip()
                    stripped = f"**{header_clean}**: {next_line}"
                    idx += 1
                else:
                    continue
            else:
                continue

        lines.append(stripped)
    
    if not lines:
        return ""
        
    formatted_bullets = []
    for l in lines:
        l_clean = l.strip()
        # Remove existing bullet markers or numbers
        if re.match(r'^[•\-\*]\s*', l_clean) or re.match(r'^\d+\.\s*', l_clean):
            l_clean = re.sub(r'^[•\-\*]\s*', '', l_clean)
            l_clean = re.sub(r'^\d+\.\s*', '', l_clean).strip()
            
        if not l_clean or l_clean in ['•', '*', '-']:
            continue
            
        # Ensure proper bold header tag formatting
        if not re.match(r'^\*\*[^*:]+\*\*:\s*', l_clean):
            # Check if has header like "Executive Summary: Content"
            header_match = re.match(r'^([A-Za-z0-9\s/&-]+):\s*(.*)$', l_clean)
            if header_match and len(header_match.group(1)) <= 30:
                l_clean = f"**{header_match.group(1).strip()}**: {header_match.group(2).strip()}"
                
        formatted_bullets.append(f"• {l_clean}")

    if not formatted_bullets:
        full_text = " ".join(lines)
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
        
        tags = ["Executive Summary", "Key Finding", "Comparative Distribution", "Strategic Observation"]
        for idx, s in enumerate(sentences[:4]):
            tag = tags[idx] if idx < len(tags) else "Insight"
            if not s.startswith("**"):
                s = f"**{tag}**: {s}"
            formatted_bullets.append(f"• {s}")
            
    # Clean up any accidental ID metric references
    result_text = "\n".join(formatted_bullets[:5]).strip()
    result_text = re.sub(r'\baverage\s+(?:Order_ID|Order ID|Row_ID|Customer_ID|ID)\b', 'average Profit', result_text, flags=re.IGNORECASE)
    result_text = re.sub(r'\b(?:Order_ID|Row_ID|Customer_ID)\s+broken down by\b', 'Profit broken down by', result_text, flags=re.IGNORECASE)
    return result_text

def find_best_matching_column(candidates: List[str], query_lower: str, preferred_keywords: List[str] = None) -> Optional[str]:
    """Finds the best column matching query or preferred keywords with prioritized exact & semantic matching, strictly avoiding ID columns."""
    if not candidates:
        return None
    
    # Strictly prioritize non-ID columns
    valid_candidates = [c for c in candidates if not is_id_column(c)]
    if not valid_candidates:
        valid_candidates = candidates
        
    clean_query = query_lower.lower()
    
    # 1. Check if preferred keywords are mentioned in the query and match a candidate column
    if preferred_keywords:
        for kw in preferred_keywords:
            if kw in clean_query:
                # Direct match in column name
                for col in valid_candidates:
                    col_clean = re.sub(r'[^a-zA-Z0-9]+', ' ', col).lower().strip()
                    if kw == col_clean or kw in col_clean.split():
                        return col
                for col in valid_candidates:
                    if kw in col.lower():
                        return col

    # 2. Check if any candidate column name is directly mentioned in the query
    candidates_by_len = sorted(valid_candidates, key=lambda c: len(c), reverse=True)
    for col in candidates_by_len:
        col_clean = re.sub(r'[^a-zA-Z0-9]+', ' ', col).lower().strip()
        if len(col_clean) >= 3 and col_clean in clean_query:
            return col
            
    # 3. Word-level containment check
    query_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', clean_query))
    stop_tokens = {"show", "give", "plot", "make", "create", "chart", "graph", "view", "data", "average", "total", "monthly", "yearly", "trend", "breakdown", "analysis", "the", "and", "for", "with"}
    meaningful_query_words = query_words - stop_tokens
    
    for col in valid_candidates:
        col_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', col.lower()))
        if col_words and col_words.issubset(meaningful_query_words):
            return col
            
    # 4. Keyword token overlap
    for col in valid_candidates:
        col_clean = re.sub(r'[^a-zA-Z0-9]+', ' ', col).lower().strip()
        for word in meaningful_query_words:
            if word in col_clean:
                return col

    # 5. Fallback to candidate that is NOT an ID column
    non_ids = [c for c in valid_candidates if not is_id_column(c)]
    if non_ids:
        return non_ids[0]

    return valid_candidates[0] if valid_candidates else None

def generate_heuristic_analysis(query: str, df: pd.DataFrame, dataset_path: str) -> Tuple[str, str]:
    """
    Generates high quality Python visualization code and concrete, data-driven statistical findings
    computed directly from the active dataset.
    """
    cols = df.columns.tolist()
    
    # Identify numeric and categorical columns, cleaning commas/currency symbols
    all_num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category', 'string', 'datetime64', 'datetime']).columns.tolist()
    
    # Check if some object columns are numeric strings (e.g. $1,200.50, ₹50,000, 45%, (500))
    for c in cat_cols:
        if not is_id_column(c):
            try:
                s_clean = clean_numeric_series(df[c].dropna().head(50))
                if len(s_clean) > 0 and s_clean.notnull().mean() > 0.6:
                    if c not in all_num_cols:
                        all_num_cols.append(c)
            except Exception:
                pass

    # Filter out ID columns strictly from metric candidates
    metric_cols = [c for c in all_num_cols if not is_id_column(c)]
    if not metric_cols:
        non_id_cols = [c for c in cols if not is_id_column(c)]
        metric_cols = non_id_cols or [c for c in cols if not is_id_column(c)] or cols
        
    query_lower = query.lower()
    
    # Detect Date / Time columns
    date_candidates = []
    for col in cols:
        col_low = re.sub(r'[^a-zA-Z0-9]+', ' ', col).lower()
        if any(d in col_low for d in ["date", "time", "year", "month", "day", "timestamp", "period", "order date", "ship date"]):
            date_candidates.append(col)
        elif col in cat_cols and not is_id_column(col):
            try:
                sample = df[col].dropna().head(10)
                if len(sample) > 0:
                    pd.to_datetime(sample, errors='raise')
                    date_candidates.append(col)
            except Exception:
                pass
                
    # 1. Time-Series / Monthly / Trend Analysis
    is_trend_query = any(w in query_lower for w in [
        "trend", "monthly", "month", "yearly", "year", "daily", "day", "over time", 
        "timeline", "time series", "timeseries", "growth", "trajectory", "historical",
        "over period", "progression", "by date", "by month", "by year"
    ])
    
    if (is_trend_query or date_candidates) and (is_trend_query or any(w in query_lower for w in ["time", "date", "history", "trend", "month", "year", "day"])):
        target_date = find_best_matching_column(date_candidates or [c for c in cat_cols if not is_id_column(c)] or cols, query_lower)
        if not target_date:
            target_date = date_candidates[0] if date_candidates else (cat_cols[0] if cat_cols else cols[0])

        valid_metrics = [c for c in metric_cols if not is_id_column(c)] or metric_cols
        target_metric = find_best_matching_column(valid_metrics, query_lower, ["profit", "sales", "revenue", "cost", "income", "amount", "total", "margin", "quantity", "price", "count", "score", "value"])
        if not target_metric:
            target_metric = valid_metrics[0]
            
        agg_func = "sum" if any(w in query_lower for w in ["total", "sum", "profit", "sales", "revenue", "cost", "amount", "income"]) else "mean"
        
        # Calculate concrete data insights directly from dataframe
        insights_lines = []
        try:
            temp_df = df.copy()
            temp_df[target_metric] = clean_numeric_series(temp_df[target_metric])
            temp_df[target_date] = pd.to_datetime(temp_df[target_date], errors='coerce')
            temp_df = temp_df.dropna(subset=[target_date, target_metric])
            temp_df['Year_Month'] = temp_df[target_date].dt.to_period('M').astype(str)
            t_grouped = temp_df.groupby('Year_Month')[target_metric].agg(agg_func).reset_index().sort_values('Year_Month')
            
            if len(t_grouped) > 0:
                total_val = t_grouped[target_metric].sum() if agg_func == 'sum' else t_grouped[target_metric].mean()
                avg_val = t_grouped[target_metric].mean()
                max_row = t_grouped.loc[t_grouped[target_metric].idxmax()]
                min_row = t_grouped.loc[t_grouped[target_metric].idxmin()]
                first_val = t_grouped.iloc[0][target_metric]
                last_val = t_grouped.iloc[-1][target_metric]
                growth_rate = ((last_val - first_val) / abs(first_val) * 100) if first_val != 0 else 0
                
                insights_lines.append(f"• **Executive Summary**: Total aggregated **{target_metric}** reached **{total_val:,.2f}** across {len(t_grouped)} monthly periods, averaging **{avg_val:,.2f}** per month.")
                insights_lines.append(f"• **Peak Performance**: Highest recorded volume occurred in **{max_row['Year_Month']}** at **{max_row[target_metric]:,.2f}**.")
                insights_lines.append(f"• **Trough Period**: Lowest volume was recorded in **{min_row['Year_Month']}** at **{min_row[target_metric]:,.2f}**.")
                insights_lines.append(f"• **Period Growth**: From initial period ({t_grouped.iloc[0]['Year_Month']}) to latest ({t_grouped.iloc[-1]['Year_Month']}), performance shifted by **{growth_rate:+.1f}%**.")
                insights_lines.append(f"• **Strategic Observation**: Monitored seasonal fluctuations and monthly momentum along the **{target_date}** timeline.")
        except Exception:
            pass
            
        if not insights_lines:
            insights_lines.append(f"• **Executive Summary**: Visualized the monthly progression of **{target_metric}** aggregated by **{target_date}**.")
            insights_lines.append(f"• **Trend Trajectory**: Computed monthly {agg_func} values across active timeline records.")
            
        explanation = "\n".join(insights_lines)
        
        code = f"""import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('{dataset_path}')

# Clean numeric metric column if needed
if df['{target_metric}'].dtype == 'object':
    df['{target_metric}'] = pd.to_numeric(df['{target_metric}'].astype(str).str.replace(r'[₹\\$€£¥,\\s%]', '', regex=True), errors='coerce')

# Convert date column and drop invalid entries
df['{target_date}'] = pd.to_datetime(df['{target_date}'], errors='coerce')
df_clean = df.dropna(subset=['{target_date}', '{target_metric}']).copy()

# Extract Year-Month for monthly aggregation
df_clean['Year_Month'] = df_clean['{target_date}'].dt.to_period('M').astype(str)
trend_df = df_clean.groupby('Year_Month')['{target_metric}'].{agg_func}().reset_index()
trend_df = trend_df.sort_values('Year_Month')

plt.figure(figsize=(12, 6))
plt.plot(trend_df['Year_Month'], trend_df['{target_metric}'], marker='o', color='#0066CC', linewidth=2.5, markersize=6)
plt.fill_between(range(len(trend_df)), trend_df['{target_metric}'], color='#0066CC', alpha=0.1)

plt.title('Monthly {target_metric} Trend Over Time', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('Month ({target_date})', fontsize=12)
plt.ylabel('{"Total" if agg_func == "sum" else "Average"} {target_metric}', fontsize=12)
plt.xticks(range(len(trend_df)), trend_df['Year_Month'], rotation=45, ha='right')
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()
"""
        return code, explanation

    # 2. Check for correlation / scatter
    if any(w in query_lower for w in ["correlation", "relationship", "vs", "versus", "scatter", "compare cost", "compare salary"]):
        valid_metrics = [c for c in metric_cols if not is_id_column(c)]
        if len(valid_metrics) >= 2:
            x_col = valid_metrics[0]
            y_col = valid_metrics[1]
            hue_col = [c for c in cat_cols if not is_id_column(c) and c not in date_candidates]
            hue_col = hue_col[0] if hue_col else None
            
            matched_x = find_best_matching_column(valid_metrics, query_lower)
            if matched_x:
                x_col = matched_x
                remaining = [c for c in valid_metrics if c != x_col]
                if remaining:
                    y_col = find_best_matching_column(remaining, query_lower) or remaining[0]

            insights_lines = []
            try:
                temp_df = df.copy()
                for c in [x_col, y_col]:
                    temp_df[c] = clean_numeric_series(temp_df[c])
                sub_df = temp_df[[x_col, y_col]].dropna()
                corr_val = sub_df[x_col].corr(sub_df[y_col])
                
                corr_desc = "strong positive" if corr_val > 0.6 else ("moderate positive" if corr_val > 0.2 else ("strong negative" if corr_val < -0.6 else ("moderate negative" if corr_val < -0.2 else "weak/neutral")))
                
                insights_lines.append(f"• **Executive Summary**: Pearson correlation coefficient between **{x_col}** and **{y_col}** is **r = {corr_val:+.2f}** ({corr_desc} correlation across {len(sub_df):,} paired observations).")
                insights_lines.append(f"• **{x_col} Range**: Averages **{sub_df[x_col].mean():,.2f}** (ranging from **{sub_df[x_col].min():,.2f}** to **{sub_df[x_col].max():,.2f}**).")
                insights_lines.append(f"• **{y_col} Range**: Averages **{sub_df[y_col].mean():,.2f}** (ranging from **{sub_df[y_col].min():,.2f}** to **{sub_df[y_col].max():,.2f}**).")
                if hue_col:
                    insights_lines.append(f"• **Subgroup Clustering**: Data points are segmented by **{hue_col}** to highlight cluster patterns.")
                insights_lines.append(f"• **Strategic Observation**: {'Strong interdependence suggests changes in ' + x_col + ' directly influence ' + y_col if abs(corr_val) > 0.5 else 'Low direct correlation indicates independent distribution drivers between variables.'}")
            except Exception:
                pass
                
            if not insights_lines:
                insights_lines = [
                    f"• **Executive Summary**: Analyzed the relationship and co-variance of **{y_col}** relative to **{x_col}**.",
                    f"• **Scatter Findings**: Points highlight clustering density and potential outlier records across {len(df)} entries."
                ]
            explanation = "\n".join(insights_lines)

            hue_code = f", hue='{hue_col}'" if hue_col else ""
            code = f"""import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('{dataset_path}')

# Clean numeric columns if needed
for c in ['{x_col}', '{y_col}']:
    if df[c].dtype == 'object':
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[₹\\$€£¥,\\s%]', '', regex=True), errors='coerce')

plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x='{x_col}', y='{y_col}'{hue_code}, s=100, alpha=0.85)
plt.title('Relationship between {x_col} and {y_col}', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('{x_col}', fontsize=12)
plt.ylabel('{y_col}', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()
"""
            return code, explanation

    # 3. Check for distribution / histogram / boxplot
    if any(w in query_lower for w in ["distribution", "histogram", "spread", "box", "density", "range"]):
        valid_metrics = [c for c in metric_cols if not is_id_column(c)] or metric_cols
        target_num = find_best_matching_column(valid_metrics, query_lower, ["profit", "sales", "revenue", "cost", "income", "amount", "total", "margin", "quantity", "price"]) or (valid_metrics[0] if valid_metrics else cols[0])
        group_col = find_best_matching_column([c for c in cat_cols if not is_id_column(c) and c not in date_candidates], query_lower)
        
        insights_lines = []
        try:
            temp_df = df.copy()
            temp_df[target_num] = clean_numeric_series(temp_df[target_num])
            clean_s = temp_df[target_num].dropna()
            
            mean_v = clean_s.mean()
            median_v = clean_s.median()
            std_v = clean_s.std()
            q25 = clean_s.quantile(0.25)
            q75 = clean_s.quantile(0.75)
            min_v = clean_s.min()
            max_v = clean_s.max()
            
            insights_lines.append(f"• **Executive Summary**: **{target_num}** exhibits a median of **{median_v:,.2f}** and mean of **{mean_v:,.2f}** (std dev: **{std_v:,.2f}** across {len(clean_s):,} entries).")
            insights_lines.append(f"• **Interquartile Concentration (IQR)**: 50% of records are concentrated between **{q25:,.2f}** (25th percentile) and **{q75:,.2f}** (75th percentile).")
            insights_lines.append(f"• **Extreme Boundaries**: Values span from a minimum of **{min_v:,.2f}** to a peak maximum of **{max_v:,.2f}**.")
            
            if group_col:
                top_group = temp_df.groupby(group_col)[target_num].median().idxmax()
                top_grp_val = temp_df.groupby(group_col)[target_num].median().max()
                insights_lines.append(f"• **Leading Segment**: Category **{top_group}** demonstrates the highest median {target_num} at **{top_grp_val:,.2f}**.")
                
            skew_desc = "positively skewed (right-tailed)" if mean_v > median_v * 1.1 else ("negatively skewed (left-tailed)" if mean_v < median_v * 0.9 else "symmetrically distributed")
            insights_lines.append(f"• **Strategic Observation**: The distribution is {skew_desc}, indicating {'a concentration of high-value outliers pulling up the mean.' if mean_v > median_v else 'balanced distribution across the population.'}")
        except Exception:
            pass

        if group_col:
            if not insights_lines:
                insights_lines = [
                    f"• **Executive Summary**: Examined statistical variations of **{target_num}** across **{group_col}**.",
                    f"• **Group Spread**: Boxplot visualizes interquartile spreads and median variance across categories."
                ]
            explanation = "\n".join(insights_lines)
            code = f"""import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('{dataset_path}')

if df['{target_num}'].dtype == 'object':
    df['{target_num}'] = pd.to_numeric(df['{target_num}'].astype(str).str.replace(r'[₹\\$€£¥,\\s%]', '', regex=True), errors='coerce')

plt.figure(figsize=(11, 6))
sns.boxplot(data=df, x='{group_col}', y='{target_num}', palette='crest')
plt.title('Distribution of {target_num} by {group_col}', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('{group_col}', fontsize=12)
plt.ylabel('{target_num}', fontsize=12)
plt.xticks(rotation=35, ha='right')
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()
"""
        else:
            if not insights_lines:
                insights_lines = [
                    f"• **Executive Summary**: Analyzed statistical density and concentration intervals for **{target_num}**.",
                    f"• **Distribution Shape**: Evaluated histogram frequency and skewness across the dataset sample."
                ]
            explanation = "\n".join(insights_lines)
            code = f"""import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('{dataset_path}')

if df['{target_num}'].dtype == 'object':
    df['{target_num}'] = pd.to_numeric(df['{target_num}'].astype(str).str.replace(r'[₹\\$€£¥,\\s%]', '', regex=True), errors='coerce')

plt.figure(figsize=(10, 5))
sns.histplot(df['{target_num}'].dropna(), kde=True, color='#0066CC', bins=15)
plt.title('Distribution of {target_num}', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('{target_num}', fontsize=12)
plt.ylabel('Frequency', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()
"""
        return code, explanation

    # 4. Categorical breakdown / Bar chart (Fallback)
    clean_cat_cols = [c for c in cat_cols if not is_id_column(c) and c not in date_candidates]
    if not clean_cat_cols:
        clean_cat_cols = [c for c in cat_cols if not is_id_column(c)] or [c for c in cols if not is_id_column(c)] or cols
        
    valid_metric_cols = [c for c in metric_cols if not is_id_column(c)]
    target_cat = find_best_matching_column(clean_cat_cols, query_lower) or clean_cat_cols[0]
    target_num = find_best_matching_column(valid_metric_cols, query_lower, ["profit", "sales", "revenue", "cost", "income", "amount", "total", "margin", "quantity", "price"]) if valid_metric_cols else None

    if target_num:
        agg_name = "Total" if any(w in query_lower for w in ["total", "sum", "sales", "revenue", "cost", "profit", "amount", "spend", "income"]) else "Average"
        agg_code = "sum()" if agg_name == "Total" else "mean()"
        agg_type = 'sum' if agg_name == 'Total' else 'mean'
        
        # Calculate real data-driven statistical breakdown
        insights_lines = []
        try:
            temp_df = df.copy()
            temp_df[target_num] = clean_numeric_series(temp_df[target_num])
            temp_clean = temp_df.dropna(subset=[target_cat, target_num])
            
            cat_agg = temp_clean.groupby(target_cat)[target_num].agg(agg_type).reset_index()
            cat_agg = cat_agg.sort_values(by=target_num, ascending=False)
            
            if len(cat_agg) > 0:
                total_sum = cat_agg[target_num].sum()
                mean_val = cat_agg[target_num].mean()
                top_row = cat_agg.iloc[0]
                top_pct = (top_row[target_num] / total_sum * 100) if total_sum > 0 else 0
                
                # 1. Executive Summary
                insights_lines.append(
                    f"• **Executive Summary**: Total aggregated **{target_num}** across all {len(cat_agg)} **{target_cat}** segments is **{total_sum:,.2f}** (segment average: **{mean_val:,.2f}**)."
                )
                
                # 2. Top Segment & Share
                insights_lines.append(
                    f"• **Top Performer**: **{top_row[target_cat]}** leads all segments with {agg_name.lower()} {target_num} of **{top_row[target_num]:,.2f}**, capturing **{top_pct:.1f}%** of the entire distribution."
                )
                
                # 3. Runner-up & Performance Gap
                if len(cat_agg) > 1:
                    second_row = cat_agg.iloc[1]
                    second_pct = (second_row[target_num] / total_sum * 100) if total_sum > 0 else 0
                    gap_pct = ((top_row[target_num] - second_row[target_num]) / second_row[target_num] * 100) if second_row[target_num] != 0 else 0
                    insights_lines.append(
                        f"• **Runner-up Comparison**: **{second_row[target_cat]}** ranks second with **{second_row[target_num]:,.2f}** ({second_pct:.1f}% share), trailing the leader by **{abs(gap_pct):.1f}%**."
                    )
                
                # 4. Lowest Segment & Disparity
                lowest_row = cat_agg.iloc[-1]
                lowest_pct = (lowest_row[target_num] / total_sum * 100) if total_sum > 0 else 0
                if lowest_row[target_num] > 0 and top_row[target_num] > 0:
                    multiplier = top_row[target_num] / lowest_row[target_num]
                    disparity_str = f" (**{multiplier:.1f}x** lower than the top performer)"
                else:
                    disparity_str = ""
                insights_lines.append(
                    f"• **Lowest Segment**: **{lowest_row[target_cat]}** recorded the lowest contribution at **{lowest_row[target_num]:,.2f}** ({lowest_pct:.1f}% share){disparity_str}."
                )
                
                # 5. Pareto / Concentration & Actionable Finding
                if len(cat_agg) >= 3:
                    top2_sum = cat_agg.iloc[:2][target_num].sum()
                    top2_pct = (top2_sum / total_sum * 100) if total_sum > 0 else 0
                    insights_lines.append(
                        f"• **Segment Concentration**: The top 2 segments (**{top_row[target_cat]}** and **{cat_agg.iloc[1][target_cat]}**) generate **{top2_pct:.1f}%** of the total {target_num}, indicating high category concentration."
                    )
                elif len(cat_agg) == 2:
                    insights_lines.append(
                        f"• **Comparative Dynamic**: Segment **{top_row[target_cat]}** accounts for **{top_pct:.1f}%** vs **{100-top_pct:.1f}%** for **{cat_agg.iloc[1][target_cat]}**."
                    )
        except Exception:
            pass

        if not insights_lines:
            insights_lines = [
                f"• **Executive Summary**: Evaluated {agg_name.lower()} **{target_num}** segmented by **{target_cat}** across {len(df)} total records.",
                f"• **Distribution Drivers**: Ranked categories in descending order to identify leading and lagging performance segments."
            ]
        explanation = "\n".join(insights_lines)
        
        code = f"""import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('{dataset_path}')

# Clean numeric column if needed
if df['{target_num}'].dtype == 'object':
    df['{target_num}'] = pd.to_numeric(df['{target_num}'].astype(str).str.replace(r'[₹\\$€£¥,\\s%]', '', regex=True), errors='coerce')

# Aggregate data by category
agg_df = df.groupby('{target_cat}')['{target_num}'].{agg_code}.reset_index().sort_values(by='{target_num}', ascending=False).head(15)

plt.figure(figsize=(11, 6))
barplot = sns.barplot(data=agg_df, x='{target_cat}', y='{target_num}', palette='viridis')
plt.title('{agg_name} {target_num} by {target_cat}', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('{target_cat}', fontsize=12)
plt.ylabel('{agg_name} {target_num}', fontsize=12)
plt.xticks(rotation=30, ha='right')

for p in barplot.patches:
    barplot.annotate(f'{{p.get_height():,.1f}}', 
                     (p.get_x() + p.get_width() / 2., p.get_height()),
                     ha='center', va='bottom', fontsize=10, xytext=(0, 4),
                     textcoords='offset points')

plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()
"""
    else:
        insights_lines = []
        try:
            v_counts = df[target_cat].value_counts()
            total_records = len(df)
            if len(v_counts) > 0:
                top_c = v_counts.index[0]
                top_cnt = v_counts.iloc[0]
                top_pct = (top_cnt / total_records * 100) if total_records > 0 else 0
                insights_lines.append(f"• **Executive Summary**: **{top_c}** has highest volume with **{top_cnt:,} records ({top_pct:.1f}%)** out of {total_records:,} total entries.")
                
                if len(v_counts) > 1:
                    second_c = v_counts.index[1]
                    second_cnt = v_counts.iloc[1]
                    second_pct = (second_cnt / total_records * 100) if total_records > 0 else 0
                    insights_lines.append(f"• **Runner-up**: **{second_c}** accounts for **{second_cnt:,} records ({second_pct:.1f}%)**.")
                    
                lowest_c = v_counts.index[-1]
                lowest_cnt = v_counts.iloc[-1]
                insights_lines.append(f"• **Smallest Segment**: **{lowest_c}** represents **{lowest_cnt:,} records**.")
                insights_lines.append(f"• **Total Volume**: Total dataset size is **{total_records:,} records** partitioned across **{len(v_counts)} distinct {target_cat}** categories.")
        except Exception:
            pass

        if not insights_lines:
            insights_lines = [
                f"• **Executive Summary**: Counted total occurrences across primary **{target_cat}** categories.",
                f"• **Segment Representation**: Visualized top category frequencies to highlight volume distribution."
            ]
        explanation = "\n".join(insights_lines)
        
        code = f"""import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('{dataset_path}')

counts = df['{target_cat}'].value_counts().reset_index().head(15)
counts.columns = ['{target_cat}', 'Count']

plt.figure(figsize=(10, 5))
barplot = sns.barplot(data=counts, x='{target_cat}', y='Count', palette='mako')
plt.title('Distribution of Records by {target_cat}', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('{target_cat}', fontsize=12)
plt.ylabel('Count', fontsize=12)
plt.xticks(rotation=30, ha='right')

for p in barplot.patches:
    barplot.annotate(f'{{int(p.get_height()):,}}', 
                     (p.get_x() + p.get_width() / 2., p.get_height()),
                     ha='center', va='bottom', fontsize=10, xytext=(0, 4),
                     textcoords='offset points')

plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()
"""
        
    return code, explanation

from chart_mcp import (
    GEMINI_CHART_TOOLS,
    TOGETHER_CHART_TOOLS,
    handle_chart_mcp_tool_call,
    execute_create_chart_from_dataset
)

def run_agent_analysis(
    query: str,
    df: pd.DataFrame,
    dataset_name: str = "dataset.csv",
    gemini_api_key: Optional[str] = None,
    together_api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Main entry point for running data visualization AI agent.
    Utilizes declarative Custom MCP Tools for structured chart rendering (zero sandbox overhead).
    """
    dataset_path = f"./{dataset_name}"
    
    python_code = ""
    llm_explanation = ""
    images = []
    stdout = ""
    stderr = ""
    model_used = "MCP Visualization Engine"
    chart_spec = None
    
    # Check for Gemini API key (passed directly or from env)
    active_gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
    active_together_key = together_api_key or os.getenv("TOGETHER_API_KEY", "")
    
    # Pre-compute rich dataset statistics and aggregations for the prompt
    rich_stats_summary = compute_rich_data_summary(df, query)
    
    # Prepare schema & sample prompt context
    buffer = io.StringIO()
    df.info(buf=buffer)
    schema_info = buffer.getvalue()
    try:
        sample_rows = df.head(3).to_markdown()
    except Exception:
        sample_rows = df.head(3).to_string()
        
    system_prompt = f"""You are an elite Business Intelligence Analyst and Data Visualization Expert.
You have access to a dataset at '{dataset_path}' with the following schema:
{schema_info}

Sample Data:
{sample_rows}

PRE-COMPUTED DATASET SUMMARY & METRIC AGGREGATIONS:
{rich_stats_summary}

CHART CREATION VIA MCP TOOLS:
You have access to custom MCP chart tools:
1. `create_chart_from_dataset`: Recommended tool! Specify `chart_type` ('bar', 'line', 'pie', 'doughnut', 'scatter'), `title`, `x_column`, `y_column`, and `aggregation` ('count', 'sum', 'mean', 'min', 'max').
2. `render_chart`: Alternatively provide explicit `labels` and `datasets` data arrays.

CRITICAL RULES FOR AI INSIGHTS & EXPLANATIONS:
1. VALUABLE & DATA-DRIVEN INSIGHTS: Output concrete statistical facts, exact numbers, currency amounts, percentages, segment names, and business takeaways from the pre-computed summary.
2. EXECUTIVE STRUCTURE: Output strictly 3 to 5 scannable markdown bullet points starting with:
   • **Executive Summary**: [Direct numerical answer with total/mean metric value and key conclusion]
   • **Top Performer & Share**: [Top category/segment with exact numbers and % share of total]
   • **Runner-up & Disparity**: [Second and lowest segments with exact values and comparison gap]
   • **Concentration & Distribution**: [Concentration ratio of top segments or spread/variance]
   • **Strategic Recommendation**: [Data-backed actionable conclusion for business stakeholders]
3. NO ID COLUMNS AS METRICS: NEVER calculate, average, or plot ID columns, Index keys, or Postal codes as numeric metrics.
"""

    # 1. Try Google Gemini with MCP Tools
    if active_gemini_key and (model_name.startswith("gemini") or not active_together_key):
        try:
            target_model = model_name if model_name.startswith("gemini") else "gemini-2.0-flash"
            raw_text, tool_call = call_gemini_llm(
                api_key=active_gemini_key.strip(),
                model_name=target_model,
                system_prompt=system_prompt,
                query=query,
                tools=GEMINI_CHART_TOOLS
            )
            
            if tool_call and tool_call.get("name"):
                chart_spec = handle_chart_mcp_tool_call(tool_call["name"], tool_call.get("args", {}), df)
                
            llm_explanation = clean_explanation_text(raw_text)
            model_used = f"Google {target_model} (MCP)"
        except Exception as gemini_err:
            stderr = f"Google Gemini API error: {str(gemini_err)}"

    # 2. Try Together AI with MCP Tools if specified or fallback
    if not chart_spec and active_together_key:
        try:
            from together import Together
            target_model = model_name if not model_name.startswith("gemini") else "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
            client = Together(api_key=active_together_key.strip())
            response = client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                tools=TOGETHER_CHART_TOOLS,
                tool_choice="auto"
            )
            choice = response.choices[0]
            if choice.message.tool_calls:
                tc = choice.message.tool_calls[0]
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments or "{}")
                chart_spec = handle_chart_mcp_tool_call(fn_name, fn_args, df)
            
            raw_response = choice.message.content or ""
            llm_explanation = clean_explanation_text(raw_response)
            model_used = f"{target_model} (MCP)"
        except Exception as tog_err:
            stderr = f"Together AI error: {str(tog_err)}"

    # 3. Fallback to Local Heuristic Chart MCP Engine
    if not chart_spec:
        fallback_code, fallback_exp = generate_heuristic_analysis(query, df, dataset_path)
        if not llm_explanation:
            llm_explanation = clean_explanation_text(fallback_exp)
        
        # Build structured chartSpec heuristically
        metric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if not is_id_column(c)]
        cat_cols = [c for c in df.select_dtypes(include=['object', 'category', 'string']).columns if not is_id_column(c)]
        
        x_target = find_best_matching_column(cat_cols, query.lower()) or (cat_cols[0] if cat_cols else df.columns[0])
        y_target = find_best_matching_column(metric_cols, query.lower(), ["profit", "sales", "revenue", "amount", "total", "margin", "quantity"]) if metric_cols else None
        
        agg_choice = "sum" if any(w in query.lower() for w in ["total", "sum", "sales", "revenue", "amount"]) else ("mean" if any(w in query.lower() for w in ["avg", "average", "mean"]) else "count")
        
        chart_type = "line" if any(w in query.lower() for w in ["trend", "month", "time", "date"]) else ("pie" if any(w in query.lower() for w in ["pie", "proportion", "share"]) else "bar")
        
        chart_spec = execute_create_chart_from_dataset(df, {
            "chart_type": chart_type,
            "title": f"{agg_choice.capitalize()} of {y_target or 'Records'} by {x_target}",
            "x_column": x_target,
            "y_column": y_target,
            "aggregation": agg_choice if y_target else "count",
            "top_n": 10
        })
        model_used = "MCP Visualization Engine (Local)"

    # Ensure explanation is filled
    if not llm_explanation or len(llm_explanation.strip()) < 30:
        _, fallback_exp = generate_heuristic_analysis(query, df, dataset_path)
        llm_explanation = clean_explanation_text(fallback_exp)

    return {
        "query": query,
        "explanation": clean_explanation_text(llm_explanation),
        "code": python_code,
        "chartSpec": chart_spec,
        "images": images,
        "stdout": stdout,
        "stderr": stderr,
        "modelUsed": model_used
    }
