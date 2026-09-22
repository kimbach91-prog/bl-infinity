#!/usr/bin/env python3
"""R232: select an R227 confidence-abstention gate with p0..p9 LOTO only.

R231 found a useful but outcome-assisted signal on the already-reused p10..p19
public-development traces. R232 removes that leakage from gate selection:

* outer leave-one-trace-out (LOTO) folds use only p0..p9;
* each fold fits the frozen R227 current_ring2hist family and all confidence
  statistics on the other nine traces;
* candidate confidence gates are scored only on the held-out fold trace;
* a gate is eligible only if its aggregate LOTO predictions have zero wrong;
* the selected gate is then frozen, refit on p0..p9 and merely audited on the
  already-reused p10..p19 public-development traces.

R221's build_models() internally assumes exactly ten traces because it selects
its own threshold by ten-fold CV. That is incompatible with an outer nine-trace
LOTO fold. For fold construction only, R232 rebuilds the same model fields
without that inner selector and keeps R225's already-frozen low-base threshold
at support>=2. This repairs the harness assumption; it does not change the
R227 representation or use the held-out fold outcome to build the model.

The p10..p19 audit is NOT independent heldout generalization and cannot itself
promote a Kaggle candidate. A later genuinely untouched public/source-generated
partition is still required before this confidence family may become a
source-assisted coverage expert.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_low_confidence_goal_manifold_veto_225 as r225
import public_ft09_coarse_local_target_gate_227 as r227

RUNG = 232
GAME = "ft09-0d8bbf25"
FAM = "current_ring2hist"
TRACE_SUPPORTS = (2, 3, 4, 5, 6)
MIN_OCCURRENCES = (2, 3, 4, 6, 8, 12)
REQUIRE_LEVEL = (False, True)
MIN_POSITION_SUPPORT = (0, 1, 2)


def pnum(p: Path) -> int:
    m = re.search(r"_p(\d+)_events\.jsonl$", p.name)
    return int(m.group(1)) if m else -1


def gp(board):
    return [row[:] for row in board[:-1]]


def build_models_fold(train_paths):
    """R221 model fields for arbitrary trace count; R225 support=2 stays frozen."""
    rm = r221.r212ff.ring2_model(train_paths)
    im = r221.r212ff.identity_model(train_paths)
    scene, _ = r221.r216.fit_scene(train_paths, 2)
    exact_goal, _, _, _ = r217.fit_goal(train_paths, rm, 2)
    fam, struct_goal, fstats = r221.r218.choose_family(train_paths, rm)
    rows = [r for p in train_paths for r in r221.r211.rows(p)]
    base = r221.cv212.fit(rows, "base")
    policy = {
        "config": "s2-fixed-r225",
        "min_support": 2,
        "source": "R225 frozen incumbent threshold; no inner threshold reselection",
    }
    return {
        "rm": rm,
        "im": im,
        "scene": scene,
        "exact_goal": exact_goal,
        "fam": fam,
        "struct_goal": struct_goal,
        "fstats": fstats,
        "base": base,
        "policy": policy,
    }


def train_stats(paths):
    d = defaultdict(
        lambda: {
            "targets": Counter(),
            "traces": set(),
            "levels": set(),
            "positions": defaultdict(set),
            "n": 0,
        }
    )
    for p in paths:
        meta = r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r["eligible"]:
                continue
            lm = meta.get(r["step0"])
            k = repr(r227.feat(FAM, r, lm))
            z = d[k]
            z["targets"][r["target"]] += 1
            z["traces"].add(r["path"])
            z["n"] += 1
            if lm:
                z["levels"].add(int(lm["level_before"]))
            r0, c0, _, _, _ = r["bbox"]
            z["positions"][(r0 // 8, c0 // 8)].add(r["path"])
    return d


def confidence(z, lm, pos):
    return {
        "train_occurrences": z["n"],
        "trace_support": len(z["traces"]),
        "level_seen": bool(lm and int(lm["level_before"]) in z["levels"]),
        "position_trace_support": len(z["positions"].get(pos, set())),
    }


def gate_key(ts, occ, req_lvl, pos_sup):
    return f"ts{ts}|occ{occ}|lvl{int(req_lvl)}|pos{pos_sup}"


def gate_cfg(ts, occ, req_lvl, pos_sup):
    return {
        "trace_support": ts,
        "min_occurrences": occ,
        "require_level_seen": req_lvl,
        "min_position_trace_support": pos_sup,
    }


def gate_accept(cfg, conf):
    return (
        conf["trace_support"] >= cfg["trace_support"]
        and conf["train_occurrences"] >= cfg["min_occurrences"]
        and (not cfg["require_level_seen"] or conf["level_seen"])
        and conf["position_trace_support"] >= cfg["min_position_trace_support"]
    )


def candidate_rows(eval_paths, train_paths):
    """Return frozen-R227 residual candidates using train-derived state only."""
    tab, rejected = r227.fit(train_paths, FAM, 2)
    stats = train_stats(train_paths)
    m = build_models_fold(train_paths)
    rows = []
    incumbent_predictions = 0
    eligible = 0
    for p in eval_paths:
        meta = r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r["eligible"]:
                continue
            eligible += 1
            lm = meta.get(r["step0"])
            pred, _ = r221.r218_predict(r, lm, m)
            if pred is None:
                pred, _ = r221.r219_predict(r, lm, m)
            if pred is None:
                pred, _, _ = r225.lowbase_goal_veto(r, lm, m)
            if pred is not None:
                incumbent_predictions += 1
                continue
            k = repr(r227.feat(FAM, r, lm))
            tgt = tab.get(k)
            if tgt is None or r227.goal_veto(r, lm, tgt, m) is not None:
                continue
            r0, c0, _, _, _ = r["bbox"]
            pos = (r0 // 8, c0 // 8)
            z = stats[k]
            conf = confidence(z, lm, pos)
            pred_board = gp(r212.recolor_bbox(r["before"], r["bbox"], tgt))
            ok = pred_board == gp(r["after"])
            rows.append(
                {
                    "p": r["p"],
                    "step0": r["step0"],
                    "action": r["action"],
                    "correct": ok,
                    "completion": bool(lm and lm["level_after"] > lm["level_before"]),
                    "target": tgt,
                    **conf,
                }
            )
    return rows, {
        "eligible": eligible,
        "incumbent_predictions": incumbent_predictions,
        "fit_rejected": dict(rejected),
        "candidate_rows": len(rows),
    }


def loto_select(train10):
    configs = {}
    for ts in TRACE_SUPPORTS:
        for occ in MIN_OCCURRENCES:
            for req_lvl in REQUIRE_LEVEL:
                for pos_sup in MIN_POSITION_SUPPORT:
                    k = gate_key(ts, occ, req_lvl, pos_sup)
                    configs[k] = gate_cfg(ts, occ, req_lvl, pos_sup)

    agg = {k: Counter() for k in configs}
    folds = []
    for i, val in enumerate(train10):
        fold_train = [p for j, p in enumerate(train10) if j != i]
        rows, meta = candidate_rows([val], fold_train)
        fold_rec = {
            "fold": pnum(val),
            "train_ps": [pnum(p) for p in fold_train],
            "candidate_rows": len(rows),
            "incumbent_predictions": meta["incumbent_predictions"],
            "eligible": meta["eligible"],
        }
        for k, cfg in configs.items():
            kept = [x for x in rows if gate_accept(cfg, x)]
            if not kept:
                continue
            c = sum(bool(x["correct"]) for x in kept)
            w = len(kept) - c
            agg[k]["predictions"] += len(kept)
            agg[k]["correct"] += c
            agg[k]["wrong"] += w
            agg[k]["folds_with_prediction"] += 1
        folds.append(fold_rec)

    scored = []
    for k, cfg in configs.items():
        a = agg[k]
        p = a["predictions"]
        scored.append(
            {
                "key": k,
                **cfg,
                "predictions": p,
                "correct": a["correct"],
                "wrong": a["wrong"],
                "folds_with_prediction": a["folds_with_prediction"],
                "accuracy": round(a["correct"] / p, 6) if p else None,
            }
        )

    eligible = [
        x
        for x in scored
        if x["predictions"] > 0
        and x["wrong"] == 0
        and x["folds_with_prediction"] >= 5
    ]
    eligible.sort(
        key=lambda x: (
            -x["correct"],
            -x["folds_with_prediction"],
            -x["trace_support"],
            -x["min_occurrences"],
            -x["min_position_trace_support"],
            -int(x["require_level_seen"]),
        )
    )
    scored.sort(
        key=lambda x: (
            x["wrong"],
            -x["correct"],
            -x["folds_with_prediction"],
            -x["trace_support"],
        )
    )
    return (eligible[0] if eligible else None), scored[:40], folds


def audit_reused_dev(train10, dev10, selected):
    rows, meta = candidate_rows(dev10, train10)
    kept = [x for x in rows if gate_accept(selected, x)] if selected else []
    c = sum(bool(x["correct"]) for x in kept)
    w = len(kept) - c
    incumbent = meta["incumbent_predictions"]
    union = incumbent + c if w == 0 else incumbent
    return {
        **meta,
        "selected_gate_predictions": len(kept),
        "selected_gate_correct": c,
        "selected_gate_wrong": w,
        "selected_gate_accuracy": round(c / len(kept), 6) if kept else None,
        "union_exact_if_zero_wrong": union,
        "union_coverage_if_zero_wrong": round(union / meta["eligible"], 6)
        if meta["eligible"]
        else 0.0,
        "wrong_examples": [x for x in kept if not x["correct"]][:40],
    }


def run(paths):
    ps = sorted(paths, key=pnum)
    if [pnum(x) for x in ps] != list(range(20)):
        raise ValueError("exact p0..p19 required")
    train10, dev10 = ps[:10], ps[10:]
    selected, top_loto, folds = loto_select(train10)
    audit = audit_reused_dev(train10, dev10, selected)

    loto_pass = bool(selected is not None)
    reused_dev_zero_wrong_gain = bool(
        selected
        and audit["selected_gate_predictions"] > 0
        and audit["selected_gate_wrong"] == 0
        and audit["union_exact_if_zero_wrong"] > audit["incumbent_predictions"]
    )
    return {
        "schema": "deus/arc3-ft09-r227-loto-confidence-gate/1",
        "rung": RUNG,
        "game": GAME,
        "representation": FAM,
        "selection": {
            "protocol": "10-fold leave-one-trace-out over p0..p9 only; R225 s2 incumbent contract fixed; zero-wrong aggregate; >=5 folds with predictions; maximize correct",
            "selected": selected,
            "top_loto_gates": top_loto,
            "folds": folds,
            "loto_gate_selection_pass": loto_pass,
        },
        "reused_public_development_audit": audit,
        "reused_dev_zero_wrong_incremental_gain": reused_dev_zero_wrong_gain,
        "promotion": {
            "source_assisted_coverage_expert_promotion": False,
            "independent_generalization_promotion": False,
            "solver_promotion": False,
            "kaggle_packaging": False,
            "confidence_family_status": (
                "PROVISIONAL_NEEDS_GENUINELY_UNTOUCHED_PUBLIC_PARTITION"
                if loto_pass and reused_dev_zero_wrong_gain
                else "CLOSE_NO_SAFE_CV_DERIVED_GAIN"
            ),
            "next_gate": (
                "freeze selected gate and test once on a genuinely untouched public/source-generated FT09 partition; require zero wrong and union coverage > incumbent"
                if loto_pass and reused_dev_zero_wrong_gain
                else "close R227 confidence family and change representation"
            ),
        },
        "truth": {
            "public_trace_only": True,
            "gate_selected_from_p0_p9_loto_only": True,
            "confidence_features_preaction_training_derived_only": True,
            "r225_lowbase_threshold_fixed_at_support2_in_outer_folds": True,
            "p10_p19_status": "PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT",
            "p10_p19_used_for_gate_selection": False,
            "p10_p19_audit_only": True,
            "untouched_public_validation_done": False,
            "outcome_assisted_selection_on_p10_p19": False,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    d = run(a.input)
    a.output.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "selected": d["selection"]["selected"],
                "loto_pass": d["selection"]["loto_gate_selection_pass"],
                "audit": d["reused_public_development_audit"],
                "status": d["promotion"]["confidence_family_status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
