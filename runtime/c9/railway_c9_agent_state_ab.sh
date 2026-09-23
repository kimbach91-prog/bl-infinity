#!/bin/sh
set -eu

ROOT="${DEUS_C9_REPO_ROOT:-/tmp/deus-c9-repo}"
FLASH="$ROOT/public_benchmark/arc3/kaggle_candidates/flash_next_340"
WORK="/tmp/deus-c9-ab"
VENV="/tmp/deus-c9-venv"
GAME="tr87-cd924810"
RUNTIME="1200"
GRACE="120"
CONCURRENCY="1"
ANALYZER="900"
SUBMISSION_REF="56474082"

fail_hold() {
  code="$1"; shift
  /bin/echo "{\"event\":\"DEUS_C9_AB_HOLD\",\"code\":\"$code\",\"message\":\"$*\",\"competition_submission\":false,\"submission_quota_spent\":false}" >&2
  while :; do sleep 3600; done
}

python3 -m venv "$VENV" || fail_hold VENV_CREATE "failed to create Python venv"
"$VENV/bin/pip" install --quiet --disable-pip-version-check --no-cache-dir kaggle || fail_hold KAGGLE_INSTALL "failed to install Kaggle client"

# Never print credentials. Authentication is proven only by successful bounded provider reads.
# Resolve the authenticated owner slug without minting a new credential.
mkdir -p "$WORK/init"
"$VENV/bin/kaggle" kernels init -p "$WORK/init" > "$WORK-kernel-init.stdout" 2> "$WORK-kernel-init.stderr" || true
KUSER="$("$VENV/bin/python" - "$WORK/init/kernel-metadata.json" <<'PY'
import json,re,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    d={}
kid=str(d.get("id",""))
m=re.fullmatch(r"([A-Za-z0-9_.-]+)/[A-Za-z0-9_.-]+",kid)
if m and "INSERT" not in m.group(1).upper():
    print(m.group(1))
PY
)"
if [ -z "$KUSER" ]; then
  "$VENV/bin/kaggle" kernels list --mine --page-size 100 -v > "$WORK-kernels.txt" 2> "$WORK-kernels.err" || fail_hold KAGGLE_AUTH "authenticated kernels list failed"
  KUSER="$("$VENV/bin/python" - "$WORK-kernels.txt" <<'PY'
import re,sys
text=open(sys.argv[1],errors="replace").read()
for token in re.findall(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",text):
    owner=token.split("/",1)[0]
    if owner.lower() not in {"https:","http:"} and "token" not in owner.lower():
        print(owner)
        break
PY
)"
fi
[ -n "$KUSER" ] || fail_hold KAGGLE_OWNER "authenticated owner slug unavailable from local init or owned-kernel listing"

BASE_REF="$KUSER/deus-arc-agi3-c9-base-tr87"
STATE_REF="$KUSER/deus-arc-agi3-c9-state-tr87"
mkdir -p "$WORK/stage/scripts" "$WORK/out/base" "$WORK/out/state"
cp "$FLASH/arc-agi-flash-next-mtp.ipynb" "$WORK/stage/arc-agi-flash-next-mtp.ipynb"
cp "$FLASH/upstream_build_flash_next_package.py" "$WORK/stage/scripts/build_flash_next_package.py"
cp "$FLASH/upstream_flash_teardown_patch.py" "$WORK/stage/scripts/flash_teardown_patch.py"
cp "$FLASH/upstream_flash_agent_state_patch.py" "$WORK/stage/scripts/flash_agent_state_patch.py"
cp "$FLASH/upstream_audit_flash_output.py" "$WORK/stage/audit_flash_output.py"

"$VENV/bin/python" "$WORK/stage/scripts/build_flash_next_package.py"   --kernel-id "$BASE_REF" --mode preflight --max-games 1 --game-id "$GAME"   --concurrency "$CONCURRENCY" --runtime-seconds "$RUNTIME"   --terminal-grace-seconds "$GRACE" --analyzer-timeout "$ANALYZER"   --output-dir "$WORK/stage/build/base"   > "$WORK/base-build.log" 2>&1 || fail_hold BASE_BUILD "base package build failed"

"$VENV/bin/python" "$WORK/stage/scripts/build_flash_next_package.py"   --kernel-id "$STATE_REF" --mode preflight --max-games 1 --game-id "$GAME"   --concurrency "$CONCURRENCY" --runtime-seconds "$RUNTIME"   --terminal-grace-seconds "$GRACE" --analyzer-timeout "$ANALYZER"   --agent-state-patch --output-dir "$WORK/stage/build/state"   > "$WORK/state-build.log" 2>&1 || fail_hold STATE_BUILD "state package build failed"

push_one() {
  dir="$1"; prefix="$2"
  "$VENV/bin/kaggle" kernels push -p "$dir" -t 30000 > "$WORK/$prefix.stdout" 2> "$WORK/$prefix.stderr" || return 1
  "$VENV/bin/python" - "$WORK/$prefix.stdout" "$WORK/$prefix.stderr" <<'PY'
import re,sys
text=open(sys.argv[1],errors="replace").read()+"\n"+open(sys.argv[2],errors="replace").read()
m=re.search(r"Kernel version\s+(\d+)\s+successfully pushed",text,re.I)
if not m:
    raise SystemExit("exact pushed version not found")
print(m.group(1))
PY
}

BASE_VERSION="$(push_one "$WORK/stage/build/base" base-push)" || fail_hold BASE_PUSH "base private preflight push failed"
STATE_VERSION="$(push_one "$WORK/stage/build/state" state-push)" || fail_hold STATE_PUSH "state private preflight push failed"
BASE_EXACT="$BASE_REF/$BASE_VERSION"
STATE_EXACT="$STATE_REF/$STATE_VERSION"

"$VENV/bin/python" - "$BASE_EXACT" "$STATE_EXACT" "$GAME" <<'PY'
import json,sys
print(json.dumps({
 "event":"DEUS_C9_AB_LAUNCHED",
 "base_exact":sys.argv[1],
 "state_exact":sys.argv[2],
 "game_id":sys.argv[3],
 "competition_submission":False,
 "submission_quota_spent":False
},sort_keys=True),flush=True)
PY

is_complete() {
  ref="$1"; file="$2"
  "$VENV/bin/kaggle" kernels status "$ref" > "$file" 2>&1 || return 2
  grep -Eqi 'complete|completed' "$file"
}
is_failed() {
  file="$1"
  grep -Eqi 'error|failed|cancelled' "$file"
}

i=0
while [ "$i" -lt 70 ]; do
  i=$((i+1))
  bc=0; sc=0
  is_complete "$BASE_EXACT" "$WORK/base-status.txt" && bc=1 || true
  is_complete "$STATE_EXACT" "$WORK/state-status.txt" && sc=1 || true
  if is_failed "$WORK/base-status.txt" || is_failed "$WORK/state-status.txt"; then
    fail_hold PROVIDER_FAILED "one matched private preflight reached provider failure"
  fi
  if [ "$bc" -eq 1 ] && [ "$sc" -eq 1 ]; then break; fi
  sleep 45
done
if ! is_complete "$BASE_EXACT" "$WORK/base-status.txt" || ! is_complete "$STATE_EXACT" "$WORK/state-status.txt"; then
  fail_hold PROVIDER_TIMEOUT "matched private preflights did not both complete inside polling window"
fi

"$VENV/bin/kaggle" kernels output "$BASE_EXACT" -p "$WORK/out/base" > "$WORK/base-output.log" 2>&1 || fail_hold BASE_OUTPUT "base output download failed"
"$VENV/bin/kaggle" kernels output "$STATE_EXACT" -p "$WORK/out/state" > "$WORK/state-output.log" 2>&1 || fail_hold STATE_OUTPUT "state output download failed"

BASE_LOG_PATH="$(find "$WORK/out/base" -maxdepth 1 -type f -name 'arc-agi3-flash-next-mtp-*.log' | head -n1)"
STATE_LOG_PATH="$(find "$WORK/out/state" -maxdepth 1 -type f -name 'arc-agi3-flash-next-mtp-*.log' | head -n1)"
BASE_LOG="$(basename "$BASE_LOG_PATH")"
STATE_LOG="$(basename "$STATE_LOG_PATH")"
[ -n "$BASE_LOG" ] || fail_hold BASE_LOG "base kernel log not found"
[ -n "$STATE_LOG" ] || fail_hold STATE_LOG "state kernel log not found"

BASE_OUT="$WORK/out/base" STATE_OUT="$WORK/out/state" BASE_LOG="$BASE_LOG" STATE_LOG="$STATE_LOG" GAME="$GAME" RUNTIME="$RUNTIME" GRACE="$GRACE" CONCURRENCY="$CONCURRENCY" ANALYZER="$ANALYZER" BASE_EXACT="$BASE_EXACT" STATE_EXACT="$STATE_EXACT" "$VENV/bin/python" - "$WORK/stage/audit_flash_output.py" <<'PY'
import importlib.util,json,os,sys
from pathlib import Path
p=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("audit_flash",p)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
kw=dict(
 check_parquet=False,
 expected_games=1,
 expected_concurrency=int(os.environ["CONCURRENCY"]),
 expected_game_id=os.environ["GAME"],
 expected_runtime_seconds=int(os.environ["RUNTIME"]),
 expected_gameplay_budget_seconds=int(os.environ["RUNTIME"]),
 require_clean=True,
 require_runtime_from_ready=True,
 expected_terminal_grace_seconds=int(os.environ["GRACE"]),
 expected_analyzer_timeout=int(os.environ["ANALYZER"]),
)
def audit(root,log,state=False):
    try:
        r=m.audit(Path(root),"preflight",kernel_log=log,require_agent_state_patch=state,**kw)
        return {"passed":True,**r}
    except Exception as e:
        return {"passed":False,"error_type":type(e).__name__}
base=audit(os.environ["BASE_OUT"],os.environ["BASE_LOG"],False)
state=audit(os.environ["STATE_OUT"],os.environ["STATE_LOG"],True)
if not (base.get("passed") and state.get("passed")):
    verdict="INCONCLUSIVE_AUDIT_FAILURE"
else:
    bm=float(base.get("offline_mean",0)); sm=float(state.get("offline_mean",0))
    ba=int(base.get("total_actions",0)); sa=int(state.get("total_actions",0))
    if sm>bm: verdict="PROMOTE_TO_WIDER_PROVIDER_TEST"
    elif sm==bm and sa<ba: verdict="PROMOTE_EFFICIENCY_ONLY"
    else: verdict="RETAIN_BASE"
receipt={
 "event":"DEUS_C9_AGENT_STATE_AB_RESULT",
 "schema":"deus/arc3-flash-agent-state-ab-railway/1",
 "status":"MATCHED_AUDIT_COMPLETE" if base.get("passed") and state.get("passed") else "MATCHED_AUDIT_FAILED",
 "verdict":verdict,
 "base_exact":os.environ["BASE_EXACT"],
 "state_exact":os.environ["STATE_EXACT"],
 "base_audit":base,
 "state_audit":state,
 "truth":{
   "kaggle_authenticated":True,
   "private_kernel_pushes":2,
   "parquet_content_check":False,
   "competition_submission":False,
   "submission_quota_spent":False,
   "leaderboard_score_observed":False,
   "candidate_promoted":False
 }
}
Path("/tmp/deus-c9-ab-result.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True),flush=True)
PY

# Preserve the incumbent score watcher after the A/B receipt.
while :; do
  "$VENV/bin/kaggle" competitions submissions -c arc-prize-2026-arc-agi-3 -q 2>/dev/null | grep "$SUBMISSION_REF" || true
  sleep 3600
done
