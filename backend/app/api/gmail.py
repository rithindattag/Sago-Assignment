from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ..integrations.gmail_client import create_draft

router = APIRouter(prefix="/gmail", tags=["gmail"])


class GmailDraftRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class GmailDraftResponse(BaseModel):
    draft_id: str | None
    thread_id: str | None


@router.post("/draft", response_model=GmailDraftResponse, status_code=status.HTTP_201_CREATED)
def create_gmail_draft(payload: GmailDraftRequest) -> GmailDraftResponse:
    try:
        result = create_draft(payload.to_email, payload.subject, payload.body)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Gmail draft.",
        ) from exc
    return GmailDraftResponse(**result)
