import httpx
import pytest

from services import ollama_client


def _patch_transport(monkeypatch, handler):
    """Route the client's httpx.AsyncClient through a mock transport."""
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(ollama_client.httpx, "AsyncClient", factory)
    monkeypatch.setattr(ollama_client, "RETRY_DELAY_SECONDS", 0)


@pytest.mark.asyncio
async def test_generate_text_retries_once_after_transient_5xx(monkeypatch):
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(500, json={"error": "llama-server terminated"})
        return httpx.Response(200, json={"response": "recovered"})

    _patch_transport(monkeypatch, handler)

    assert await ollama_client.generate_text("hi") == "recovered"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_generate_text_gives_up_after_two_failed_attempts(monkeypatch):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(500, json={"error": "still broken"})

    _patch_transport(monkeypatch, handler)

    with pytest.raises(Exception, match="Error generating text"):
        await ollama_client.generate_text("hi")
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_generate_text_does_not_retry_client_errors(monkeypatch):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404, json={"error": "model not found"})

    _patch_transport(monkeypatch, handler)

    with pytest.raises(Exception, match="Error generating text"):
        await ollama_client.generate_text("hi")
    assert len(calls) == 1
