"""
PDF to Spreadsheet - REST API
==============================

FastAPI-based REST API for PDF processing.
"""

import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.pipeline import Pipeline


# Initialize FastAPI app
app = FastAPI(
    title="PDF to Spreadsheet API",
    description="Extract structured data from PDFs and export to CSV, JSON, or Excel",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory for uploads and outputs
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory job storage (use Redis/DB in production)
jobs = {}


# -------------- Models --------------

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: str
    filename: str
    parser_type: str
    output_format: str
    progress: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None
    output_file: Optional[str] = None


class ProcessingOptions(BaseModel):
    parser_type: str = "auto"
    output_format: str = "csv"
    normalize: bool = True
    validate: bool = True


# -------------- Background Tasks --------------

def process_pdf_task(job_id: str, file_path: str, options: dict):
    """Background task to process PDF."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        
        # Load config
        config = load_config("config.yaml")
        
        jobs[job_id]["progress"] = 20
        
        # Create pipeline
        pipeline = Pipeline(
            config=config,
            output_format=options.get("output_format", "csv"),
            parser_type=options.get("parser_type", "auto") if options.get("parser_type") != "auto" else None,
            dry_run=False
        )
        
        jobs[job_id]["progress"] = 30
        
        # Process file
        result = pipeline.process_file(file_path, str(OUTPUT_DIR))
        
        jobs[job_id]["progress"] = 90
        
        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = {
            "total_rows": result.get("total_rows", 0),
            "errors": result.get("errors", 0),
            "warnings": result.get("warnings", 0),
            "elapsed_time": result.get("elapsed_time", 0)
        }
        
        if result.get("output_file"):
            jobs[job_id]["output_file"] = str(result["output_file"])
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
    
    finally:
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass


# -------------- API Endpoints --------------

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/upload", response_model=JobStatus)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    parser_type: str = "auto",
    output_format: str = "csv"
):
    """
    Upload a PDF file for processing.
    
    Returns a job ID to track processing status.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Save uploaded file
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create job entry
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "filename": file.filename,
        "parser_type": parser_type,
        "output_format": output_format,
        "progress": 0,
        "result": None,
        "error": None,
        "output_file": None
    }
    
    # Start background processing
    background_tasks.add_task(
        process_pdf_task,
        job_id,
        str(file_path),
        {"parser_type": parser_type, "output_format": output_format}
    )
    
    return JobStatus(**jobs[job_id])


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a processing job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(**jobs[job_id])


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    return {"jobs": list(jobs.values())}


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    """Download the processed result file."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job["output_file"] or not os.path.exists(job["output_file"]):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        job["output_file"],
        media_type="application/octet-stream",
        filename=os.path.basename(job["output_file"])
    )


@app.get("/api/preview/{job_id}")
async def preview_result(job_id: str, limit: int = 20):
    """Preview the first N rows of the result."""
    import csv
    import json
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job["output_file"] or not os.path.exists(job["output_file"]):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    output_file = job["output_file"]
    
    # Read based on format
    if output_file.endswith('.csv'):
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = []
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                # Clean row - remove internal fields
                clean_row = {k: v for k, v in row.items() if not k.startswith('_')}
                rows.append(clean_row)
        
        return {
            "format": "csv",
            "total_preview": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows
        }
    
    elif output_file.endswith('.json'):
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return {
                "format": "json",
                "total_preview": min(len(data), limit),
                "rows": data[:limit]
            }
        
        return {"format": "json", "data": data}
    
    return {"error": "Unknown format"}


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its output file."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    # Delete output file if exists
    if job.get("output_file") and os.path.exists(job["output_file"]):
        try:
            os.remove(job["output_file"])
        except:
            pass
    
    del jobs[job_id]
    
    return {"message": "Job deleted successfully"}


@app.get("/api/parsers")
async def list_parsers():
    """List available parsers."""
    return {
        "parsers": [
            {"id": "auto", "name": "Auto-detect", "description": "Automatically detect document type"},
            {"id": "invoice", "name": "Invoice", "description": "Commercial invoices and bills"},
            {"id": "report", "name": "Report", "description": "Tabular reports and tables"},
            {"id": "financial_report", "name": "Financial Report", "description": "Financial statements and annual reports"}
        ]
    }


@app.get("/api/formats")
async def list_formats():
    """List available output formats."""
    return {
        "formats": [
            {"id": "csv", "name": "CSV", "extension": ".csv"},
            {"id": "json", "name": "JSON", "extension": ".json"},
        ]
    }


# Serve static files for dashboard (if exists)
dashboard_path = Path(__file__).parent / "dashboard"
if dashboard_path.exists():
    app.mount("/", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")


# -------------- Run Server --------------

if __name__ == "__main__":
    import uvicorn
    
    print()
    print("=" * 50)
    print("  PDF to Spreadsheet API Server")
    print("=" * 50)
    print()
    print("  API Docs:    http://localhost:8000/api/docs")
    print("  Dashboard:   http://localhost:8000/")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
