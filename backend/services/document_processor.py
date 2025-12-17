"""
Document processing service for extracting text from various file formats
"""
from pathlib import Path
from typing import Optional

WORD_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


def is_word_doc(file_path: Path, content_type: Optional[str]) -> bool:
    if content_type in WORD_MIME_TYPES:
        return True

    return file_path.suffix.lower() in {".doc", ".docx"}

async def process_document(file_path: Path, content_type: Optional[str]) -> str:
    """
    Process a document and extract text content
    
    Args:
        file_path: Path to the document
        content_type: MIME type of the document
    
    Returns:
        Extracted text content
    """
    try:
        # For now, handle text files directly
        if content_type and "text" in content_type:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        # Handle PDF files
        elif content_type == "application/pdf":
            return await extract_pdf_text(file_path)
        
        # Handle Word documents (by MIME or extension)
        elif is_word_doc(file_path, content_type):
            return await extract_docx_text(file_path)
        
        # Default: try to read as text
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                return f"[Binary file: {file_path.name}]"
    
    except Exception as e:
        return f"[Error processing file: {str(e)}]"

async def extract_pdf_text(file_path: Path) -> str:
    """Extract text from PDF (placeholder - requires PyPDF2 or similar)"""
    # TODO: Implement PDF extraction
    # For now, return placeholder
    return f"[PDF content from {file_path.name} - PDF extraction not yet implemented]"

async def extract_docx_text(file_path: Path) -> str:
    """Extract text from Word document (placeholder - requires python-docx)"""
    # TODO: Implement DOCX extraction
    # For now, return placeholder
    return f"[Word document content from {file_path.name} - DOCX extraction not yet implemented]"
