from __future__ import annotations

import os
import uuid
from typing import Literal

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from .infrai_ocr import InfraiError, InfraiOcrClient
from .resume_pipeline import collect_text, decide_delivery


class ParsedFields(BaseModel):
    name: str | None
    email: str | None
    phone: str | None
    skills: list[str]


class ResumeDelivery(BaseModel):
    asset_id: str
    job_id: str
    status: Literal["ready_for_delivery", "needs_review"]
    fields: ParsedFields


app = FastAPI(title="Resume media ingestion")


@app.post("/resumes", response_model=ResumeDelivery)
async def ingest_resume(document: UploadFile = File(...)) -> ResumeDelivery:
    if document.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Upload a PDF document")
    content = await document.read()
    if not content:
        raise HTTPException(status_code=400, detail="The PDF is empty")

    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is not configured")

    asset_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    client = InfraiOcrClient(api_key)
    try:
        ocr_data = await client.parse_resume(document.filename or "resume.pdf", content)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Document processing transport error") from exc

    decision = decide_delivery(collect_text(ocr_data))
    return ResumeDelivery(
        asset_id=asset_id,
        job_id=job_id,
        status=decision.status,
        fields=ParsedFields(**decision.fields.__dict__),
    )
