import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

# Standard MCP / JSON Schema tool definitions for Gemini and OpenAI/Together format

GEMINI_CHART_TOOLS = [
    {
        "name": "create_chart_from_dataset",
        "description": "Aggregate data from the current dataset and produce a structured chart specification (bar, line, pie, doughnut, scatter).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "chart_type": {
                    "type": "STRING",
                    "description": "The type of chart to display: 'bar', 'line', 'pie', 'doughnut', or 'scatter'."
                },
                "title": {
                    "type": "STRING",
                    "description": "Informative title for the chart."
                },
                "x_column": {
                    "type": "STRING",
                    "description": "Column name from the dataset to use for categories / X-axis."
                },
                "y_column": {
                    "type": "STRING",
                    "description": "Optional numeric column name from the dataset to aggregate for Y-axis (leave empty for row count)."
                },
                "aggregation": {
                    "type": "STRING",
                    "description": "Aggregation function to apply on y_column: 'count', 'sum', 'mean', 'min', 'max'."
                },
                "top_n": {
                    "type": "INTEGER",
                    "description": "Maximum number of categories to display (default 10, max 25)."
                },
                "sort_desc": {
                    "type": "BOOLEAN",
                    "description": "Whether to sort categories by metric in descending order."
                }
            },
            "required": ["chart_type", "title", "x_column"]
        }
    },
    {
        "name": "render_chart",
        "description": "Directly render a chart given custom computed labels and data points.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "chart_type": {
                    "type": "STRING",
                    "description": "Type of chart: 'bar', 'line', 'pie', 'doughnut', 'scatter'."
                },
                "title": {
                    "type": "STRING",
                    "description": "Title of the chart."
                },
                "labels": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of category labels for the X-axis."
                },
                "datasets": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "label": {"type": "STRING"},
                            "data": {"type": "ARRAY", "items": {"type": "NUMBER"}}
                        },
                        "required": ["label", "data"]
                    },
                    "description": "List of dataset series with numeric data arrays matching labels."
                },
                "xAxisLabel": {"type": "STRING"},
                "yAxisLabel": {"type": "STRING"}
            },
            "required": ["chart_type", "title", "labels", "datasets"]
        }
    }
]

TOGETHER_CHART_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_chart_from_dataset",
            "description": "Aggregate data from the current dataset and produce a structured chart specification (bar, line, pie, doughnut, scatter).",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "doughnut", "scatter"],
                        "description": "The type of chart to display."
                    },
                    "title": {"type": "string", "description": "Informative title for the chart."},
                    "x_column": {"type": "string", "description": "Column name for X-axis categories."},
                    "y_column": {"type": "string", "description": "Optional numeric column to aggregate for Y-axis."},
                    "aggregation": {
                        "type": "string",
                        "enum": ["count", "sum", "mean", "min", "max"],
                        "description": "Aggregation function."
                    },
                    "top_n": {"type": "integer", "description": "Top N categories (e.g. 10)."},
                    "sort_desc": {"type": "boolean", "description": "Sort descending by value."}
                },
                "required": ["chart_type", "title", "x_column"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "render_chart",
            "description": "Directly render a chart given custom computed labels and data points.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "doughnut", "scatter"],
                        "description": "Type of chart."
                    },
                    "title": {"type": "string", "description": "Title of the chart."},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Labels for X-axis."},
                    "datasets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "data": {"type": "array", "items": {"type": "number"}}
                            },
                            "required": ["label", "data"]
                        }
                    },
                    "xAxisLabel": {"type": "string"},
                    "yAxisLabel": {"type": "string"}
                },
                "required": ["chart_type", "title", "labels", "datasets"]
            }
        }
    }
]

# Color palette for charts
THEME_PALETTE = [
    "#18181B", "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#14B8A6", "#6366F1", "#84CC16"
]

def execute_create_chart_from_dataset(df: pd.DataFrame, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes in-memory aggregation of DataFrame based on tool parameters
    and produces a standardized Chart.js compliant chart specification.
    """
    chart_type = args.get("chart_type", "bar").lower()
    title = args.get("title", "Dataset Analysis")
    x_col = args.get("x_column")
    y_col = args.get("y_column")
    agg = args.get("aggregation", "count").lower()
    top_n = min(int(args.get("top_n", 10)), 30)
    sort_desc = args.get("sort_desc", True)

    if x_col not in df.columns:
        # Find closest match or fallback to first column
        matched_x = [c for c in df.columns if str(c).lower() == str(x_col).lower()]
        x_col = matched_x[0] if matched_x else df.columns[0]

    if y_col and y_col not in df.columns:
        matched_y = [c for c in df.columns if str(c).lower() == str(y_col).lower()]
        if matched_y:
            y_col = matched_y[0]

    df_clean = df.copy()

    # Convert y_col to numeric if specified
    if y_col and y_col in df_clean.columns and agg != "count":
        df_clean[y_col] = pd.to_numeric(df_clean[y_col], errors="coerce")
        # Check if y_col is completely empty/NaN
        if df_clean[y_col].dropna().empty:
            # Check if we can compute sales/revenue from Quantity and Unit Price
            cols_norm = {str(c).lower().replace(' ', '').replace('_', ''): c for c in df_clean.columns}
            y_lower = str(y_col).lower()
            if any(term in y_lower for term in ['sales', 'revenue', 'amount', 'total']) and \
               any(k in cols_norm for k in ['quantity', 'qty']) and \
               any(k in cols_norm for k in ['unitprice', 'price']):
                qty_col = cols_norm.get('quantity') or cols_norm.get('qty')
                price_col = cols_norm.get('unitprice') or cols_norm.get('price')
                qty_s = pd.to_numeric(df_clean[qty_col], errors='coerce').fillna(0)
                price_s = pd.to_numeric(df_clean[price_col], errors='coerce').fillna(0)
                disc_keys = [c for c in cols_norm if 'discount' in c]
                if disc_keys:
                    disc_s = pd.to_numeric(df_clean[cols_norm[disc_keys[0]]], errors='coerce').fillna(0)
                    df_clean[y_col] = qty_s * price_s * (1 - disc_s)
                else:
                    df_clean[y_col] = qty_s * price_s

        # If still empty after calculation attempt, fallback to an available numeric column or row count
        if df_clean[y_col].dropna().empty:
            other_nums = [c for c in df_clean.columns if c != y_col and pd.to_numeric(df_clean[c], errors="coerce").dropna().count() > 0]
            if other_nums:
                y_col = other_nums[0]
                df_clean[y_col] = pd.to_numeric(df_clean[y_col], errors="coerce")
            else:
                y_col = None

    # Determine metric and aggregation
    if not y_col or y_col not in df_clean.columns or agg == "count":
        # Group by x_col and count
        summary = df_clean.groupby(x_col).size().reset_index(name="Count")
        metric_col = "Count"
        agg_label = f"Count of records by {x_col}"
    else:
        # Numeric aggregation
        df_clean = df_clean.dropna(subset=[x_col, y_col])
        if agg == "sum":
            summary = df_clean.groupby(x_col)[y_col].sum().reset_index()
            agg_label = f"Total {y_col}"
        elif agg in ("mean", "avg"):
            summary = df_clean.groupby(x_col)[y_col].mean().reset_index()
            agg_label = f"Average {y_col}"
        elif agg == "min":
            summary = df_clean.groupby(x_col)[y_col].min().reset_index()
            agg_label = f"Min {y_col}"
        elif agg == "max":
            summary = df_clean.groupby(x_col)[y_col].max().reset_index()
            agg_label = f"Max {y_col}"
        else:
            summary = df_clean.groupby(x_col)[y_col].sum().reset_index()
            agg_label = f"Sum of {y_col}"
        metric_col = y_col

    # Sort
    if metric_col in summary.columns:
        summary = summary.sort_values(by=metric_col, ascending=not sort_desc)

    # Limit top_n
    summary = summary.head(top_n)

    labels = [str(val) for val in summary[x_col].tolist()]
    values = [float(round(val, 2)) if isinstance(val, (int, float, np.number)) and not np.isnan(val) else 0.0 
              for val in summary[metric_col].tolist()]

    # Format dataset colors
    if chart_type in ["pie", "doughnut"]:
        background_colors = [THEME_PALETTE[i % len(THEME_PALETTE)] for i in range(len(labels))]
    else:
        background_colors = THEME_PALETTE[0]

    chart_spec = {
        "chart_type": chart_type,
        "title": title,
        "labels": labels,
        "datasets": [
            {
                "label": agg_label,
                "data": values,
                "backgroundColor": background_colors,
                "borderColor": THEME_PALETTE[0] if chart_type == "line" else None,
                "fill": chart_type != "line"
            }
        ],
        "xAxisLabel": str(x_col),
        "yAxisLabel": agg_label
    }

    return chart_spec

def execute_render_chart(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Directly validates and returns structured chart spec from explicit labels and datasets.
    """
    chart_type = args.get("chart_type", "bar").lower()
    title = args.get("title", "Chart")
    labels = [str(l) for l in args.get("labels", [])]
    datasets_raw = args.get("datasets", [])

    datasets = []
    for idx, ds in enumerate(datasets_raw):
        color = THEME_PALETTE[idx % len(THEME_PALETTE)]
        if chart_type in ["pie", "doughnut"]:
            bg_color = [THEME_PALETTE[i % len(THEME_PALETTE)] for i in range(len(labels))]
        else:
            bg_color = color

        datasets.append({
            "label": ds.get("label", f"Series {idx + 1}"),
            "data": [float(v) if isinstance(v, (int, float)) else 0.0 for v in ds.get("data", [])],
            "backgroundColor": bg_color,
            "borderColor": color if chart_type == "line" else None,
            "fill": chart_type != "line"
        })

    return {
        "chart_type": chart_type,
        "title": title,
        "labels": labels,
        "datasets": datasets,
        "xAxisLabel": args.get("xAxisLabel", ""),
        "yAxisLabel": args.get("yAxisLabel", "")
    }

def handle_chart_mcp_tool_call(tool_name: str, tool_args: Dict[str, Any], df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
    """
    Dispatcher for chart MCP tools.
    """
    if tool_name == "create_chart_from_dataset":
        if df is None:
            raise ValueError("DataFrame is required for create_chart_from_dataset")
        return execute_create_chart_from_dataset(df, tool_args)
    elif tool_name == "render_chart":
        return execute_render_chart(tool_args)
    return None
