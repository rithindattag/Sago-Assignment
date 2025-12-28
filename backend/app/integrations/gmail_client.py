import base64
import json
import re
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

BASE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_PATH = BASE_DIR / "secrets" / "credentials.json"
TOKEN_PATH = BASE_DIR / "secrets" / "token.json"


def get_gmail_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

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

    return build("gmail", "v1", credentials=creds)


def create_draft(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    service = get_gmail_service()

    message = EmailMessage()
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    draft_body = {"message": {"raw": encoded_message}}

    draft = (
        service.users()
        .drafts()
        .create(userId="me", body=draft_body)
        .execute()
    )

    draft_id = draft.get("id")
    thread_id = None
    message_meta = draft.get("message")
    if isinstance(message_meta, dict):
        thread_id = message_meta.get("threadId")

    return {"draft_id": draft_id, "thread_id": thread_id}


def _extract_body_from_payload(payload: Dict[str, Any]) -> str:
    body = payload.get("body") or {}
    data = body.get("data")
    if data:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode(
            "utf-8", "ignore"
        )

    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain":
            return _extract_body_from_payload(part)

    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/html":
            return _extract_body_from_payload(part)

    return ""


def _strip_signature_and_quotes(body: str) -> str:
    cleaned: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            break
        if re.match(r"^On .+ wrote:$", stripped):
            break
        if stripped in ("--", "__", "---"):
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def get_sent_messages(
    max_results: int = 20, query: str = "label:SENT"
) -> list[Dict[str, Any]]:
    service = get_gmail_service()
    messages: list[Dict[str, Any]] = []
    page_token: str | None = None

    while len(messages) < max_results:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=min(100, max_results - len(messages)),
                pageToken=page_token,
            )
            .execute()
        )
        for item in response.get("messages", []) or []:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=item["id"], format="full")
                .execute()
            )
            payload = msg.get("payload", {})
            raw_body = _extract_body_from_payload(payload)
            cleaned_body = _strip_signature_and_quotes(raw_body)
            messages.append(
                {
                    "id": msg.get("id"),
                    "thread_id": msg.get("threadId"),
                    "snippet": msg.get("snippet") or "",
                    "body": cleaned_body,
                }
            )
            if len(messages) >= max_results:
                break
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return messages


def get_sent_email_texts(max_results: int = 20) -> list[str]:
    service = get_gmail_service()
    texts: list[str] = []
    page_token: str | None = None

    while len(texts) < max_results:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q="label:SENT",
                maxResults=min(100, max_results - len(texts)),
                pageToken=page_token,
            )
            .execute()
        )
        for item in response.get("messages", []) or []:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=item["id"], format="full")
                .execute()
            )
            payload = msg.get("payload", {})
            raw_body = _extract_body_from_payload(payload)
            cleaned_body = _strip_signature_and_quotes(raw_body)
            if cleaned_body:
                texts.append(cleaned_body)
            if len(texts) >= max_results:
                break
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return texts


def send_draft(draft_id: str) -> Dict[str, Any]:
    service = get_gmail_service()
    result = (
        service.users()
        .drafts()
        .send(userId="me", body={"id": draft_id})
        .execute()
    )
    return {
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
    }
