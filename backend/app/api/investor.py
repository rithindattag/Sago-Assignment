import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..db import get_db
from ..integrations.gmail_client import get_sent_messages
from ..models import Investor
from ..schemas import InvestorCreate, InvestorRead
from ..rag.investor_voice import build_voice_guide

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investor", tags=["investor"])


class VoiceGuideResponse(BaseModel):
    investor_id: str
    voice_guide: str


@router.post(
    "s",
    response_model=InvestorRead,
    status_code=status.HTTP_201_CREATED,
)
def create_investor(
    payload: InvestorCreate, db: Session = Depends(get_db)
) -> InvestorRead:
    investor = Investor(email=payload.email, name=payload.name)
    try:
        db.add(investor)
        db.commit()
        db.refresh(investor)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Investor could not be created.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating investor.",
        ) from exc
    return investor


@router.get("s", response_model=list[InvestorRead])
def list_investors(db: Session = Depends(get_db)) -> list[InvestorRead]:
    result = db.execute(select(Investor).order_by(Investor.created_at.desc()))
    return result.scalars().all()


@router.post(
    "/{investor_id}/build-voice",
    response_model=VoiceGuideResponse,
    status_code=status.HTTP_200_OK,
)
def build_investor_voice(
    investor_id: UUID,
    query: str | None = Query(
        default=None,
        description="Optional Gmail search query. Defaults to sent to investor email.",
    ),
    db: Session = Depends(get_db),
) -> VoiceGuideResponse:
    investor = db.get(Investor, investor_id)
    if not investor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investor not found.",
        )

    gmail_query = query or f"label:SENT to:{investor.email}"
    try:
        messages = get_sent_messages(max_results=50, query=gmail_query)
    except Exception as exc:
        logger.exception("Failed to fetch sent emails from Gmail.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch sent emails.",
        ) from exc

    texts: List[str] = []
    for message in messages:
        body = (message.get("body") or "").strip()
        snippet = (message.get("snippet") or "").strip()
        if body:
            texts.append(body)
        elif snippet:
            texts.append(snippet)

    if not texts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sent emails found for investor.",
        )

    try:
        voice_guide = build_voice_guide(texts)
    except Exception as exc:
        logger.exception("Failed to build voice guide.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build voice guide.",
        ) from exc

    investor.voice_guide = voice_guide
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist voice guide.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store voice guide.",
        ) from exc

    return VoiceGuideResponse(investor_id=str(investor.id), voice_guide=voice_guide)


@router.get("/{investor_id}/voice", response_model=VoiceGuideResponse)
def get_investor_voice(
    investor_id: UUID, db: Session = Depends(get_db)
) -> VoiceGuideResponse:
    investor = db.get(Investor, investor_id)
    if not investor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investor not found.",
        )
    if not investor.voice_guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice guide not found.",
        )

    return VoiceGuideResponse(
        investor_id=str(investor.id),
        voice_guide=investor.voice_guide,
    )
