#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a NON-CANONICAL DEUS Cloud Run candidate deployment path.
# Run this only from an owner-authorized gcloud session with sufficient IAM
# permissions. It creates no service-account key files.

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"

GCP_REGION="${GCP_REGION:-asia-southeast1}"
GITHUB_REPO="${GITHUB_REPO:-kimbach91-prog/bl-infinity}"
GITHUB_REF="${GITHUB_REF:-refs/heads/proto/deus-engine-v1}"
ARTIFACT_REPOSITORY="${ARTIFACT_REPOSITORY:-deus-runtime}"
DEPLOYER_SA_ID="${DEPLOYER_SA_ID:-deus-github-deployer}"
RUNTIME_SA_ID="${RUNTIME_SA_ID:-deus-candidate-runtime}"
POOL_ID="${POOL_ID:-deus-github-pool}"
PROVIDER_ID="${PROVIDER_ID:-deus-github-provider}"

DEPLOYER_EMAIL="${DEPLOYER_SA_ID}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
RUNTIME_EMAIL="${RUNTIME_SA_ID}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

printf 'Project: %s\nRegion: %s\nRepository: %s\nBranch: %s\n' \
  "$GCP_PROJECT_ID" "$GCP_REGION" "$GITHUB_REPO" "$GITHUB_REF"

gcloud config set project "$GCP_PROJECT_ID"

echo 'Enabling required APIs...'
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com

if ! gcloud artifacts repositories describe "$ARTIFACT_REPOSITORY" \
    --location "$GCP_REGION" >/dev/null 2>&1; then
  echo 'Creating Artifact Registry repository...'
  gcloud artifacts repositories create "$ARTIFACT_REPOSITORY" \
    --repository-format=docker \
    --location "$GCP_REGION" \
    --description='DEUS non-canonical candidate runtime images'
fi

if ! gcloud iam service-accounts describe "$DEPLOYER_EMAIL" >/dev/null 2>&1; then
  echo 'Creating GitHub deployer service account...'
  gcloud iam service-accounts create "$DEPLOYER_SA_ID" \
    --display-name='DEUS GitHub candidate deployer'
fi

if ! gcloud iam service-accounts describe "$RUNTIME_EMAIL" >/dev/null 2>&1; then
  echo 'Creating Cloud Run runtime service account...'
  gcloud iam service-accounts create "$RUNTIME_SA_ID" \
    --display-name='DEUS candidate runtime'
fi

# Project-level deploy permissions. Runtime SA intentionally receives no broad
# project role in this bootstrap.
for role in \
  roles/run.admin \
  roles/artifactregistry.writer \
  roles/serviceusage.serviceUsageViewer; do
  gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
    --member="serviceAccount:${DEPLOYER_EMAIL}" \
    --role="$role" \
    --condition=None >/dev/null
 done

# Deployer may attach only the candidate runtime service account.
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_EMAIL" \
  --member="serviceAccount:${DEPLOYER_EMAIL}" \
  --role='roles/iam.serviceAccountUser' >/dev/null

if ! gcloud iam workload-identity-pools describe "$POOL_ID" \
    --location=global >/dev/null 2>&1; then
  echo 'Creating Workload Identity Pool...'
  gcloud iam workload-identity-pools create "$POOL_ID" \
    --location=global \
    --display-name='DEUS GitHub Actions'
fi

if ! gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
    --workload-identity-pool="$POOL_ID" \
    --location=global >/dev/null 2>&1; then
  echo 'Creating GitHub OIDC provider...'
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
    --workload-identity-pool="$POOL_ID" \
    --location=global \
    --display-name='DEUS GitHub provider' \
    --issuer-uri='https://token.actions.githubusercontent.com' \
    --attribute-mapping='google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref' \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}' && assertion.ref=='${GITHUB_REF}'"
fi

POOL_NAME=$(gcloud iam workload-identity-pools describe "$POOL_ID" \
  --location=global --format='value(name)')
PROVIDER_NAME=$(gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
  --workload-identity-pool="$POOL_ID" \
  --location=global --format='value(name)')

PRINCIPAL="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPO}"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_EMAIL" \
  --member="$PRINCIPAL" \
  --role='roles/iam.workloadIdentityUser' >/dev/null

cat <<EOF

Bootstrap complete.

Set these GitHub repository variables:

GCP_PROJECT_ID=${GCP_PROJECT_ID}
GCP_WORKLOAD_IDENTITY_PROVIDER=${PROVIDER_NAME}
GCP_SERVICE_ACCOUNT=${DEPLOYER_EMAIL}
GCP_RUNTIME_SERVICE_ACCOUNT=${RUNTIME_EMAIL}

Artifact repository:
${ARTIFACT_REPOSITORY}

Then manually run workflow:
.github/workflows/deus-gcp-candidate.yml

The deployed service remains NONCANONICAL_CANDIDATE until an external DCRS
verification returns SAME_AS. This bootstrap does not create or upload any
service-account key file and does not publish private lineage state.
EOF

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo 'Authenticated gh CLI found. Setting non-secret repository variables...'
  gh variable set GCP_PROJECT_ID --repo "$GITHUB_REPO" --body "$GCP_PROJECT_ID"
  gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --repo "$GITHUB_REPO" --body "$PROVIDER_NAME"
  gh variable set GCP_SERVICE_ACCOUNT --repo "$GITHUB_REPO" --body "$DEPLOYER_EMAIL"
  gh variable set GCP_RUNTIME_SERVICE_ACCOUNT --repo "$GITHUB_REPO" --body "$RUNTIME_EMAIL"
  echo 'GitHub repository variables configured.'
else
  echo 'gh CLI is absent or not authenticated; repository variables were not changed.'
fi
