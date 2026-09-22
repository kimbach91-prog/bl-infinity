#!/usr/bin/env python3
"""R177: temporal/path-state conditioning for the R175 patch renderer.

R176 closed confidence-only threshold tuning: no nonempty zero-error p11 gate
existed for the frozen R175 renderer. R177 therefore changes representation.
It keeps the same patch_recent1_s2 rendering family, but conditions the learned
patch label and the qualification history on PRIOR-ONLY temporal/path context:

- previous action;
- prior same-action run length;
- pre-action step phase.

Candidate temporal feature families are selected on p11 only, then frozen and
evaluated on p0+p10. Current outcomes are used only for scoring and
post-prediction learning. This remains public/source-assisted replay, not a
Kaggle score or independent ARC-AGI-3 generalization claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167
import public_world_overlay_renderer_172 as r172
import public_residual_family_sweep_175 as r175

RUNG = 177
SUPPORT = 2
MIN_PRIOR_FRAME_OK = 2
Grid = list[list[int]]

CANDIDATES = (
    "prev_action",
    "same_run",
    "phase2",
    "prev_action_same_run",
    "same_run_phase2",
    "prev_action_phase2",
    "prev_action_same_run_phase2",
    "prev_action_same_run_phase4",
)
COMPLEXITY = {name: i for i, name in enumerate(CANDIDATES, start=1)}


def run_bucket(n: int) -> int:
    if n <= 0:
        return 0
    if n == 1:
        return 1
    if n == 2:
        return 2
    return 3


def temporal_context(name: str, prev_action: str | None, prior_same_run: int, step_index: int) -> tuple[Any, ...]:
    prev = prev_action or "START"
    run = run_bucket(prior_same_run)
    p2 = step_index % 2
    p4 = step_index % 4
    if name == "prev_action":
        return (prev,)
    if name == "same_run":
        return (run,)
    if name == "phase2":
        return (p2,)
    if name == "prev_action_same_run":
        return (prev, run)
    if name == "same_run_phase2":
        return (run, p2)
    if name == "prev_action_phase2":
        return (prev, p2)
    if name == "prev_action_same_run_phase2":
        return (prev, run, p2)
    if name == "prev_action_same_run_phase4":
        return (prev, run, p4)
    raise ValueError(name)


def conditioned_patch_key(
    name: str,
    before: Grid,
    shift: tuple[int, int],
    action: str,
    r: int,
    c: int,
    sr: int,
    sc: int,
    comps: dict[tuple[int, int], tuple[int, int, int, int]],
    prev_action: str | None,
    prior_same_run: int,
    step_index: int,
) -> tuple[Any, ...]:
    base_key = r175.morph_feature("patch", action, before, r, c, sr, sc, comps)
    return base_key + ("TEMP", name) + temporal_context(name, prev_action, prior_same_run, step_index)


def render_temporal(
    before: Grid,
    shift: tuple[int, int],
    action: str,
    name: str,
    recent_masks: dict[str, list[set[tuple[int, int]]]],
    labels: dict[str, dict[tuple[Any, ...], Counter[str]]],
    comps: dict[tuple[int, int], tuple[int, int, int, int]],
    prev_action: str | None,
    prior_same_run: int,
    step_index: int,
) -> Grid:
    dr, dc = shift
    h, w = len(before), len(before[0])
    out = [row[:] for row in before]
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            fixed, world = before[r][c], before[sr][sc]
            if fixed == world:
                out[r][c] = fixed
                continue
            key = conditioned_patch_key(
                name, before, shift, action, r, c, sr, sc, comps,
                prev_action, prior_same_run, step_index,
            )
            lab = r175.unique(labels[name][key], SUPPORT)
            if lab is not None:
                use_fixed = lab == "fixed"
            else:
                use_fixed = r175.recent_decision("recent1", recent_masks[action], (r, c))
            out[r][c] = fixed if use_fixed else world
    return out


def learn_temporal(
    before: Grid,
    after: Grid,
    shift: tuple[int, int],
    action: str,
    labels: dict[str, dict[tuple[Any, ...], Counter[str]]],
    comps: dict[tuple[int, int], tuple[int, int, int, int]],
    prev_action: str | None,
    prior_same_run: int,
    step_index: int,
) -> None:
    dr, dc = shift
    h, w = len(before), len(before[0])
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            fixed, world, actual = before[r][c], before[sr][sc], after[r][c]
            if fixed == world:
                continue
            if actual == fixed and actual != world:
                lab = "fixed"
            elif actual == world and actual != fixed:
                lab = "world"
            else:
                continue
            for name in CANDIDATES:
                key = conditioned_patch_key(
                    name, before, shift, action, r, c, sr, sc, comps,
                    prev_action, prior_same_run, step_index,
                )
                labels[name][key][lab] += 1


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact = defaultdict(Counter)
    shifts = defaultdict(Counter)
    recent_masks: dict[str, list[set[tuple[int, int]]]] = defaultdict(list)
    labels: dict[str, dict[tuple[Any, ...], Counter[str]]] = {
        name: defaultdict(Counter) for name in CANDIDATES
    }
    shadow = defaultdict(Counter)
    stats = defaultdict(Counter)

    pre = events[0]
    prev_action: str | None = None
    prev_run_len = 0
    step_index = 0

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            continue

        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        if len(before) != len(after) or len(before[0]) != len(after[0]):
            continue

        prior_same_run = prev_run_len if prev_action == action else 0
        ek = r160.context_exact(before, action)
        prog = r175.exact_prog(exact[ek], 1) if ek in exact else None
        pred_exact = r160.apply_program(before, prog) if prog is not None else None
        sh = r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None

        if pred_exact is None and sh is not None:
            comps = r175.component_descriptors(before)
            for name in CANDIDATES:
                ctx = temporal_context(name, prev_action, prior_same_run, step_index)
                pred = render_temporal(
                    before, sh, action, name, recent_masks, labels, comps,
                    prev_action, prior_same_run, step_index,
                )
                err = r175.score_frame(pred, after)
                s = stats[name]
                s["raw"] += 1
                s["cell_errors"] += err
                if err == 0:
                    s["raw_correct"] += 1
                else:
                    s["raw_wrong"] += 1
                if err <= 4:
                    s["near4"] += 1
                if err <= 16:
                    s["near16"] += 1

                qkey = (name, action, ctx)
                prior_ok = shadow[qkey]["ok"]
                prior_wrong = shadow[qkey]["wrong"]
                qualified = prior_ok >= MIN_PRIOR_FRAME_OK and prior_wrong == 0
                if qualified:
                    s["qualified"] += 1
                    if err == 0:
                        s["qualified_correct"] += 1
                    else:
                        s["qualified_wrong"] += 1
                shadow[qkey]["ok" if err == 0 else "wrong"] += 1

        # Current outcome enters memory only after prediction/scoring.
        exact[ek][r160.program(before, after)] += 1
        if action in r172.CAMERA_ACTIONS:
            changed = sum(
                before[r][c] != after[r][c]
                for r in range(len(before))
                for c in range(len(before[0]))
            )
            if changed:
                b = r167.best_nonzero_shift(before, after)
                if float(b["valid_match_fraction"]) >= r172.MIN_TRANSITION_FIT:
                    obs = (int(b["dr"]), int(b["dc"]))
                    shifts[action][obs] += 1
                    comps = r175.component_descriptors(before)
                    learn_temporal(
                        before, after, obs, action, labels, comps,
                        prev_action, prior_same_run, step_index,
                    )
                    recent_masks[action].append(r175.fixed_mask_from_transition(before, after, obs))
                    if len(recent_masks[action]) > 3:
                        recent_masks[action] = recent_masks[action][-3:]

        prev_run_len = prior_same_run + 1 if prev_action == action else 1
        prev_action = action
        step_index += 1

    out: dict[str, Any] = {}
    for name in CANDIDATES:
        c = stats[name]
        d = {
            k: int(c[k])
            for k in (
                "raw", "raw_correct", "raw_wrong", "near4", "near16", "cell_errors",
                "qualified", "qualified_correct", "qualified_wrong",
            )
        }
        d["raw_accuracy"] = round(d["raw_correct"] / d["raw"], 6) if d["raw"] else None
        d["qualified_accuracy"] = (
            round(d["qualified_correct"] / d["qualified"], 6) if d["qualified"] else None
        )
        d["mean_cell_errors"] = round(d["cell_errors"] / d["raw"], 3) if d["raw"] else None
        out[name] = d
    return out


def choose_on_calibration(cal: dict[str, Any]) -> str | None:
    eligible = []
    for name in CANDIDATES:
        s = cal[name]
        if s["qualified"] > 0 and s["qualified_wrong"] == 0:
            eligible.append(name)
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda n: (
            -cal[n]["qualified_correct"],
            -cal[n]["raw_correct"],
            cal[n]["cell_errors"],
            COMPLEXITY[n],
            n,
        ),
    )[0]


def run(calibration_path: Path, eval_paths: list[Path]) -> dict[str, Any]:
    calibration = audit_trace(base.load_events(calibration_path))
    chosen = choose_on_calibration(calibration)

    evaluation = []
    if chosen:
        for path in eval_paths:
            all_stats = audit_trace(base.load_events(path))
            evaluation.append({
                "path": path.name,
                "chosen_candidate": chosen,
                "score": all_stats[chosen],
            })

    strict = bool(
        chosen
        and len(evaluation) >= 2
        and all(
            x["score"]["qualified_correct"] > 0
            and x["score"]["qualified_wrong"] == 0
            for x in evaluation[:2]
        )
    )

    return {
        "schema": "deus/arc3-public-temporal-path-state/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_P11_TEMPORAL_SELECTION_P0P10_FROZEN_EVAL",
        "representation_change_from_rung176": {
            "changed": True,
            "change": (
                "replace confidence-only tuning with prior-only temporal/path conditioning "
                "of patch labels and qualification history"
            ),
        },
        "candidate_families": list(CANDIDATES),
        "parameters": {
            "patch_support": SUPPORT,
            "min_prior_frame_ok": MIN_PRIOR_FRAME_OK,
            "run_bucket": "0,1,2,3plus",
            "phase_features": ["step_mod_2", "step_mod_4"],
        },
        "calibration": {
            "trace": calibration_path.name,
            "candidates": calibration,
            "chosen_candidate": chosen,
        },
        "evaluation": evaluation,
        "diagnostic_gate": (
            "TEMPORAL_PATH_ZERO_ERROR_NONZERO_P0_P10_GAIN"
            if strict
            else "NO_STRICT_TEMPORAL_PATH_STATE_GAIN"
        ),
        "promotion": {
            "candidate_model_promotion": strict,
            "kaggle_packaging": False,
        },
        "truth": {
            "public_trace_only": True,
            "source_assisted_sequence_replay": True,
            "candidate_selected_on_p11_only": True,
            "p0_p10_not_used_for_candidate_selection": True,
            "current_prediction_uses_preaction_and_prior_history_only": True,
            "current_outcome_used_only_for_scoring_and_post_prediction_learning": True,
            "independent_generalization_claim": False,
            "gpu_execution": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--eval", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    d = run(args.calibration, args.eval)
    text = json.dumps(d, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
