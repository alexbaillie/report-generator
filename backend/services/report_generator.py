"""
Report generation service using Ollama AI
"""
import re
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
    Generate a complete psychological report using AI
    
    Args:
        db: Database session
        template_id: ID of the template to use
        document_ids: List of document IDs to include
        additional_inputs: Additional text inputs from the form (now contains generated sections)
    
    Returns:
        Generated report content
    """
    # For now, just combine the generated sections
    # In the future, this could do final formatting/editing
    if additional_inputs and isinstance(additional_inputs, dict):
        sections = []
        for section_name, content in additional_inputs.items():
            if content:
                sections.append(f"# {section_name}\n\n{content}")
        return "\n\n".join(sections)
    
    # Fallback
    return "Report generation completed."

async def generate_report_section(
    db: Session,
    template_id: int,
    section_name: str,
    document_ids: List[int],
    section_inputs: Dict
) -> str:
    """
    Generate a specific section of a psychological report using AI
    
    Args:
        db: Database session
        template_id: ID of the template to use
        section_name: Name of the section to generate
        document_ids: List of document IDs to include
        section_inputs: Inputs specific to this section
    
    Returns:
        Generated section content
    """
    # Get template
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise ValueError("Template not found")
    
    # Get documents
    documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
    
    if wants_bullets(template, section_name) and (section_name or '').strip().lower().startswith('presenting concerns'):
        by_area = await generate_by_area(template, section_name, documents, section_inputs)
        if by_area:
            return by_area

    # Build prompt for section
    prompt = build_section_prompt(template, section_name, documents, section_inputs)
    
    # Generate section using Ollama
    section_content = await generate_text(prompt, max_tokens=1500)
    
    return section_content

# The Sunny Hill CDBC reports list these background sections as bullet points, not paragraphs.
BULLET_SECTION_PREFIXES = (
    "presenting concerns",
    "areas of relative strength",
    "family history",
    "developmental & medical history",
    "educational history",
    "previous assessments",
)


def bullet_instructions(template, section_name: str) -> str:
    name = (getattr(template, "name", "") or "").lower()
    girl = "girl" in name
    # "Joe"/"Jane" are the templates' own placeholder names; the Word export swaps them for the client's real name.
    child, pronoun = ("Jane", "she") if girl else ("Joe", "he")
    text = (
        "\n\nInstructions: Write this section as bullet points, one fact per line, each line starting with \"- \". "
        "Each bullet is one short, complete sentence in the third person. Do not write paragraphs, and do not nest "
        "bullets under other bullets. "
        f"Refer to the child as \"{child}\" (and \"{pronoun}\" after that); never make up any other name. "
        "Use only the information given and do not add facts. Be clear, objective and clinically appropriate. "
        "Do not use italics, bold or any markdown other than the leading \"- \"."
    )
    text += (
        " Do not use headings. Do not write bullets about information that is missing, unreported or unknown. "
        "If the information says there are no concerns, write one bullet saying so, for example "
        "'No concerns with anxiety were indicated.'"
    )
    return text


def area_heading(label: str) -> str:
    """'Attention / Impulsivity / Activity' -> 'Attention'; 'Social concerns (peers)' -> 'Social concerns'."""
    return label.split(" / ")[0].split(" (")[0].strip()


_NO_CONCERNS = re.compile(
    r"^\W*(?:no|none|nil|n/a|nothing)(?:\s+(?:concerns?|issues?|problems?|difficulties|reported|noted|indicated|to report))*\W*$",
    re.IGNORECASE,
)


def no_concerns_bullet(heading: str, value: str) -> str:
    """'- No concerns with anxiety were indicated.' when the whole answer is just 'no concerns'; else ''."""
    if not _NO_CONCERNS.match(value or ""):
        return ""
    area = heading.strip().lower()
    if area.endswith(" concerns"):
        return f"- No {area} were indicated."
    return f"- No concerns with {area} were indicated."


async def generate_by_area(template, section_name: str, documents, section_inputs: Dict) -> str:
    """One short generation per area the person filled in, each under that area's heading, so every
    area is present and labelled however well the model follows a formatting instruction."""
    parts = []
    for label, value in section_inputs.items():
        if not str(value or '').strip():
            continue
        no_concerns = no_concerns_bullet(area_heading(label), str(value))
        if no_concerns:  # a plain "no concerns" needs no model, which tends to pad it with invented bullets
            parts.append(area_heading(label) + "\n" + no_concerns)
            continue
        prompt = build_section_prompt(template, section_name, documents, {label: value})
        text = (await generate_text(prompt, max_tokens=700)).strip()
        if text:
            parts.append(area_heading(label) + "\n" + text)
    return "\n".join(parts)


def wants_bullets(template, section_name: str) -> bool:
    name = (getattr(template, "name", "") or "").lower()
    if "cdbc" not in name and "sunny hill" not in name and "sunnyhill" not in name:
        return False
    return (section_name or "").strip().lower().startswith(BULLET_SECTION_PREFIXES)


def build_section_prompt(template: Template, section_name: str, documents: List[Document], section_inputs: Dict) -> str:
    """
    Build the prompt for AI generation of a specific section
    
    Args:
        template: Report template
        section_name: Name of the section to generate
        documents: List of documents
        section_inputs: Inputs specific to this section
    
    Returns:
        Formatted prompt for section generation
    """
    prompt_parts = [
        "You are a professional psychologist writing a section of a psychological report.",
        f"\nReport Type: {template.template_type}",
        f"\nSection to Generate: {section_name}",
        "\n\nInstructions: Write a professional, well-structured paragraph for this section of the psychological report.",
        "Focus on being clear, objective, and clinically appropriate. Use formal psychological terminology where appropriate.",
    ]
    bullets = wants_bullets(template, section_name)
    if bullets:
        prompt_parts[-2:] = [bullet_instructions(template, section_name)]

    # Add document contents if relevant to this section
    if documents:
        prompt_parts.append("\n\nRelevant Source Documents:")
        for doc in documents:
            prompt_parts.append(f"\n--- {doc.filename} ---")
            prompt_parts.append(doc.content or "[No content extracted]")
    
    # Add section-specific inputs
    if section_inputs:
        prompt_parts.append(f"\n\nInformation for {section_name} section:")
        for key, value in section_inputs.items():
            if value:  # Only include non-empty values
                prompt_parts.append(f"\n{key}: {value}")
    
    # Add section-specific guidance from template AI_use instructions
    section_guidance = "" if bullets else extract_section_guidance(template.content, section_name)
    if section_guidance:
        prompt_parts.append(f"\n\nSection Guidance:\n{section_guidance}")
    
    prompt_parts.append(f"\n\nPlease generate only the content for the {section_name} section. Do not include section headers or titles in your response.")
    
    return "\n".join(prompt_parts)

def extract_section_guidance(template_content: str, section_name: str) -> str:
    """
    Extract AI_use guidance for a specific section from template content
    """
    lines = template_content.split('\n')
    current_section = None
    guidance_lines = []
    
    for line in lines:
        trimmed = line.strip()
        
        # Check if this is a section header
        if trimmed.startswith(section_name.upper()) or section_name.upper() in trimmed.upper():
            current_section = section_name
            guidance_lines = []
        elif current_section == section_name and trimmed.startswith('AI_use:'):
            # Extract the AI instruction
            ai_instruction = trimmed.replace('AI_use:', '').strip()
            guidance_lines.append(ai_instruction)
        elif current_section == section_name and trimmed.startswith('AI_use:') is False and guidance_lines:
            # Continue collecting guidance until next section
            if trimmed and not trimmed[0].isdigit() and ':' in trimmed:
                break
    
    if guidance_lines:
        return ' '.join(guidance_lines)
    
    # Fallback to default guidance if no AI_use found
    return get_default_section_guidance(section_name)

def get_default_section_guidance(section_name: str) -> str:
    """
    Get default guidance for different report sections when AI_use is not specified
    """
    guidance = {
        "REPORT METADATA": "Generate standardized clinic identity and administrative information",
        "CLIENT & ADMINISTRATIVE INFORMATION": "Insert consistently into report text with client demographics and assessment details",
        "DIAGNOSTIC SUMMARY": "Rephrase into narrative summary without adding or changing diagnoses",
        "SUMMARY OF FINDINGS": "Generate cohesive paragraph from structured bullets about referral and client background",
        "REASON FOR REFERRAL": "Generate standard referral paragraph based on provided information",
        "SOURCES OF INFORMATION": "Insert standardized sentence listing all sources used in the assessment",
        "PRESENTING CONCERNS": "Expand checklist items into paragraph per domain",
        "FAMILY HISTORY": "Generate family history paragraph from provided information",
        "DEVELOPMENTAL & MEDICAL HISTORY": "Generate standardized developmental history text",
        "EDUCATIONAL HISTORY": "Generate educational history narrative",
        "BEHAVIOURAL OBSERVATIONS": "Convert checklist to narrative observation section",
        "TESTS ADMINISTERED": "Insert standardized descriptions of tests and summarize results",
        "COGNITIVE FUNCTIONING": "Generate index-by-index interpretation paragraphs with caution statements when flags selected",
        "ACADEMIC ACHIEVEMENT": "Generate domain-based academic interpretation",
        "EXECUTIVE FUNCTIONING": "Summarize parent vs teacher patterns in executive functioning",
        "ADAPTIVE BEHAVIOUR": "Generate comparative adaptive functioning narrative",
        "SOCIAL / EMOTIONAL FUNCTIONING": "Generate integrated emotional-behavioural summary",
        "DIAGNOSTIC IMPRESSIONS": "Draft diagnostic rationale paragraph for clinician review",
        "RELATIVE STRENGTHS & WEAKNESSES": "Generate concise summary lists",
        "RECOMMENDATIONS": "Insert standardized recommendation paragraphs based on selections",
        "COMMUNITY / THERAPY": "Generate community support section with appropriate referrals",
        "STRATEGIES": "Compile and organize strategy lists by category",
        "CONCLUSION": "Polished closing paragraph summarizing the assessment"
    }
    
    return guidance.get(section_name.upper(), "Provide a professional summary of the relevant information for this section of the psychological report.")
