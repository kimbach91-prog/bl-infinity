#!/usr/bin/env python3
"""R301: causal temporal residual-motion diagnostic for lp85.

Purpose: test one materially different mechanism for the errors left after the
R300 structural residual primitive.  The test is deliberately train-only and
public: exact lp85 p0-p4 only; p5-p19 must not be staged/read.

Mechanism under test:
- build the frozen R300 structural base from p0-p4;
- observe only *past* residual connected components after each transition;
- when the same residual template has repeated with a stable period and
  translation, extrapolate its next occurrence;
- require every predicted target cell's current base value to match the
  historical pre-value before applying the historical delta.

This is a causal/history representation test, not a solver promotion and not
an independent heldout/Kaggle claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_hierarchical_sparse_delta_gate_298 as r298
import public_lp85_seeded_structural_residual_gate_300 as r300

TARGET_GAME = "lp85-305b61c3"
RUNG = 301
MODES = ("H2_PERIOD_VELOCITY", "H3_STABLE_PERIOD_VELOCITY")


def world(board, action):
    return r275.canon_board(board, action, use_ui_mask=True)


def r300_predict(row: dict[str, Any], templates):
    b = world(row["before"], row["action"])
    a = world(row["after"], row["action"])
    h = len(b); w = len(b[0]) if h else 0
    proposals = defaultdict(set)
    for r in range(h):
        for c in range(w):
            key = (r298.patch(b, r, c, 1), r298.patch(b, r, c, 2))
            rel = templates.get(key)
            if rel is None:
                continue
            ok = True
            for dr, dc, before, after in rel:
                rr, cc = r + dr, c + dc
                if not (0 <= rr < h and 0 <= cc < w and int(b[rr][cc]) == before):
                    ok = False
                    break
            if not ok:
                continue
            for dr, dc, before, after in rel:
                proposals[(r + dr, c + dc)].add(int(after))
    pred = [list(map(int, x)) for x in b]
    for (r, c), vals in proposals.items():
        if len(vals) == 1:
            pred[r][c] = next(iter(vals))
    return b, a, pred


def connected_components(mask):
    h = len(mask); w = len(mask[0]) if h else 0
    seen = set(); out = []
    for r in range(h):
        for c in range(w):
            if not mask[r][c] or (r, c) in seen:
                continue
            stack = [(r, c)]; seen.add((r, c)); comp = []
            while stack:
                x, y = stack.pop(); comp.append((x, y))
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < h and 0 <= yy < w and mask[xx][yy] and (xx, yy) not in seen:
                        seen.add((xx, yy)); stack.append((xx, yy))
            out.append(sorted(comp))
    return out


def residual_components(base_pred, actual):
    h = len(base_pred); w = len(base_pred[0]) if h else 0
    mask = [[int(base_pred[r][c]) != int(actual[r][c]) for c in range(w)] for r in range(h)]
    out = []
    for comp in connected_components(mask):
        r0 = min(r for r, _ in comp); c0 = min(c for _, c in comp)
        rel = tuple(sorted((r-r0, c-c0, int(base_pred[r][c]), int(actual[r][c])) for r, c in comp))
        out.append({"anchor": (r0, c0), "rel": rel, "size": len(comp)})
    return out


def due_prediction(history, current_index: int, mode: str):
    if mode == "H2_PERIOD_VELOCITY":
        if len(history) < 2:
            return None
        i0, a0 = history[-2]
        i1, a1 = history[-1]
        gap = i1 - i0
        if gap <= 0 or current_index - i1 != gap:
            return None
        vel = (a1[0] - a0[0], a1[1] - a0[1])
        return (a1[0] + vel[0], a1[1] + vel[1])
    if mode == "H3_STABLE_PERIOD_VELOCITY":
        if len(history) < 3:
            return None
        i0, a0 = history[-3]
        i1, a1 = history[-2]
        i2, a2 = history[-1]
        g1, g2 = i1-i0, i2-i1
        v1 = (a1[0]-a0[0], a1[1]-a0[1])
        v2 = (a2[0]-a1[0], a2[1]-a1[1])
        if g1 <= 0 or g1 != g2 or v1 != v2 or current_index - i2 != g2:
            return None
        return (a2[0] + v2[0], a2[1] + v2[1])
    raise KeyError(mode)


def run_mode(traces, templates, mode: str):
    m = Counter(); per_trace = {}
    for ti, trace in enumerate(traces):
        histories = defaultdict(list)
        tm = Counter()
        for idx, row in enumerate(trace):
            b, actual, base = r300_predict(row, templates)
            h = len(base); w = len(base[0]) if h else 0
            proposals = defaultdict(set)
            fires = 0
            # Predict from past-only unique residual histories.
            for sig, hist in histories.items():
                anchor = due_prediction(hist, idx, mode)
                if anchor is None:
                    continue
                r0, c0 = anchor
                ok = True
                for dr, dc, before, after in sig:
                    rr, cc = r0 + dr, c0 + dc
                    if not (0 <= rr < h and 0 <= cc < w and int(base[rr][cc]) == int(before)):
                        ok = False; break
                if not ok:
                    continue
                fires += 1
                for dr, dc, before, after in sig:
                    proposals[(r0+dr, c0+dc)].add(int(after))

            cand = [x[:] for x in base]
            for (r, c), vals in proposals.items():
                if len(vals) == 1:
                    cand[r][c] = next(iter(vals))
                else:
                    tm["conflicting_cells"] += 1

            base_err = cand_err = 0
            for r in range(h):
                for c in range(w):
                    bv, cv, av = int(base[r][c]), int(cand[r][c]), int(actual[r][c])
                    base_err += bv != av; cand_err += cv != av
                    if cv != bv:
                        tm["predicted_changes"] += 1
                        if cv == av and bv != av:
                            tm["true_changed_correct"] += 1
                        elif cv != av:
                            tm["false_changes"] += 1
            tm["frames"] += 1
            tm["base_errors"] += base_err
            tm["candidate_errors"] += cand_err
            tm["base_exact_frames"] += base_err == 0
            tm["candidate_exact_frames"] += cand_err == 0
            tm["temporal_firings"] += fires

            # Outcome is now observed; update causal histories for the *next* transition.
            comps = residual_components(base, actual)
            grouped = defaultdict(list)
            for comp in comps:
                grouped[comp["rel"]].append(comp)
            for sig, same in grouped.items():
                if len(same) == 1:  # ambiguity guard
                    histories[sig].append((idx, same[0]["anchor"]))
                else:
                    tm["ambiguous_same_signature_rows"] += 1

        per_trace[str(ti)] = dict(tm)
        m.update(tm)
    m["error_reduction_vs_r300_base"] = m["base_errors"] - m["candidate_errors"]
    m["exact_frame_delta_vs_r300_base"] = m["candidate_exact_frames"] - m["base_exact_frames"]
    return dict(m), per_trace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    if set(by) != {TARGET_GAME}:
        raise SystemExit(f"exact target required, got {sorted(by)}")
    ps = sorted(by[TARGET_GAME], key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(5)):
        raise SystemExit(f"exact p0-p4 required, got {nums}")

    traces = [r278.annotated_rows([p]) for p in ps]
    train = [r for tr in traces for r in tr]
    templates, fit = r300.fit_templates(train, traces)

    modes = {}
    for mode in MODES:
        total, per = run_mode(traces, templates, mode)
        modes[mode] = {"total": total, "per_trace": per}

    safe = []
    for mode in MODES:
        t = modes[mode]["total"]
        if int(t.get("predicted_changes", 0)) > 0 and int(t.get("false_changes", 0)) == 0 and int(t.get("error_reduction_vs_r300_base", 0)) > 0:
            safe.append(mode)
    best = max(safe, key=lambda x: (modes[x]["total"]["error_reduction_vs_r300_base"], modes[x]["total"].get("predicted_changes",0))) if safe else None
    if best:
        verdict = "TEMPORAL_RESIDUAL_ZERO_FALSE_SIGNAL"
    elif any(int(modes[x]["total"].get("error_reduction_vs_r300_base",0)) > 0 for x in MODES):
        verdict = "TEMPORAL_RESIDUAL_GAIN_UNSAFE"
    else:
        verdict = "TEMPORAL_RESIDUAL_NO_SIGNAL"

    out = {
        "schema": "deus/arc3-r301-lp85-temporal-residual-motion-diagnostic/1",
        "rung": RUNG,
        "game": TARGET_GAME,
        "lineage": {"r300": "structural residual base; public/source-assisted primitive only"},
        "mechanism": {
            "representation": "past-only residual connected-component recurrence",
            "timing": "repeat period from prior residual occurrences",
            "motion": "constant anchor translation from prior occurrences",
            "guard": "exact current base pre-values + unique residual signature per observed row",
        },
        "protocol": {
            "diagnostic": "p0-p4 only",
            "p5_p19_staged_or_read": False,
            "same_source_diagnostic_only": True,
            "past_only_online_history": True,
            "promotion_in_r301": False,
        },
        "r300_fit_gate": fit,
        "modes": modes,
        "safe_modes": safe,
        "best_safe_mode": best,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "p5_p19_read": False,
            "independent_hidden_generalization_claim": False,
            "solver_promotion": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "owner_score_claim": False,
            "submission_quota_spent_by_r301": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "best_safe_mode": best, "safe_modes": safe, "modes": {k:v["total"] for k,v in modes.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
