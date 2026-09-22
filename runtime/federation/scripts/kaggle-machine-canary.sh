#!/bin/sh
set -eu
umask 077

AUTH_OK=false
ENTERED_OK=false
TOKEN_PRESENT=false

if [ -n "${KAGGLE_API_TOKEN:-}" ]; then
  TOKEN_PRESENT=true
else
  printf '%s
' '{"event":"KAGGLE_MACHINE_CANARY","token_present":false,"cli_auth":false,"arc_prize_2026_entered":false}'
  exit 41
fi

python3 -m venv /tmp/kaggle-canary-venv
/tmp/kaggle-canary-venv/bin/pip install --disable-pip-version-check --quiet kaggle >/dev/null 2>&1

if /tmp/kaggle-canary-venv/bin/kaggle kernels list --mine --page-size 1 --format json >/tmp/kg_kernels.json 2>/dev/null; then
  AUTH_OK=true
fi

if /tmp/kaggle-canary-venv/bin/kaggle competitions list --group entered --search "ARC Prize 2026" --format json >/tmp/kg_entered.json 2>/dev/null; then
  if grep -qi 'arc-prize-2026' /tmp/kg_entered.json; then
    ENTERED_OK=true
  fi
fi

printf '{"event":"KAGGLE_MACHINE_CANARY","token_present":%s,"cli_auth":%s,"arc_prize_2026_entered":%s}
' "$TOKEN_PRESENT" "$AUTH_OK" "$ENTERED_OK"

rm -rf /tmp/kaggle-canary-venv /tmp/kg_kernels.json /tmp/kg_entered.json

[ "$AUTH_OK" = true ] || exit 42
[ "$ENTERED_OK" = true ] || exit 43
