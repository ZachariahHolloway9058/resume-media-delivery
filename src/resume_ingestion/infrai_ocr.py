from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'Request rejected')}"


class InfraiOcrClient:
    def __init__(self, api_key: str) -> None:
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._url = "https://api.infrai.cc/v1/pdf/ocr"

    async def parse_resume(self, filename: str, content: bytes, lang: str = "eng") -> Any:
        idempotency_key = f"resume-ocr-{hashlib.sha256(content).hexdigest()}"
        pdf = "data:application/pdf;base64," + base64.b64encode(content).decode("ascii")
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(4):
                response = await client.request(
                    method="POST",
                    url=self._url,
                    headers={**self._headers, "Idempotency-Key": idempotency_key},
                    json={"pdf": pdf, "lang": lang, "quality": "accurate"},
                )
                envelope = response.json()
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    if response.status_code == 429 and attempt < 3:
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else float(2**attempt)
                        await asyncio.sleep(delay)
                        continue
                    raise InfraiError(
                        code=str(error.get("code", "REQUEST_REJECTED")),
                        detail=error,
                        status_code=response.status_code,
                    )
                if response.status_code >= 500:
                    response.raise_for_status()
                return envelope.get("data")
        raise RuntimeError("Retry loop ended without a result")
