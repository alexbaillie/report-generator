"""
Documents API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import shutil
from database.db import get_db
from database.models import Document
from services.document_processor import process_document

router = APIRouter()

# Create uploads directory
UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    content: Optional[str]
    uploaded_at: datetime
    report_id: Optional[int]

    model_config = {"from_attributes": True}

def _save_upload(file: UploadFile, file_path: Path) -> None:
    """Write the uploaded stream to disk (blocking; run off the event loop)."""
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload and process a document"""
    try:
        # Use only the base filename to avoid path traversal from a crafted upload name.
        safe_name = Path(file.filename or "upload").name
        if not safe_name:
            raise HTTPException(status_code=400, detail="Invalid filename.")

        # Save file (blocking I/O offloaded so it does not stall the event loop).
        file_path = UPLOAD_DIR / safe_name
        await run_in_threadpool(_save_upload, file, file_path)

        # Process document to extract text
        content = await process_document(file_path, file.content_type)
        
        # Save to database
        db_document = Document(
            filename=safe_name,
            file_path=str(file_path),
            file_type=file.content_type or "unknown",
            content=content
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        return db_document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all documents"""
    documents = db.query(Document).offset(skip).limit(limit).all()
    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get a specific document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from disk
    try:
        Path(document.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    
    db.delete(document)
    db.commit()
    return {"message": "Document deleted successfully"}
