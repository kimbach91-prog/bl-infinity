#!/usr/bin/env python3
"""R250: source-free pre-action exact-memory / contradiction audit.

Purpose
-------
Test a portable mechanism grounded by the independently verified OY1 public
controller without importing its game results, action logs, solutions, source
for ARC environments, or remote model behavior:

* exact visible-state + action empirical transition memory;
* prediction is scored BEFORE the current outcome is incorporated;
* run-local online memory is reset for every p10..p19 trajectory;
* contradictory outcomes permanently invalidate an online edge for that trace.

Protocol per game
-----------------
p0..p9   : fit a static exact visible-state/action -> exact next-frame table,
           keeping only keys with one observed outcome.
p10..p19 : frozen public-development scoring.  For each trajectory independently,
           process transitions in temporal order.  First audit the static table.
           Where it abstains, permit an online prediction only from an identical
           visible-state/action observed earlier in THAT SAME trajectory.  The
           current outcome is added only after scoring, so no future leakage.

This is PUBLIC_OFFLINE development evidence only.  The same public traces have
been reused elsewhere; it is not independent generalization or Kaggle evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

RUNG = 250


def stable(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(x: Any) -> str:
    return hashlib.sha256(stable(x).encode()).hexdigest()


def pnum(path: Path) -> int:
    m = re.search(r"_p(\d+)_events\.jsonl$", path.name)
    return int(m.group(1)) if m else -1


def game_id(path: Path) -> str:
    m = re.match(r"(.+)_p\d+_events\.jsonl$", path.name)
    return m.group(1) if m else path.stem


def load_events(path: Path) -> list[dict]:
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if obj.get("type") in {"initial", "action"} and isinstance(obj.get("board"), list):
            rows.append(obj)
    if len(rows) < 2:
        raise ValueError(f"{path}: insufficient events")
    return rows


def action_name(event: dict) -> str:
    return str(event.get("action_display") or event.get("action_name") or "")


def transitions(path: Path) -> list[dict]:
    events = load_events(path)
    before = events[0]
    out = []
    for event in events[1:]:
        if event.get("type") != "action":
            before = event
            continue
        b = [[int(v) for v in row] for row in before["board"]]
        a = [[int(v) for v in row] for row in event["board"]]
        if len(b) == len(a) and len(b[0]) == len(a[0]):
            out.append({
                "trace": path.name,
                "before": b,
                "after": a,
                "action": action_name(event),
            })
        before = event
    return out


def key(row: dict) -> str:
    return digest({"before": row["before"], "action": row["action"]})


def fit_static(paths: list[Path]) -> dict[str, list[list[int]]]:
    outcomes: dict[str, dict[str, list[list[int]]]] = defaultdict(dict)
    for path in paths:
        for row in transitions(path):
            outcomes[key(row)][digest(row["after"])] = row["after"]
    return {
        k: next(iter(by_digest.values()))
        for k, by_digest in outcomes.items()
        if len(by_digest) == 1
    }


def evaluate_game(paths: list[Path]) -> dict:
    paths = sorted(paths, key=pnum)
    nums = [pnum(p) for p in paths]
    if nums != list(range(20)):
        raise ValueError(f"{game_id(paths[0])}: exact p0..p19 required, got {nums}")

    static = fit_static(paths[:10])
    stats = Counter()
    per_trace = {}
    wrong_examples = []

    for path in paths[10:]:
        online_outcomes: dict[str, dict[str, list[list[int]]]] = defaultdict(dict)
        invalidated: set[str] = set()
        ts = Counter()

        for row in transitions(path):
            stats["transitions"] += 1
            ts["transitions"] += 1
            k = key(row)
            actual = row["after"]
            actual_digest = digest(actual)

            if k in static:
                stats["static_predictions"] += 1
                ts["static_predictions"] += 1
                ok = static[k] == actual
                stats["static_correct" if ok else "static_wrong"] += 1
                ts["static_correct" if ok else "static_wrong"] += 1
                if not ok and len(wrong_examples) < 40:
                    wrong_examples.append({
                        "trace": path.name,
                        "lane": "static",
                        "action": row["action"],
                        "key": k,
                    })
            else:
                stats["static_abstain"] += 1
                ts["static_abstain"] += 1
                prior = online_outcomes.get(k, {})
                if k not in invalidated and len(prior) == 1:
                    pred = next(iter(prior.values()))
                    stats["online_predictions"] += 1
                    ts["online_predictions"] += 1
                    ok = pred == actual
                    stats["online_correct" if ok else "online_wrong"] += 1
                    ts["online_correct" if ok else "online_wrong"] += 1
                    if not ok and len(wrong_examples) < 40:
                        wrong_examples.append({
                            "trace": path.name,
                            "lane": "online",
                            "action": row["action"],
                            "key": k,
                        })
                else:
                    stats["online_abstain"] += 1
                    ts["online_abstain"] += 1

            # Outcome becomes available only AFTER the pre-action prediction above.
            bucket = online_outcomes[k]
            bucket[actual_digest] = actual
            if len(bucket) > 1 and k not in invalidated:
                invalidated.add(k)
                stats["online_contradictions"] += 1
                ts["online_contradictions"] += 1

        per_trace[path.name] = dict(ts)

    sp = stats["static_predictions"]
    op = stats["online_predictions"]
    static_accuracy = stats["static_correct"] / sp if sp else None
    online_accuracy = stats["online_correct"] / op if op else None
    online_gate = bool(op > 0 and stats["online_wrong"] == 0)

    return {
        "static_keys": len(static),
        "heldout": {
            **dict(stats),
            "static_accuracy": round(static_accuracy, 6) if static_accuracy is not None else None,
            "online_added_accuracy": round(online_accuracy, 6) if online_accuracy is not None else None,
        },
        "online_zero_wrong_added_gain": online_gate,
        "per_trace": per_trace,
        "wrong_examples": wrong_examples,
    }


def run(paths: list[Path]) -> dict:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        grouped[game_id(path)].append(path)
    games = {g: evaluate_game(ps) for g, ps in sorted(grouped.items())}

    agg = Counter()
    gain_games = []
    for g, result in games.items():
        h = result["heldout"]
        for name in (
            "transitions", "static_predictions", "static_correct", "static_wrong",
            "static_abstain", "online_predictions", "online_correct", "online_wrong",
            "online_abstain", "online_contradictions",
        ):
            agg[name] += int(h.get(name, 0) or 0)
        if result["online_zero_wrong_added_gain"]:
            gain_games.append(g)

    sp = agg["static_predictions"]
    op = agg["online_predictions"]
    aggregate = {
        **dict(agg),
        "static_accuracy": round(agg["static_correct"] / sp, 6) if sp else None,
        "online_added_accuracy": round(agg["online_correct"] / op, 6) if op else None,
        "online_gain_games": gain_games,
        "online_gain_game_count": len(gain_games),
        "game_count": len(games),
    }
    integration_candidate = bool(op > 0 and agg["online_wrong"] == 0)

    return {
        "schema": "deus/arc3-r250-online-exact-memory-audit/1",
        "rung": RUNG,
        "grounding": {
            "mechanism_source": "OYLabsAI/arc-agi-3-api-harness",
            "source_commit": "0c7848dafeb4d7969279b5f193af71112404309a",
            "source_runtime_receipt": "R249/run35778071015/artifact10716079453",
            "portable_mechanism": "run-local empirical transition memory with contradiction invalidation",
            "game_results_or_action_logs_imported": False,
        },
        "protocol": {
            "static_fit": "p0-p9 exact visible-state/action unique next frame",
            "frozen_eval": "p10-p19 public development",
            "online_scope": "reset independently for every p10-p19 trajectory",
            "prediction_timing": "before current outcome is incorporated",
            "contradiction_policy": "multiple observed outcomes permanently invalidate online key within trace",
        },
        "games": games,
        "aggregate": aggregate,
        "promotion": {
            "integration_candidate": integration_candidate,
            "solver_promotion": False,
            "kaggle_packaging": False,
        },
        "truth": {
            "public_trace_only": True,
            "game_source_read": False,
            "upstream_oy_game_results_imported": False,
            "upstream_oy_action_logs_imported": False,
            "remote_inference_called": False,
            "paid_api_called": False,
            "p10_p19_future_outcomes_used_for_prediction": False,
            "online_updates_after_scoring_only": True,
            "public_development_reused_not_independent_heldout": True,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "aggregate": result["aggregate"],
        "integration_candidate": result["promotion"]["integration_candidate"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
