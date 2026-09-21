#!/usr/bin/env python3
"""Rung 138: object-role executable transition programs.

Representation change from rung 137
-----------------------------------
Rung 137 matched a local pixel patch. Rung 138 instead segments same-color
4-connected non-background objects and learns executable *role* programs:
select an object by a state-relative role (for example unique smallest object or
a unique directional extreme), then apply a translation. Directional actions may
encode the translation in action-relative coordinates, so the program is not tied
to literal colors, locations, or local pixel patches.

The audit is prefix-only and prequential. Exact visible-state/action memory has
priority. A role program must have >=2 prior-state support and >=3 prior unseen-
state shadow tests with zero error before it may affect the candidate. The current
outcome is revealed only after the current decision. Ambiguous selection,
non-translation effects, collisions, and out-of-bounds moves fail closed.

This is source-assisted replay on pinned public traces only. It is not independent
generalization, model/GPU/Kaggle execution, submission, leaderboard, or award
evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base

RUNG = 138
MIN_PROGRAM_SUPPORT = 2
MIN_PRIOR_SHADOW_TESTS = 3
Grid = list[list[int]]

# Human-readable directional actions are handled action-relatively. ARC-AGI-3
# generic ACTIONn names remain literal-delta programs unless their semantics are
# learned elsewhere; we do not guess hidden control mappings here.
ACTION_VEC = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}


@dataclass(frozen=True)
class Obj:
    color: int
    cells: tuple[tuple[int, int], ...]
    r0: int
    c0: int
    r1: int
    c1: int

    @property
    def area(self) -> int:
        return len(self.cells)

    @property
    def h(self) -> int:
        return self.r1 - self.r0 + 1

    @property
    def w(self) -> int:
        return self.c1 - self.c0 + 1

    @property
    def shape(self) -> tuple[tuple[int, int], ...]:
        return tuple(sorted((r - self.r0, c - self.c0) for r, c in self.cells))

    @property
    def center2(self) -> tuple[int, int]:
        # Twice the bbox center, kept integral for deterministic comparisons.
        return (self.r0 + self.r1, self.c0 + self.c1)


def background_color(board: Grid) -> int:
    counts = Counter(v for row in board for v in row)
    # Deterministic tie break; 0 is naturally preferred if equally frequent.
    return min(counts, key=lambda v: (-counts[v], v))


def objects(board: Grid) -> list[Obj]:
    h, w = len(board), len(board[0])
    bg = background_color(board)
    seen: set[tuple[int, int]] = set()
    out: list[Obj] = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or board[r][c] == bg:
                continue
            color = board[r][c]
            stack = [(r, c)]
            seen.add((r, c))
            cells: list[tuple[int, int]] = []
            while stack:
                rr, cc = stack.pop()
                cells.append((rr, cc))
                for nr, nc in ((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)):
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen and board[nr][nc] == color:
                        seen.add((nr, nc))
                        stack.append((nr, nc))
            rs = [x for x, _ in cells]
            cs = [y for _, y in cells]
            out.append(Obj(color, tuple(sorted(cells)), min(rs), min(cs), max(rs), max(cs)))
    return out


def translated_cells(obj: Obj, dr: int, dc: int) -> tuple[tuple[int, int], ...]:
    return tuple(sorted((r + dr, c + dc) for r, c in obj.cells))


def infer_pure_translation(before: Grid, after: Grid) -> tuple[int, int, int] | None:
    """Return (before-object-index, dr, dc) iff one object translation reproduces after."""
    if not base.same_shape(before, after) or before == after:
        return None
    bgs = background_color(before), background_color(after)
    if bgs[0] != bgs[1]:
        return None
    bg = bgs[0]
    obs = objects(before)
    oas = objects(after)
    candidates: list[tuple[int, int, int]] = []
    for i, ob in enumerate(obs):
        for oa in oas:
            if ob.color != oa.color or ob.shape != oa.shape or ob.area != oa.area:
                continue
            dr, dc = oa.r0 - ob.r0, oa.c0 - ob.c0
            if (dr, dc) == (0, 0):
                continue
            pred = move_object(before, ob, dr, dc, bg)
            if pred == after:
                candidates.append((i, dr, dc))
    # More than one explanation means object identity/role is not grounded.
    if len(candidates) != 1:
        return None
    return candidates[0]


def move_object(board: Grid, obj: Obj, dr: int, dc: int, bg: int | None = None) -> Grid | None:
    h, w = len(board), len(board[0])
    if bg is None:
        bg = background_color(board)
    src = set(obj.cells)
    dst = {(r + dr, c + dc) for r, c in obj.cells}
    if any(not (0 <= r < h and 0 <= c < w) for r, c in dst):
        return None
    # Destination may overlap the object's own old cells, but not other content.
    for r, c in dst - src:
        if board[r][c] != bg:
            return None
    out = [row[:] for row in board]
    for r, c in src - dst:
        out[r][c] = bg
    for r, c in dst:
        out[r][c] = obj.color
    return out


def unique_arg(objs: list[Obj], key, want_min: bool) -> int | None:
    if not objs:
        return None
    vals = [key(o) for o in objs]
    target = min(vals) if want_min else max(vals)
    idx = [i for i, v in enumerate(vals) if v == target]
    return idx[0] if len(idx) == 1 else None


def role_indices(board: Grid) -> dict[str, int]:
    """State-relative roles that do not encode literal color, shape, or location."""
    obs = objects(board)
    roles: dict[str, int] = {}
    if len(obs) == 1:
        roles["only_object"] = 0

    specs = {
        "smallest_area": (lambda o: o.area, True),
        "largest_area": (lambda o: o.area, False),
        "topmost": (lambda o: o.r0, True),
        "bottommost": (lambda o: o.r1, False),
        "leftmost": (lambda o: o.c0, True),
        "rightmost": (lambda o: o.c1, False),
        "narrowest": (lambda o: o.w, True),
        "widest": (lambda o: o.w, False),
        "shortest": (lambda o: o.h, True),
        "tallest": (lambda o: o.h, False),
    }
    for name, (fn, want_min) in specs.items():
        idx = unique_arg(obs, fn, want_min)
        if idx is not None:
            roles[name] = idx

    h, w = len(board), len(board[0])
    border_specs = {
        "nearest_top_border": (lambda o: o.r0, True),
        "nearest_bottom_border": (lambda o: h - 1 - o.r1, True),
        "nearest_left_border": (lambda o: o.c0, True),
        "nearest_right_border": (lambda o: w - 1 - o.c1, True),
    }
    for name, (fn, want_min) in border_specs.items():
        idx = unique_arg(obs, fn, want_min)
        if idx is not None:
            roles[name] = idx

    # Squared distance of bbox center to board center, scale-free enough for a
    # role selector while retaining deterministic integer comparisons.
    cr2, cc2 = h - 1, w - 1
    dist2 = lambda o: (o.center2[0] - cr2) ** 2 + (o.center2[1] - cc2) ** 2
    idx = unique_arg(obs, dist2, True)
    if idx is not None:
        roles["nearest_center"] = idx
    idx = unique_arg(obs, dist2, False)
    if idx is not None:
        roles["farthest_center"] = idx
    return roles


ROLE_PRIORITY = (
    "only_object",
    "smallest_area",
    "largest_area",
    "nearest_top_border",
    "nearest_bottom_border",
    "nearest_left_border",
    "nearest_right_border",
    "topmost",
    "bottommost",
    "leftmost",
    "rightmost",
    "nearest_center",
    "farthest_center",
    "narrowest",
    "widest",
    "shortest",
    "tallest",
)


def encode_delta(action: str, dr: int, dc: int) -> dict[str, Any]:
    vec = ACTION_VEC.get(action.upper())
    if vec is not None:
        vr, vc = vec
        # Unit action vectors make these dot/cross coordinates exact.
        along = dr * vr + dc * vc
        lateral = dr * (-vc) + dc * vr
        return {"mode": "action_relative", "along": along, "lateral": lateral}
    return {"mode": "literal", "dr": dr, "dc": dc}


def decode_delta(action: str, delta: dict[str, Any]) -> tuple[int, int] | None:
    if delta.get("mode") == "literal":
        return int(delta["dr"]), int(delta["dc"])
    if delta.get("mode") == "action_relative":
        vec = ACTION_VEC.get(action.upper())
        if vec is None:
            return None
        vr, vc = vec
        along, lateral = int(delta["along"]), int(delta["lateral"])
        return along * vr + lateral * (-vc), along * vc + lateral * vr
    return None


def infer_programs(before: Grid, after: Grid, action: str) -> list[dict[str, Any]]:
    moved = infer_pure_translation(before, after)
    if moved is None:
        return []
    idx, dr, dc = moved
    roles = role_indices(before)
    delta = encode_delta(action, dr, dc)
    programs: list[dict[str, Any]] = []
    for role in ROLE_PRIORITY:
        if roles.get(role) == idx:
            programs.append({"kind": "object_role_translation", "role": role, "delta": delta})
    return programs


def apply_program(program: dict[str, Any], board: Grid, action: str) -> Grid | None:
    obs = objects(board)
    idx = role_indices(board).get(str(program["role"]))
    if idx is None or not (0 <= idx < len(obs)):
        return None
    delta = decode_delta(action, dict(program["delta"]))
    if delta is None or delta == (0, 0):
        return None
    return move_object(board, obs[idx], delta[0], delta[1])


def qualified(stats: dict[str, int]) -> bool:
    return stats["tests"] >= MIN_PRIOR_SHADOW_TESTS and stats["wrong"] == 0


@dataclass
class Metrics:
    transitions: int = 0
    baseline_predictions: int = 0
    baseline_correct: int = 0
    baseline_wrong: int = 0
    candidate_predictions: int = 0
    candidate_correct: int = 0
    candidate_wrong: int = 0
    added_program_predictions: int = 0
    added_program_correct: int = 0
    added_program_wrong: int = 0
    program_shadow_tests: int = 0
    program_shadow_correct: int = 0
    program_shadow_wrong: int = 0
    no_qualified_program_abstentions: int = 0
    qualified_program_conflict_abstentions: int = 0
    qualified_program_applications: int = 0
    programs_inferred: int = 0
    pure_translation_transitions: int = 0
    stable_programs_final: int = 0
    reliability_qualified_programs_final: int = 0
    exact_unique_keys_final: int = 0

    def finalize(self) -> dict[str, Any]:
        d = asdict(self)
        d["baseline_accuracy"] = round(self.baseline_correct / self.baseline_predictions, 6) if self.baseline_predictions else None
        d["baseline_coverage"] = round(self.baseline_predictions / self.transitions, 6) if self.transitions else 0.0
        d["candidate_accuracy"] = round(self.candidate_correct / self.candidate_predictions, 6) if self.candidate_predictions else None
        d["candidate_coverage"] = round(self.candidate_predictions / self.transitions, 6) if self.transitions else 0.0
        d["added_program_accuracy"] = round(self.added_program_correct / self.added_program_predictions, 6) if self.added_program_predictions else None
        d["program_shadow_accuracy"] = round(self.program_shadow_correct / self.program_shadow_tests, 6) if self.program_shadow_tests else None
        return d


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_outcomes: dict[str, set[str]] = defaultdict(set)
    exact_exemplar: dict[tuple[str, str], Grid] = {}
    program_bank: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    shadow: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"tests": 0, "correct": 0, "wrong": 0})
    m = Metrics()
    pre = events[0]

    for event in events[1:]:
        if event.get("type") != "action":
            pre = event
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(event["board"])
        action = base.action_name(event)
        pre_digest = base.digest(before)
        exact_key = base.digest({"board": before, "action": action})
        actual_digest = base.digest(after)
        m.transitions += 1

        seen = exact_outcomes.get(exact_key, set())
        baseline_prediction: Grid | None = None
        if len(seen) == 1:
            exp_digest = next(iter(seen))
            baseline_prediction = exact_exemplar[(exact_key, exp_digest)]
            m.baseline_predictions += 1
            if baseline_prediction == after:
                m.baseline_correct += 1
            else:
                m.baseline_wrong += 1

        candidate_prediction = baseline_prediction
        candidate_from_program = False
        shadow_applicable: list[tuple[str, Grid]] = []

        if baseline_prediction is None:
            qualified_predictions: dict[str, Grid] = {}
            for pkey, entry in program_bank.get(action, {}).items():
                if entry["support"] < MIN_PROGRAM_SUPPORT or len(entry["pre_states"]) < MIN_PROGRAM_SUPPORT:
                    continue
                pred = apply_program(entry["program"], before, action)
                if pred is None:
                    continue
                shadow_applicable.append((pkey, pred))
                stats = shadow[(action, pkey)]
                if qualified(stats):
                    qualified_predictions[base.digest(pred)] = pred
                    m.qualified_program_applications += 1
            if not qualified_predictions:
                m.no_qualified_program_abstentions += 1
            elif len(qualified_predictions) > 1:
                m.qualified_program_conflict_abstentions += 1
            else:
                candidate_prediction = next(iter(qualified_predictions.values()))
                candidate_from_program = True

        if candidate_prediction is not None:
            m.candidate_predictions += 1
            correct = candidate_prediction == after
            if correct:
                m.candidate_correct += 1
            else:
                m.candidate_wrong += 1
            if candidate_from_program:
                m.added_program_predictions += 1
                if correct:
                    m.added_program_correct += 1
                else:
                    m.added_program_wrong += 1

        # Reveal the current outcome only after the candidate decision is locked.
        for pkey, pred in shadow_applicable:
            stats = shadow[(action, pkey)]
            stats["tests"] += 1
            m.program_shadow_tests += 1
            if pred == after:
                stats["correct"] += 1
                m.program_shadow_correct += 1
            else:
                stats["wrong"] += 1
                m.program_shadow_wrong += 1

        exact_outcomes[exact_key].add(actual_digest)
        exact_exemplar[(exact_key, actual_digest)] = [row[:] for row in after]
        programs = infer_programs(before, after, action)
        if programs:
            m.pure_translation_transitions += 1
        for program in programs:
            pkey = base.stable(program)
            entry = program_bank[action].setdefault(pkey, {"program": program, "support": 0, "pre_states": set()})
            entry["support"] += 1
            entry["pre_states"].add(pre_digest)
            m.programs_inferred += 1
        pre = event

    m.exact_unique_keys_final = len(exact_outcomes)
    m.stable_programs_final = sum(
        1 for by_program in program_bank.values() for entry in by_program.values()
        if entry["support"] >= MIN_PROGRAM_SUPPORT and len(entry["pre_states"]) >= MIN_PROGRAM_SUPPORT
    )
    m.reliability_qualified_programs_final = sum(1 for stats in shadow.values() if qualified(stats))
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
    traces: list[dict[str, Any]] = []
    for path in paths:
        events = base.load_events(path)
        metrics = audit_trace(events)
        per_trace.append(metrics)
        traces.append({"path": str(path), "board_events": len(events), "metrics": metrics})
    agg = aggregate(per_trace)
    strict_gain = (
        agg["added_program_predictions"] > 0
        and agg["added_program_correct"] > 0
        and agg["added_program_wrong"] == 0
        and agg["candidate_correct"] > agg["baseline_correct"]
        and agg["candidate_wrong"] <= agg["baseline_wrong"]
    )
    return {
        "schema": "deus/arc3-public-object-role-transition-prequential/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREFIX_ONLY_OBJECT_ROLE_TRANSITION_AUDIT",
        "representation_change_from_rung137": {
            "changed": True,
            "change": "replace local pixel-patch matching with 4-connected object segmentation, state-relative role selection, and executable translation programs",
            "minimum_program_support": MIN_PROGRAM_SUPPORT,
            "minimum_prior_shadow_tests": MIN_PRIOR_SHADOW_TESTS,
            "allowed_prior_shadow_wrong": 0,
            "literal_color_in_role_key": False,
            "literal_location_in_role_key": False,
            "ambiguous_role_selection": "ABSTAIN",
            "collision_or_out_of_bounds": "ABSTAIN",
            "non_translation_effect": "REJECT",
        },
        "source_grounding": {
            "public_trace_repo": base.TUFA_REPO,
            "public_trace_commit": base.TUFA_COMMIT,
            "architectural_reference_repo": base.TWIN_REPO,
            "architectural_reference_commit": base.TWIN_COMMIT,
            "clean_room_implementation": True,
            "upstream_twin_code_imported": False,
            "upstream_twin_code_copied": False,
        },
        "causality_contract": {
            "prediction_uses_current_outcome": False,
            "prediction_uses_future_transitions": False,
            "program_learned_only_after_observed_outcome": True,
            "candidate_qualification_uses_only_prior_shadow_outcomes": True,
            "current_outcome_added_to_shadow_only_after_current_decision": True,
            "exact_baseline_consulted_first": True,
            "maps_reset_between_trace_files": True,
        },
        "traces": traces,
        "aggregate": agg,
        "next_gate_signal": "STRICT_PREQUENTIAL_OBJECT_ROLE_TRANSITION_GAIN" if strict_gain else "NO_STRICT_PREQUENTIAL_OBJECT_ROLE_TRANSITION_GAIN",
        "promotion": {
            "strict_prequential_object_role_transition_gain": strict_gain,
            "candidate_model_promotion": False,
            "kaggle_packaging": False,
        },
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "prefix_unseen_exact_state_prediction_measured": True,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "model_execution": False,
            "gpu_execution": False,
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
    events: list[dict[str, Any]] = []
    # Palette and absolute locations vary. The moving one-cell object is always
    # the unique smallest component; a 2x2 obstacle stays fixed.
    for i, col in enumerate((1, 2, 3, 4, 5, 6)):
        h, w = 8, 14
        before = [[0] * w for _ in range(h)]
        after = [[0] * w for _ in range(h)]
        mobile_color = 1 + i
        obstacle_color = 8 + i
        r = 1 + (i % 5)
        before[r][col] = mobile_color
        after[r][col + 1] = mobile_color
        for rr, cc in ((5, 10), (5, 11), (6, 10), (6, 11)):
            before[rr][cc] = obstacle_color
            after[rr][cc] = obstacle_color
        events.append({"type": "initial", "board": before, "level": 1})
        events.append({"type": "action", "board": after, "level": 1, "action_display": "RIGHT"})
    return events


def self_test() -> dict[str, Any]:
    m = audit_trace(synthetic_events())
    invariants = {
        "baseline_abstains_on_unique_states": m["baseline_predictions"] == 0,
        "object_role_programs_inferred": m["programs_inferred"] >= 2,
        "stable_role_program_exists": m["stable_programs_final"] >= 1,
        "shadow_validation_occurs": m["program_shadow_tests"] >= 3,
        "shadow_validation_is_clean": m["program_shadow_wrong"] == 0,
        "qualified_program_eventually_acts": m["added_program_predictions"] >= 1,
        "qualified_program_is_correct": m["added_program_correct"] >= 1,
        "qualified_program_adds_no_error": m["added_program_wrong"] == 0,
    }
    return {
        "schema": "deus/arc3-public-object-role-transition-prequential-selftest/1",
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
