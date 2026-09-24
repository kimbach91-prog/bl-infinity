#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python3.12 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --no-index --find-links wheelhouse/linux -r requirements.lock
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python arc3_offline.py smoke --root . --seeds 0,1,2 --steps 8
