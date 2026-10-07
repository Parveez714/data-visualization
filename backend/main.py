import os
import sys
import io
import uuid
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from agent import run_agent_analysis, generate_smart_prompt_suggestions

app = FastAPI(
    title="AI Data Visualization & Analytics API",
    description="Backend for AI Data Visualization & Exploration Agent powered by Google Gemini",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active datasets uploaded by users
datasets_store: Dict[str, Dict[str, Any]] = {}

# Request Models
class AnalyzeRequest(BaseModel):
    datasetId: str
    query: str
    geminiApiKey: Optional[str] = None
    togetherApiKey: Optional[str] = None
    modelName: Optional[str] = "gemini-3.6-flash"

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "AI Data Visualization API",
        "datasetsAvailable": list(datasets_store.keys())
    }

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Backend service is healthy"}

@app.get("/api/models")
def get_available_models():
    return {
        "models": [
            {"id": "gemini-3.6-flash", "name": "Google Gemini 3.6 Flash", "tag": "Recommended", "provider": "Google Gemini"},
            {"id": "gemini-3.7-flash", "name": "Google Gemini 3.7 Flash", "tag": "Ultra Fast", "provider": "Google Gemini"},
            {"id": "gemini-2.5-pro", "name": "Google Gemini 2.5 Pro", "tag": "Deep Reasoning", "provider": "Google Gemini"},
            {"id": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "name": "Meta-Llama 3.1 405B", "tag": "Open Source Titan", "provider": "Together AI"},
            {"id": "deepseek-ai/DeepSeek-V3", "name": "DeepSeek V3", "tag": "High Performance", "provider": "Together AI"}
        ]
    }

@app.get("/api/datasets")
def list_datasets():
    results = []
    for d_id, data in datasets_store.items():
        results.append({
            "id": d_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "rowCount": data["rowCount"],
            "columnCount": data["columnCount"],
            "columns": data["columns"],
            "suggestions": data.get("suggestions", [])
        })
    return {"datasets": results}

@app.get("/api/dataset/{dataset_id}")
def get_dataset_details(dataset_id: str, preview_limit: int = 50):
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    data = datasets_store[dataset_id]
    df: pd.DataFrame = data["df"]
    
    # Statistical Summary
    desc_df = df.describe(include="all").fillna("").to_dict()
    
    # Column types
    col_types = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
    
    # Sample records with safe conversion for dates/NaNs
    preview_df = df.head(preview_limit).copy()
    for col in preview_df.select_dtypes(include=['datetime64', 'datetime']).columns:
        preview_df[col] = preview_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    preview_df = preview_df.fillna("")
    preview = preview_df.to_dict(orient="records")
    
    return {
        "id": dataset_id,
        "name": data["name"],
        "description": data.get("description", ""),
        "rowCount": len(df),
        "columnCount": len(df.columns),
        "columns": [str(c) for c in df.columns],
        "columnTypes": col_types,
        "preview": preview,
        "summary": desc_df,
        "suggestions": data.get("suggestions", [])
    }

class SuggestionsRequest(BaseModel):
    geminiApiKey: Optional[str] = None
    togetherApiKey: Optional[str] = None
    modelName: Optional[str] = "gemini-2.5-flash"

@app.get("/api/dataset/{dataset_id}/suggestions")
def get_dataset_suggestions(
    dataset_id: str,
    geminiApiKey: Optional[str] = Query(None),
    modelName: Optional[str] = Query("gemini-2.5-flash")
):
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found")
    data = datasets_store[dataset_id]
    df: pd.DataFrame = data["df"]
    suggestions = generate_smart_prompt_suggestions(
        df=df,
        dataset_name=data["name"],
        gemini_api_key=geminiApiKey,
        model_name=modelName
    )
    datasets_store[dataset_id]["suggestions"] = suggestions
    return {"datasetId": dataset_id, "suggestions": suggestions}

@app.post("/api/dataset/{dataset_id}/suggestions")
def post_dataset_suggestions(dataset_id: str, req: SuggestionsRequest):
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found")
    data = datasets_store[dataset_id]
    df: pd.DataFrame = data["df"]
    suggestions = generate_smart_prompt_suggestions(
        df=df,
        dataset_name=data["name"],
        gemini_api_key=req.geminiApiKey,
        together_api_key=req.togetherApiKey,
        model_name=req.modelName
    )
    datasets_store[dataset_id]["suggestions"] = suggestions
    return {"datasetId": dataset_id, "suggestions": suggestions}

@app.post("/api/upload")
async def upload_dataset_file(
    file: UploadFile = File(...),
    geminiApiKey: Optional[str] = Form(None),
    togetherApiKey: Optional[str] = Form(None),
    modelName: Optional[str] = Form(None)
):
    try:
        content = await file.read()
        filename = file.filename or "uploaded_file"
        lower_name = filename.lower()
        
        if lower_name.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb')):
            try:
                df = pd.read_excel(io.BytesIO(content))
            except Exception as excel_err:
                raise ValueError(f"Failed to read Excel file: {str(excel_err)}")
        elif lower_name.endswith(('.csv', '.txt', '.tsv')):
            sep = '\t' if lower_name.endswith('.tsv') else ','
            try:
                df = pd.read_csv(io.BytesIO(content), sep=sep)
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(content), sep=sep, encoding='latin1')
        else:
            # Fallback: try CSV first, then Excel
            try:
                df = pd.read_csv(io.BytesIO(content))
            except Exception:
                try:
                    df = pd.read_excel(io.BytesIO(content))
                except Exception as parse_err:
                    raise ValueError(f"Unsupported format. Please upload an Excel (.xlsx, .xls) or CSV (.csv) file.")
        
        # Clean dataframe column names to strings
        df.columns = [str(c).strip() for c in df.columns]
        
        dataset_id = f"custom_{uuid.uuid4().hex[:8]}"
        file_type = "Excel" if lower_name.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb')) else "CSV"
        
        # Generate initial smart prompt suggestions based on uploaded data columns
        initial_suggestions = generate_smart_prompt_suggestions(
            df=df,
            dataset_name=filename,
            gemini_api_key=geminiApiKey,
            together_api_key=togetherApiKey,
            model_name=modelName or "gemini-2.5-flash"
        )

        datasets_store[dataset_id] = {
            "id": dataset_id,
            "name": filename,
            "description": f"Uploaded {file_type} dataset with {len(df)} rows and {len(df.columns)} columns.",
            "df": df,
            "rowCount": len(df),
            "columnCount": len(df.columns),
            "columns": df.columns.tolist(),
            "suggestions": initial_suggestions
        }
        
        return {
            "success": True,
            "datasetId": dataset_id,
            "name": filename,
            "rowCount": len(df),
            "columnCount": len(df.columns),
            "columns": df.columns.tolist(),
            "suggestions": initial_suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded file: {str(e)}")

@app.delete("/api/dataset/{dataset_id}")
def delete_dataset(dataset_id: str):
    if dataset_id in datasets_store:
        del datasets_store[dataset_id]
        return {"success": True, "message": f"Dataset {dataset_id} deleted."}
    raise HTTPException(status_code=404, detail="Dataset not found")

@app.post("/api/analyze")
def analyze_data(req: AnalyzeRequest):
    if req.datasetId not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload a dataset first.")
    
    dataset_info = datasets_store[req.datasetId]
    df = dataset_info["df"]
    dataset_filename = dataset_info["name"]
    
    result = run_agent_analysis(
        query=req.query,
        df=df,
        dataset_name=dataset_filename,
        gemini_api_key=req.geminiApiKey,
        together_api_key=req.togetherApiKey,
        model_name=req.modelName or "gemini-2.5-flash"
    )
    
    return {
        "success": True,
        "datasetId": req.datasetId,
        "query": req.query,
        "explanation": result["explanation"],
        "chartSpec": result.get("chartSpec"),
        "code": result["code"],
        "images": result["images"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "modelUsed": result["modelUsed"]
    }

@app.get("/api/mcp/tools")
def get_mcp_tools():
    from chart_mcp import GEMINI_CHART_TOOLS, TOGETHER_CHART_TOOLS
    return {
        "geminiTools": GEMINI_CHART_TOOLS,
        "togetherTools": TOGETHER_CHART_TOOLS
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8005"))
    uvicorn.run(app, host="127.0.0.1", port=port)
