"""
LLM service for text generation and editing
"""
from services.ollama_client import generate_text

async def generate_text_with_llm(prompt: str, context: str) -> str:
    """
    Generate or edit text using the LLM based on a prompt and context
    
    Args:
        prompt: User's instruction (e.g., "Add a confidentiality section")
        context: Current document content
    
    Returns:
        Generated/edited text
    """
    # Construct the full prompt with context
    if context.strip():
        full_prompt = f"""You are a professional psychological report writer. 

Current report content:
{context}

User instruction: {prompt}

Please provide the complete updated report incorporating the user's instruction. Maintain professional language and formatting."""
    else:
        full_prompt = f"""You are a professional psychological report writer.

User instruction: {prompt}

Please generate the requested content in a professional format suitable for a psychological report."""
    
    # Generate text using Ollama
    generated_text = await generate_text(
        prompt=full_prompt,
        model="tinyllama",
        max_tokens=3000
    )
    
    return generated_text
