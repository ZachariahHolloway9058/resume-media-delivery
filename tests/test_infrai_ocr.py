import asyncio
import base64
import json

import httpx
import pytest

from resume_ingestion.infrai_ocr import InfraiOcrClient


def test_ocr_sends_pdf_as_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["content-type"] == "application/json"
        body = json.loads(request.content)
        assert set(body) == {"pdf", "lang", "quality"}
        assert body["lang"] == "eng"
        assert body["quality"] == "accurate"
        assert base64.b64decode(body["pdf"].split(",", 1)[1]) == b"%PDF-1.4"
        return httpx.Response(200, json={"ok": True, "data": {"text": "Ada Lovelace"}})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    assert asyncio.run(InfraiOcrClient("test-key").parse_resume("resume.pdf", b"%PDF-1.4")) == {
        "text": "Ada Lovelace"
    }
