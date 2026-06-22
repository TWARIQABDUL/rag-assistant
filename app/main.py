import time
# from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any
# from engine import run_rag_pipeline
from fastapi import FastAPI, HTTPException, status, UploadFile, File
import shutil
import tempfile
import os

from app.engine import run_rag_pipeline, add_pdf_to_index # Make sure to import it!
from app.engine import run_rag_pipeline
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Rwandan Legal & Gov RAG Engine",
    description="API service providing hybrid semantic search and generation over government documentation.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Request/Response Schemas ---

class QueryRequest(BaseModel):
    text: str = Field(..., example="Amategeko agenga umuryango avuga iki ku nkwano?")
    max_sources: int = Field(default=3, ge=1, le=10)

class SourceDocument(BaseModel):
    id: str
    title: str
    content_snippet: str
    score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    execution_time_seconds: float

# --- Endpoints ---

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Verifies the API is alive and internal configurations are loaded."""
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/api/v1/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def process_rag_query(payload: QueryRequest):
    """
    Accepts a natural language query, performs hybrid FAISS + keyword search,
    contextualizes the prompt, and returns the response from Gemini.
    """
    start_time = time.time()
    
    try:
        # Execute your core engine logic
        # Ensure your engine function handles Kinyarwanda nuances cleanly
        result = run_rag_pipeline(query=payload.text, max_results=payload.max_sources)
        
        execution_time = time.time() - start_time
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],  # Expected list of dicts matching SourceDocument
            execution_time_seconds=round(execution_time, 3)
        )
        
    except Exception as e:
        # Log the complete error internally for debugging
        print(f"Error processing RAG pipeline: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request within the RAG pipeline."
        )

@app.post("/api/v1/ingest", status_code=status.HTTP_201_CREATED)
async def upload_pdf_document(file: UploadFile = File(...)):
    """
    Accepts a PDF file, runs OCR/Extraction, chunks it, and updates the live RAG database.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are currently supported.")

    # PyMuPDF requires a physical file path to work, so we save the upload to a temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        # Save the uploaded content to the temp file
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close() # Close it so PyMuPDF can open it

        # Run the ingestion pipeline (this might take a while for large PDFs with OCR)
        # Note: For very large files in production, this should be moved to a background task (like Celery)
        chunks_added = add_pdf_to_index(temp_file.name, file.filename)
        
        return {
            "message": "Document successfully ingested and database updated.",
            "filename": file.filename,
            "new_chunks_indexed": chunks_added
        }

    except Exception as e:
        print(f"Ingestion Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)