#!/usr/bin/env python3
"""R269: frozen source-free relational gate for re86.

R267 diagnostic (p0-p4 fit / p5-p9 only) found the strongest supported
zero-wrong separator for the mixed R266 RIGHT variant:
  variant = source_dest_color, pad=2, edit_radius=12, support=2
  pre-action selector = dest_collision_count == 3 and dest_ring_nonbg == 19
  diagnostic support = 3 correct / 0 wrong across 2 validation traces.

R269 freezes that exact selector before touching p10-p19, replays the p0-p9
fit, and evaluates reused public-development p10-p19 without updating any
selection or model. This is not independent hidden generalization.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_contextual_object_interaction_gate_266 as r266
import public_interaction_separator_diag_267 as r267

MODE = "source_dest_color"
PAD = 2
EDIT_RADIUS = 12
SUPPORT = 2
SELECTOR = {"dest_collision_count": 3, "dest_ring_nonbg": 19}


def match(fv):
    return fv is not None and all(int(fv[k]) == int(v) for k, v in SELECTOR.items())


def prep(p):
    return r266.prep(p)


def eval_rows(rows, exact, model, rules):
    s = Counter()
    examples = []
    for row in rows:
        s["transitions"] += 1
        if row["exact_key"] in exact:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        if row["action"] != "RIGHT":
            s["candidate_abstain"] += 1
            continue
        fv = r267.feature_vector(row, model)
        if not match(fv):
            s["candidate_abstain"] += 1
            continue
        pred = r266.apply(row, model, rules, MODE, PAD)
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        ok = pred == row["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 30:
            examples.append({"trace": row["trace"], "transition_id": row["transition_id"], "correct": ok, "selector_features": {k: fv[k] for k in SELECTOR}})
    n = s["candidate_predictions"]
    return {**dict(s), "accuracy": round(s["candidate_correct"] / n, 6) if n else None, "examples": examples}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    ps = sorted(a.input, key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise ValueError(f"exact p0..p19 required, got {nums}")
    parts = [prep(p) for p in ps]
    tr = [r for x in parts[:5] for r in x]
    va = [r for x in parts[5:10] for r in x]
    fit = [r for x in parts[:10] for r in x]
    ho = [r for x in parts[10:] for r in x]

    tr_right = [r for r in tr if r["action"] == "RIGHT"]
    model_tr = r266.fit_base(tr_right)
    rules_tr = r266.fit_rules(tr_right, model_tr, MODE, PAD, EDIT_RADIUS, SUPPORT)
    selection_replay = eval_rows([r for r in va if r["action"] == "RIGHT"], r251.fit_exact(tr), model_tr, rules_tr)

    fit_right = [r for r in fit if r["action"] == "RIGHT"]
    model = r266.fit_base(fit_right)
    rules = r266.fit_rules(fit_right, model, MODE, PAD, EDIT_RADIUS, SUPPORT)
    heldout = eval_rows(ho, r251.fit_exact(fit), model, rules)
    nd = bool(heldout.get("candidate_predictions", 0) > 0 and heldout.get("candidate_wrong", 0) == 0 and heldout.get("candidate_correct", 0) > 0)
    out = {
        "schema": "deus/arc3-r269-relational-frozen-gate/1",
        "rung": 269,
        "lineage": {"r267": "run35802117735/artifact10726311672", "frozen_variant": f"{MODE}_p{PAD}_e{EDIT_RADIUS}_s{SUPPORT}", "frozen_selector": SELECTOR},
        "protocol": {"selection_replay": "p0-p4 fit / p5-p9", "refit": "p0-p9", "frozen_eval": "p10-p19", "p10_p19_updates_selection_or_model": False},
        "selection_replay": selection_replay,
        "heldout": heldout,
        "non_dominated_source_side_gain": nd,
        "promotion": {"integration_candidate": nd, "solver_promotion": False, "kaggle_packaging": False},
        "truth": {"public_trace_only": True, "game_source_read": False, "selection_uses_p0_p9_only": True, "p10_p19_never_updates_selection_or_model": True, "p10_p19_status": "PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT", "independent_generalization_claim": False, "kaggle_execution": False, "competition_submission": False, "submission_quota_spent": False, "owner_score_claim": False},
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"selection_replay": selection_replay, "heldout": heldout, "gain": nd}, sort_keys=True))

if __name__ == "__main__":
    main()
