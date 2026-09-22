#!/usr/bin/env python3
"""R247: repair R246 selection harness after the R225 10-trace-only CV falsifier.

The representation is unchanged.  The repair changes only the model-selection
harness: p0-p9 leave-one-trace-out scores the source-free adapter by itself,
without trying to refit the R225 incumbent on nine traces (R225's internal CV is
contractually fixed to ten).  After a lens/support pair is frozen, the final
p10-p19 diagnostic composes it behind the unchanged R225 incumbent trained on
all p0-p9.  This preserves the residual precedence and avoids validation-fold
leakage into adapter labels.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path
import public_ft09_markov_lens_worldmodel_246 as r246

RUNG=247

def eval_adapter_only(train, eval_paths, lens_name, min_support):
    model,diag=r246.build_adapter(train,lens_name,min_support); s=Counter()
    for p in eval_paths:
        for r in r246.r212.all_rows(p):
            if not r.get('eligible'): continue
            s['eligible']+=1
            k=(repr(r246.LENSES[lens_name](r)),r246.action_token(r)); mech=model.get(k)
            if mech is None:
                s['adapter_abstain']+=1; continue
            pred=r246.apply_mech(mech,r); s['adapter_predictions']+=1
            ok=pred==r['after'] if pred is not None else False
            s['adapter_correct' if ok else 'adapter_wrong']+=1
    return s,diag

def select_config(train):
    scores=[]
    for lname in sorted(r246.LENSES):
        for sup in r246.MIN_SUPPORTS:
            total=Counter(); fids=[]
            for i,val in enumerate(train):
                tr=[p for j,p in enumerate(train) if j!=i]
                ss,dd=eval_adapter_only(tr,[val],lname,sup)
                total.update(ss); fids.append(dd['fidelity'])
            scores.append({'lens':lname,'min_support':sup,'metrics':dict(total),'mean_fidelity':round(sum(fids)/len(fids),6)})
    safe=[x for x in scores if x['metrics'].get('adapter_wrong',0)==0 and x['metrics'].get('adapter_predictions',0)>0]
    pool=safe if safe else scores
    chosen=max(pool,key=lambda x:(x['metrics'].get('adapter_correct',0)-10*x['metrics'].get('adapter_wrong',0),x['metrics'].get('adapter_predictions',0),x['mean_fidelity'],-x['min_support'],x['lens']))
    return chosen,scores

def run(paths):
    ps=sorted(paths,key=r246.pnum)
    if [r246.pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
    train,held=ps[:10],ps[10:]
    chosen,scores=select_config(train)
    hs,diag,examples=r246.eval_paths(train,held,chosen['lens'],chosen['min_support'],True)
    eligible=hs['eligible']; union=hs['union_predictions']
    held_metrics={**dict(hs),'union_accuracy':round(hs['union_correct']/union,6) if union else None,'union_coverage':round(union/eligible,6) if eligible else 0.0}
    strict_gain=bool(hs['adapter_predictions']>0 and hs['adapter_wrong']==0 and hs['union_wrong']==0 and hs['union_predictions']>307)
    return {
      'schema':'deus/arc3-ft09-markov-lens-worldmodel/2','rung':RUNG,'game':r246.GAME,
      'repair':{'from_rung':246,'falsifier':'R225 build_models requires exactly ten traces; nine-trace nested refit raised IndexError','delta':'adapter-only LOTO selection; unchanged R225 composed only after adapter config freeze'},
      'source_grounding':{'pattern':'OpenWorld/Fable E134 Markov fidelity SELECT + executable verification','upstream_commit':'e8248685e4f682dd6587e1af6296733cf3838a59','implementation':'clean-room source-free adapter; no game source/runtime'},
      'selection':{'protocol':'p0-p9 adapter-only leave-one-trace-out; zero-wrong-first; no R225 refit inside folds','chosen':chosen,'candidate_count':len(scores),'all_candidates':scores},
      'frozen_adapter':diag,
      'reused_public_development_p10_p19':{'metrics':held_metrics,'examples':examples,'strict_zero_wrong_gain_vs_r225':strict_gain},
      'promotion':{'source_free_adapter_diagnostic_accept':strict_gain,'independent_generalization':False,'solver_promotion':False,'kaggle_packaging':False,'next_gate':'if gain, require genuinely untouched/frozen evidence or provider Output audit before rank integration; if no gain, close this representation family'},
      'truth':{'public_trace_only':True,'source_free_game_runtime':True,'p10_p19_reused_public_development':True,'selection_uses_p0_p9_only':True,'heldout_never_updates_adapter':True,'source_assisted_replay':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'leaderboard_score_claim':False,'submission_quota_spent':False}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); d=run(a.input); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'repair':d['repair'],'chosen':d['selection']['chosen'],'adapter':d['frozen_adapter'],'held':d['reused_public_development_p10_p19']['metrics'],'gate':d['reused_public_development_p10_p19']['strict_zero_wrong_gain_vs_r225']},sort_keys=True))
if __name__=='__main__': main()
