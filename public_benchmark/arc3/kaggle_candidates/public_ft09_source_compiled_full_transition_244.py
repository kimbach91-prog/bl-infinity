#!/usr/bin/env python3
"""R244: compose the verified FT09 source-assisted transition mechanisms.

Precedence / mechanism chain:
  R234 compiled local + next-scene transitions
  R239 zero-dynamic-hit non-node no-op
  R242 level0 animation macro-step closure (same external action)
  R243 explicit RESET -> current visible level compiled initial frame

Each component was separately falsified/repaired and zero-wrong at its accepted
gate. R244 verifies the combined composer over all 1982 public actions without
using public outcomes at inference. The result, even if 1982/1982, remains
SOURCE_ASSISTED PUBLIC-DEVELOPMENT transition evidence. It is not independent
generalization, a hidden Kaggle score, provider Output, or a competition
submission.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path
import public_ft09_compiled_observation_mechanism_234 as r234
import public_ft09_source_compiled_nonnode_noop_239 as r239
import public_ft09_source_compiled_animation_macrostep_242 as r242
RUNG=244; GAME='ft09-0d8bbf25'
def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name); return int(m.group(1)) if m else -1

def predict(before,action,manifest):
    levels=manifest['levels']
    pred,meta=r234.predict(before,action,levels)
    if pred is not None:return pred,meta,'r234'
    if meta.get('abstain')=='click_not_unique_node':
        p2,m2=r239.fill_nonnode_noop(before,action,levels)
        if p2 is not None:return p2,m2,'r239'
        if m2.get('abstain')=='level0_animation_click':
            return r242.paint_final(before,manifest['animation_macrostep']),{'branch':'compiled_animation_macrostep_final2','level':0},'r242'
        return None,m2,'none'
    if meta.get('abstain')=='non_mouse' and action.strip().upper()=='RESET':
        lev,ident=r234.identify_level(before,levels)
        if lev is None:return None,{'abstain':'reset_level_identification',**ident},'none'
        return r234.clone_board(lev['initial_frame']),{'branch':'explicit_reset_to_current_level_initial','level':int(lev['index'])},'r243'
    return None,meta,'none'

def evaluate(paths,manifest):
    tot=Counter();branches=Counter();stages=Counter();reasons=Counter();wrong=[];per=[]
    for p in sorted(paths,key=pnum):
        ev=r234.load_events(p);pre=None;s=Counter()
        for e in ev:
            if e.get('board') is None:continue
            if e.get('type')!='action':pre=e;continue
            if pre is None:pre=e;continue
            before=pre['board'];expected=e['board'];action=r234.action_name(e);tot['eligible']+=1;s['eligible']+=1
            pred,meta,stage=predict(before,action,manifest)
            if pred is None:
                tot['abstain']+=1;s['abstain']+=1;reasons[meta.get('abstain','unknown')]+=1;pre=e;continue
            ok=(pred[:-1]==expected[:-1]);tot['predictions']+=1;s['predictions']+=1;tot['correct' if ok else 'wrong']+=1;s['correct' if ok else 'wrong']+=1;branches[meta.get('branch','unknown')]+=1;stages[stage]+=1
            if not ok and len(wrong)<80:
                diff=sum(a!=b for ra,rb in zip(pred[:-1],expected[:-1]) for a,b in zip(ra,rb));wrong.append({'trace':p.name,'action':action,'stage':stage,'meta':meta,'diff_gameplay_cells':diff})
            pre=e
        per.append({'trace':p.name,**dict(s)})
    pp=tot['predictions'];ee=tot['eligible'];full=bool(ee==1982 and pp==ee and tot['wrong']==0 and tot['abstain']==0)
    return {'schema':'deus/arc3-ft09-source-compiled-full-transition-composer/1','rung':RUNG,'game':GAME,
      'aggregate':{**dict(tot),'accuracy':round(tot['correct']/pp,6) if pp else None,'coverage':round(pp/ee,6) if ee else 0.0},
      'stage_counts':dict(stages),'branch_counts':dict(branches),'abstain_reasons':dict(reasons),'wrong_examples':wrong,'per_trace':per,
      'full_public_source_assisted_transition_gate_pass':full,
      'decision':{'source_assisted_transition_expert_promotion':full,'solver_promotion':False,'independent_generalization_promotion':False,'kaggle_packaging':False,
                  'next_gate':'freeze R244 public source-assisted transition model; use it only as mechanism/verifier support. Independent rank promotion requires untouched/provider/Kaggle evidence.'},
      'truth':{'source_assisted_public_development':True,'public_outcomes_do_not_update_compiled_manifest':True,'source_removed_before_evaluation':True,
               'gameplay_rows0_62_exact_scoring':True,'independent_generalization_claim':False,'hidden_kaggle_score':False,'provider_runtime_claim':False,
               'competition_submission':False,'official_leaderboard_claim':False,'submission_quota_spent':False}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    d=evaluate(a.input,json.loads(a.manifest.read_text()));a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'aggregate':d['aggregate'],'stages':d['stage_counts'],'branches':d['branch_counts'],'abstain_reasons':d['abstain_reasons'],'full_gate':d['full_public_source_assisted_transition_gate_pass'],'wrong':d['wrong_examples']},sort_keys=True))
if __name__=='__main__':main()
# trigger after workflow registration
