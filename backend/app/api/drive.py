import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..integrations.drive_client import download_pdf, list_pdfs_in_folder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drive", tags=["drive"])


class DriveFile(BaseModel):
    file_id: str
    name: str
    modifiedTime: str


class DriveDownloadResponse(BaseModel):
    file_id: str
    path: str


@router.get("/decks", response_model=List[DriveFile])
def list_decks() -> List[DriveFile]:
    try:
        files = list_pdfs_in_folder()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Failed to list Drive PDFs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list Drive PDFs.",
        ) from exc

    return [
        DriveFile(file_id=file["id"], name=file["name"], modifiedTime=file["modifiedTime"])
        for file in files
    ]


@router.post("/decks/{file_id}/download", response_model=DriveDownloadResponse)
def download_deck(file_id: str) -> DriveDownloadResponse:
    destination = Path("backend/data/decks") / f"{file_id}.pdf"
    try:
        download_pdf(file_id, destination)
    except Exception as exc:
        logger.exception("Failed to download Drive PDF.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download Drive PDF.",
        ) from exc

    return DriveDownloadResponse(file_id=file_id, path=str(destination))
