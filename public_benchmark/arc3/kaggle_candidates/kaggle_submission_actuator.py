#!/usr/bin/env python3
"""Fail-closed gate helpers for the ARC-AGI-3 Kaggle submission actuator.

This module never authenticates to Kaggle and never submits anything by itself.
It validates candidate/package invariants and produces machine-readable gate receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

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



def _run(cmd: list[str], *, timeout: int = 300, cwd: Path | None = None) -> dict:
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


def _must(result: dict, label: str) -> dict:
    if result["returncode"] != 0:
        raise RuntimeError(
            f"{label} failed rc={result['returncode']}: "
            f"{result['stderr'][-1200:] or result['stdout'][-1200:]}"
        )
    return result


def _status_terminal(text: str) -> tuple[bool, bool]:
    low = text.lower()
    if any(x in low for x in ("error", "failed", "cancelled", "canceled")):
        return True, False
    if any(x in low for x in ("complete", "completed")):
        return True, True
    return False, False


def _safe_excerpt(text: str, limit: int = 1600) -> str:
    return text[-limit:].replace("\x00", "")


def execute_actuator(
    candidate_dir: Path,
    gate_path: Path,
    *,
    kernel: str,
    message: str,
    receipt_path: Path,
    kernel_timeout_seconds: int,
    score_wait_seconds: int,
) -> dict:
    receipt = {
        "schema": "deus/arc3-kaggle-submission-actuator-execution/1",
        "competition": COMPETITION,
        "kernel": kernel,
        "status": "STARTED",
        "steps": {},
        "truth": {
            "kaggle_authenticated": False,
            "kernel_pushed": False,
            "provider_version_readback": False,
            "competition_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_observed": False,
        },
    }

    def persist() -> None:
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    persist()
    try:
        pf = preflight(candidate_dir, gate_path)
        receipt["preflight"] = pf
        if pf["status"] != "READY":
            receipt["status"] = "HOLD_PREFLIGHT"
            persist()
            return receipt

        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", kernel):
            raise ValueError("kernel must be owner/slug")
        if not os.environ.get("DEUS_KAGGLE_EXECUTE_APPROVED") == "TRUE":
            receipt["status"] = "HOLD_EXECUTION_APPROVAL"
            persist()
            return receipt

        auth = _run(["kaggle", "kernels", "list", "--mine", "--page-size", "1"], timeout=90)
        receipt["steps"]["auth"] = {
            "returncode": auth["returncode"],
            "latency_ms": auth["latency_ms"],
            "stdout_excerpt": _safe_excerpt(auth["stdout"], 600),
            "stderr_excerpt": _safe_excerpt(auth["stderr"], 600),
        }
        _must(auth, "Kaggle auth")
        receipt["truth"]["kaggle_authenticated"] = True
        persist()

        before = _run(["kaggle", "competitions", "submissions", COMPETITION, "-v"], timeout=90)
        _must(before, "submissions-before readback")
        receipt["steps"]["submissions_before"] = {
            "sha256": hashlib.sha256(before["stdout"].encode()).hexdigest(),
            "stdout_excerpt": _safe_excerpt(before["stdout"], 1200),
        }

        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            package = work / "candidate"
            shutil.copytree(candidate_dir, package)
            meta_path = package / "kernel-metadata.json"
            meta = load_json(meta_path)
            meta["id"] = kernel
            meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            notebook = next(package.glob("*.ipynb"))
            local_byte_sha = sha256_file(notebook)
            local_semantic_sha = notebook_semantic_digest(notebook)
            receipt["local_notebook_sha256"] = local_byte_sha
            receipt["local_notebook_semantic_sha256"] = local_semantic_sha

            push = _run(
                ["kaggle", "kernels", "push", "-p", str(package), "--accelerator", REQUIRED_MACHINE],
                timeout=180,
            )
            receipt["steps"]["kernel_push"] = {
                "returncode": push["returncode"],
                "latency_ms": push["latency_ms"],
                "stdout_excerpt": _safe_excerpt(push["stdout"]),
                "stderr_excerpt": _safe_excerpt(push["stderr"]),
            }
            _must(push, "kernel push")
            version = parse_push_version(push["stdout"] + "\n" + push["stderr"])
            receipt["kernel_version"] = version
            receipt["truth"]["kernel_pushed"] = True
            persist()

            version_ref = f"{kernel}/{version}"
            deadline = time.monotonic() + kernel_timeout_seconds
            status_history = []
            while True:
                status = _run(["kaggle", "kernels", "status", version_ref], timeout=90)
                _must(status, "kernel status")
                text = status["stdout"] + "\n" + status["stderr"]
                terminal, success = _status_terminal(text)
                status_history.append({
                    "at_monotonic_s": round(time.monotonic(), 3),
                    "text_excerpt": _safe_excerpt(text, 800),
                })
                if terminal:
                    if not success:
                        raise RuntimeError("Kaggle kernel reached failure terminal state")
                    break
                if time.monotonic() >= deadline:
                    receipt["status"] = "CHECKPOINT_KERNEL_STILL_RUNNING"
                    receipt["steps"]["kernel_status_history"] = status_history[-12:]
                    persist()
                    return receipt
                time.sleep(30)
            receipt["steps"]["kernel_status_history"] = status_history[-12:]

            pulled = work / "readback"
            pulled.mkdir()
            pull = _run(["kaggle", "kernels", "pull", version_ref, "-p", str(pulled), "-m"], timeout=180)
            receipt["steps"]["provider_pull"] = {
                "returncode": pull["returncode"],
                "stdout_excerpt": _safe_excerpt(pull["stdout"], 1000),
                "stderr_excerpt": _safe_excerpt(pull["stderr"], 1000),
            }
            _must(pull, "exact-version provider pull")
            pulled_nbs = sorted(pulled.glob("*.ipynb"))
            if len(pulled_nbs) != 1:
                raise RuntimeError(f"provider pull expected one notebook, found {len(pulled_nbs)}")
            provider_semantic_sha = notebook_semantic_digest(pulled_nbs[0])
            receipt["provider_notebook_semantic_sha256"] = provider_semantic_sha
            receipt["semantic_source_match"] = provider_semantic_sha == local_semantic_sha
            if not receipt["semantic_source_match"]:
                raise RuntimeError("provider exact-version source semantic digest mismatch")
            receipt["truth"]["provider_version_readback"] = True
            persist()

            outputs = work / "outputs"
            outputs.mkdir()
            out = _run(
                [
                    "kaggle", "kernels", "output", version_ref,
                    "-p", str(outputs), "-o",
                    "--file-pattern", r"(^|/)submission\.parquet$",
                ],
                timeout=300,
            )
            receipt["steps"]["kernel_output"] = {
                "returncode": out["returncode"],
                "stdout_excerpt": _safe_excerpt(out["stdout"], 1000),
                "stderr_excerpt": _safe_excerpt(out["stderr"], 1000),
            }
            _must(out, "kernel output")
            submission_files = [p for p in outputs.rglob("*") if p.is_file() and p.name == "submission.parquet"]
            if len(submission_files) != 1:
                raise RuntimeError(f"expected exactly one submission.parquet, found {len(submission_files)}")
            receipt["submission_output_sha256"] = sha256_file(submission_files[0])
            receipt["submission_output_bytes"] = submission_files[0].stat().st_size
            persist()

            submit_cmd = [
                "kaggle", "competitions", "submit", COMPETITION,
                "-k", kernel,
                "-v", str(version),
                "-f", "submission.parquet",
                "-m", message,
                "--wait", str(score_wait_seconds),
                "--poll-interval", "60",
            ]
            receipt["truth"]["competition_submission_attempted"] = True
            receipt["truth"]["submission_quota_spent"] = True
            persist()
            submit = _run(submit_cmd, timeout=max(score_wait_seconds + 300, 900))
            receipt["steps"]["competition_submit"] = {
                "returncode": submit["returncode"],
                "stdout_excerpt": _safe_excerpt(submit["stdout"], 2400),
                "stderr_excerpt": _safe_excerpt(submit["stderr"], 1600),
            }
            _must(submit, "competition submit")
            submission_ref = parse_submission_ref(submit["stdout"] + "\n" + submit["stderr"])
            receipt["submission_ref"] = submission_ref
            persist()

            score = _run(["kaggle", "competitions", "submission", submission_ref], timeout=120)
            receipt["steps"]["score_readback"] = {
                "returncode": score["returncode"],
                "stdout_excerpt": _safe_excerpt(score["stdout"], 2400),
                "stderr_excerpt": _safe_excerpt(score["stderr"], 1600),
            }
            _must(score, "submission score readback")
            m = re.search(r"Public Score:\s*([^\s]+)", score["stdout"], flags=re.I)
            receipt["public_score_raw"] = m.group(1) if m else None
            receipt["truth"]["leaderboard_score_observed"] = bool(m)
            receipt["status"] = "VERIFIED_DONE" if m else "SUBMISSION_COMPLETE_SCORE_PARSE_PENDING"
            persist()
            return receipt

    except Exception as exc:
        receipt["status"] = "BLOCKED_OR_FAILED"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        persist()
        return receipt


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

    ex = sub.add_parser("execute")
    ex.add_argument("--candidate-dir", required=True)
    ex.add_argument("--gate-file", required=True)
    ex.add_argument("--kernel", required=True)
    ex.add_argument("--message", required=True)
    ex.add_argument("--receipt", required=True)
    ex.add_argument("--kernel-timeout-seconds", type=int, default=18000)
    ex.add_argument("--score-wait-seconds", type=int, default=18000)

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

    if args.cmd == "execute":
        result = execute_actuator(
            Path(args.candidate_dir),
            Path(args.gate_file),
            kernel=args.kernel,
            message=args.message,
            receipt_path=Path(args.receipt),
            kernel_timeout_seconds=args.kernel_timeout_seconds,
            score_wait_seconds=args.score_wait_seconds,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] in ("VERIFIED_DONE", "HOLD_PREFLIGHT", "HOLD_EXECUTION_APPROVAL", "CHECKPOINT_KERNEL_STILL_RUNNING") else 4

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
