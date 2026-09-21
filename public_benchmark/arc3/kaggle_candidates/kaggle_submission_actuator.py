#!/usr/bin/env python3
"""Fail-closed gate helpers for the ARC-AGI-3 Kaggle submission actuator.

This module never authenticates to Kaggle and never submits anything by itself.
It validates candidate/package invariants and produces machine-readable gate receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

COMPETITION = "arc-prize-2026-arc-agi-3"
REQUIRED_MACHINE = "NvidiaRtxPro6000"
GATE_SCHEMA = "deus/arc3-kaggle-submission-gate/1"
RECEIPT_SCHEMA = "deus/arc3-kaggle-submission-preflight/1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def notebook_semantic_digest(path: Path) -> str:
    obj = json.loads(path.read_text(encoding="utf-8"))
    cells = []
    for cell in obj.get("cells", []):
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        cells.append({
            "cell_type": cell.get("cell_type"),
            "source": source,
        })
    payload = json.dumps(cells, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return raw


def preflight(candidate_dir: Path, gate_path: Path) -> dict:
    checks = {}
    errors = []

    checks["candidate_dir_exists"] = candidate_dir.is_dir()
    if not checks["candidate_dir_exists"]:
        errors.append("candidate directory missing")
        return {
            "schema": RECEIPT_SCHEMA,
            "status": "HOLD",
            "checks": checks,
            "errors": errors,
        }

    notebooks = sorted(candidate_dir.glob("*.ipynb"))
    checks["exactly_one_notebook"] = len(notebooks) == 1
    if not checks["exactly_one_notebook"]:
        errors.append(f"expected one notebook, found {len(notebooks)}")

    metadata_path = candidate_dir / "kernel-metadata.json"
    checks["metadata_present"] = metadata_path.is_file()
    if not checks["metadata_present"]:
        errors.append("kernel-metadata.json missing")

    checks["gate_present"] = gate_path.is_file()
    if not checks["gate_present"]:
        errors.append("gate file missing")

    if errors:
        return {
            "schema": RECEIPT_SCHEMA,
            "status": "HOLD",
            "checks": checks,
            "errors": errors,
        }

    notebook = notebooks[0]
    metadata = load_json(metadata_path)
    gate = load_json(gate_path)

    byte_sha = sha256_file(notebook)
    semantic_sha = notebook_semantic_digest(notebook)

    checks.update({
        "gate_schema": gate.get("schema") == GATE_SCHEMA,
        "decision_non_dominated": gate.get("decision") == "APPROVED_NON_DOMINATED",
        "owner_incumbent_protection": gate.get("owner_incumbent_protection") is True,
        "submission_quota_authorized": gate.get("submission_quota_authorized") is True,
        "competition_exact": gate.get("competition") == COMPETITION,
        "required_output_exact": gate.get("required_output") == "submission.parquet",
        "expected_notebook_hash_present": bool(gate.get("expected_notebook_sha256")),
        "notebook_hash_match": gate.get("expected_notebook_sha256") == byte_sha,
        "metadata_competition_source": COMPETITION in (metadata.get("competition_sources") or []),
        "gpu_enabled": metadata.get("enable_gpu") is True,
        "internet_disabled": metadata.get("enable_internet") is False,
        "machine_shape_exact": metadata.get("machine_shape") == REQUIRED_MACHINE,
        "code_file_matches": Path(str(metadata.get("code_file", ""))).name == notebook.name,
    })

    for name, passed in checks.items():
        if not passed:
            errors.append(name)

    status = "READY" if not errors else "HOLD"
    return {
        "schema": RECEIPT_SCHEMA,
        "status": status,
        "candidate_dir": str(candidate_dir),
        "notebook_file": notebook.name,
        "notebook_sha256": byte_sha,
        "notebook_semantic_sha256": semantic_sha,
        "competition": COMPETITION,
        "required_machine": REQUIRED_MACHINE,
        "required_output": "submission.parquet",
        "checks": checks,
        "errors": errors,
        "truth": {
            "kaggle_authenticated": False,
            "kernel_pushed": False,
            "provider_version_readback": False,
            "competition_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_observed": False,
        },
    }


def parse_push_version(text: str) -> int:
    m = re.search(r"Kernel version\s+(\d+)\s+successfully pushed", text, flags=re.I)
    if not m:
        raise ValueError("Kaggle push output did not expose a kernel version")
    return int(m.group(1))


def parse_submission_ref(text: str) -> str:
    m = re.search(r"Submission ref:\s*(\d+)", text, flags=re.I)
    if not m:
        raise ValueError("Kaggle submit output did not expose a submission ref")
    return m.group(1)


def self_test() -> dict:
    checks = {}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cand = root / "cand"
        cand.mkdir()
        nb = cand / "solver.ipynb"
        nb.write_text(json.dumps({
            "cells": [{"cell_type": "code", "source": ["print('ok')\n"], "metadata": {}, "outputs": [], "execution_count": None}],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        }), encoding="utf-8")
        meta = {
            "id": "placeholder/solver",
            "title": "solver",
            "code_file": "solver.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": True,
            "enable_gpu": True,
            "enable_internet": False,
            "machine_shape": REQUIRED_MACHINE,
            "competition_sources": [COMPETITION],
            "dataset_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        }
        (cand / "kernel-metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        gate = {
            "schema": GATE_SCHEMA,
            "decision": "APPROVED_NON_DOMINATED",
            "owner_incumbent_protection": True,
            "submission_quota_authorized": True,
            "competition": COMPETITION,
            "required_output": "submission.parquet",
            "expected_notebook_sha256": sha256_file(nb),
        }
        gate_path = root / "gate.json"
        gate_path.write_text(json.dumps(gate), encoding="utf-8")

        good = preflight(cand, gate_path)
        checks["approved_ready"] = good["status"] == "READY"

        gate["expected_notebook_sha256"] = "0" * 64
        gate_path.write_text(json.dumps(gate), encoding="utf-8")
        checks["wrong_hash_holds"] = preflight(cand, gate_path)["status"] == "HOLD"

        gate["expected_notebook_sha256"] = sha256_file(nb)
        gate["submission_quota_authorized"] = False
        gate_path.write_text(json.dumps(gate), encoding="utf-8")
        checks["quota_not_authorized_holds"] = preflight(cand, gate_path)["status"] == "HOLD"

        gate["submission_quota_authorized"] = True
        gate["decision"] = "HOLD"
        gate_path.write_text(json.dumps(gate), encoding="utf-8")
        checks["dominated_or_unapproved_holds"] = preflight(cand, gate_path)["status"] == "HOLD"

    checks["push_version_parser"] = parse_push_version(
        "Kernel version 12 successfully pushed. Please check progress"
    ) == 12
    checks["submission_ref_parser"] = parse_submission_ref("Submission ref: 12345678") == "12345678"

    return {
        "schema": "deus/arc3-kaggle-submission-actuator-self-test/1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "truth": {
            "network_calls": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    st = sub.add_parser("self-test")
    st.add_argument("--receipt")

    pf = sub.add_parser("preflight")
    pf.add_argument("--candidate-dir", required=True)
    pf.add_argument("--gate-file", required=True)
    pf.add_argument("--receipt", required=True)

    dg = sub.add_parser("digest")
    dg.add_argument("--notebook", required=True)

    pv = sub.add_parser("parse-push-version")
    pv.add_argument("--file", required=True)

    ps = sub.add_parser("parse-submission-ref")
    ps.add_argument("--file", required=True)

    args = ap.parse_args()

    if args.cmd == "self-test":
        result = self_test()
        text = json.dumps(result, indent=2, sort_keys=True)
        print(text)
        if args.receipt:
            Path(args.receipt).write_text(text + "\n", encoding="utf-8")
        return 0 if result["status"] == "PASS" else 1

    if args.cmd == "preflight":
        result = preflight(Path(args.candidate_dir), Path(args.gate_file))
        text = json.dumps(result, indent=2, sort_keys=True)
        print(text)
        Path(args.receipt).write_text(text + "\n", encoding="utf-8")
        return 0 if result["status"] == "READY" else 3

    if args.cmd == "digest":
        p = Path(args.notebook)
        print(json.dumps({
            "notebook_sha256": sha256_file(p),
            "notebook_semantic_sha256": notebook_semantic_digest(p),
        }, sort_keys=True))
        return 0

    if args.cmd == "parse-push-version":
        print(parse_push_version(Path(args.file).read_text(encoding="utf-8", errors="replace")))
        return 0

    if args.cmd == "parse-submission-ref":
        print(parse_submission_ref(Path(args.file).read_text(encoding="utf-8", errors="replace")))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
