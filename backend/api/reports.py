"""
Reports API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
import json
from typing import List, Dict, Literal, Optional
from pydantic import BaseModel
from datetime import datetime
from database.db import get_db
from database.models import Report, ReportTestResult
from services.report_generator import generate_report, generate_report_section
from services.score_report_extractor import html_to_tables
from services.docx_exporter import (
    DocxExportError,
    create_report_docx,
    export_filename,
)

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

    model_config = {"from_attributes": True}

class TestResultItem(BaseModel):
    """One score table or graph picked from an uploaded score report."""
    kind: Literal["table", "image"]
    caption: str = ""
    rows: Optional[List[List[str]]] = None
    merges: Optional[List[List[int]]] = None   # [row, col, rowspan, colspan]
    widths: Optional[List[int]] = None         # relative column widths
    content_type: Optional[str] = None
    data_b64: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

class TestResultGroup(BaseModel):
    """Everything attached for one test (e.g. WISC-V): chosen items plus any pasted HTML tables."""
    test_name: str
    # "fill": fill the Word template's own score tables (its look is untouched);
    # "insert": replace them with the tables as they appear in the score report.
    mode: Literal["fill", "insert"] = "fill"
    pasted_html: str = ""
    items: List[TestResultItem] = []

class TestResultSummary(BaseModel):
    test_name: str
    tables: int
    images: int

class GenerateReportRequest(BaseModel):
    title: str
    patient_name: str
    report_type: str
    template_id: int
    document_ids: List[int] = []
    additional_inputs: Dict = {}
    test_results: List[TestResultGroup] = []
    # Every test added to the report, with or without results. Tests the template lists that
    # are not in here (or in test_results) are removed from the Word export.
    tests_administered: List[str] = []

class UpdateReportRequest(BaseModel):
    title: Optional[str] = None
    patient_name: Optional[str] = None
    content: Optional[str] = None

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

def _save_tests_administered(db: Session, report_id: int, names: List[str], saved: set, first_position: int) -> None:
    """Record tests that were given but have no results, as a result row with nothing in it."""
    for offset, name in enumerate(n.strip() for n in names):
        if name and name.lower() not in saved:
            saved.add(name.lower())
            db.add(ReportTestResult(report_id=report_id, test_name=name, position=first_position + offset,
                                    payload=json.dumps({"items": [], "mode": "fill"})))


def _save_test_results(db: Session, report_id: int, groups: List[TestResultGroup], tests_administered: Optional[List[str]] = None) -> None:
    saved = set()
    for position, group in enumerate(groups):
        name = group.test_name.strip()
        items = [item.model_dump(exclude_none=True) for item in group.items]
        items += html_to_tables(group.pasted_html)  # every pasted table, not just the first
        if name and items:
            saved.add(name.lower())
            db.add(
                ReportTestResult(
                    report_id=report_id,
                    test_name=name,
                    position=position,
                    payload=json.dumps({"items": items, "mode": group.mode}),
                )
            )
    _save_tests_administered(db, report_id, tests_administered or [], saved, len(groups))


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
        db.flush()  # need the id for the attached test results; commit once below
        _save_test_results(db, report.id, request.test_results, request.tests_administered)
        db.commit()
        db.refresh(report)

        return report
    except Exception as e:
        db.rollback()
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

@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(report_id: int, request: UpdateReportRequest, db: Session = Depends(get_db)):
    """Update an existing report's editable fields (title, patient name, content)."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    if "content" in updates and not (updates["content"] or "").strip():
        raise HTTPException(status_code=400, detail="Report content cannot be empty.")

    for field, value in updates.items():
        setattr(report, field, value)

    db.commit()
    db.refresh(report)
    return report

@router.get("/{report_id}/test-results", response_model=List[TestResultSummary])
async def list_test_results(report_id: int, db: Session = Depends(get_db)):
    """What score tables/graphs are attached to a report (counts only, no payload)."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    summaries = []
    for result in report.test_results:
        items = json.loads(result.payload).get("items", [])
        if not items:
            continue  # a test that was given but has no results attached
        summaries.append(
            TestResultSummary(
                test_name=result.test_name,
                tables=sum(1 for i in items if i.get("kind") == "table"),
                images=sum(1 for i in items if i.get("kind") == "image"),
            )
        )
    return summaries


def _stored_group(result: ReportTestResult) -> dict:
    payload = json.loads(result.payload)
    return {
        "test_name": result.test_name,
        "mode": payload.get("mode", "fill"),
        "items": payload.get("items", []),
    }


@router.get("/{report_id}/export-docx")
async def export_report_docx(report_id: int, db: Session = Depends(get_db)):
    """Export a saved report into its configured Word template."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    fill_report: List[dict] = []
    try:
        document = await run_in_threadpool(
            create_report_docx,
            title=report.title,
            patient_name=report.patient_name,
            report_type=report.report_type,
            content=report.content,
            test_results=[_stored_group(r) for r in report.test_results],
            fill_report=fill_report,
            tests_administered=[r.test_name for r in report.test_results],
        )
    except DocxExportError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    filename = export_filename(report.title)
    return StreamingResponse(
        document,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # What was filled into the template (and what wasn't), for the UI to show.
            "X-Score-Fill": json.dumps(fill_report, separators=(",", ":")),
        },
    )

@router.delete("/{report_id}")
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    """Delete a report"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    db.delete(report)
    db.commit()
    return {"message": "Report deleted successfully"}
