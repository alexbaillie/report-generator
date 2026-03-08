"""
FastAPI backend for Psychological Report Generator
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import reports, documents, templates, ai
from database.db import init_db

app = FastAPI(
    title="Psychological Report Generator API",
    description="Offline API for generating psychological reports",
    version="1.0.0"
)

# CORS middleware for local Electron app
app.add_middleware(
    CORSMiddleware,
    # Allow all origins during development to avoid CORS issues from different dev servers/electron
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()

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
