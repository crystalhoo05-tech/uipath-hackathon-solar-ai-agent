# Solar Post-Installation Support — UiPath + Gemini AI

End-to-end solar post-installation support automation for the UiPath hackathon. A customer-reported issue flows through **UiPath Agent Builder agents** and a **Maestro agentic process**, with a **custom Python/Gemini diagnostic API** handling the reboot-and-verify AI brain.

---

## What this project does

This solution automates solar post-installation support from customer intake through AI diagnosis, optional remote reboot, and human engineer review.

### Business flow

1. **Customer reports an issue** (e.g. missing generation data in the portal, low output).
2. **Solar AI Intake Agent** (Agent Builder) classifies the issue, assigns priority, checks for missing information, and creates a structured case.
3. **Solar Diagnostic Agent (External API)** runs a diagnose → mock remote reboot → post-reboot analysis workflow powered by **Google Gemini**.
4. **UiPath branches on the result:**
   - `workflow_status = "resolved"` → close the case (reboot fixed cloud sync / generation reporting).
   - `workflow_status = "needs_engineer_review"` → route to human engineer with `engineer_debug_steps`.
5. **Human-in-the-loop** steps (engineer review, site inspection scheduling, warranty handling, customer notification) complete the case in Maestro.

### Diagnostic AI workflow (external API)

Every diagnostic case runs this pipeline:

| Step | Action |
|------|--------|
| 1 | Initial diagnosis on pre-reboot telemetry |
| 2 | Mock remote reboot (simulated inverter cloud sync) |
| 3 | Collect post-reboot telemetry (simulated or provided) |
| 4 | **Gemini AI verdict** — compare pre/post data and decide resolved vs escalate |

---

## Agent approach: combination

> **This solution uses a combination of low-code Agent Builder agents and a custom-coded AI agent.**

| Layer | Type | Technology |
|-------|------|------------|
| **Intake & case structuring** | Low-code agent (Agent Builder) | `Solar AI Intake Agent` |
| **Diagnostic investigation (in-process)** | Low-code agent (Agent Builder) | `Solar AI Diagnostic Agent` |
| **Reboot + Gemini AI verdict** | **Custom-coded agent** | Python / FastAPI / Google Gemini on GCP Cloud Run |
| **Orchestration** | Maestro agentic process | BPMN workflow in `Agentic Process` |

The Maestro process calls the external Python API via **HTTP Request** when the reboot-and-verify brain is needed. Agent Builder agents handle structured intake and in-platform diagnostic reasoning; the custom API adds Gemini-powered reboot workflow logic that is not available out of the box in Agent Builder.

---

## UiPath components used

The solution package is included as:

`UIPath Solution - Solar Panel Installation Post Support.uis`

### Agent Builder (low-code agents)

| Agent | Role |
|-------|------|
| **Solar AI Intake Agent** | Receives customer details, classifies issue category, assigns priority, flags missing info, generates `caseId` and case summary |
| **Solar AI Diagnostic Agent** | Analyses system telemetry, alert history, and historical cases; returns root-cause analysis and recommended next action |

Both agents are `type: "lowCode"` Agent Builder agents with structured JSON input/output schemas.

### Maestro / Agentic Process

| Component | Role |
|-----------|------|
| **Agentic Process** (BPMN) | End-to-end case orchestration |
| **Orchestrator.StartAgentJob** | Invokes Solar AI Intake Agent |
| **HTTP Request** (`uipath-uipath-http`) | Calls the external Gemini diagnostic API |
| **Exclusive / parallel gateways** | Branch on diagnostic result, warranty, engineer decision |
| **Solar Engineer Review (HITL)** | Human-in-the-loop script task for engineer approval |
| **SimpleApprovalApp** | Workflow App for human review actions |
| **User tasks** | Schedule site inspection, confirm issue resolved |
| **Orchestrator queues** | `EngineerReviewQueue` and related queues for task routing |
| **Service tasks** | Create technician task, notify customer, submit warranty request |

### External integration

| Component | Role |
|-----------|------|
| **Solar Diagnostic API** (this repo) | FastAPI service on GCP Cloud Run; Gemini via Vertex AI |

**Hosted API URL:**

```
https://solar-diagnostic-api-yguvvsuspa-uc.a.run.app
```

**Endpoint used by UiPath:**

```
POST /api/v1/diagnostics/run
```

---

## Prerequisites

### For the Python diagnostic API

- Python 3.11+
- Google Gemini access via **one** of:
  - **Vertex AI** on GCP (recommended for production / Cloud Run)
  - **Google AI Studio API key** (local development)
- For GCP deployment:
  - `gcloud` CLI authenticated
  - GCP project with billing enabled
  - Vertex AI API enabled

### For the UiPath solution

- UiPath Automation Cloud or on-prem Orchestrator
- UiPath Studio Web (for Maestro / Agentic Process)
- UiPath Agent Builder (for low-code agents)
- Access to deploy/import the `.uis` solution package
- Network access from Orchestrator to the Cloud Run API URL

---

## Setup instructions

### 1. Clone and install the Python API

```bash
git clone <your-repo-url>
cd hackathon-ai-uipath

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
# Skip Gemini locally (rule-based fallback). Set false to enable AI brain.
DEMO_MODE=false

# Option A — Vertex AI (same as Cloud Run)
GEMINI_API_KEY=
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Option B — Google AI Studio (local dev)
# GEMINI_API_KEY=AIza...
# GOOGLE_CLOUD_PROJECT=

GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MODEL_FALLBACKS=gemini-2.5-flash,gemini-2.0-flash

HOST=0.0.0.0
PORT=8080
LOG_LEVEL=info
```

For Vertex AI locally, authenticate once:

```bash
gcloud auth application-default login
```

### 3. Run the API locally

```bash
python main.py
```

Open interactive docs at [http://localhost:8080/docs](http://localhost:8080/docs).

### 4. Test with example payloads

```bash
# Healthy pass case
curl -X POST http://localhost:8080/api/v1/diagnostics/run \
  -H "Content-Type: application/json" \
  -d @examples/01_healthy_pass.json

# Reboot resolves (comm stale → fixed after reboot)
curl -X POST http://localhost:8080/api/v1/diagnostics/run \
  -H "Content-Type: application/json" \
  -d @examples/06_reboot_resolves_case.json

# Reboot fails → escalate to engineer
curl -X POST http://localhost:8080/api/v1/diagnostics/run \
  -H "Content-Type: application/json" \
  -d @examples/07_reboot_needs_engineer.json
```

### 5. Deploy to GCP Cloud Run

```bash
chmod +x deploy/gcp/deploy.sh
./deploy/gcp/deploy.sh YOUR_GCP_PROJECT_ID
```

Allow public access for UiPath / Postman (if needed):

```bash
gcloud run services add-iam-policy-binding solar-diagnostic-api \
  --region=us-central1 \
  --project=YOUR_GCP_PROJECT_ID \
  --member="allUsers" \
  --role="roles/run.invoker"
```

### 6. Import the UiPath solution

1. Open **UiPath Studio Web** or **Automation Cloud → Solutions**.
2. Import `UIPath Solution - Solar Panel Installation Post Support.uis`.
3. Publish **Solar AI Intake Agent** and **Solar AI Diagnostic Agent** to Orchestrator.
4. Open **Agentic Process** and confirm the HTTP Request step points to your API URL:
   ```
   https://solar-diagnostic-api-yguvvsuspa-uc.a.run.app/api/v1/diagnostics/run
   ```
5. Publish the Maestro process and run a test case.

Use `examples/uipath_request_template.json` as the HTTP body template when wiring variables from the intake agent output.

---

## API reference

### `POST /api/v1/diagnostics/run`

Runs the full diagnostic + reboot + AI verdict workflow.

**Request body** (see `examples/`):

```json
{
  "caseId": "CASE-2025-101",
  "issueCategory": "Performance",
  "priority": "Low",
  "caseSummary": "Customer reports system operating normally.",
  "solarSystemId": "SOL-2025-101",
  "customerId": "CUST-88421",
  "warrantyEligibilityFlag": true,
  "systemData": {
    "currentOutputKw": 6.8,
    "expectedOutputKw": 7.0,
    "inverterStatus": "Online",
    "batteryChargePercent": 82,
    "lastCommunication": "2025-06-20T14:30:00Z",
    "gridConnectionStatus": "Connected"
  },
  "alertHistory": [],
  "historicalCases": []
}
```

**Key response fields for UiPath branching:**

| Field | Values | UiPath action |
|-------|--------|---------------|
| `workflow_status` | `"resolved"` | Close case |
| `workflow_status` | `"needs_engineer_review"` | Create engineer ticket, send `engineer_debug_steps` |
| `overall_status` | `"pass"` / `"warning"` / `"fail"` | Logging and reporting |
| `workflow_steps` | Array of 4 steps | Audit trail (includes **AI verdict** step) |
| `resolution_summary` | String | Customer / case closure note |

### `POST /api/v1/diagnostics/chat`

Follow-up Q&A with the diagnostic agent (optional).

### `GET /health`

Health check for Cloud Run and monitoring.

---

## Example test files

| File | Scenario | Expected `workflow_status` |
|------|----------|---------------------------|
| `examples/01_healthy_pass.json` | Healthy system, no alerts | `resolved` |
| `examples/06_reboot_resolves_case.json` | COMM-STALE, low output | `resolved` |
| `examples/07_reboot_needs_engineer.json` | Critical underproduction persists | `needs_engineer_review` |
| `examples/chat_followup.json` | Chat follow-up payload | — |

---

## Project structure

```
hackathon-ai-uipath/
├── main.py                          # Local entry point (python main.py)
├── src/hackathon_ai_uipath/
│   ├── agents/
│   │   ├── gemini_client.py         # Gemini client (AI Studio + Vertex AI)
│   │   ├── solar_diagnostic_agent.py
│   │   └── diagnostic_workflow.py   # Reboot workflow logic
│   ├── api/                         # FastAPI routes
│   ├── models/schemas.py            # Request/response Pydantic models
│   └── config.py
├── deploy/gcp/                      # Cloud Build + deploy script
├── examples/                        # Sample JSON payloads
├── tests/
└── UIPath Solution - Solar Panel Installation Post Support.uis
```

---

## Development

```bash
pytest
ruff check src tests
```

---

## Architecture diagram

```
Customer issue
      │
      ▼
┌─────────────────────────┐
│  Solar AI Intake Agent  │  ← Agent Builder (low-code)
│  classify · prioritize  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Maestro Agentic Process│  ←  Orchestration
│  HTTP Request activity  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Solar Diagnostic API   │  ← Custom-coded (Python + Gemini)
│  diagnose → reboot → AI │
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     ▼             ▼
 resolved    needs_engineer_review
     │             │
     ▼             ▼
 Close case   HITL engineer review
               → site visit / warranty / notify
```

---