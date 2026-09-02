#!/usr/bin/env bash
set -Eeuo pipefail
export PROJECT_ID="${PROJECT_ID:-deus-code-sss}"
export REGION="${REGION:-asia-southeast1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/verify-install.sh"
