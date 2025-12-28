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

### 1) Drive → Download → Ingest

```bash
curl http://127.0.0.1:8000/drive/decks
curl -X POST http://127.0.0.1:8000/drive/decks/{file_id}/download
curl -X POST http://127.0.0.1:8000/ingest/pdf \
  -H "Content-Type: application/json" \
  -d '{"file_path":"backend/data/decks/{file_id}.pdf"}'
```

### 2) Investor voice profiling

```bash
curl -X POST http://127.0.0.1:8000/investors \
  -H "Content-Type: application/json" \
  -d '{"email":"you@domain.com","name":"You"}'

curl -X POST "http://127.0.0.1:8000/investors/{investor_id}/build-voice?query=label:SENT"
```

### 3) Re-engagement decision + draft

```bash
curl -X POST http://127.0.0.1:8000/agent/reengage/{startup_id} \
  -H "Content-Type: application/json" \
  -d '{
    "investor_id":"{investor_id}",
    "signals":[
      {"type":"product","description":"Launched paid tier","score":30},
      {"type":"hiring","description":"Hired Head of Sales ex-Snowflake","score":25},
      {"type":"traction","description":"10k GitHub stars","score":20}
    ],
    "auto_send": false
  }'
```

## API endpoints (high level)

- `GET /health`
- `POST /startups`, `GET /startups`, `GET /startups/{startup_id}`
- `POST /investors`, `GET /investors`
- `POST /investors/{investor_id}/build-voice`, `GET /investors/{investor_id}/voice`
- `POST /gmail/draft`
- `GET /drive/decks`, `POST /drive/decks/{file_id}/download`
- `POST /ingest/pdf`
- `POST /agent/reengage/{startup_id}`, `GET /agent/reengagements`

## Notes

- `backend/data/` and `backend/secrets/` are local-only and excluded via `.gitignore`.
- This is a prototype; auth, rate limits, and PII handling should be tightened for production.

## License

Internal prototype for evaluation.
