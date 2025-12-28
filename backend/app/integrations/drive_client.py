import io
import logging
from pathlib import Path
from typing import Any, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ..config import get_settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

BASE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_PATH = BASE_DIR / "secrets" / "credentials.json"
TOKEN_PATH = BASE_DIR / "secrets" / "token.json"


def _load_credentials() -> Credentials | None:
    if TOKEN_PATH.exists():
        return Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    return None


def get_drive_service():
    creds = _load_credentials()

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Missing OAuth credentials at {CREDENTIALS_PATH}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TOKEN_PATH.open("w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def list_pdfs_in_folder() -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.drive_folder_id:
        raise ValueError("DRIVE_FOLDER_ID is not configured.")

    service = get_drive_service()
    query = (
        f"'{settings.drive_folder_id}' in parents and "
        "mimeType='application/pdf' and trashed=false"
    )

    try:
        response = (
            service.files()
            .list(
                q=query,
                fields="files(id, name, modifiedTime)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )
    except HttpError as exc:
        logger.exception("Drive API list failed.")
        raise RuntimeError("Failed to list Drive files.") from exc

    return response.get("files", [])


def download_pdf(file_id: str, destination_path: Path) -> Path:
    service = get_drive_service()
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    request = service.files().get_media(fileId=file_id)
    with io.FileIO(destination_path, "wb") as file_handle:
        downloader = MediaIoBaseDownload(file_handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return destination_path
