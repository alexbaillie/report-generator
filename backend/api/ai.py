"""
AI text generation endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_service import generate_text_with_llm

router = APIRouter()

class TextGenerationRequest(BaseModel):
    prompt: str
    context: str

class TextGenerationResponse(BaseModel):
    text: str

@router.post("/generate-text", response_model=TextGenerationResponse)
async def generate_text(request: TextGenerationRequest):
    """
    Generate or edit text using the AI model based on a prompt and context
    """
    try:
        # Call the LLM service to generate text
        generated_text = await generate_text_with_llm(
            prompt=request.prompt,
            context=request.context
        )
        
        return TextGenerationResponse(text=generated_text)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate text: {str(e)}"
        )
