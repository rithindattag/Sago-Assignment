import logging
import time

from openai import OpenAI

from ..config import get_settings

logger = logging.getLogger(__name__)


def build_voice_guide(email_texts: list[str]) -> str:
    if not email_texts:
        raise ValueError("email_texts must not be empty")

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    prompt = (
        "Analyze writing style across these emails and output a concise, reusable "
        "style guide. Use this exact structure and order:\n"
        "Tone:\n"
        "Greeting style:\n"
        "Sentence length:\n"
        "Formality level:\n"
        "Common phrases:\n"
        "Things to avoid:\n"
        "Example sentence:\n\n"
        "Constraints:\n"
        "- Plain text only\n"
        "- No markdown\n"
        "- Under 200 words\n\n"
        "EMAILS:\n"
        + "\n---\n".join(email_texts)
    )

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a writing style analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            if content:
                return content.strip()
        except Exception as exc:
            last_error = exc
            logger.warning("Voice guide LLM call failed (attempt %s).", attempt + 1)
            time.sleep(1 + attempt)

    raise RuntimeError("Failed to generate voice guide.") from last_error
