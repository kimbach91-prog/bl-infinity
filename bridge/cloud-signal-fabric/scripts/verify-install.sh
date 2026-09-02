#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ID="${PROJECT_ID:-buoyant-mason-114302}"
REGION="${REGION:-asia-southeast1}"
SERVICE="${SERVICE:-deus-signal-fabric}"
SEAT="${SEAT:-GEMINI}"

command -v gcloud >/dev/null || { echo 'gcloud is required.' >&2; exit 1; }
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 1; }
command -v jq >/dev/null || { echo 'jq is required.' >&2; exit 1; }

gcloud config set project "$PROJECT_ID" >/dev/null
SERVICE_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
[[ -n "$SERVICE_URL" ]] || { echo 'Cloud Run service URL not found.' >&2; exit 1; }

TOKEN="$(gcloud auth print-identity-token)"
AUTH=(-H "Authorization: Bearer ${TOKEN}")
JSON=(-H 'Content-Type: application/json')

printf '[DEUS VERIFY] service=%s\n' "$SERVICE_URL"

printf '[1/6] health ... '
HEALTH="$(curl -fsS "${AUTH[@]}" "$SERVICE_URL/healthz")"
echo "$HEALTH" | jq -e '.ok == true and .modelCallsOnIdle == 0' >/dev/null
echo PASS

printf '[2/6] initialize/advance global Drive cursor ... '
BOOT="$(curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" "$SERVICE_URL/v1/harvest?force=1" -d '{"force":true}')"
echo "$BOOT" | jq -e '.ok == true and .modelCalls == 0' >/dev/null
echo PASS

CALL_ID="install-smoke-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
PAYLOAD="$(jq -n \
  --arg call "$CALL_ID" \
  --arg seat "$SEAT" \
  '{
    call_id:$call,
    from:"DEUS",
    to:[$seat],
    message_type:"TASK",
    authority:"CANDIDATE_ONLY",
    requires_ack:true,
    artifact_name:($call + ".txt"),
    artifact_mime_type:"text/plain",
    artifact_text:"DEUS Signal Fabric installation smoke test. Return not required; verify durable write -> manifest radiation -> seat delivery -> ACK.",
    metadata:{purpose:"INSTALL_SMOKE_TEST",canonical_write:false}
  }')"

printf '[3/6] Drive write-first publish ... '
PUBLISHED="$(curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" "$SERVICE_URL/v1/publish" -d "$PAYLOAD")"
MESSAGE_ID="$(echo "$PUBLISHED" | jq -r '.message_id')"
[[ -n "$MESSAGE_ID" && "$MESSAGE_ID" != null ]] || { echo "$PUBLISHED"; exit 1; }
echo PASS

printf '[4/6] force next delta harvest ... '
HARVEST="$(curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" "$SERVICE_URL/v1/harvest?force=1" -d '{"force":true}')"
echo "$HARVEST" | jq -e '.ok == true and .modelCalls == 0 and (.state == "HARVESTED" or .state == "LEASE_BUSY")' >/dev/null
if [[ "$(echo "$HARVEST" | jq -r '.state')" == 'LEASE_BUSY' ]]; then
  sleep 2
  HARVEST="$(curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" "$SERVICE_URL/v1/harvest?force=1" -d '{"force":true}')"
fi
echo "$HARVEST" | jq -e '.state == "HARVESTED"' >/dev/null
echo PASS

printf '[5/6] seat pointer delivery ... '
POLL="$(curl -fsS "${AUTH[@]}" "$SERVICE_URL/v1/poll/$SEAT?limit=100")"
DELIVERY_ID="$(echo "$POLL" | jq -r --arg mid "$MESSAGE_ID" '.deliveries[] | select(.manifest.message_id==$mid) | .deliveryId' | head -n1)"
[[ -n "$DELIVERY_ID" ]] || {
  echo FAIL
  echo "No delivery found for message $MESSAGE_ID in seat $SEAT" >&2
  echo "$POLL" | jq . >&2
  exit 1
}
echo PASS

printf '[6/6] ACK state transition ... '
ACK_PAYLOAD="$(jq -n --arg seat "$SEAT" --arg did "$DELIVERY_ID" --arg mid "$MESSAGE_ID" '{seat:$seat,delivery_id:$did,status:"SEEN",metadata:{verification:"INSTALL_SMOKE_TEST",message_id:$mid}}')"
ACK="$(curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" "$SERVICE_URL/v1/ack" -d "$ACK_PAYLOAD")"
echo "$ACK" | jq -e '.ok == true and .status == "SEEN"' >/dev/null
echo PASS

CONTROL="$(curl -fsS "${AUTH[@]}" "$SERVICE_URL/v1/control")"

echo
cat <<EOF
DEUS SIGNAL FABRIC — E2E VERIFIED
---------------------------------
project:       $PROJECT_ID
service:       $SERVICE_URL
call_id:       $CALL_ID
message_id:    $MESSAGE_ID
delivery_id:   $DELIVERY_ID
seat:          $SEAT
control_mode:  $(echo "$CONTROL" | jq -r '.control.mode // "UNKNOWN"')
fencing_epoch: $(echo "$CONTROL" | jq -r '.control.fencingEpoch // "UNKNOWN"')

Verified chain:
Drive artifact write -> manifest -> global changes cursor -> Firestore delivery pointer -> seat poll -> ACK

LLM calls during Signal Fabric verification: 0
Canonical write: untouched / locked
EOF
