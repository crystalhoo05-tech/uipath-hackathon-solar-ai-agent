#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-solar-diagnostic-api}"
ARTIFACT_REPO="${ARTIFACT_REPO:-solar-diagnostic}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-solar-diagnostic-api@${PROJECT_ID}.iam.gserviceaccount.com}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Usage: ./deploy/gcp/deploy.sh <gcp-project-id>"
  exit 1
fi

echo "Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  --project="${PROJECT_ID}"

echo "Creating Artifact Registry repo (if needed)..."
gcloud artifacts repositories describe "${ARTIFACT_REPO}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" 2>/dev/null || \
gcloud artifacts repositories create "${ARTIFACT_REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}"

echo "Creating service account (if needed)..."
gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" 2>/dev/null || \
gcloud iam service-accounts create solar-diagnostic-api \
  --display-name="Solar Diagnostic API" \
  --project="${PROJECT_ID}"

echo "Granting Vertex AI access..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user" \
  --quiet

echo "Submitting Cloud Build..."
SHORT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo manual)"
gcloud builds submit \
  --config=deploy/gcp/cloudbuild.yaml \
  --substitutions=_REGION="${REGION}",_SERVICE_ACCOUNT="${SERVICE_ACCOUNT}",SHORT_SHA="${SHORT_SHA}" \
  --project="${PROJECT_ID}"

echo "Deployment complete."
echo
echo "Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)'
