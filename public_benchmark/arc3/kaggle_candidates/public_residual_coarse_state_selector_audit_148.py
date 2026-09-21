#!/usr/bin/env python3
"""Rung 148: coarsened pre-outcome state selectors focused on p0/p10 coverage.

Rung 147 made the current-state representation too specific: exact histograms and
component inventories were zero-error only in p11 and never repeated in p0/p10.
This rung changes representation by dropping exact counts/shapes and testing a
small, predeclared family of coarse structural summaries available before outcome:
palette, frequency rank, component counts, and component-area inventories. Each is
also tested with the prior-two residual semantic phase from rung146.

Targets are the residual value-pair semantics from rung145. Current outcome is used
only retrospectively to isolate the eligible motion-core residual and score the
target. Context lookup is prefix-only and the target is ingested after prediction.
Diagnostic only; no full-frame/solver/model/GPU/Kaggle claim.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138
import public_residual_shape_canonical_audit_145 as shape145

RUNG = 148


def palette(board: list[list[int]]) -> Any:
    return tuple(sorted({v for row in board for v in row}))


def frequency_rank(board: list[list[int]]) -> Any:
    c = Counter(v for row in board for v in row)
    # Keep ties explicit but drop exact pixel counts.
    by_count: dict[int, list[int]] = defaultdict(list)
    for color, n in c.items():
        by_count[n].append(color)
    return tuple(tuple(sorted(by_count[n])) for n in sorted(by_count, reverse=True))


def component_count_by_color(board: list[list[int]]) -> Any:
    c = Counter(o.color for o in obj138.objects(board))
    return tuple(sorted(c.items()))


def component_area_multiset(board: list[list[int]], keep_color: bool) -> Any:
    obs = obj138.objects(board)
    if keep_color:
        return tuple(sorted((o.color, o.area) for o in obs))
    return tuple(sorted(o.area for o in obs))


def structural_bundle(board: list[list[int]]) -> Any:
    return {
        'palette': palette(board),
        'rank': frequency_rank(board),
        'component_counts': component_count_by_color(board),
        'areas0': component_area_multiset(board, False),
    }

FEATURES: dict[str, Callable[[list[list[int]]], Any]] = {
    'palette': palette,
    'frequency_rank': frequency_rank,
    'component_count_by_color': component_count_by_color,
    'component_area_color': lambda b: component_area_multiset(b, True),
    'component_area_colorless': lambda b: component_area_multiset(b, False),
    'structural_bundle': structural_bundle,
}


def single(c: Counter[str]) -> str | None:
    return next(iter(c)) if len(c) == 1 else None


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    names = tuple([f'{n}_action' for n in FEATURES] + [f'{n}_prev2_action' for n in FEATURES])
    banks: dict[str, dict[str, Counter[str]]] = {n: defaultdict(Counter) for n in names}
    stats = {n: {'predictions': 0, 'correct': 0, 'wrong': 0, 'conflict_abstentions': 0, 'unseen_abstentions': 0} for n in names}
    eligible = 0
    reasons = Counter()
    prev1: str | None = None
    prev2: str | None = None
    pre = events[0]

    for e in events[1:]:
        if e.get('type') != 'action':
            pre = e
            continue
        before = base.as_grid(pre['board'])
        after = base.as_grid(e['board'])
        action = base.action_name(e)
        enc = shape145.encode(before, after, action)
        pre = e
        if not enc['eligible']:
            reasons[enc['reason']] += 1
            continue
        eligible += 1
        target = enc['value_pair_multiset']
        contexts: dict[str, str | None] = {}
        for fname, fn in FEATURES.items():
            feat = fn(before)
            contexts[f'{fname}_action'] = base.stable({'f': feat, 'a': action})
            contexts[f'{fname}_prev2_action'] = base.stable({'f': feat, 'p2': prev2, 'p1': prev1, 'a': action}) if prev2 is not None and prev1 is not None else None

        for name, key in contexts.items():
            if key is None or key not in banks[name]:
                stats[name]['unseen_abstentions'] += 1
                continue
            pred = single(banks[name][key])
            if pred is None:
                stats[name]['conflict_abstentions'] += 1
                continue
            stats[name]['predictions'] += 1
            if pred == target:
                stats[name]['correct'] += 1
            else:
                stats[name]['wrong'] += 1
        for name, key in contexts.items():
            if key is not None:
                banks[name][key][target] += 1
        prev2, prev1 = prev1, target

    for name, s in stats.items():
        s['accuracy'] = round(s['correct'] / s['predictions'], 6) if s['predictions'] else None
        s['coverage_of_eligible'] = round(s['predictions'] / eligible, 6) if eligible else 0.0
        s['strict_zero_error'] = bool(s['predictions'] and s['wrong'] == 0)
        s['unique_contexts_final'] = len(banks[name])
        s['conflicted_contexts_final'] = sum(len(c) > 1 for c in banks[name].values())
    return {'eligible_transitions': eligible, 'ineligible_reasons': dict(sorted(reasons.items())), 'contexts': stats}


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    names = tuple(parts[0]['contexts']) if parts else ()
    eligible = sum(p['eligible_transitions'] for p in parts)
    out: dict[str, Any] = {}
    qualified_hard = []
    for name in names:
        pred = sum(p['contexts'][name]['predictions'] for p in parts)
        correct = sum(p['contexts'][name]['correct'] for p in parts)
        wrong = sum(p['contexts'][name]['wrong'] for p in parts)
        per_trace_predictions = [p['contexts'][name]['predictions'] for p in parts]
        per_trace_wrong = [p['contexts'][name]['wrong'] for p in parts]
        out[name] = {
            'predictions': pred,
            'correct': correct,
            'wrong': wrong,
            'accuracy': round(correct / pred, 6) if pred else None,
            'coverage_of_eligible': round(pred / eligible, 6) if eligible else 0.0,
            'strict_zero_error': bool(pred and wrong == 0),
            'per_trace_predictions': per_trace_predictions,
            'per_trace_wrong': per_trace_wrong,
        }
        # Hard-trace qualification requires nonzero p0 and p10 predictions and
        # zero errors in both; p11 cannot hide zero hard-trace coverage.
        if per_trace_predictions[0] > 0 and per_trace_predictions[1] > 0 and per_trace_wrong[0] == 0 and per_trace_wrong[1] == 0:
            qualified_hard.append((per_trace_predictions[0] + per_trace_predictions[1], name))
    return {
        'trace_count': len(parts),
        'eligible_transitions': eligible,
        'contexts': out,
        'best_zero_error_p0_p10_context': max(qualified_hard)[1] if qualified_hard else None,
        'per_trace': parts,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts=[]; traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p)); parts.append(a); traces.append({'path':str(p),'audit':a})
    return {
        'schema':'deus/arc3-public-residual-coarse-state-selector-audit/1',
        'rung':RUNG,
        'execution_class':'CPU_PUBLIC_TRACE_RESIDUAL_COARSE_STATE_SELECTOR_DIAGNOSTIC',
        'representation_change_from_rung147':{'changed':True,'change':'coarsen pre-outcome state from exact histograms/shapes to palette, frequency rank, component counts, and component-area inventories, with optional prior-two semantic phase'},
        'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},
        'traces':traces,
        'aggregate':aggregate(parts),
        'diagnostic_gate':'RESIDUAL_COARSE_STATE_SELECTOR_CHARACTERIZED',
        'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},
        'truth':{'public_trace_only':True,'source_assisted_replay':True,'diagnostic_only':True,'selector_features_available_pre_outcome':True,'current_outcome_used_for_regime_isolation_and_target_scoring':True,'prediction_context_prior_only':True,'current_target_ingested_after_prediction':True,'hard_trace_gate_requires_p0_and_p10_nonzero_coverage':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False},
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path); args=ap.parse_args()
    if not args.input: raise SystemExit('at least one --input is required')
    d=run(args.input); text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output: args.output.write_text(text,encoding='utf-8')
    print(text,end=''); return 0

if __name__=='__main__': raise SystemExit(main())
