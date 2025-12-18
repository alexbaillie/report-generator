"""
Document processing service for extracting text from various file formats
"""
from pathlib import Path
from typing import Optional

# Optional dependencies: import at module level so missing packages produce
# a clear, single point of failure and can be checked by helper functions.
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except Exception:
    DocxDocument = None

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
    """Extract text from PDF using PyPDF2.

    Falls back to a helpful message if PyPDF2 is not installed.
    """
    if PdfReader is None:
        return f"[PDF extraction requires PyPDF2; please install backend/requirements.txt dependencies]"

    try:
        reader = PdfReader(str(file_path))
        texts: list[str] = []
        for page in reader.pages:
            # PyPDF2's page.extract_text() may be None for pages without extractable text
            text = page.extract_text()
            if text:
                texts.append(text)
        joined = "\n".join(texts).strip()
        return joined if joined else f"[No text found in PDF {file_path.name}]"
    except Exception as e:
        return f"[Error extracting PDF: {e}]"

async def extract_docx_text(file_path: Path) -> str:
    """Extract text from Word documents (.docx) using python-docx.

    - For `.docx` files this will return the concatenated paragraph text.
    - For legacy `.doc` files, returns a short message (conversion required).
    - If `python-docx` is not installed, returns a helpful message.
    """
    suffix = file_path.suffix.lower()
    if suffix == ".doc":
        return f"[Legacy .doc files are not supported; please convert {file_path.name} to .docx]"

    if DocxDocument is None:
        return f"[DOCX extraction requires python-docx; please install backend/requirements.txt dependencies]"

    try:
        doc = DocxDocument(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        joined = "\n".join(paragraphs).strip()
        return joined if joined else f"[No text found in Word document {file_path.name}]"
    except Exception as e:
        return f"[Error extracting Word document: {e}]"
