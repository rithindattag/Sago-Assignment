import json
import logging
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from ..agent.decide_reengage import decide_reengage
from ..agent.draft_email import draft_reengagement_email
from ..integrations.gmail_client import create_draft, send_draft
from ..models import Interaction, ReengagementEvent, Startup, Investor

logger = logging.getLogger(__name__)


def _build_startup_summary(startup: Startup, interactions: list[Interaction]) -> str:
    summary = None
    for interaction in interactions:
        try:
            payload = json.loads(interaction.content)
            if isinstance(payload, dict):
                summary = payload.get("summary") or summary
        except Exception:
            continue
        if summary:
            break

    base = f"Startup: {startup.name}."
    if startup.domain:
        base += f" Domain: {startup.domain}."
    if summary:
        base += f" Summary: {summary}"
    return base.strip()


def _build_interaction_history(interactions: list[Interaction]) -> str:
    snippets: list[str] = []
    for interaction in interactions[:5]:
        text = interaction.content
        try:
            payload = json.loads(interaction.content)
            if isinstance(payload, dict):
                text = payload.get("summary") or interaction.content
        except Exception:
            pass
        snippets.append(f"{interaction.source}: {text}")
    return "\n".join(snippets)


def execute_reengagement(
    investor: Investor,
    startup: Startup,
    signals: List[Dict[str, Any]],
    auto_send: bool = False,
) -> Dict[str, Any]:
    decision = decide_reengage(signals)
    if not decision.get("should_reengage"):
        return decision

    session = object_session(investor) or object_session(startup)
    if session is None:
        raise RuntimeError("Investor and startup must be attached to a session.")

    result = session.execute(
        select(Interaction)
        .where(Interaction.startup_id == startup.id)
        .order_by(Interaction.created_at.desc())
    )
    interactions = result.scalars().all()

    startup_summary = _build_startup_summary(startup, interactions)
    interaction_history = _build_interaction_history(interactions)

    if not investor.voice_guide:
        raise RuntimeError("Investor voice_guide is not set.")

    draft_payload = draft_reengagement_email(
        investor_voice=investor.voice_guide,
        startup_summary=startup_summary,
        interaction_history=interaction_history,
        decision_reason=decision.get("reason", ""),
    )

    draft_meta = create_draft(
        to_email=investor.email,
        subject=draft_payload["subject"],
        body=draft_payload["body"],
    )

    status = "drafted"
    if auto_send and draft_meta.get("draft_id"):
        try:
            send_draft(draft_meta["draft_id"])
            status = "sent"
        except Exception:
            logger.exception("Failed to send Gmail draft.")

    event = ReengagementEvent(
        startup_id=startup.id,
        investor_id=investor.id,
        reason=decision.get("reason", ""),
        draft_id=draft_meta.get("draft_id") or "",
        status=status,
    )
    session.add(event)
    session.commit()

    return {
        "draft_created": True,
        "draft_id": draft_meta.get("draft_id"),
        "subject": draft_payload["subject"],
        "body": draft_payload["body"],
        "reason": decision.get("reason", ""),
    }
