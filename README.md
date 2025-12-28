# Sago Re-engage Agent

End-to-end prototype for re-engaging founders using signals, Gmail/Drive context, and LLM-driven personalization. The system ingests pitch decks, builds an investor voice guide, drafts outreach emails, and logs re-engagement events.

## What this does

- Ingest a PDF deck from Google Drive and extract structured startup intelligence.
- Build an investor voice guide from sent Gmail messages.
- Score signals and decide whether to re-engage.
- Draft a personalized re-engagement email and create a Gmail draft.
- Track re-engagement events in Postgres.

## Tech stack

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy 2.0 + Postgres
- Alembic migrations
- OpenAI API
- Google OAuth (Gmail + Drive)

## Project layout

- `backend/app` – API, models, integrations, agent logic
- `backend/alembic` – migrations
- `backend/data/decks` – downloaded PDF decks (local)
- `backend/secrets` – OAuth credentials + token (local)
- `backend/README.md` – backend-specific docs and sample inputs/outputs

## Setup

### 1) Create and activate venv

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 3) Start Postgres

```bash
docker compose up -d
```

### 4) Run migrations

```bash
alembic -c backend/alembic.ini upgrade head
```

### 5) Run the API

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Environment variables

Create `backend/.env` (or export in shell):

```bash
DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/sago_reengage"
OPENAI_API_KEY="your_openai_key"
OPENAI_MODEL="gpt-4o-mini"
DRIVE_FOLDER_ID="your_drive_folder_id"
```

Optional:

```bash
DB_CONNECT_TIMEOUT=5
DB_CHECK_ON_STARTUP=true
```

## Google OAuth setup

Place your OAuth credentials at:

```
backend/secrets/credentials.json
```

On first Gmail/Drive usage, a browser window will open. The token will be stored at:

```
backend/secrets/token.json
```

If scopes change (e.g., new Gmail/Drive scopes), delete the token and re-auth:

```bash
rm backend/secrets/token.json
```

## Main flows

## Sample inputs/outputs

### Drive → ingest

List PDFs:

```bash
curl http://127.0.0.1:8000/drive/decks
```

Example response:

```json
[
  {
    "file_id": "1XyJFpPJTcR28nQVahUndRQMWZkV-Cfh7",
    "name": "Sago Assigment (Nov 25).pdf",
    "modifiedTime": "2025-12-28T03:34:37.000Z"
  }
]
```

Download a PDF:

```bash
curl -X POST http://127.0.0.1:8000/drive/decks/1XyJFpPJTcR28nQVahUndRQMWZkV-Cfh7/download
```

Example response:

```json
{
  "file_id": "1XyJFpPJTcR28nQVahUndRQMWZkV-Cfh7",
  "path": "backend/data/decks/1XyJFpPJTcR28nQVahUndRQMWZkV-Cfh7.pdf"
}
```

Ingest the downloaded PDF:

```bash
curl -X POST http://127.0.0.1:8000/ingest/pdf \
  -H "Content-Type: application/json" \
  -d '{"file_path":"backend/data/decks/1XyJFpPJTcR28nQVahUndRQMWZkV-Cfh7.pdf"}'
```

Example response:

```json
{
  "startup_id": "fa3e1cda-106d-437e-96de-f9179e29860d",
  "startup_name": "Sago",
  "interaction_id": "3acd8ab4-6034-4554-a787-7d100e8a77c2"
}
```

### Investor voice

Create an investor:

```bash
curl -X POST http://127.0.0.1:8000/investors \
  -H "Content-Type: application/json" \
  -d '{"email":"investor@example.com","name":"Test Investor"}'
```

Example response:

```json
{
  "id": "df122170-fa38-4573-aa45-ea79a53e74bc",
  "email": "investor@example.com",
  "name": "Test Investor",
  "voice_guide": null,
  "created_at": "2025-12-28T10:20:25.979400Z"
}
```

Build voice guide:

```bash
curl -X POST "http://127.0.0.1:8000/investors/df122170-fa38-4573-aa45-ea79a53e74bc/build-voice?query=label:SENT"
```

Example response:

```json
{
  "investor_id": "df122170-fa38-4573-aa45-ea79a53e74bc",
  "voice_guide": "Tone: Polite, direct, professional. Greeting style: Hi [Name], ..."
}
```

### Re-engagement

Trigger the agent:

```bash
curl -X POST http://127.0.0.1:8000/agent/reengage/599f94b9-1a80-430c-ae61-c085a7a48442 \
  -H "Content-Type: application/json" \
  -d '{
    "investor_id":"77b36c1b-2ac2-4167-9899-34aab6ba6b88",
    "signals":[
      {"type":"product","description":"Launched paid tier","score":30},
      {"type":"hiring","description":"Hired Head of Sales ex-Snowflake","score":25},
      {"type":"traction","description":"10k GitHub stars","score":20}
    ],
    "auto_send": false
  }'
```

Example response:

```json
{
  "draft_created": true,
  "draft_id": "r-3054751566628671032",
  "subject": "Reconnecting on Acme AI",
  "body": "Hi [Name], ...",
  "reason": "Signals observed: Launched paid tier, Hired Head of Sales ex-Snowflake, 10k GitHub stars. Total score is 75 and the threshold is 70."
}
```
