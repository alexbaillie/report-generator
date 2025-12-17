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
