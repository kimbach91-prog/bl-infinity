#!/usr/bin/env python3
from __future__ import annotations

# Trigger independent verification after the workflow definition is present in the PR ref.
import argparse, hashlib, json
from pathlib import Path

EXPECTED = {
    "m0r0": {
        "game_key": "game_id", "game": "m0r0-492f87ba", "levels": 6, "actions": 183,
        "route": "447eeb9b406ec8e9d7c57e9a645051bbb5c78d5c163c2c8a0f05c7e0a655dba3",
        "frame": "52cf50ae7cc9145f27a3f80246aaf4bac868c722954934b77b188baec8c78ec2",
        "source": "fb261a3918819cd4964bf34f5c32d0e69df3d142",
        "online_card": "f60ace31-51fd-4652-a323-3b79041b267b",
        "online_run": "35523110479",
    },
    "ls20": {
        "game_key": "game", "game": "ls20", "levels": 7, "actions": 348,
        "route": "c6f7e561e61aa171ffdbb07568ac99c05ecc968819d5246d336ef09d40fec24b",
        "frame": "25ff8487db87dd5230c0f5704c32011f0894df50319b165dcd5923b55a0a160e",
        "source": "15e8b921da5f84ad31d36d5cbf7d4380af4b299e",
        "online_card": "0d0145fb-4a48-494a-a42e-de0f43dc8e88",
        "online_run": "35523274978",
    },
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def route_digest(game: str, actions):
    if game == "m0r0":
        return hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return hashlib.sha256(",".join(map(str, actions)).encode()).hexdigest()


def verify_one(game: str, d: Path, mode: str, require_online_card: bool) -> dict:
    exp = EXPECTED[game]
    r = json.loads((d / "receipt.json").read_text())
    actions = json.loads((d / "actions.json").read_text())
    transcript = json.loads((d / "transcript.json").read_text())
    checks = {
        "result_pass": r.get("result") == "PASS",
        "mode_exact": r.get("mode") == mode,
        "game_exact": r.get(exp["game_key"]) == exp["game"],
        "source_exact": r.get("source_sha") == exp["source"],
        "run_exact": str(r.get("run_id")) == exp["online_run"],
        "levels_exact": r.get("levels_completed") == exp["levels"],
        "state_win": r.get("state") == "WIN",
        "score_100": float(r.get("scorecard_score")) == 100.0,
        "actions_exact": r.get("actions_executed") == exp["actions"] == len(actions) == len(transcript),
        "route_exact": r.get("route_sha256") == exp["route"] == route_digest(game, actions),
        "frame_exact": r.get("final_frame_sha256") == exp["frame"] == transcript[-1].get("frame_sha256"),
        "public_scope": (
            (r.get("protocol") == "PUBLIC_DEVELOPMENT_FROZEN_ROUTE_REPLAY" or r.get("official_competition_claim") is False)
            and r.get("exploration_actions_included") is False
        ),
    }
    if require_online_card:
        checks["online_scorecard_exact"] = r.get("scorecard_id") == exp["online_card"]
    failures = [k for k, v in checks.items() if not v]
    return {
        "game": game, "mode": mode, "verdict": "PASS" if not failures else "FAIL",
        "checks": checks, "failures": failures,
        "scorecard_id": r.get("scorecard_id"), "scorecard_score": r.get("scorecard_score"),
        "levels_completed": r.get("levels_completed"), "actions_executed": r.get("actions_executed"),
        "route_sha256": r.get("route_sha256"), "final_frame_sha256": r.get("final_frame_sha256"),
        "receipt_sha256": sha256(d / "receipt.json"), "actions_sha256": sha256(d / "actions.json"),
        "transcript_sha256": sha256(d / "transcript.json"),
    }


def p09(root: Path) -> dict:
    rows = [verify_one("m0r0", root / "m0r0-online", "ONLINE", True), verify_one("ls20", root / "ls20-online", "ONLINE", True)]
    ok = all(x["verdict"] == "PASS" for x in rows)
    return {
        "schema": "DEUS_P09_ARC3_CURRENT_PUBLIC_CLOSURES_V1", "verdict": "PASS" if ok else "FAIL", "games": rows,
        "scope": "fresh ARC ONLINE public-development frozen-route replay receipts only",
        "claim_boundary": "Verifies m0r0 6/6 and ls20 7/7 public-development replays at scorecard_score=100.0. Not a hidden/private Kaggle competition score, not unseen-game generalization, and not an AGI claim.",
    }


def netci(root: Path, p09_path: Path) -> dict:
    p = json.loads(p09_path.read_text())
    online = {x["game"]: x for x in p["games"]}
    normal = [verify_one("m0r0", root / "m0r0-normal", "NORMAL", False), verify_one("ls20", root / "ls20-normal", "NORMAL", False)]
    cross = {}
    for n in normal:
        o = online[n["game"]]
        cross[n["game"]] = {
            "p09_pass": o["verdict"] == "PASS",
            "normal_pass": n["verdict"] == "PASS",
            "route_equivalent": o["route_sha256"] == n["route_sha256"],
            "final_frame_equivalent": o["final_frame_sha256"] == n["final_frame_sha256"],
            "levels_equivalent": o["levels_completed"] == n["levels_completed"],
            "actions_equivalent": o["actions_executed"] == n["actions_executed"],
            "score_100_both": float(o["scorecard_score"]) == 100.0 == float(n["scorecard_score"]),
        }
    ok = p.get("verdict") == "PASS" and all(x["verdict"] == "PASS" for x in normal) and all(all(v.values()) for v in cross.values())
    return {
        "schema": "DEUS_NET_CI_QUORUM_ARC3_CURRENT_PUBLIC_CLOSURES_V1", "verdict": "PASS" if ok else "FAIL",
        "normal_games": normal, "cross_mode": cross,
        "p09_receipt_sha256": sha256(p09_path),
        "scope": "cross-mode corroboration of the same frozen public-development routes",
        "provider_runtime_freshly_requeried_by_netci": False,
        "claim_boundary": "Corroborates current public-development route closure across ONLINE and NORMAL receipts. Does not promote these receipts to hidden/private Kaggle competition performance.",
    }


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", choices=["p09", "netci"], required=True); ap.add_argument("--root", type=Path, required=True); ap.add_argument("--p09", type=Path); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    out = p09(a.root) if a.mode == "p09" else netci(a.root, a.p09)
    a.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["verdict"] == "PASS" else 1)

if __name__ == "__main__": main()
