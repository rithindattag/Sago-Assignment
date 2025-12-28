# sago-reengage-agent backend

FastAPI backend scaffold with SQLAlchemy 2.0, Alembic, and structured JSON logging.

## Local setup

From the repo root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Configure the database URL (defaults to a local Postgres instance):

```bash
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/sago_reengage"
```

Optional DB startup checks:

```bash
export DB_CONNECT_TIMEOUT=5
export DB_CHECK_ON_STARTUP=true
```

Run Postgres locally with Docker Compose:

```bash
cat <<'EOF' > docker-compose.yml
services:
  postgres:
    image: postgres:16
    container_name: sago-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: sago_reengage
    ports:
      - "5432:5432"
    volumes:
      - sago_postgres_data:/var/lib/postgresql/data
volumes:
  sago_postgres_data:
EOF

docker compose up -d
```

Run the API:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```


## Gmail OAuth (first-time setup)

Ensure you have OAuth credentials at `backend/secrets/credentials.json`.

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Create a draft (first run will open a browser for OAuth consent and store
`backend/secrets/token.json`):

```bash
curl -X POST http://127.0.0.1:8000/gmail/draft \
  -H "Content-Type: application/json" \
  -d '{"to_email":"you@example.com","subject":"Hello","body":"Test draft"}'
```

## Google Drive (PDF listings + downloads)

Set the Drive folder ID (in `backend/.env` or your shell):

```bash
export DRIVE_FOLDER_ID="your_drive_folder_id"
```

List PDFs in the folder:

```bash
curl http://127.0.0.1:8000/drive/decks
```

Download a PDF by file ID:

```bash
curl -X POST http://127.0.0.1:8000/drive/decks/{file_id}/download
```

If you created `token.json` before Drive access was added, delete
`backend/secrets/token.json` and call the endpoint again to re-auth with the
Drive scope.

## PDF ingestion (LLM)

Set OpenAI credentials:

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_MODEL="gpt-4o-mini"
```

Ingest a downloaded PDF:

```bash
curl -X POST http://127.0.0.1:8000/ingest/pdf \
  -H "Content-Type: application/json" \
  -d '{"file_path":"backend/data/decks/{file_id}.pdf"}'
```

Health check:

```bash
curl http://localhost:8000/health
```

## Migrations (Alembic)

```bash
alembic -c backend/alembic.ini upgrade head
```

To generate a new migration after model changes:

```bash
alembic -c backend/alembic.ini revision --autogenerate -m "describe_change"
alembic -c backend/alembic.ini upgrade head
```

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
