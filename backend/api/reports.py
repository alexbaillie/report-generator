"""
Reports API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
from database.db import get_db
from database.models import Report
from services.report_generator import generate_report

router = APIRouter()

class ReportCreate(BaseModel):
    title: str
    patient_name: str
    report_type: str
    template_id: int
    document_ids: List[int] = []
    additional_inputs: dict = {}

class ReportResponse(BaseModel):
    id: int
    title: str
    patient_name: str
    report_type: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@router.post("/generate", response_model=ReportResponse)
async def create_report(report_data: ReportCreate, db: Session = Depends(get_db)):
    """Generate a new psychological report"""
    try:
        # Generate report content using AI
        content = await generate_report(
            db=db,
            template_id=report_data.template_id,
            document_ids=report_data.document_ids,
            additional_inputs=report_data.additional_inputs
        )
        
        # Save report to database
        db_report = Report(
            title=report_data.title,
            patient_name=report_data.patient_name,
            report_type=report_data.report_type,
            content=content
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        
        return db_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ReportResponse])
async def list_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all reports"""
    reports = db.query(Report).offset(skip).limit(limit).all()
    return reports

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get a specific report"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.delete("/{report_id}")
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    """Delete a report"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    db.delete(report)
    db.commit()
    return {"message": "Report deleted successfully"}
