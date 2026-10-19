import json
import httpx
import pytest
from pydantic import ValidationError
from app.core.config import settings
from app.services import extraction


def mock_ollama(monkeypatch, handler):
    cfg = settings()
    monkeypatch.setattr(cfg, "extraction_provider", "ollama")
    monkeypatch.setattr(cfg, "ollama_base_url", "http://ollama.test:11434/")
    monkeypatch.setattr(cfg, "ollama_model", "llama3.2")
    original = httpx.Client
    monkeypatch.setattr(
        extraction.httpx,
        "Client",
        lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
    )


def test_ollama_structured_extraction(monkeypatch, valid):
    def respond(request):
        assert str(request.url) == "http://ollama.test:11434/api/chat"
        assert "authorization" not in request.headers
        body = json.loads(request.content)
        assert body["model"] == "llama3.2"
        assert body["stream"] is False
        assert body["format"]["additionalProperties"] is False
        assert body["options"]["temperature"] == 0
        assert body["messages"][1]["content"] == "invoice text"
        return httpx.Response(
            200, json={"done": True, "message": {"content": json.dumps(valid)}}
        )

    mock_ollama(monkeypatch, respond)
    data = extraction.extract_invoice("invoice text")
    assert data.invoice_number == valid["invoice_number"]
    assert len(data.line_items) == 1


@pytest.mark.parametrize(
    "result",
    [
        {"done": False, "message": {"content": "{}"}},
        {"done": True, "done_reason": "length", "message": {"content": "{}"}},
        {"done": True, "message": {"content": "not JSON"}},
        {"done": True, "message": {"content": '{"total":"not a number"}'}},
    ],
)
def test_ollama_rejects_incomplete_or_invalid_output(monkeypatch, result):
    mock_ollama(monkeypatch, lambda _: httpx.Response(200, json=result))
    with pytest.raises((ValueError, ValidationError)):
        extraction.extract_invoice("invoice text")


def test_ollama_missing_model(monkeypatch):
    mock_ollama(
        monkeypatch, lambda _: httpx.Response(404, json={"error": "model not found"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        extraction.extract_invoice("invoice text")


def test_ollama_rejects_oversize_input_before_request(monkeypatch):
    def unexpected(_):
        pytest.fail("Oversized input must not be sent to the model")

    mock_ollama(monkeypatch, unexpected)
    with pytest.raises(ValueError, match="input limit"):
        extraction.extract_invoice("x" * 4001)
