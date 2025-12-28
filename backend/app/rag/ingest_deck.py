import json
import logging
import time
from typing import Any, Dict, List

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from pypdf import PdfReader

from ..config import get_settings

logger = logging.getLogger(__name__)


class StartupExtraction(BaseModel):
    startup_name: str
    domain: str | None
    founder_email: str | None
    sector: str | None
    key_metrics: list[str]
    summary: str
    why_too_early_guess: str


def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    text_parts: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            text_parts.append(page_text)
    return "\n\n".join(text_parts)


def _chunk_text(text: str, max_chars: int = 6000) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def _call_llm(prompt: str, max_attempts: int = 3) -> str:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise information extractor.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content
            if content:
                return content
        except Exception as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError("LLM call failed") from last_error


def _summarize_chunk(chunk: str) -> str:
    prompt = (
        "Summarize this startup deck chunk for extraction. "
        "Include startup name, domain, founder email, sector, key metrics, "
        "and any hints about why the startup might be too early.\n\n"
        f"CHUNK:\n{chunk}"
    )
    return _call_llm(prompt)


def _extract_json(text: str) -> Dict[str, Any]:
    prompt = (
        "Extract startup intelligence and return STRICT JSON only. "
        "No markdown, no extra text. Use this schema:\n"
        "{\n"
        '  "startup_name": string,\n'
        '  "domain": string | null,\n'
        '  "founder_email": string | null,\n'
        '  "sector": string | null,\n'
        '  "key_metrics": [string],\n'
        '  "summary": string,\n'
        '  "why_too_early_guess": string\n'
        "}\n\n"
        f"TEXT:\n{text}"
    )
    raw = _call_llm(prompt)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM JSON response.")
        logger.error("LLM response: %s", raw)
        raise


def parse_startup_from_text(text: str) -> StartupExtraction:
    chunks = _chunk_text(text)
    if len(chunks) > 1:
        summaries = [_summarize_chunk(chunk) for chunk in chunks]
        combined = "\n\n".join(summaries)
        payload = _extract_json(combined)
    else:
        payload = _extract_json(chunks[0])

    try:
        return StartupExtraction.model_validate(payload)
    except ValidationError:
        logger.error("LLM JSON failed validation.")
        logger.error("LLM parsed payload: %s", payload)
        raise
