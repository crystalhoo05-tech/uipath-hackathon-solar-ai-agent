# Solar Post-Installation Diagnostic API

AI agent API for diagnosing solar PV systems after installation. Powered by **Google Gemini**, packaged for deployment on **GCP Cloud Run**.

## Features

- **POST `/api/v1/diagnostics/run`** — Full structured diagnostic from installation specs, telemetry, and field notes
- **POST `/api/v1/diagnostics/chat`** — Follow-up Q&A with the diagnostic agent
- **GET `/health`** — Health check for Cloud Run
- **Gemini auth** — Google AI Studio API key (local dev) or Vertex AI via service account (GCP production)

## Requirements

- Python 3.11+
- Gemini API key **or** GCP project with Vertex AI enabled

## Local setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
cp .env.example .env
# Add your GEMINI_API_KEY to .env
```

## Run locally

```bash
python main.py
```

Optional flags:

```bash
python main.py --host 127.0.0.1 --port 8080
```

Other ways to start the server:

```bash
solar-diagnostic-api
uvicorn hackathon_ai_uipath.api.app:app --reload --port 8080
```

Open API docs at [http://localhost:8080/docs](http://localhost:8080/docs).

## Example request

```bash
curl -X POST http://localhost:8080/api/v1/diagnostics/run \
  -H "Content-Type: application/json" \
  -d @examples/diagnostic_request.json
```

Example response:

```json
{
  "installation_id": "SOL-2024-001",
  "overall_status": "fail",
  "summary": "String 4 is offline; production significantly below expected.",
  "findings": [
    {
      "category": "electrical",
      "severity": "critical",
      "title": "String 4 at 0V",
      "description": "...",
      "evidence": "string_voltages[3] = 0.0"
    }
  ],
  "recommendations": ["..."],
  "priority_actions": ["..."],
  "estimated_impact": "~25% production loss",
  "follow_up_questions": ["..."]
}
```

## Deploy to GCP (Cloud Run)

The recommended production setup uses **Vertex AI Gemini** with a Cloud Run service account (no API key in the container).

### Prerequisites

- `gcloud` CLI authenticated
- GCP project with billing enabled

### One-command deploy

```bash
chmod +x deploy/gcp/deploy.sh
./deploy/gcp/deploy.sh YOUR_GCP_PROJECT_ID
```

This script:

1. Enables Cloud Run, Artifact Registry, Cloud Build, and Vertex AI APIs
2. Creates an Artifact Registry repo and service account
3. Grants `roles/aiplatform.user` to the service account
4. Builds the Docker image and deploys to Cloud Run

### Manual deploy

```bash
gcloud builds submit --config=deploy/gcp/cloudbuild.yaml --project=YOUR_GCP_PROJECT_ID
```

### Environment variables (Cloud Run)

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID (enables Vertex AI) |
| `GOOGLE_CLOUD_LOCATION` | Region, e.g. `us-central1` |
| `GEMINI_MODEL` | Model name, default `gemini-2.0-flash` |
| `GEMINI_API_KEY` | Optional; use for dev instead of Vertex AI |
| `ENVIRONMENT` | `production` or `development` |

## Project structure

```
src/hackathon_ai_uipath/
├── agents/          # Gemini client + solar diagnostic agent
├── api/             # FastAPI app and routes
├── models/          # Pydantic request/response schemas
└── config.py        # Environment-based settings
deploy/gcp/            # Cloud Build + deploy script
examples/              # Sample API payloads
```

## Development

```bash
pytest
ruff check src tests
```

## UiPath integration

This API is designed to be called from a UiPath workflow after field data collection:

1. UiPath robot gathers inverter telemetry, inspection photos/notes, and commissioning checklist
2. Robot POSTs payload to `/api/v1/diagnostics/run`
3. Agent returns structured findings and priority actions
4. UiPath routes critical issues to ticketing and logs the report
