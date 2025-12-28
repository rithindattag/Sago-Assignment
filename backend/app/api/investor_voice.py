import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..integrations.gmail_client import get_sent_email_texts
from ..models import Investor
from ..rag.investor_voice import build_voice_guide

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investors", tags=["investors"])


class VoiceGuideResponse(BaseModel):
    investor_id: str
    voice_guide: str


@router.post(
    "/{investor_id}/build-voice",
    response_model=VoiceGuideResponse,
    status_code=status.HTTP_200_OK,
)
def build_investor_voice(
    investor_id: UUID, db: Session = Depends(get_db)
) -> VoiceGuideResponse:
    investor = db.get(Investor, investor_id)
    if not investor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investor not found.",
        )

    try:
        texts = get_sent_email_texts(max_results=50)
    except Exception as exc:
        logger.exception("Failed to fetch sent emails from Gmail.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch sent emails.",
        ) from exc

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
