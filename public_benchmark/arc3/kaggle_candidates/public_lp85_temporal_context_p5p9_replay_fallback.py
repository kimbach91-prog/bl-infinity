#!/usr/bin/env python3
"""Fallback: frozen lp85 temporal-context p5-p9 public replay.

The mechanism is frozen from prior p0-p4 diagnostics/holdout:
  ACTION_REGION4 + H3 stable period/velocity + exact base-prevalue guard.
R300 structural templates are fit ONLY on p0-p4.  The frozen mechanism is then
replayed on p5-p9; temporal history may update causally from earlier outcomes
inside each replay trace.  p10-p19 must not be staged/read.

Truth boundary: source-assisted public replay with online same-trace past-outcome
adaptation.  Not independent generalization, solver promotion, Kaggle execution,
submission, or leaderboard score.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_lp85_seeded_structural_residual_gate_300 as r300
import public_lp85_temporal_residual_context_diag_302 as r302

TARGET_GAME='lp85-305b61c3'
CTX_MODE='ACTION_REGION4'
HISTORY_MODE='H3_STABLE_PERIOD_VELOCITY'


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--train',type=Path,action='append',default=[])
    ap.add_argument('--replay',type=Path,action='append',default=[])
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    tr=sorted(a.train,key=r246.pnum); rp=sorted(a.replay,key=r246.pnum)
    if [r246.pnum(p) for p in tr] != list(range(5)):
        raise SystemExit('train must be exact p0-p4')
    if [r246.pnum(p) for p in rp] != list(range(5,10)):
        raise SystemExit('replay must be exact p5-p9')
    if any(r246.game_id(p)!=TARGET_GAME for p in tr+rp):
        raise SystemExit('exact lp85 target required')

    train_traces=[r278.annotated_rows([p]) for p in tr]
    train_rows=[row for trace in train_traces for row in trace]
    templates,fit=r300.fit_templates(train_rows,train_traces)

    replay_traces=[r278.annotated_rows([p]) for p in rp]
    total,per=r302.run_mode(replay_traces,templates,CTX_MODE,HISTORY_MODE)
    pred=int(total.get('predicted_changes',0)); false=int(total.get('false_changes',0)); gain=int(total.get('error_reduction_vs_r300_base',0))
    if pred>0 and false==0 and gain>0:
        verdict='P5P9_FROZEN_CAUSAL_REPLAY_ZERO_FALSE'
    elif gain>0:
        verdict='P5P9_FROZEN_CAUSAL_REPLAY_GAIN_UNSAFE'
    else:
        verdict='P5P9_FROZEN_CAUSAL_REPLAY_NO_SIGNAL'

    out={
      'schema':'deus/arc3-lp85-temporal-context-p5p9-replay-fallback/1',
      'game':TARGET_GAME,
      'frozen_mechanism':{'context':CTX_MODE,'history':HISTORY_MODE,'structural_fit_ps':[0,1,2,3,4],'selection_changed_after_replay_read':False},
      'protocol':{'train':'p0-p4','replay':'p5-p9','p10_p19_staged_or_read':False,'same_trace_past_outcome_adaptation':True,'source_assisted_public_replay':True,'promotion_in_this_run':False},
      'fit_gate':fit,'replay_total':total,'per_replay_trace':per,'verdict':verdict,
      'truth':{'public_trace_only':True,'source_assisted_replay':True,'independent_generalization':False,'p10_p19_read':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'replay_total':total},sort_keys=True))

if __name__=='__main__': main()
