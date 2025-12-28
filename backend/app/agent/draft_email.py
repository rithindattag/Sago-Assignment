import json
import logging
import time
from typing import Any, Dict

from openai import OpenAI

from ..config import get_settings

logger = logging.getLogger(__name__)


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
                        "content": "You draft concise, professional outreach emails.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            if content:
                return content
        except Exception as exc:
            last_error = exc
            logger.warning("Draft email LLM call failed (attempt %s).", attempt + 1)
            time.sleep(1 + attempt)

    raise RuntimeError("Failed to draft outreach email.") from last_error


def draft_reengagement_email(
    investor_voice: str,
    startup_summary: str,
    interaction_history: str,
    decision_reason: str,
) -> Dict[str, Any]:
    prompt = (
        "Write a personalized re-engagement email in the investor's voice. "
        "Reference prior context using phrasing like 'when we last spoke'. "
        "Mention why now based on the decision reason. "
        "Keep it concise, professional, and human.\n\n"
        "Constraints:\n"
        "- No hype\n"
        "- No emojis\n"
        "- Max 120 words\n"
        "- Output STRICT JSON only: {\"subject\": string, \"body\": string}\n\n"
        f"VOICE GUIDE:\n{investor_voice}\n\n"
        f"STARTUP SUMMARY:\n{startup_summary}\n\n"
        f"INTERACTION HISTORY:\n{interaction_history}\n\n"
        f"DECISION REASON:\n{decision_reason}"
    )

    raw = _call_llm(prompt)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM JSON response.")
        logger.error("LLM response: %s", raw)
        raise RuntimeError("Invalid JSON from LLM.") from exc

    subject = str(payload.get("subject", "")).strip()
    body = str(payload.get("body", "")).strip()
    if not subject or not body:
        raise RuntimeError("LLM response missing subject or body.")

    return {"subject": subject, "body": body}
