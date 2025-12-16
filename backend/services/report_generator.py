"""
Report generation service using Ollama AI
"""
from sqlalchemy.orm import Session
from typing import List, Dict
from database.models import Template, Document
from services.ollama_client import generate_text

async def generate_report(
    db: Session,
    template_id: int,
    document_ids: List[int],
    additional_inputs: Dict
) -> str:
    """
    Generate a psychological report using AI
    
    Args:
        db: Database session
        template_id: ID of the template to use
        document_ids: List of document IDs to include
        additional_inputs: Additional text inputs from the form
    
    Returns:
        Generated report content
    """
    # Get template
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise ValueError("Template not found")
    
    # Get documents
    documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
    
    # Build prompt
    prompt = build_prompt(template, documents, additional_inputs)
    
    # Generate report using Ollama
    report_content = await generate_text(prompt, max_tokens=3000)
    
    return report_content

def build_prompt(template: Template, documents: List[Document], additional_inputs: Dict) -> str:
    """
    Build the prompt for AI generation
    
    Args:
        template: Report template
        documents: List of documents
        additional_inputs: Additional inputs
    
    Returns:
        Formatted prompt
    """
    prompt_parts = [
        "You are a professional psychologist writing a psychological report.",
        f"\nReport Type: {template.template_type}",
        f"\nTemplate Instructions:\n{template.content}",
    ]
    
    # Add document contents
    if documents:
        prompt_parts.append("\n\nSource Documents:")
        for doc in documents:
            prompt_parts.append(f"\n--- {doc.filename} ---")
            prompt_parts.append(doc.content or "[No content extracted]")
    
    # Add additional inputs
    if additional_inputs:
        prompt_parts.append("\n\nAdditional Information:")
        for key, value in additional_inputs.items():
            prompt_parts.append(f"\n{key}: {value}")
    
    prompt_parts.append("\n\nPlease generate a professional psychological report based on the above information. The report should be well-structured, clear, and follow professional standards.")
    
    return "\n".join(prompt_parts)
