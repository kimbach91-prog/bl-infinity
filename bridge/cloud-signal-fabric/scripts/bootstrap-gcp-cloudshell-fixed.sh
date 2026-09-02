#!/usr/bin/env bash
set -Eeuo pipefail
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
curl -fsSL 'https://raw.githubusercontent.com/kimbach91-prog/bl-infinity/deus/signal-fabric-gcp-v1/bridge/cloud-signal-fabric/scripts/bootstrap-gcp-cloudshell.sh' \
  | python3 -c 'import sys; s=sys.stdin.read(); old="  local name=\"$1\" display=\"$2\" email=\"${name}@${PROJECT_ID}.iam.gserviceaccount.com\""; new="  local name=\"$1\"\n  local display=\"$2\"\n  local email=\"${name}@${PROJECT_ID}.iam.gserviceaccount.com\""; assert old in s, "bootstrap patch target not found"; sys.stdout.write(s.replace(old,new,1))' \
  > "$TMP"
bash "$TMP"
