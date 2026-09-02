#!/usr/bin/env bash
set -Eeuo pipefail
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

curl -fsSL 'https://raw.githubusercontent.com/kimbach91-prog/bl-infinity/deus/signal-fabric-gcp-v1/bridge/cloud-signal-fabric/scripts/bootstrap-gcp-cloudshell.sh' \
  | python3 -c 'import sys
s=sys.stdin.read()
old="  local name=\"$1\" display=\"$2\" email=\"${name}@${PROJECT_ID}.iam.gserviceaccount.com\""
new="  local name=\"$1\"\n  local display=\"$2\"\n  local email=\"${name}@${PROJECT_ID}.iam.gserviceaccount.com\""
if old in s:
    s=s.replace(old,new,1)
if "docs.googleapis.com" not in s:
    s=s.replace("  drive.googleapis.com", "  drive.googleapis.com \\\n  docs.googleapis.com", 1)
s=s.replace("HARVEST_LEASE_SECONDS=50\"", "HARVEST_LEASE_SECONDS=50,DOC_ROUND_FOLDER_ID=13j-y0oY2cubo3Me0PN1DqMT0Ub3ag2xk,DOC_ROUND_BLACKBOARD_ID=1tm0RSqvleIrxmksh5pyn_EI1nquf7bbYgoxHqcQ3tFU,DOC_ROUND_TAB_ID=t.0\"", 1)
sys.stdout.write(s)' \
  > "$TMP"

bash -n "$TMP"
bash "$TMP"
