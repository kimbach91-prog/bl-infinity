#!/usr/bin/env python3
"""Rung 147: observable current-state selectors for residual semantic effects.

Rung 146 showed that prior semantic history alone predicts the recurrent residual
value-pair vocabulary with high but non-zero error. This rung adds only features
available before the current outcome: board color histogram and translation-
invariant connected-component inventories, optionally combined with the strongest
prior semantic history. It tests whether current rendered state disambiguates the
next residual semantic effect.

The current outcome is still used retrospectively to identify the conservative
motion-core regime and score the residual semantic target. Each context lookup is
prefix-only and the current target is ingested after prediction. Diagnostic only;
no full-frame/solver/model/GPU/Kaggle claim.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138
import public_residual_shape_canonical_audit_145 as shape145

RUNG = 147


def color_hist(board: list[list[int]]) -> str:
    c = Counter(v for row in board for v in row)
    return base.stable(sorted(c.items()))


def component_inventory(board: list[list[int]], *, keep_color: bool) -> str:
    desc = []
    for o in obj138.objects(board):
        shape = tuple(sorted((r - o.r0, c - o.c0) for r, c in o.cells))
        if keep_color:
            desc.append((o.color, o.area, o.h, o.w, shape))
        else:
            desc.append((o.area, o.h, o.w, shape))
    return base.stable(sorted(desc, key=repr))


def single(counter: Counter[str]) -> str | None:
    return next(iter(counter)) if len(counter) == 1 else None


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    names = (
        'hist_action',
        'hist_prev2_action',
        'inventory_color_action',
        'inventory_color_prev2_action',
        'inventory_colorless_action',
        'inventory_colorless_prev2_action',
    )
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
        hist = color_hist(before)
        invc = component_inventory(before, keep_color=True)
        inv0 = component_inventory(before, keep_color=False)
        contexts: dict[str, str | None] = {
            'hist_action': base.stable({'h': hist, 'a': action}),
            'hist_prev2_action': base.stable({'h': hist, 'p2': prev2, 'p1': prev1, 'a': action}) if prev2 is not None and prev1 is not None else None,
            'inventory_color_action': base.stable({'i': invc, 'a': action}),
            'inventory_color_prev2_action': base.stable({'i': invc, 'p2': prev2, 'p1': prev1, 'a': action}) if prev2 is not None and prev1 is not None else None,
            'inventory_colorless_action': base.stable({'i': inv0, 'a': action}),
            'inventory_colorless_prev2_action': base.stable({'i': inv0, 'p2': prev2, 'p1': prev1, 'a': action}) if prev2 is not None and prev1 is not None else None,
        }
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
    out = {}
    for name in names:
        pred = sum(p['contexts'][name]['predictions'] for p in parts)
        correct = sum(p['contexts'][name]['correct'] for p in parts)
        wrong = sum(p['contexts'][name]['wrong'] for p in parts)
        out[name] = {
            'predictions': pred,
            'correct': correct,
            'wrong': wrong,
            'accuracy': round(correct / pred, 6) if pred else None,
            'coverage_of_eligible': round(pred / eligible, 6) if eligible else 0.0,
            'strict_zero_error': bool(pred and wrong == 0),
        }
    zero = [(v['predictions'], k) for k, v in out.items() if v['strict_zero_error']]
    return {
        'trace_count': len(parts),
        'eligible_transitions': eligible,
        'contexts': out,
        'best_strict_zero_error_context': max(zero)[1] if zero else None,
        'per_trace': parts,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = []
    traces = []
    for p in paths:
        a = audit_trace(base.load_events(p))
        parts.append(a)
        traces.append({'path': str(p), 'audit': a})
    return {
        'schema': 'deus/arc3-public-residual-state-selector-audit/1',
        'rung': RUNG,
        'execution_class': 'CPU_PUBLIC_TRACE_RESIDUAL_STATE_SELECTOR_DIAGNOSTIC',
        'representation_change_from_rung146': {
            'changed': True,
            'change': 'add current pre-outcome color-histogram and translation-invariant component-inventory selectors to prior semantic phase context',
        },
        'source_grounding': {'public_trace_repo': base.TUFA_REPO, 'public_trace_commit': base.TUFA_COMMIT, 'clean_room_implementation': True},
        'traces': traces,
        'aggregate': aggregate(parts),
        'diagnostic_gate': 'RESIDUAL_CURRENT_STATE_SELECTOR_CHARACTERIZED',
        'promotion': {'candidate_model_promotion': False, 'kaggle_packaging': False},
        'truth': {
            'public_trace_only': True,
            'source_assisted_replay': True,
            'diagnostic_only': True,
            'selector_features_available_pre_outcome': True,
            'current_outcome_used_for_regime_isolation_and_target_scoring': True,
            'prediction_context_prior_only': True,
            'current_target_ingested_after_prediction': True,
            'independent_generalization_claim': False,
            'solver_behavior_gain_claim': False,
            'model_execution': False,
            'gpu_execution': False,
            'kaggle_execution': False,
            'kaggle_submission_attempted': False,
            'submission_quota_spent': False,
            'leaderboard_score_claim': False,
            'owner_score_claim': False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, action='append', default=[])
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if not args.input:
        raise SystemExit('at least one --input is required')
    d = run(args.input)
    text = json.dumps(d, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
