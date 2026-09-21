#!/usr/bin/env python3
"""Rung 146: prefix-only history-phase predictability of residual transition semantics.

Rung 145 found that residual geometry remains nonrecurrent in p0/p10 after
translation/action canonicalization, while the residual value-pair multiset is
highly recurrent. This diagnostic asks whether that recurrent semantic signature
is actually predictable from already observed history rather than merely common.

The current transition outcome is still required retrospectively to establish the
conservative motion correspondence, isolate the residual, and score the semantic
target. Prediction contexts use only prior residual signatures/actions plus the
current action; each prediction is committed before the current semantic target is
ingested. This remains source-assisted public replay, not an independent solver or
Kaggle/model/GPU result.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_residual_shape_canonical_audit_145 as shape145

RUNG = 146


def _single_target(counter: Counter[str]) -> str | None:
    return next(iter(counter)) if len(counter) == 1 else None


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    # Per-context maps contain *prior* observations only when each prediction is made.
    banks: dict[str, dict[str, Counter[str]]] = {
        name: defaultdict(Counter)
        for name in (
            'action_only',
            'prev_value_action',
            'prev2_value_action',
            'prev_action_action',
            'prev_value_prev_action_action',
        )
    }
    stats = {
        name: {'predictions': 0, 'correct': 0, 'wrong': 0, 'conflict_abstentions': 0, 'unseen_abstentions': 0}
        for name in banks
    }

    eligible = 0
    reasons = Counter()
    target_hist = Counter()
    prev_value: str | None = None
    prev2_value: str | None = None
    prev_action: str | None = None
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
            # Keep action history observable even if this outcome is not in the
            # residual-motion regime; semantic residual history stays unchanged.
            prev_action = action
            continue

        eligible += 1
        target = enc['value_pair_multiset']
        target_hist[target] += 1
        contexts = {
            'action_only': base.stable({'a': action}),
            'prev_value_action': base.stable({'pv': prev_value, 'a': action}) if prev_value is not None else None,
            'prev2_value_action': base.stable({'p2': prev2_value, 'p1': prev_value, 'a': action}) if prev2_value is not None and prev_value is not None else None,
            'prev_action_action': base.stable({'pa': prev_action, 'a': action}) if prev_action is not None else None,
            'prev_value_prev_action_action': base.stable({'pv': prev_value, 'pa': prev_action, 'a': action}) if prev_value is not None and prev_action is not None else None,
        }

        # Predict from prior-only banks.
        for name, key in contexts.items():
            if key is None or key not in banks[name]:
                stats[name]['unseen_abstentions'] += 1
                continue
            pred = _single_target(banks[name][key])
            if pred is None:
                stats[name]['conflict_abstentions'] += 1
                continue
            stats[name]['predictions'] += 1
            if pred == target:
                stats[name]['correct'] += 1
            else:
                stats[name]['wrong'] += 1

        # Reveal/ingest current target only after all current predictions lock.
        for name, key in contexts.items():
            if key is not None:
                banks[name][key][target] += 1

        prev2_value, prev_value = prev_value, target
        prev_action = action

    for name, s in stats.items():
        s['accuracy'] = round(s['correct'] / s['predictions'], 6) if s['predictions'] else None
        s['coverage_of_eligible'] = round(s['predictions'] / eligible, 6) if eligible else 0.0
        s['strict_zero_error'] = bool(s['predictions'] and s['wrong'] == 0)
        s['unique_contexts_final'] = len(banks[name])
        s['conflicted_contexts_final'] = sum(len(c) > 1 for c in banks[name].values())
    return {
        'eligible_transitions': eligible,
        'ineligible_reasons': dict(sorted(reasons.items())),
        'unique_value_pair_targets': len(target_hist),
        'target_reuse_fraction': round((eligible - len(target_hist)) / eligible, 6) if eligible else 0.0,
        'contexts': stats,
    }


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    names = tuple(parts[0]['contexts']) if parts else ()
    eligible = sum(p['eligible_transitions'] for p in parts)
    out: dict[str, Any] = {}
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
    best_zero = None
    candidates = [(v['predictions'], k) for k, v in out.items() if v['strict_zero_error']]
    if candidates:
        best_zero = max(candidates)[1]
    return {
        'trace_count': len(parts),
        'eligible_transitions': eligible,
        'contexts': out,
        'best_strict_zero_error_context': best_zero,
        'per_trace': parts,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = []
    traces = []
    for p in paths:
        a = audit_trace(base.load_events(p))
        parts.append(a)
        traces.append({'path': str(p), 'audit': a})
    agg = aggregate(parts)
    return {
        'schema': 'deus/arc3-public-residual-history-phase-audit/1',
        'rung': RUNG,
        'execution_class': 'CPU_PUBLIC_TRACE_RESIDUAL_HISTORY_PHASE_DIAGNOSTIC',
        'representation_change_from_rung145': {
            'changed': True,
            'change': 'test whether recurrent residual value-pair semantics are prequentially predictable from prior semantic/action history instead of treating recurrence itself as predictability',
        },
        'source_grounding': {
            'public_trace_repo': base.TUFA_REPO,
            'public_trace_commit': base.TUFA_COMMIT,
            'clean_room_implementation': True,
        },
        'traces': traces,
        'aggregate': agg,
        'diagnostic_gate': 'RESIDUAL_HISTORY_PHASE_PREDICTABILITY_CHARACTERIZED',
        'promotion': {'candidate_model_promotion': False, 'kaggle_packaging': False},
        'truth': {
            'public_trace_only': True,
            'source_assisted_replay': True,
            'diagnostic_only': True,
            'current_outcome_used_for_correspondence_residual_and_scoring': True,
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
