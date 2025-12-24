"""
Reports API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
from database.db import get_db
from database.models import Report
from services.report_generator import generate_report, generate_report_section

router = APIRouter()

class SectionGenerationRequest(BaseModel):
    template_id: int
    section_name: str
    document_ids: List[int] = []
    section_inputs: dict = {}

class SectionGenerationResponse(BaseModel):
    section_content: str

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

class GenerateReportRequest(BaseModel):
    title: str
    patient_name: str
    report_type: str
    template_id: int
    document_ids: List[int] = []
    additional_inputs: Dict = {}

@router.post("/generate-section", response_model=SectionGenerationResponse)
async def generate_section(request: SectionGenerationRequest, db: Session = Depends(get_db)):
    """Generate a specific section of a psychological report"""
    try:
        # Generate section content using AI
        section_content = await generate_report_section(
            db=db,
            template_id=request.template_id,
            section_name=request.section_name,
            document_ids=request.document_ids,
            section_inputs=request.section_inputs
        )
        
        return SectionGenerationResponse(section_content=section_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate", response_model=ReportResponse)
async def generate_report_endpoint(request: GenerateReportRequest, db: Session = Depends(get_db)):
    """Generate a full report by combining section outputs and save it"""
    try:
        # Generate final content from provided sections
        content = await generate_report(
            db=db,
            template_id=request.template_id,
            document_ids=request.document_ids,
            additional_inputs=request.additional_inputs,
        )

        # Persist report
        report = Report(
            title=request.title,
            patient_name=request.patient_name,
            report_type=request.report_type,
            content=content,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        return report
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
