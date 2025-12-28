import logging
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agent.execute import execute_reengagement
from ..db import get_db
from ..models import Investor, ReengagementEvent, Startup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


class Signal(BaseModel):
    type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    score: float = Field(ge=0, le=100)


class ReengageRequest(BaseModel):
    investor_id: UUID
    signals: List[Signal]
    auto_send: bool = False


@router.post("/reengage/{startup_id}")
def reengage(
    startup_id: UUID, payload: ReengageRequest, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    investor = db.get(Investor, payload.investor_id)
    if not investor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investor not found.",
        )

    startup = db.get(Startup, startup_id)
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Startup not found.",
        )

    try:
        result = execute_reengagement(
            investor=investor,
            startup=startup,
            signals=[signal.model_dump() for signal in payload.signals],
            auto_send=payload.auto_send,
        )
    except Exception as exc:
        logger.exception("Failed to execute reengagement.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute reengagement.",
        ) from exc

    return result


class ReengagementEventResponse(BaseModel):
    id: str
    startup_id: str
    investor_id: str
    reason: str
    draft_id: str
    status: str
    created_at: str


@router.get("/reengagements", response_model=list[ReengagementEventResponse])
def list_reengagements(
    startup_id: UUID | None = None,
    investor_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> list[ReengagementEventResponse]:
    stmt = select(ReengagementEvent).order_by(ReengagementEvent.created_at.desc())
    if startup_id:
        stmt = stmt.where(ReengagementEvent.startup_id == startup_id)
    if investor_id:
        stmt = stmt.where(ReengagementEvent.investor_id == investor_id)
    result = db.execute(stmt)
    events = result.scalars().all()

    return [
        ReengagementEventResponse(
            id=str(event.id),
            startup_id=str(event.startup_id),
            investor_id=str(event.investor_id),
            reason=event.reason,
            draft_id=event.draft_id,
            status=event.status,
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]
