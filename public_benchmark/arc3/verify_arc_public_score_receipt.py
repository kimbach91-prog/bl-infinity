#!/usr/bin/env python3
"""Independent P09 + NET-CI scope verifier for the pinned ARC-AGI-3 public score receipt.

This verifier intentionally does NOT contact a hidden/private benchmark and does not
promote a public-development-game score into a Kaggle competition score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PINNED_ARTIFACT_COMMIT = "9f8b5ab7a2dc0bee8430414047b2dd767acd153c"
EXPECTED_SOURCE_COMMIT = "1c5973aea2e821ac3bdc1ffe1a95d38fced94dcf"
EXPECTED_CARD = "48180853-70f8-42d8-abe7-b5e00e701650"
EXPECTED_REPLAY = "3e93f549-89f6-4c93-86ad-d9227d5ebd95"
EXPECTED_ENV = "ls20-9607627b"
EXPECTED_SCORE = 10.714285714285714
EXPECTED_ROUTE_HASH = "1a7c9454283970113a8f0d2160155893f3341a36e1c37b43d17e8b0a10882807"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(source_dir: Path):
    route = json.loads((source_dir / "route.json").read_text(encoding="utf-8"))
    result = json.loads((source_dir / "result.json").read_text(encoding="utf-8"))
    readme = (source_dir / "README.md").read_text(encoding="utf-8")
    replay = (source_dir / "replay_route.py").read_text(encoding="utf-8")
    return route, result, readme, replay


def route_hash(actions: list[int]) -> str:
    return hashlib.sha256(",".join(str(x) for x in actions).encode("ascii")).hexdigest()


def check(name: str, cond: bool, details: dict, failures: list[str]):
    details[name] = bool(cond)
    if not cond:
        failures.append(name)


def verify_p09(source_dir: Path) -> dict:
    route, result, readme, replay = load(source_dir)
    failures: list[str] = []
    checks: dict[str, bool] = {}
    actions = route.get("actions", [])
    envs = result.get("environments", [])
    run = envs[0]["runs"][0] if len(envs) == 1 and envs[0].get("runs") else {}
    reproduction = result.get("reproduction", {})
    opaque = result.get("opaque", {})

    check("route_hash_recomputed", route_hash(actions) == EXPECTED_ROUTE_HASH == route.get("route_sha256"), checks, failures)
    check("action_count_58", len(actions) == 58 == route.get("action_count") == result.get("total_actions"), checks, failures)
    check("environment_exact", route.get("environment") == EXPECTED_ENV and opaque.get("environment") == EXPECTED_ENV and envs and envs[0].get("id") == EXPECTED_ENV, checks, failures)
    check("scope_public_development_game", route.get("evaluation_scope") == "public-development-game" and opaque.get("evaluation_scope") == "public-development-game", checks, failures)
    check("competition_mode_false", result.get("competition_mode") is False, checks, failures)
    check("score_exact", abs(float(result.get("score")) - EXPECTED_SCORE) < 1e-12 and abs(float(run.get("score")) - EXPECTED_SCORE) < 1e-12, checks, failures)
    check("levels_2_of_7", result.get("total_levels_completed") == 2 and result.get("total_levels") == 7 and envs and envs[0].get("levels_completed") == 2 and envs[0].get("level_count") == 7, checks, failures)
    check("scorecard_id_exact", result.get("card_id") == EXPECTED_CARD, checks, failures)
    check("replay_id_exact", run.get("guid") == EXPECTED_REPLAY, checks, failures)
    check("reproduction_route_hash_exact", reproduction.get("route_sha256") == EXPECTED_ROUTE_HASH, checks, failures)
    check("reproduction_source_commit_exact", reproduction.get("source_commit") == EXPECTED_SOURCE_COMMIT, checks, failures)
    check("claim_boundary_public_only", "not hidden" in str(opaque.get("claim_boundary", "")).lower() and "not hidden" in readme.lower(), checks, failures)
    check("replay_script_closes_server_scorecard", "close_scorecard" in replay and "model_dump" in replay, checks, failures)
    check("no_api_key_serialized", result.get("api_key") is None, checks, failures)

    return {
        "schema": "DEUS_P09_ARC3_PUBLIC_SCORE_RECEIPT_V1",
        "verdict": "PASS" if not failures else "FAIL",
        "pinned_artifact_commit": PINNED_ARTIFACT_COMMIT,
        "declared_reproduction_source_commit": EXPECTED_SOURCE_COMMIT,
        "benchmark": "ARC-AGI-3",
        "environment": EXPECTED_ENV,
        "evaluation_scope": "public-development-game",
        "score_percent": EXPECTED_SCORE,
        "levels_completed": 2,
        "level_count": 7,
        "actions": 58,
        "scorecard_id": EXPECTED_CARD,
        "replay_id": EXPECTED_REPLAY,
        "route_sha256": EXPECTED_ROUTE_HASH,
        "checks": checks,
        "failures": failures,
        "source_digests": {
            "README.md": sha256(source_dir / "README.md"),
            "route.json": sha256(source_dir / "route.json"),
            "result.json": sha256(source_dir / "result.json"),
            "replay_route.py": sha256(source_dir / "replay_route.py"),
        },
        "claim_boundary": "Independent P09 verification of a pinned ARC server receipt for one public-development game (ls20). This is not a Kaggle hidden/private competition score, not general ARC-AGI-3 performance, and not an AGI claim.",
    }


def verify_netci(source_dir: Path, p09_path: Path) -> dict:
    route, result, readme, replay = load(source_dir)
    p09 = json.loads(p09_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    checks: dict[str, bool] = {}
    actions = route.get("actions", [])

    check("p09_pass", p09.get("verdict") == "PASS", checks, failures)
    check("p09_scope_exact", p09.get("evaluation_scope") == "public-development-game" and p09.get("environment") == EXPECTED_ENV, checks, failures)
    check("p09_score_exact", abs(float(p09.get("score_percent")) - EXPECTED_SCORE) < 1e-12, checks, failures)
    check("source_route_hash_exact", route_hash(actions) == EXPECTED_ROUTE_HASH == result.get("reproduction", {}).get("route_sha256"), checks, failures)
    check("source_card_replay_exact", result.get("card_id") == EXPECTED_CARD and result.get("environments", [])[0].get("runs", [])[0].get("guid") == EXPECTED_REPLAY, checks, failures)
    check("source_scope_noncompetition", result.get("competition_mode") is False and "public-development-game" in readme, checks, failures)
    check("public_provider_links_disclosed", f"https://arcprize.org/scorecards/{EXPECTED_CARD}" in readme and f"https://arcprize.org/replay/{EXPECTED_REPLAY}" in readme, checks, failures)
    check("reproduction_code_present", "create_scorecard" in replay and "environment.step" in replay and "close_scorecard" in replay, checks, failures)

    return {
        "schema": "DEUS_NET_CI_QUORUM_ARC3_PUBLIC_SCORE_V1",
        "verdict": "PASS" if not failures else "FAIL",
        "corroboration_scope": "core-source-equivalent public ARC receipt scope",
        "p09_receipt_sha256": sha256(p09_path),
        "pinned_artifact_commit": PINNED_ARTIFACT_COMMIT,
        "scorecard_id": EXPECTED_CARD,
        "score_percent": EXPECTED_SCORE,
        "checks": checks,
        "failures": failures,
        "provider_runtime_freshly_requeried": False,
        "claim_boundary": "NET-CI corroborates source/receipt identity and exact public-development scope only. It does not convert this into a hidden/private Kaggle competition score and does not itself prove fresh provider runtime.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["p09", "netci"], required=True)
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--p09", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.mode == "p09":
        receipt = verify_p09(args.source_dir)
    else:
        if args.p09 is None:
            raise SystemExit("--p09 is required for netci mode")
        receipt = verify_netci(args.source_dir, args.p09)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
