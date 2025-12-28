import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Interaction, Startup
from ..rag.ingest_deck import extract_text_from_pdf, parse_startup_from_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    file_path: str = Field(min_length=1)


class IngestResponse(BaseModel):
    startup_id: str
    startup_name: str
    interaction_id: str


@router.post("/pdf", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_pdf(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    pdf_path = Path(payload.file_path)
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found.",
        )

    try:
        text = extract_text_from_pdf(str(pdf_path))
    except Exception as exc:
        logger.exception("Failed to extract PDF text.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract PDF text.",
        ) from exc

    try:
        extraction = parse_startup_from_text(text)
    except Exception as exc:
        logger.exception("Failed to parse startup from PDF text.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse startup information.",
        ) from exc

    startup = _get_startup_by_name(db, extraction.startup_name)
    if startup is None:
        startup = Startup(
            name=extraction.startup_name,
            domain=extraction.domain,
            founder_email=extraction.founder_email,
            status="watching",
        )
        db.add(startup)
    else:
        startup.domain = startup.domain or extraction.domain
        startup.founder_email = startup.founder_email or extraction.founder_email

    interaction_payload = {
        "summary": extraction.summary,
        "extracted": extraction.model_dump(),
    }
    interaction = Interaction(
        startup=startup,
        source="deck",
        content=json.dumps(interaction_payload, ensure_ascii=True),
    )
    db.add(interaction)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist ingestion results.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist ingestion results.",
        ) from exc

    db.refresh(startup)
    db.refresh(interaction)

    return IngestResponse(
        startup_id=str(startup.id),
        startup_name=startup.name,
        interaction_id=str(interaction.id),
    )


def _get_startup_by_name(db: Session, name: str) -> Optional[Startup]:
    result = db.execute(select(Startup).where(Startup.name == name))
    return result.scalars().first()
