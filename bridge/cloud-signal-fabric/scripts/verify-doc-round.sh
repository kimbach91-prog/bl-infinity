#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ID="${PROJECT_ID:-deus-code-sss}"
REGION="${REGION:-asia-southeast1}"
SERVICE="${SERVICE:-deus-signal-fabric}"
BLACKBOARD_ID="${DOC_ROUND_BLACKBOARD_ID:-1tm0RSqvleIrxmksh5pyn_EI1nquf7bbYgoxHqcQ3tFU}"

gcloud config set project "$PROJECT_ID" >/dev/null
SERVICE_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
[[ -n "$SERVICE_URL" ]] || { echo 'Cloud Run service URL not found.' >&2; exit 1; }
TOKEN="$(gcloud auth print-identity-token)"
AUTH=(-H "Authorization: Bearer ${TOKEN}")
JSON=(-H 'Content-Type: application/json')

ROUND_ID="doc-round-smoke-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
TASK_ID="install-smoke"
TENANT_ID="DEUS-INTERNAL"

printf '[1/6] participant batch -> Google Doc ... '
BODY="$(jq -n \
  --arg round "$ROUND_ID" \
  --arg tenant "$TENANT_ID" \
  --arg task "$TASK_ID" \
  --arg doc "$BLACKBOARD_ID" \
  '{round_id:$round,tenant_id:$tenant,task_id:$task,from:"DEUS",to:["DEUS"],signal_type:"ROUND_READY",state:"CANDIDATE",document_id:$doc,contributions:[{actor:"CLAUDE",final_text:"DOC-ROUND smoke: Claude explicit final."},{actor:"GEMINI",final_text:"DOC-ROUND smoke: Gemini explicit final."},{actor:"GROK",final_text:"DOC-ROUND smoke: Grok explicit final."}],metadata:{purpose:"DOC_ROUND_E2E_SMOKE"}}')"
ROUND_READY="$(curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" "$SERVICE_URL/v1/doc-round/batch" -d "$BODY")"
echo "$ROUND_READY" | jq -e '.ok==true and .protocol=="DEUS-DOC-ROUND/1.0" and .docs_write_requests==1 and .cloud_answer_bytes==0' >/dev/null
echo PASS

printf '[2/6] DEUS pointer poll ... '
POLL="$(curl -fsS "${AUTH[@]}" "$SERVICE_URL/v1/doc-round/poll/DEUS?limit=100")"
DELIVERY_ID="$(echo "$POLL" | jq -r --arg rid "$ROUND_ID" '.deliveries[] | select(.roundId==$rid and .signalType=="ROUND_READY") | .deliveryId' | head -n1)"
[[ -n "$DELIVERY_ID" ]] || { echo FAIL; echo "$POLL" | jq . >&2; exit 1; }
echo PASS

printf '[3/6] DEUS ACK ... '
ACK="$(jq -n --arg did "$DELIVERY_ID" '{seat:"DEUS",delivery_id:$did,status:"SEEN",metadata:{verification:"DOC_ROUND_E2E_SMOKE"}}')"
curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" "$SERVICE_URL/v1/doc-round/ack" -d "$ACK" | jq -e '.ok==true and .status=="SEEN"' >/dev/null
echo PASS

printf '[4/6] DEUS final -> Google Doc ... '
FINAL_BODY="$(jq -n \
  --arg round "$ROUND_ID" \
  --arg tenant "$TENANT_ID" \
  --arg task "$TASK_ID" \
  --arg doc "$BLACKBOARD_ID" \
  '{round_id:$round,tenant_id:$tenant,task_id:$task,from:"DEUS",to:["CLAUDE","GEMINI","GROK"],signal_type:"FINAL_READY",state:"FINAL",document_id:$doc,contributions:[{actor:"DEUS",final_text:"DOC-ROUND E2E smoke synthesis: transport verified; this is not a canonical business decision."}],metadata:{purpose:"DOC_ROUND_E2E_SMOKE",canonical_business_commit:false}}')"
FINAL="$(curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" "$SERVICE_URL/v1/doc-round/batch" -d "$FINAL_BODY")"
echo "$FINAL" | jq -e '.ok==true and .deliveries==3 and .cloud_answer_bytes==0' >/dev/null
echo PASS

printf '[5/6] participant FINAL_READY pointer ... '
FPOLL="$(curl -fsS "${AUTH[@]}" "$SERVICE_URL/v1/doc-round/poll/GEMINI?limit=100")"
FINAL_DELIVERY="$(echo "$FPOLL" | jq -r --arg rid "$ROUND_ID" '.deliveries[] | select(.roundId==$rid and .signalType=="FINAL_READY") | .deliveryId' | head -n1)"
[[ -n "$FINAL_DELIVERY" ]] || { echo FAIL; echo "$FPOLL" | jq . >&2; exit 1; }
echo PASS

printf '[6/6] round metadata state ... '
STATE="$(curl -fsS "${AUTH[@]}" "$SERVICE_URL/v1/doc-round/state/$ROUND_ID")"
echo "$STATE" | jq -e '.ok==true and .state.lastSignalType=="FINAL_READY" and .state.lastState=="FINAL"' >/dev/null
echo PASS

echo
cat <<EOF
DEUS DOC-ROUND — E2E VERIFIED
-----------------------------
project:     $PROJECT_ID
service:     $SERVICE_URL
round_id:    $ROUND_ID
blackboard:  https://docs.google.com/document/d/$BLACKBOARD_ID/edit

Verified:
participant batch -> one Google Docs write -> pointer-only Cloud signal -> DEUS poll/ACK -> DEUS final write -> selective FINAL_READY fan-out

Cloud answer-body transport: 0 bytes by protocol
LLM calls in verification: 0
Legacy manifest path: unchanged as compatibility/recovery
EOF
