#!/usr/bin/env python3
"""R304: frozen cn04 exact relational-topology p5-p9 public replay.

R303 selected graph_exact solely from p0-p4 five-fold LOTO. This rung freezes
that representation, fits its deterministic transition table on all p0-p4,
and evaluates exact p5-p9 without selector changes. p10-p19 must not be staged.

Truth boundary: public/source-assisted replay only; not independent hidden
generalization, solver promotion, Kaggle execution, submission, or score.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_exact_topology_loto_303 as r303

TARGET='cn04-2fe56bfb'
MODE='graph_exact'


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--train',type=Path,action='append',default=[]); ap.add_argument('--replay',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    train=sorted(a.train,key=r246.pnum); replay=sorted(a.replay,key=r246.pnum)
    if [r246.pnum(p) for p in train]!=list(range(5)): raise SystemExit('train must be p0-p4')
    if [r246.pnum(p) for p in replay]!=list(range(5,10)): raise SystemExit('replay must be p5-p9')
    if any(r246.game_id(p)!=TARGET for p in train+replay): raise SystemExit('exact cn04 required')
    train_traces=[r278.annotated_rows([p]) for p in train]
    replay_traces=[r278.annotated_rows([p]) for p in replay]
    tab,fit=r303.fit(train_traces,MODE)
    total={'transitions':0,'predictions':0,'correct':0,'wrong':0,'abstain':0}
    per={}
    for i,tr in enumerate(replay_traces,5):
        ev=r303.evaluate(tr,tab,MODE); per[str(i)]=ev
        for k in ('transitions','predictions','correct','wrong','abstain'): total[k]+=int(ev.get(k,0))
    total['accuracy']=round(total['correct']/total['predictions'],6) if total['predictions'] else None
    if total['predictions']>0 and total['wrong']==0: verdict='P5P9_GRAPH_EXACT_ZERO_WRONG'
    elif total['predictions']>0: verdict='P5P9_GRAPH_EXACT_UNSAFE'
    else: verdict='P5P9_GRAPH_EXACT_NO_COVERAGE'
    out={'schema':'deus/arc3-r304-cn04-graph-exact-p5p9-replay/1','rung':304,'game':TARGET,'frozen_from':'R303 p0-p4 LOTO best_mode=graph_exact','mode':MODE,'fit':fit,'replay_total':total,'per_trace':per,'verdict':verdict,'protocol':{'train':'p0-p4','replay':'p5-p9','selection_changed_after_replay_read':False,'p10_p19_staged_or_read':False},'truth':{'public_trace_only':True,'source_assisted_replay':True,'independent_hidden_generalization_claim':False,'p10_p19_read':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'replay_total':total,'fit':fit},sort_keys=True))
if __name__=='__main__': main()
