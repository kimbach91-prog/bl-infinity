#!/usr/bin/env python3
"""R276 frozen gate for the exact R275 action-canonical signal.

R275 selected exactly two public games and one representation using p0-p4 fit and
p5-p9 diagnostic only. R276 freezes that selector/mechanism before reading p10-p19:
  games: g50t-5849a774, m0r0-492f87ba
  mode:  canon_nodes_ui
Then it refits the deterministic transition table on p0-p9 and evaluates frozen
public-development p10-p19. No heldout row can update selector, representation, or model.
PUBLIC_OFFLINE only; not independent hidden generalization or Kaggle performance.
"""
from __future__ import annotations

import argparse, json, math
from pathlib import Path
from collections import defaultdict

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_action_canonical_topology_diag_275 as r275

FROZEN_GAMES=("g50t-5849a774","m0r0-492f87ba")
FROZEN_MODE="canon_nodes_ui"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,action='append',default=[])
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    if tuple(sorted(by)) != tuple(sorted(FROZEN_GAMES)):
        raise SystemExit(f'exact frozen games required: {FROZEN_GAMES}; got {sorted(by)}')

    rows_out={}; pass_games=[]
    agg={k:0 for k in ('transitions','predictions','correct','wrong','abstain')}
    raw_agg={k:0 for k in ('transitions','predictions','correct','wrong','abstain')}
    for g in FROZEN_GAMES:
        ps=sorted(by[g],key=r246.pnum)
        nums=[r246.pnum(p) for p in ps]
        if nums != list(range(20)):
            raise SystemExit(f'{g}: exact p0-p19 required, got {nums}')
        train=r268.rows([p for p in ps if r246.pnum(p)<=9])
        hold=r268.rows([p for p in ps if r246.pnum(p)>=10])

        frozen_tab, fit_stats=r275.fit(train,FROZEN_MODE)
        frozen_eval=r275.evaluate(hold,frozen_tab,FROZEN_MODE)
        raw_tab, raw_fit=r275.fit(train,'raw')
        raw_eval=r275.evaluate(hold,raw_tab,'raw')

        min_predictions=max(10,math.ceil(0.05*int(frozen_eval.get('transitions',0))))
        candidate_pass=(
            int(frozen_eval.get('wrong',0))==0
            and int(frozen_eval.get('predictions',0))>=min_predictions
            and float(frozen_eval.get('accuracy') or 0.0)>=0.99
            and int(frozen_eval.get('correct',0))>int(raw_eval.get('correct',0))
        )
        if candidate_pass:
            pass_games.append(g)
        rows_out[g]={
            'frozen_mode':FROZEN_MODE,
            'fit':fit_stats,
            'heldout':frozen_eval,
            'raw_fit':raw_fit,
            'raw_heldout':raw_eval,
            'min_predictions':min_predictions,
            'gate_pass':candidate_pass,
        }
        for k in agg:
            agg[k]+=int(frozen_eval.get(k,0))
            raw_agg[k]+=int(raw_eval.get(k,0))

    agg['accuracy']=round(agg['correct']/agg['predictions'],6) if agg['predictions'] else None
    raw_agg['accuracy']=round(raw_agg['correct']/raw_agg['predictions'],6) if raw_agg['predictions'] else None
    verdict='PROMOTE_FROZEN_REPRESENTATION' if pass_games else 'NO_PROMOTION'
    out={
        'schema':'deus/arc3-r276-action-canonical-frozen-gate/1',
        'rung':276,
        'lineage':{
            'r275_run':35808617133,
            'r275_head':'89b793adc410e1b59b0a90ce9f6c6ba6e3e29bb1',
            'r275_artifact':10728599593,
            'r275_selector_frozen_before_p10_p19':True,
        },
        'frozen_selector':{'games':list(FROZEN_GAMES),'mode':FROZEN_MODE},
        'protocol':{
            'mechanism_selection':'R275 p0-p4 fit -> p5-p9 diagnostic',
            'model_fit':'p0-p9 only after selector freeze',
            'evaluation':'p10-p19 reused public-development heldout',
            'p10_p19_updates_selector':False,
            'p10_p19_updates_representation':False,
            'p10_p19_updates_model':False,
        },
        'games':rows_out,
        'pass_games':pass_games,
        'aggregate':agg,
        'raw_aggregate':raw_agg,
        'verdict':verdict,
        'truth':{
            'public_trace_only':True,
            'source_free_runtime_logic':True,
            'reused_public_development_holdout':True,
            'independent_hidden_generalization_claim':False,
            'kaggle_execution':False,
            'competition_submission':False,
            'submission_quota_spent_by_r276':False,
            'full_game_solver_claim':False,
        },
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'pass_games':pass_games,'aggregate':agg,'raw_aggregate':raw_agg,'games':{g:rows_out[g]['heldout'] for g in FROZEN_GAMES}},sort_keys=True))

if __name__=='__main__': main()
