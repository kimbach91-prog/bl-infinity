#!/usr/bin/env python3
"""Rung 155: relational object/state-anchor executable residual placement programs.

Rung 154 showed that coarse residual-to-residual temporal transforms can remain
zero-error on a few p11 events but do not recur on p0/p10. This rung changes the
representation rather than retrying temporal keys: it binds the already-retained
rung149 semantic primitive to *current pre-action relational anchors*.

For every observed residual, after the prediction for that event has been locked,
we encode the exact residual edit set relative to anchors available from the
pre-action board: unique object roles, movable-object-set bounds, foreground bounds,
and board bounds. At prediction time only prior programs are used. A program must
have >=2 identical prior supports with no alternative program under the same key;
all applicable qualified anchors must agree on one exact edit set before emitting a
placement prediction. Any ambiguity, invalid old-cell check, or disagreement causes
abstention.

This is public/source-assisted prequential diagnostic evidence only. The current
outcome is still used after prediction to isolate and score the residual. It is not
independent generalization, a full-frame solver result, model/GPU/Kaggle execution,
a submission, or a leaderboard result.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138
import public_residual_action_mobility_selector_audit_149 as sel149
import public_residual_history_state_machine_audit_153 as r153
import public_residual_placement_reconstruction_audit_150 as r150

RUNG = 155
MIN_SUPPORT = 2
MIN_AGREEING_ANCHORS = 2
Grid = list[list[int]]
Edit = tuple[int, int, int, int]


def anchor_points(board: Grid, action: str) -> dict[str, tuple[int, int]]:
    """Return deterministic integer anchors computable before the action outcome."""
    h, w = len(board), len(board[0])
    out: dict[str, tuple[int, int]] = {
        "board_tl": (0, 0),
        "board_tr": (0, w - 1),
        "board_bl": (h - 1, 0),
        "board_br": (h - 1, w - 1),
    }

    obs = obj138.objects(board)
    roles = obj138.role_indices(board)
    for role, idx in roles.items():
        if not (0 <= idx < len(obs)):
            continue
        o = obs[idx]
        out[f"role:{role}:tl"] = (o.r0, o.c0)
        out[f"role:{role}:tr"] = (o.r0, o.c1)
        out[f"role:{role}:bl"] = (o.r1, o.c0)
        out[f"role:{role}:br"] = (o.r1, o.c1)

    bg = obj138.background_color(board)
    fg = [(r, c) for r, row in enumerate(board) for c, v in enumerate(row) if v != bg]
    if fg:
        r0 = min(r for r, _ in fg); r1 = max(r for r, _ in fg)
        c0 = min(c for _, c in fg); c1 = max(c for _, c in fg)
        out.update({"foreground:tl": (r0, c0), "foreground:tr": (r0, c1),
                    "foreground:bl": (r1, c0), "foreground:br": (r1, c1)})

    delta = sel149.ACTION_DELTA.get(action.upper())
    if delta is not None:
        dr, dc = delta
        movable = [o for o in obs if sel149.can_shift(board, o, dr, dc)]
        blocked = [o for o in obs if not sel149.can_shift(board, o, dr, dc)]
        for label, group in (("movable", movable), ("blocked", blocked)):
            pts = [p for o in group for p in o.cells]
            if not pts:
                continue
            r0 = min(r for r, _ in pts); r1 = max(r for r, _ in pts)
            c0 = min(c for _, c in pts); c1 = max(c for _, c in pts)
            out.update({f"{label}:tl": (r0, c0), f"{label}:tr": (r0, c1),
                        f"{label}:bl": (r1, c0), f"{label}:br": (r1, c1)})
    return out


def encode_program(edits: list[Edit], anchor: tuple[int, int]) -> str:
    ar, ac = anchor
    return base.stable(sorted((r - ar, c - ac, old, new) for r, c, old, new in edits))


def apply_program(board: Grid, anchor: tuple[int, int], program: str) -> list[Edit] | None:
    raw = json.loads(program)
    ar, ac = anchor
    h, w = len(board), len(board[0])
    out: list[Edit] = []
    for dr, dc, old, new in raw:
        r, c = ar + int(dr), ac + int(dc)
        old, new = int(old), int(new)
        if not (0 <= r < h and 0 <= c < w):
            return None
        if board[r][c] != old:
            return None
        out.append((r, c, old, new))
    if not out:
        return None
    return sorted(out)


def reliable(counter: Counter[str]) -> str | None:
    if len(counter) != 1:
        return None
    value, n = next(iter(counter.items()))
    return value if n >= MIN_SUPPORT else None


def semantic_key(before: Grid, action: str, prev2_sem: str | None, prev1_sem: str | None) -> str | None:
    return r153.semantic_context(before, action, prev2_sem, prev1_sem)


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    semantic_bank: dict[str, Counter[str]] = defaultdict(Counter)
    # Two scopes are deliberately compared. action_sem is conservative; sem_only
    # tests whether action-canonical spatial anchors can share programs across
    # directions without importing the full r149 context into the placement key.
    banks: dict[str, dict[str, Counter[str]]] = {
        "action_sem": defaultdict(Counter),
        "sem_only": defaultdict(Counter),
    }
    stats = {scope: {
        "semantic_predictions": 0, "semantic_correct": 0, "semantic_wrong": 0,
        "placement_predictions": 0, "placement_correct": 0, "placement_wrong": 0,
        "no_qualified_anchor_abstentions": 0,
        "anchor_disagreement_abstentions": 0,
        "insufficient_consensus_abstentions": 0,
        "invalid_program_applications": 0,
        "qualified_anchor_applications": 0,
    } for scope in banks}
    eligible = 0
    prev2_sem = prev1_sem = None
    pre = events[0]

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        detail = r150.residual_edits(before, after, action)
        if detail is None:
            continue
        edits, target_sem = detail
        eligible += 1
        anchors = anchor_points(before, action)
        ctx = semantic_key(before, action, prev2_sem, prev1_sem)
        sem_pred = r153.unique(semantic_bank[ctx]) if ctx is not None and ctx in semantic_bank else None

        if sem_pred is not None:
            for scope in banks:
                s = stats[scope]
                s["semantic_predictions"] += 1
                if sem_pred == target_sem:
                    s["semantic_correct"] += 1
                else:
                    s["semantic_wrong"] += 1

                proposals: dict[str, tuple[list[Edit], int]] = {}
                for aname, anchor in anchors.items():
                    if scope == "action_sem":
                        key = base.stable({"a": action, "sem": sem_pred, "anchor": aname})
                    else:
                        key = base.stable({"sem": sem_pred, "anchor": aname})
                    counter = banks[scope].get(key)
                    if not counter:
                        continue
                    program = reliable(counter)
                    if program is None:
                        continue
                    pred = apply_program(before, anchor, program)
                    if pred is None:
                        s["invalid_program_applications"] += 1
                        continue
                    s["qualified_anchor_applications"] += 1
                    d = base.digest(pred)
                    if d in proposals:
                        old_pred, n = proposals[d]
                        proposals[d] = (old_pred, n + 1)
                    else:
                        proposals[d] = (pred, 1)

                if not proposals:
                    s["no_qualified_anchor_abstentions"] += 1
                elif len(proposals) != 1:
                    s["anchor_disagreement_abstentions"] += 1
                else:
                    pred, agree = next(iter(proposals.values()))
                    if agree < MIN_AGREEING_ANCHORS:
                        s["insufficient_consensus_abstentions"] += 1
                    else:
                        s["placement_predictions"] += 1
                        if pred == sorted(edits):
                            s["placement_correct"] += 1
                        else:
                            s["placement_wrong"] += 1

        # Ingest the current semantic/programs only after the prediction is locked.
        if ctx is not None:
            semantic_bank[ctx][target_sem] += 1
        for aname, anchor in anchors.items():
            program = encode_program(edits, anchor)
            key_a = base.stable({"a": action, "sem": target_sem, "anchor": aname})
            key_s = base.stable({"sem": target_sem, "anchor": aname})
            banks["action_sem"][key_a][program] += 1
            banks["sem_only"][key_s][program] += 1
        prev2_sem, prev1_sem = prev1_sem, target_sem

    for scope, s in stats.items():
        s["semantic_accuracy"] = round(s["semantic_correct"] / s["semantic_predictions"], 6) if s["semantic_predictions"] else None
        s["placement_accuracy"] = round(s["placement_correct"] / s["placement_predictions"], 6) if s["placement_predictions"] else None
        s["placement_coverage_of_eligible"] = round(s["placement_predictions"] / eligible, 6) if eligible else 0.0
        s["strict_zero_error_placement"] = bool(s["placement_predictions"] and s["placement_wrong"] == 0 and s["semantic_wrong"] == 0)
        s["program_keys_final"] = len(banks[scope])
        s["conflicted_program_keys_final"] = sum(len(c) > 1 for c in banks[scope].values())
    return {"eligible_transitions": eligible, "scopes": stats}


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    scopes = tuple(parts[0]["scopes"]) if parts else ()
    eligible = sum(p["eligible_transitions"] for p in parts)
    out: dict[str, Any] = {}
    hard: list[tuple[int, str]] = []
    sum_keys = (
        "semantic_predictions", "semantic_correct", "semantic_wrong",
        "placement_predictions", "placement_correct", "placement_wrong",
        "no_qualified_anchor_abstentions", "anchor_disagreement_abstentions",
        "insufficient_consensus_abstentions", "invalid_program_applications",
        "qualified_anchor_applications",
    )
    for scope in scopes:
        s = {k: sum(p["scopes"][scope][k] for p in parts) for k in sum_keys}
        pp = [p["scopes"][scope]["placement_predictions"] for p in parts]
        pc = [p["scopes"][scope]["placement_correct"] for p in parts]
        pw = [p["scopes"][scope]["placement_wrong"] for p in parts]
        sw = [p["scopes"][scope]["semantic_wrong"] for p in parts]
        s.update({
            "semantic_accuracy": round(s["semantic_correct"] / s["semantic_predictions"], 6) if s["semantic_predictions"] else None,
            "placement_accuracy": round(s["placement_correct"] / s["placement_predictions"], 6) if s["placement_predictions"] else None,
            "placement_coverage_of_eligible": round(s["placement_predictions"] / eligible, 6) if eligible else 0.0,
            "strict_zero_error_placement": bool(s["placement_predictions"] and s["placement_wrong"] == 0 and s["semantic_wrong"] == 0),
            "per_trace_placement_predictions": pp,
            "per_trace_placement_correct": pc,
            "per_trace_placement_wrong": pw,
            "per_trace_semantic_wrong": sw,
        })
        out[scope] = s
        if len(pp) >= 2 and pp[0] > 0 and pp[1] > 0 and pw[0] == 0 and pw[1] == 0 and sw[0] == 0 and sw[1] == 0:
            hard.append((pp[0] + pp[1], scope))
    return {
        "trace_count": len(parts),
        "eligible_transitions": eligible,
        "scopes": out,
        "best_zero_error_p0_p10_relational_anchor_scope": max(hard)[1] if hard else None,
        "per_trace": parts,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = []
    traces = []
    for p in paths:
        a = audit_trace(base.load_events(p))
        parts.append(a)
        traces.append({"path": str(p), "audit": a})
    return {
        "schema": "deus/arc3-public-residual-relational-anchor-program-audit/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_RELATIONAL_ANCHOR_RESIDUAL_PROGRAM_DIAGNOSTIC",
        "representation_change_from_rung154": {
            "changed": True,
            "change": "replace residual-to-residual temporal placement transforms with executable exact-edit programs anchored to current pre-action object roles and state-relative bounds; require prior support plus multi-anchor agreement",
        },
        "parameters": {"min_support": MIN_SUPPORT, "min_agreeing_anchors": MIN_AGREEING_ANCHORS},
        "source_grounding": {
            "public_trace_repo": base.TUFA_REPO,
            "public_trace_commit": base.TUFA_COMMIT,
            "clean_room_implementation": True,
            "reused_internal_primitives": ["r138 object roles", "r149 mobility semantics", "r150 residual isolation", "r153 prefix-only semantic bank"],
        },
        "traces": traces,
        "aggregate": aggregate(parts),
        "diagnostic_gate": "RELATIONAL_ANCHOR_RESIDUAL_PROGRAM_CHARACTERIZED",
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "diagnostic_only": True,
            "anchors_and_semantic_context_available_pre_outcome": True,
            "current_targets_ingested_after_prediction": True,
            "current_outcome_used_for_residual_isolation_and_scoring": True,
            "hard_trace_gate_requires_p0_and_p10_nonzero_zero_error_coverage": True,
            "full_frame_prediction_claim": False,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "model_execution": False,
            "gpu_execution": False,
            "kaggle_execution": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
            "owner_score_claim": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if not args.input:
        raise SystemExit("at least one --input is required")
    d = run(args.input)
    text = json.dumps(d, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
