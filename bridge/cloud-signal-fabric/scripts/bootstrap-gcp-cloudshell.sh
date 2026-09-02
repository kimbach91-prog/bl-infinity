#!/usr/bin/env bash
set -Eeuo pipefail

# DEUS Signal Fabric — one-shot GCP bootstrap + first deployment.
# Intended to be run from Google Cloud Shell by the project owner/admin.
# No static service-account key is created.

PROJECT_ID="${PROJECT_ID:-buoyant-mason-114302}"
PROJECT_NUMBER_EXPECTED="${PROJECT_NUMBER_EXPECTED:-580664224085}"
REGION="${REGION:-asia-southeast1}"
FIRESTORE_LOCATION="${FIRESTORE_LOCATION:-asia-southeast1}"
REPO_URL="${REPO_URL:-https://github.com/kimbach91-prog/bl-infinity.git}"
REPO_SLUG="${REPO_SLUG:-kimbach91-prog/bl-infinity}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-deus/signal-fabric-gcp-v1}"

SERVICE="deus-signal-fabric"
RUNTIME_SA_NAME="deus-signal-fabric"
SCHEDULER_SA_NAME="deus-signal-scheduler"
DEPLOY_SA_NAME="deus-github-deploy"
POOL_ID="deus-github"
PROVIDER_ID="bl-infinity"

DRIVE_PARENT_FOLDER_ID="19SL26W6guCXVrXM7eP1eWFpKUxJNdUVr"
DRIVE_MANIFEST_FOLDER_ID="17xOH5L1K9149PXKcBjvQ9qVgnq6faoYV"
DRIVE_ARTIFACTS_ID="1jrAdJxsQLdKnhY6oWloZRQ8KBTwKSlo1"

say() { printf '\n\033[1;36m[DEUS]\033[0m %s\n' "$*"; }
warn() { printf '\n\033[1;33m[DEUS WARN]\033[0m %s\n' "$*" >&2; }

command -v gcloud >/dev/null || { echo 'gcloud is required. Run this in Google Cloud Shell.' >&2; exit 1; }
command -v git >/dev/null || { echo 'git is required.' >&2; exit 1; }

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1 || true)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo 'No active gcloud identity. Open Google Cloud Shell while signed into the owning account.' >&2
  exit 1
fi

say "Active Google identity: $ACTIVE_ACCOUNT"
say "Binding installer to project: $PROJECT_ID"
gcloud config set project "$PROJECT_ID" >/dev/null

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
PROJECT_STATE="$(gcloud projects describe "$PROJECT_ID" --format='value(lifecycleState)')"
if [[ "$PROJECT_STATE" != "ACTIVE" ]]; then
  echo "Project is not ACTIVE: $PROJECT_STATE" >&2
  exit 1
fi
if [[ -n "$PROJECT_NUMBER_EXPECTED" && "$PROJECT_NUMBER" != "$PROJECT_NUMBER_EXPECTED" ]]; then
  warn "Observed project number $PROJECT_NUMBER differs from expected $PROJECT_NUMBER_EXPECTED. Continuing only because PROJECT_ID resolved successfully."
fi

RUNTIME_SA="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SCHEDULER_SA="${SCHEDULER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
DEPLOY_SA="${DEPLOY_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

say 'Enabling required Google APIs'
gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  serviceusage.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  cloudscheduler.googleapis.com \
  drive.googleapis.com

create_sa() {
  local name="$1" display="$2" email="${name}@${PROJECT_ID}.iam.gserviceaccount.com"
  if ! gcloud iam service-accounts describe "$email" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$name" --display-name="$display"
  fi
}

say 'Creating dedicated identities'
create_sa "$RUNTIME_SA_NAME" 'DEUS Signal Fabric runtime'
create_sa "$SCHEDULER_SA_NAME" 'DEUS Signal Fabric scheduler'
create_sa "$DEPLOY_SA_NAME" 'DEUS GitHub deployer'

say 'Granting runtime roles'
for role in roles/datastore.user roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${RUNTIME_SA}" --role="$role" --condition=None >/dev/null
 done

say 'Granting GitHub deployer roles'
DEPLOY_ROLES=(
  roles/serviceusage.serviceUsageAdmin
  roles/serviceusage.serviceUsageConsumer
  roles/run.admin
  roles/run.sourceDeveloper
  roles/iam.serviceAccountAdmin
  roles/iam.serviceAccountUser
  roles/resourcemanager.projectIamAdmin
  roles/datastore.owner
  roles/cloudscheduler.admin
)
for role in "${DEPLOY_ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${DEPLOY_SA}" --role="$role" --condition=None >/dev/null
 done

# Cloud Run source deploys use Cloud Build. Newer projects might not auto-grant broad
# default-SA roles, so explicitly grant only the documented Cloud Run Builder role.
say 'Hardening Cloud Build service identity for source deploys'
for _ in $(seq 1 12); do
  if gcloud iam service-accounts describe "$COMPUTE_SA" >/dev/null 2>&1; then break; fi
  sleep 5
done
if gcloud iam service-accounts describe "$COMPUTE_SA" >/dev/null 2>&1; then
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${COMPUTE_SA}" --role='roles/run.builder' --condition=None >/dev/null
else
  warn "Compute default service account $COMPUTE_SA is not visible yet. Source deployment may create it later; if build fails, rerun this script."
fi

say 'Creating Firestore native database when absent'
if ! gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
  gcloud firestore databases create \
    --database='(default)' \
    --location="$FIRESTORE_LOCATION" \
    --type=firestore-native
fi

say 'Creating GitHub → GCP Workload Identity Federation'
if ! gcloud iam workload-identity-pools describe "$POOL_ID" --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL_ID" \
    --location=global \
    --display-name='DEUS GitHub' \
    --description='Keyless GitHub Actions identity for bl-infinity'
fi

if ! gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
    --location=global --workload-identity-pool="$POOL_ID" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
    --location=global \
    --workload-identity-pool="$POOL_ID" \
    --display-name='bl-infinity GitHub OIDC' \
    --issuer-uri='https://token.actions.githubusercontent.com/' \
    --attribute-mapping='google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref' \
    --attribute-condition="assertion.repository=='${REPO_SLUG}' && assertion.repository_owner=='kimbach91-prog'"
fi

PRINCIPAL_SET="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO_SLUG}"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --role='roles/iam.workloadIdentityUser' \
  --member="$PRINCIPAL_SET" >/dev/null

WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

say 'Checking out the DEUS deployment source'
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
git clone --depth=1 --branch "$DEPLOY_BRANCH" "$REPO_URL" "$WORKDIR/bl-infinity"
cd "$WORKDIR/bl-infinity"

say 'Deploying private DEUS Signal Fabric to Cloud Run'
gcloud run deploy "$SERVICE" \
  --source=bridge/cloud-signal-fabric \
  --region="$REGION" \
  --service-account="$RUNTIME_SA" \
  --no-allow-unauthenticated \
  --min=0 \
  --max=3 \
  --cpu=1 \
  --memory=512Mi \
  --concurrency=40 \
  --set-env-vars="DRIVE_MANIFEST_FOLDER_ID=${DRIVE_MANIFEST_FOLDER_ID},DRIVE_ARTIFACTS_ID=${DRIVE_ARTIFACTS_ID},CANONICAL_WRITE_ENABLED=false,POLL_HOT_MINUTES=1,POLL_WARM_MINUTES=3,POLL_IDLE_MINUTES=5,HOT_WINDOW_MINUTES=10,WARM_WINDOW_MINUTES=30,HARVEST_LEASE_SECONDS=50"

SERVICE_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"

gcloud run services add-iam-policy-binding "$SERVICE" \
  --region="$REGION" \
  --member="serviceAccount:${SCHEDULER_SA}" \
  --role='roles/run.invoker' >/dev/null

# Ensure the interactive installer identity can smoke-test the private endpoint.
gcloud run services add-iam-policy-binding "$SERVICE" \
  --region="$REGION" \
  --member="user:${ACTIVE_ACCOUNT}" \
  --role='roles/run.invoker' >/dev/null || true

say 'Installing one-minute heartbeat; runtime internally gates 1/3/5-minute cadence'
JOB='deus-signal-harvest'
COMMON=(
  --location="$REGION"
  --schedule='* * * * *'
  --time-zone='Asia/Bangkok'
  --uri="${SERVICE_URL}/v1/harvest"
  --http-method=POST
  --oidc-service-account-email="$SCHEDULER_SA"
  --oidc-token-audience="$SERVICE_URL"
  --attempt-deadline=50s
)
if gcloud scheduler jobs describe "$JOB" --location="$REGION" >/dev/null 2>&1; then
  gcloud scheduler jobs update http "$JOB" "${COMMON[@]}"
else
  gcloud scheduler jobs create http "$JOB" "${COMMON[@]}"
fi

say 'Cloud-side installation completed'
printf '%s\n' \
  "PROJECT_ID=$PROJECT_ID" \
  "PROJECT_NUMBER=$PROJECT_NUMBER" \
  "SERVICE_URL=$SERVICE_URL" \
  "RUNTIME_SERVICE_ACCOUNT=$RUNTIME_SA" \
  "SCHEDULER_SERVICE_ACCOUNT=$SCHEDULER_SA" \
  "GITHUB_DEPLOY_SERVICE_ACCOUNT=$DEPLOY_SA" \
  "GCP_WIF_PROVIDER=$WIF_PROVIDER" \
  "DRIVE_SIGNAL_FABRIC_FOLDER=https://drive.google.com/drive/folders/${DRIVE_PARENT_FOLDER_ID}"

cat <<EOF

NEXT MANUAL GATE — GOOGLE DRIVE ACL
-----------------------------------
Open this folder:
  https://drive.google.com/drive/folders/${DRIVE_PARENT_FOLDER_ID}

Share the parent folder with this runtime identity as Editor:
  ${RUNTIME_SA}

Google Drive folder permissions propagate to children, so one parent-folder share is sufficient unless a child uses limited-access mode.

Then run the verification command from the repository installer guide, or execute:
  PROJECT_ID=${PROJECT_ID} REGION=${REGION} bash bridge/cloud-signal-fabric/scripts/verify-install.sh

GitHub Actions WIF values are now deterministic and NON-SECRET:
  workload_identity_provider: ${WIF_PROVIDER}
  service_account: ${DEPLOY_SA}

Reality state now:
  CLOUD_RUN_DEPLOYED / FIRESTORE_READY / SCHEDULER_READY / WIF_READY / DRIVE_ACL_PENDING
EOF
