"""
FastAPI backend for Psychological Report Generator
"""
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import reports, documents, templates, ai
from database.db import init_db
from database.backup import backup_database
from seed_data import seed_templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Back up the existing database, initialize it, and ensure default templates exist, on startup."""
    backup_database()
    init_db()
    seed_templates()
    yield


app = FastAPI(
    title="Psychological Report Generator API",
    description="Offline API for generating psychological reports",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for local Electron app
app.add_middleware(
    CORSMiddleware,
    # Allow all origins during development to avoid CORS issues from different dev servers/electron
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    # Expose the download filename to the browser for DOCX export.
    expose_headers=["Content-Disposition"],
)

# Include routers
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])

@app.get("/")
async def root():
    return {"message": "Psychological Report Generator API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )
