#!/usr/bin/env bash
# Build this repository on Cloud Build and deploy it to Cloud Run as "dmaic-planner",
# then print the public URL. Do the one-time setup in deploy/README.md first.
#
#   deploy/cloudrun_deploy.sh [PROJECT_ID] [REGION] [MODEL]
#   MIN_INSTANCES=1 deploy/cloudrun_deploy.sh
#   deploy/cloudrun_deploy.sh another-project us-east1 placeholder
#
# PROJECT_ID defaults to dmaic-planner-ari510, REGION to us-central1, and MODEL to the
# DEFAULT_MODEL line in app/predictor.py. Every deploy sets the environment variables
# from scratch (--set-env-vars), so nothing is left over from an earlier revision.
set -euo pipefail

PROJECT_ID="${1:-dmaic-planner-ari510}"
REGION="${2:-us-central1}"
MODEL="${3:-}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-2}"
MEMORY="${MEMORY:-2Gi}"
CPU="${CPU:-1}"
SERVICE="${SERVICE:-dmaic-planner}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v gcloud >/dev/null || {
  echo "gcloud is not on PATH. Install the Google Cloud CLI and do the one-time setup in deploy/README.md." >&2
  exit 1
}
if [[ -z "$MODEL" ]]; then
  MODEL="$(sed -n 's/^DEFAULT_MODEL = "\([^"]*\)".*/\1/p' "$REPO/app/predictor.py")"
  [[ -n "$MODEL" ]] || { echo "Could not read the DEFAULT_MODEL line in app/predictor.py." >&2; exit 1; }
fi

echo "Deploying $SERVICE to project $PROJECT_ID, region $REGION, DMAIC_MODEL=$MODEL"
echo "(instances $MIN_INSTANCES-$MAX_INSTANCES, $CPU CPU, $MEMORY). The first build takes several minutes."
cd "$REPO"
gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory "$MEMORY" \
  --cpu "$CPU" \
  --cpu-boost \
  --min-instances "$MIN_INSTANCES" \
  --max-instances "$MAX_INSTANCES" \
  --session-affinity \
  --set-env-vars "DMAIC_MODEL=$MODEL,DMAIC_THREADS=$CPU"

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format 'value(status.url)')"
echo
echo "Live at: $URL"
