#!/usr/bin/env python3
"""ARC-AGI-3 representation-granularity guard.

Purpose: prevent solver/harness changes from being promoted on evidence that is
an artefact of how finely or coarsely state is encoded. This is a generic,
clean-room audit utility: it consumes trace rows and evaluates named
representations without assuming any particular game solution.

Public research grounding (not copied implementation):
  iamvxrn/arc-agi-compressed@6350c2ee7f18ba7e66b1582e7afdb796ce10e5a5
  docs/GRANULARITY_DECIDES_EVERY_TEST.md
The cited work reports that ARC-AGI-3 conclusions can flip when the same world is
partitioned too finely (near-unique board hashes) or too coarsely. This guard
turns that observation into a fail-closed promotion check.

Input JSONL row shape:
  {"outcome": <JSON scalar>, "representations": {"name": <JSON scalar>, ...}}

No Kaggle score is produced by this tool. A PASS only means the evidence has
repeat support and is not obviously degenerate at the tested representation.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

SOURCE_REPO = "iamvxrn/arc-agi-compressed"
SOURCE_COMMIT = "6350c2ee7f18ba7e66b1582e7afdb796ce10e5a5"
SOURCE_DOC = "docs/GRANULARITY_DECIDES_EVERY_TEST.md"


@dataclass(frozen=True)
class Audit:
    name: str
    rows: int
    distinct_states: int
    uniqueness_ratio: float
    repeated_rows: int
    repeat_support_ratio: float
    repeated_states: int
    contradictory_repeated_states: int
    contradictory_repeated_state_ratio: float
    status: str
    promotable_evidence: bool


def _stable_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def audit_representation(
    rows: Iterable[dict[str, Any]],
    name: str,
    *,
    max_uniqueness: float = 0.80,
    min_repeat_support: float = 0.20,
    max_contradictory_repeated_state_ratio: float = 0.25,
) -> Audit:
    rows = list(rows)
    if not rows:
        raise ValueError("no rows")

    states: dict[str, list[str]] = defaultdict(list)
    for i, row in enumerate(rows):
        if "outcome" not in row:
            raise ValueError(f"row {i}: missing outcome")
        reps = row.get("representations")
        if not isinstance(reps, dict) or name not in reps:
            raise ValueError(f"row {i}: missing representation {name!r}")
        states[_stable_key(reps[name])].append(_stable_key(row["outcome"]))

    n = len(rows)
    distinct = len(states)
    repeated = {k: v for k, v in states.items() if len(v) > 1}
    repeated_rows = sum(len(v) for v in repeated.values())
    contradictions = sum(1 for v in repeated.values() if len(set(v)) > 1)
    repeated_state_count = len(repeated)
    contradiction_ratio = contradictions / repeated_state_count if repeated_state_count else 0.0
    uniqueness = distinct / n
    repeat_support = repeated_rows / n

    if uniqueness > max_uniqueness or repeat_support < min_repeat_support:
        status = "OVERFINE_OR_UNSUPPORTED"
    elif contradiction_ratio > max_contradictory_repeated_state_ratio:
        status = "TOO_COARSE_OR_HIDDEN_STATE"
    else:
        status = "SUPPORTED_NONDEGENERATE"

    return Audit(
        name=name,
        rows=n,
        distinct_states=distinct,
        uniqueness_ratio=round(uniqueness, 6),
        repeated_rows=repeated_rows,
        repeat_support_ratio=round(repeat_support, 6),
        repeated_states=repeated_state_count,
        contradictory_repeated_states=contradictions,
        contradictory_repeated_state_ratio=round(contradiction_ratio, 6),
        status=status,
        promotable_evidence=status == "SUPPORTED_NONDEGENERATE",
    )


def audit_all(rows: list[dict[str, Any]], names: list[str]) -> dict[str, Any]:
    audits = [audit_representation(rows, name) for name in names]
    promotable = [a.name for a in audits if a.promotable_evidence]
    return {
        "schema": "deus/arc3-representation-granularity-guard/1",
        "source_grounding": {
            "repo": SOURCE_REPO,
            "commit": SOURCE_COMMIT,
            "document": SOURCE_DOC,
            "claim_scope": "public research evidence about representation-granularity confounding",
        },
        "truth": {
            "kaggle_score": False,
            "hidden_score": False,
            "competition_submission": False,
            "model_behavior_gain": False,
        },
        "audits": [asdict(a) for a in audits],
        "promotable_representations": promotable,
        "gate": "PASS" if promotable else "HOLD",
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text().splitlines(), 1):
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError(f"line {line_no}: object required")
        rows.append(obj)
    return rows


def self_test() -> dict[str, Any]:
    rows = []
    outcomes = [0, 0, 1, 1, 0, 0, 1, 1, 0, 0]
    for i, outcome in enumerate(outcomes):
        rows.append(
            {
                "outcome": outcome,
                "representations": {
                    "too_fine": f"unique-{i}",
                    "too_coarse": "one-state",
                    "supported": "left" if i < 5 else "right",
                },
            }
        )
    # Make supported representation internally consistent while retaining repeats.
    for i, row in enumerate(rows):
        row["outcome"] = 0 if i < 5 else 1

    fine = audit_representation(rows, "too_fine")
    coarse_rows = [
        {"outcome": i % 2, "representations": {"too_coarse": "one-state"}}
        for i in range(10)
    ]
    coarse = audit_representation(coarse_rows, "too_coarse")
    supported = audit_representation(rows, "supported")

    assert fine.status == "OVERFINE_OR_UNSUPPORTED", fine
    assert coarse.status == "TOO_COARSE_OR_HIDDEN_STATE", coarse
    assert supported.status == "SUPPORTED_NONDEGENERATE", supported
    assert supported.promotable_evidence is True

    return {
        "schema": "deus/arc3-representation-granularity-guard-selftest/1",
        "passed": True,
        "cases": [asdict(fine), asdict(coarse), asdict(supported)],
        "truth": {
            "synthetic_fixture_only": True,
            "kaggle_score": False,
            "model_behavior_gain": False,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path)
    p.add_argument("--representation", action="append", default=[])
    p.add_argument("--output", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        result = self_test()
    else:
        if not args.input or not args.representation:
            p.error("--input and at least one --representation are required unless --self-test")
        result = audit_all(load_jsonl(args.input), args.representation)

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
