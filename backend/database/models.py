"""
SQLAlchemy database models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.db import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    patient_name = Column(String, nullable=False)
    report_type = Column(String, nullable=False)  # e.g., "intake", "assessment"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    documents = relationship("Document", back_populates="report", cascade="all, delete-orphan")
    test_results = relationship(
        "ReportTestResult",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportTestResult.position",
    )

class ReportTestResult(Base):
    """Score tables and graphs for one test (e.g. WISC-V) attached to a report.

    Kept out of Report.content so the editable report text stays clean; the
    Word exporter places these under that test's section. A new table (not a
    new column) so create_all adds it to existing databases without migrations.
    """
    __tablename__ = "report_test_results"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    test_name = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)
    # JSON: {"items": [{"kind": "table"|"image", "caption": str, "rows": [[str]],
    #                   "content_type": str, "data_b64": str}]}
    payload = Column(Text, nullable=False)

    report = relationship("Report", back_populates="test_results")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    content = Column(Text)  # Extracted text content
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    
    # Relationships
    report = relationship("Report", back_populates="documents")

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    template_type = Column(String, nullable=False)  # e.g., "intake", "assessment"
    content = Column(Text, nullable=False)  # Template structure/prompt
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
