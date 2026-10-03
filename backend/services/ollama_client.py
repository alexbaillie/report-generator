"""
Ollama client for local AI inference
"""
import asyncio
import os
import httpx
from typing import Optional

RETRY_DELAY_SECONDS = 2.0
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
# Default model can be overridden with the OLLAMA_MODEL env var.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

async def generate_text(prompt: str, model: Optional[str] = None, max_tokens: int = 2000) -> str:
    """
    Generate text using Ollama
    
    Args:
        prompt: The prompt to send to the model
        model: The model to use (defaults to OLLAMA_MODEL, i.e. llama3.1:8b)
        max_tokens: Maximum tokens to generate
    
    Returns:
        Generated text
    """
    model = model or OLLAMA_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.7,
        }
    }
    # Ollama can answer the first request after a cold start with a 5xx while its
    # model runner (CUDA init, model load) is still coming up; a second attempt
    # normally succeeds once the runner has restarted.
    attempts = 2
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except httpx.ConnectError:
            raise Exception("Could not connect to Ollama. Make sure Ollama is running on localhost:11434")
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and attempt < attempts:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
            raise Exception(f"Error generating text: {str(e)}")
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
