#!/usr/bin/env python3
"""Rung 134: prefix-only executable-rule world-model audit on pinned public ARC-AGI-3 traces.

Purpose
-------
Test whether a tiny clean-room executable hypothesis bank can predict transitions
for *previously unseen exact visible states* using only earlier transitions in the
same public trace. This is deliberately narrower than a solver benchmark and is
not an independent-generalization or Kaggle claim.

Rules are inferred only after an outcome has been observed. Before each current
outcome is revealed, the evaluator first asks the exact-state baseline, then (only
when exact-state lookup abstains) asks stable executable rules learned from the
prefix. Candidate rules must have support from at least two distinct prior visible
states and all applicable rules must agree on the same predicted frame; otherwise
the rule lane abstains.

The clean-room rule families are intentionally small:
  * identity
  * whole-foreground translation against a dominant background
  * single connected-component translation
  * deterministic whole-grid color map

Source inspiration/provenance: executable-world-model validation is a public
architectural idea also used by TWIN, pinned separately in the workflow metadata.
No upstream TWIN implementation is imported or copied here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

RUNG = 134
TUFA_REPO = "Tufalabs/duck-harness"
TUFA_COMMIT = "7652836056c59e044f093e3c13ed7438c814169e"
TWIN_REPO = "Alexyskoutnev/TWIN-ARC-AGI-3"
TWIN_COMMIT = "b9b937cf571a9cbd33e2074d83949cd761677ae7"
MIN_RULE_SUPPORT = 2
Grid = list[list[int]]


def stable(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(x: Any) -> str:
    return hashlib.sha256(stable(x).encode("utf-8")).hexdigest()


def as_grid(value: Any) -> Grid:
    if not isinstance(value, list) or not value:
        raise ValueError("board must be a non-empty list")
    out: Grid = []
    width: int | None = None
    for row in value:
        if not isinstance(row, list) or not row:
            raise ValueError("board rows must be non-empty lists")
        vals = [int(v) for v in row]
        width = len(vals) if width is None else width
        if len(vals) != width:
            raise ValueError("ragged board")
        out.append(vals)
    return out


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: object required")
        if obj.get("type") not in {"initial", "action"} or "board" not in obj:
            continue
        as_grid(obj["board"])
        events.append(obj)
    if len(events) < 2:
        raise ValueError(f"{path}: fewer than two board-bearing events")
    return events


def action_name(event: dict[str, Any]) -> str:
    return str(event.get("action_display") or event.get("action_name") or "")


def dominant_background(board: Grid) -> int:
    counts = Counter(v for row in board for v in row)
    # deterministic tie-break: most frequent, then smallest color id
    return min(counts, key=lambda c: (-counts[c], c))


def same_shape(a: Grid, b: Grid) -> bool:
    return len(a) == len(b) and len(a[0]) == len(b[0])


def blank_like(board: Grid, value: int) -> Grid:
    return [[value for _ in row] for row in board]


def rule_identity(before: Grid, after: Grid) -> dict[str, Any] | None:
    return {"kind": "identity"} if before == after else None


def detect_color_map(before: Grid, after: Grid) -> dict[str, Any] | None:
    if not same_shape(before, after) or before == after:
        return None
    mapping: dict[int, int] = {}
    for br, ar in zip(before, after):
        for x, y in zip(br, ar):
            prev = mapping.get(x)
            if prev is not None and prev != y:
                return None
            mapping[x] = y
    if all(k == v for k, v in mapping.items()):
        return None
    return {"kind": "color_map", "map": [[k, mapping[k]] for k in sorted(mapping)]}


def detect_global_translation(before: Grid, after: Grid) -> dict[str, Any] | None:
    if not same_shape(before, after) or before == after:
        return None
    bg = dominant_background(before)
    if dominant_background(after) != bg:
        return None
    bf = [(r, c, before[r][c]) for r in range(len(before)) for c in range(len(before[0])) if before[r][c] != bg]
    af = [(r, c, after[r][c]) for r in range(len(after)) for c in range(len(after[0])) if after[r][c] != bg]
    if not bf or len(bf) != len(af) or Counter(v for _, _, v in bf) != Counter(v for _, _, v in af):
        return None
    r0, c0, v0 = bf[0]
    candidates = {(ra - r0, ca - c0) for ra, ca, va in af if va == v0}
    good: list[tuple[int, int]] = []
    target = sorted(af)
    h, w = len(before), len(before[0])
    for dr, dc in sorted(candidates):
        shifted = []
        ok = True
        for r, c, v in bf:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w):
                ok = False
                break
            shifted.append((nr, nc, v))
        if ok and sorted(shifted) == target:
            good.append((dr, dc))
    if len(good) != 1 or good[0] == (0, 0):
        return None
    dr, dc = good[0]
    return {"kind": "global_translation", "background": bg, "dr": dr, "dc": dc}


def components(board: Grid, bg: int) -> list[list[tuple[int, int, int]]]:
    h, w = len(board), len(board[0])
    seen: set[tuple[int, int]] = set()
    out: list[list[tuple[int, int, int]]] = []
    for r in range(h):
        for c in range(w):
            if board[r][c] == bg or (r, c) in seen:
                continue
            q = deque([(r, c)])
            seen.add((r, c))
            comp: list[tuple[int, int, int]] = []
            while q:
                rr, cc = q.popleft()
                comp.append((rr, cc, board[rr][cc]))
                for nr, nc in ((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)):
                    if 0 <= nr < h and 0 <= nc < w and board[nr][nc] != bg and (nr, nc) not in seen:
                        seen.add((nr, nc))
                        q.append((nr, nc))
            out.append(sorted(comp))
    return out


def abs_comp_key(comp: Iterable[tuple[int, int, int]]) -> str:
    return stable(sorted(comp))


def shape_key(comp: list[tuple[int, int, int]]) -> tuple[str, tuple[int, int]]:
    min_r = min(r for r, _, _ in comp)
    min_c = min(c for _, c, _ in comp)
    norm = sorted((r - min_r, c - min_c, v) for r, c, v in comp)
    return stable(norm), (min_r, min_c)


def detect_single_component_translation(before: Grid, after: Grid) -> dict[str, Any] | None:
    if not same_shape(before, after) or before == after:
        return None
    bg = dominant_background(before)
    if dominant_background(after) != bg:
        return None
    bc = components(before, bg)
    ac = components(after, bg)
    bmap = {abs_comp_key(c): c for c in bc}
    amap = {abs_comp_key(c): c for c in ac}
    removed = [c for k, c in bmap.items() if k not in amap]
    added = [c for k, c in amap.items() if k not in bmap]
    if len(removed) != 1 or len(added) != 1:
        return None
    bshape, (br, bc0) = shape_key(removed[0])
    ashape, (ar, ac0) = shape_key(added[0])
    if bshape != ashape:
        return None
    dr, dc = ar - br, ac0 - bc0
    if (dr, dc) == (0, 0):
        return None
    return {
        "kind": "component_translation",
        "background": bg,
        "shape": bshape,
        "dr": dr,
        "dc": dc,
    }


def infer_rules(before: Grid, after: Grid) -> list[dict[str, Any]]:
    rules = [
        rule_identity(before, after),
        detect_global_translation(before, after),
        detect_single_component_translation(before, after),
        detect_color_map(before, after),
    ]
    uniq: dict[str, dict[str, Any]] = {}
    for rule in rules:
        if rule is not None:
            uniq[stable(rule)] = rule
    return [uniq[k] for k in sorted(uniq)]


def apply_rule(rule: dict[str, Any], board: Grid) -> Grid | None:
    kind = rule["kind"]
    if kind == "identity":
        return [row[:] for row in board]
    if kind == "color_map":
        mp = {int(a): int(b) for a, b in rule["map"]}
        if any(v not in mp for row in board for v in row):
            return None
        return [[mp[v] for v in row] for row in board]
    if kind == "global_translation":
        bg = int(rule["background"])
        if dominant_background(board) != bg:
            return None
        dr, dc = int(rule["dr"]), int(rule["dc"])
        h, w = len(board), len(board[0])
        out = blank_like(board, bg)
        for r in range(h):
            for c in range(w):
                v = board[r][c]
                if v == bg:
                    continue
                nr, nc = r + dr, c + dc
                if not (0 <= nr < h and 0 <= nc < w):
                    return None
                if out[nr][nc] != bg:
                    return None
                out[nr][nc] = v
        return out
    if kind == "component_translation":
        bg = int(rule["background"])
        if dominant_background(board) != bg:
            return None
        wanted = str(rule["shape"])
        matching: list[list[tuple[int, int, int]]] = []
        for comp in components(board, bg):
            sk, _ = shape_key(comp)
            if sk == wanted:
                matching.append(comp)
        if len(matching) != 1:
            return None
        moving = matching[0]
        dr, dc = int(rule["dr"]), int(rule["dc"])
        h, w = len(board), len(board[0])
        moving_pos = {(r, c) for r, c, _ in moving}
        out = [row[:] for row in board]
        for r, c, _ in moving:
            out[r][c] = bg
        targets: list[tuple[int, int, int]] = []
        for r, c, v in moving:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w):
                return None
            # Collision is allowed only with cells vacated by the moving component.
            if (nr, nc) not in moving_pos and board[nr][nc] != bg:
                return None
            targets.append((nr, nc, v))
        if len({(r, c) for r, c, _ in targets}) != len(targets):
            return None
        for r, c, v in targets:
            out[r][c] = v
        return out
    raise ValueError(f"unknown rule kind {kind}")


@dataclass
class Metrics:
    transitions: int = 0
    baseline_predictions: int = 0
    baseline_correct: int = 0
    baseline_wrong: int = 0
    candidate_predictions: int = 0
    candidate_correct: int = 0
    candidate_wrong: int = 0
    added_rule_predictions: int = 0
    added_rule_correct: int = 0
    added_rule_wrong: int = 0
    rule_conflict_abstentions: int = 0
    rule_no_applicable_abstentions: int = 0
    eligible_rule_applications: int = 0
    rules_learned: int = 0
    stable_rules_final: int = 0
    exact_unique_keys_final: int = 0

    def finalize(self) -> dict[str, Any]:
        d = asdict(self)
        d["baseline_accuracy"] = round(self.baseline_correct / self.baseline_predictions, 6) if self.baseline_predictions else None
        d["baseline_coverage"] = round(self.baseline_predictions / self.transitions, 6) if self.transitions else 0.0
        d["candidate_accuracy"] = round(self.candidate_correct / self.candidate_predictions, 6) if self.candidate_predictions else None
        d["candidate_coverage"] = round(self.candidate_predictions / self.transitions, 6) if self.transitions else 0.0
        d["added_rule_accuracy"] = round(self.added_rule_correct / self.added_rule_predictions, 6) if self.added_rule_predictions else None
        return d


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_outcomes: dict[str, set[str]] = defaultdict(set)
    exact_exemplar: dict[tuple[str, str], Grid] = {}

    # action -> stable(rule) -> metadata
    rule_bank: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    m = Metrics()
    pre = events[0]

    for event in events[1:]:
        if event.get("type") != "action":
            pre = event
            continue
        before = as_grid(pre["board"])
        after = as_grid(event["board"])
        action = action_name(event)
        pre_digest = digest(before)
        exact_key = digest({"board": before, "action": action})
        actual_digest = digest(after)
        m.transitions += 1

        # Baseline prediction from exact visible-state/action prefix only.
        seen = exact_outcomes.get(exact_key, set())
        baseline_prediction: Grid | None = None
        if len(seen) == 1:
            exp_digest = next(iter(seen))
            baseline_prediction = exact_exemplar[(exact_key, exp_digest)]
            m.baseline_predictions += 1
            if exp_digest == actual_digest and baseline_prediction == after:
                m.baseline_correct += 1
            else:
                m.baseline_wrong += 1

        # Candidate uses the exact prediction when available; otherwise asks only
        # stable rules learned from earlier outcomes for this action.
        candidate_prediction = baseline_prediction
        candidate_from_rule = False
        if candidate_prediction is None:
            proposed: dict[str, Grid] = {}
            eligible_count = 0
            for entry in rule_bank.get(action, {}).values():
                if entry["support"] < MIN_RULE_SUPPORT or len(entry["pre_states"]) < MIN_RULE_SUPPORT:
                    continue
                pred = apply_rule(entry["rule"], before)
                if pred is None:
                    continue
                eligible_count += 1
                proposed[digest(pred)] = pred
            m.eligible_rule_applications += eligible_count
            if not proposed:
                m.rule_no_applicable_abstentions += 1
            elif len(proposed) > 1:
                m.rule_conflict_abstentions += 1
            else:
                candidate_prediction = next(iter(proposed.values()))
                candidate_from_rule = True

        if candidate_prediction is not None:
            m.candidate_predictions += 1
            correct = candidate_prediction == after
            if correct:
                m.candidate_correct += 1
            else:
                m.candidate_wrong += 1
            if candidate_from_rule:
                m.added_rule_predictions += 1
                if correct:
                    m.added_rule_correct += 1
                else:
                    m.added_rule_wrong += 1

        # Reveal/ingest the current outcome only now.
        exact_outcomes[exact_key].add(actual_digest)
        exact_exemplar[(exact_key, actual_digest)] = [row[:] for row in after]
        for rule in infer_rules(before, after):
            key = stable(rule)
            entry = rule_bank[action].setdefault(key, {"rule": rule, "support": 0, "pre_states": set()})
            entry["support"] += 1
            entry["pre_states"].add(pre_digest)
            m.rules_learned += 1
        pre = event

    m.exact_unique_keys_final = len(exact_outcomes)
    m.stable_rules_final = sum(
        1
        for by_rule in rule_bank.values()
        for entry in by_rule.values()
        if entry["support"] >= MIN_RULE_SUPPORT and len(entry["pre_states"]) >= MIN_RULE_SUPPORT
    )
    return m.finalize()


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    summed = Metrics()
    fields = list(asdict(summed))
    for p in parts:
        for f in fields:
            setattr(summed, f, getattr(summed, f) + int(p[f]))
    return summed.finalize()


def run(paths: list[Path]) -> dict[str, Any]:
    per_trace: list[dict[str, Any]] = []
    meta: list[dict[str, Any]] = []
    for path in paths:
        events = load_events(path)
        result = audit_trace(events)
        per_trace.append(result)
        meta.append({"path": str(path), "board_events": len(events), "metrics": result})
    agg = aggregate(per_trace)
    strict_gain = (
        agg["added_rule_predictions"] > 0
        and agg["added_rule_correct"] > 0
        and agg["added_rule_wrong"] == 0
        and agg["candidate_correct"] > agg["baseline_correct"]
        and agg["candidate_wrong"] <= agg["baseline_wrong"]
    )
    return {
        "schema": "deus/arc3-public-executable-world-model/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREFIX_ONLY_EXECUTABLE_RULE_AUDIT",
        "source_grounding": {
            "public_trace_repo": TUFA_REPO,
            "public_trace_commit": TUFA_COMMIT,
            "architectural_reference_repo": TWIN_REPO,
            "architectural_reference_commit": TWIN_COMMIT,
            "clean_room_implementation": True,
            "upstream_twin_code_imported": False,
            "upstream_twin_code_copied": False,
        },
        "causality_contract": {
            "prediction_uses_current_outcome": False,
            "prediction_uses_future_transitions": False,
            "rule_is_learned_only_after_observed_outcome": True,
            "minimum_distinct_prior_states_per_rule": MIN_RULE_SUPPORT,
            "exact_baseline_consulted_first": True,
            "rule_prediction_only_when_exact_baseline_abstains": True,
            "all_applicable_stable_rules_must_agree": True,
            "maps_reset_between_trace_files": True,
        },
        "rule_families": ["identity", "global_translation", "component_translation", "color_map"],
        "traces": meta,
        "aggregate": agg,
        "next_gate_signal": "STRICT_PREFIX_UNSEEN_STATE_RULE_GAIN" if strict_gain else "NO_STRICT_PREFIX_UNSEEN_STATE_RULE_GAIN",
        "promotion": {
            "strict_prefix_rule_gain": strict_gain,
            "candidate_model_promotion": False,
            "kaggle_packaging": False,
            "reason": (
                "positive CPU public-trace rule evidence may justify a later fixed-model A/B; "
                "it cannot establish solver gain or Kaggle hidden-score gain"
            ),
        },
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "prefix_unseen_exact_state_prediction_measured": True,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "model_execution": False,
            "gpu_execution": False,
            "kaggle_data_read": False,
            "kaggle_execution": False,
            "kaggle_output_claim": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
            "owner_score_claim": False,
            "award_or_settlement_claim": False,
        },
    }


def synthetic_events() -> list[dict[str, Any]]:
    # Three distinct states with the same single-cell component moving RIGHT.
    # The first two teach a stable executable component/global translation;
    # the third is unseen to exact lookup and should be predicted from prefix.
    states = [
        ([[1, 0, 0, 0]], [[0, 1, 0, 0]]),
        ([[0, 1, 0, 0]], [[0, 0, 1, 0]]),
        ([[0, 0, 1, 0]], [[0, 0, 0, 1]]),
    ]
    events: list[dict[str, Any]] = []
    for before, after in states:
        events.append({"type": "initial", "board": before, "level": 1})
        events.append({"type": "action", "board": after, "level": 1, "action_display": "RIGHT"})
    return events


def self_test() -> dict[str, Any]:
    m = audit_trace(synthetic_events())
    invariants = {
        "baseline_has_no_unique_state_prediction": m["baseline_predictions"] == 0,
        "rule_adds_prediction": m["added_rule_predictions"] >= 1,
        "rule_added_prediction_is_correct": m["added_rule_correct"] >= 1,
        "rule_adds_no_wrong_prediction": m["added_rule_wrong"] == 0,
        "candidate_strictly_improves_correct_count": m["candidate_correct"] > m["baseline_correct"],
        "stable_rule_exists": m["stable_rules_final"] >= 1,
    }
    return {
        "schema": "deus/arc3-public-executable-world-model-selftest/1",
        "rung": RUNG,
        "passed": all(invariants.values()),
        "invariants": invariants,
        "metrics": m,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        result = self_test()
        code = 0 if result["passed"] else 2
    else:
        if not args.input:
            raise SystemExit("at least one --input is required")
        result = run(args.input)
        code = 0
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
