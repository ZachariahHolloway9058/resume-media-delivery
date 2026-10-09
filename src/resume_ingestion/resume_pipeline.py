from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal


EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")


@dataclass(frozen=True)
class ResumeFields:
    name: str | None
    email: str | None
    phone: str | None
    skills: list[str]


@dataclass(frozen=True)
class ProcessingDecision:
    status: Literal["ready_for_delivery", "needs_review"]
    fields: ResumeFields


def collect_text(value: Any) -> str:
    """Flatten textual OCR data without depending on a document layout."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (collect_text(item) for item in value)))
    if isinstance(value, dict):
        return "\n".join(filter(None, (collect_text(item) for item in value.values())))
    return ""


def extract_resume_fields(text: str) -> ResumeFields:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = next((line for line in lines if 1 < len(line.split()) <= 5 and not EMAIL.search(line)), None)
    email_match = EMAIL.search(text)
    phone_match = PHONE.search(text)
    known_skills = ("Python", "PyTorch", "TensorFlow", "Kubernetes", "LangChain", "SQL")
    skills = [skill for skill in known_skills if re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE)]
    return ResumeFields(
        name=name,
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0) if phone_match else None,
        skills=skills,
    )


def decide_delivery(text: str) -> ProcessingDecision:
    fields = extract_resume_fields(text)
    has_contact = fields.email is not None or fields.phone is not None
    status: Literal["ready_for_delivery", "needs_review"] = (
        "ready_for_delivery" if fields.name and has_contact else "needs_review"
    )
    return ProcessingDecision(status=status, fields=fields)

