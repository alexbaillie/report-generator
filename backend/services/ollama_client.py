"""
Ollama client for local AI inference
"""
import httpx
from typing import Optional

OLLAMA_BASE_URL = "http://localhost:11434"

async def generate_text(prompt: str, model: str = "tinyllama", max_tokens: int = 2000) -> str:
    """
    Generate text using Ollama
    
    Args:
        prompt: The prompt to send to the model
        model: The model to use (default: tinyllama)
        max_tokens: Maximum tokens to generate
    
    Returns:
        Generated text
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
    except httpx.ConnectError:
        raise Exception("Could not connect to Ollama. Make sure Ollama is running on localhost:11434")
    except Exception as e:
        raise Exception(f"Error generating text: {str(e)}")

async def check_ollama_status() -> bool:
    """Check if Ollama is running and accessible"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return response.status_code == 200
    except:
        return False
