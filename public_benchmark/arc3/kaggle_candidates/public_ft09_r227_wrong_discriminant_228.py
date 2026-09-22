#!/usr/bin/env python3
"""R228: smallest-falsifier diagnostic for the four R227 heldout errors.

R227 deliberately failed promotion (342/346 correct, four wrong).  This rung
replays that frozen candidate and, only for those errors, compares pre-action
signatures against p0-p9 evidence.  It measures which added discriminants
(level, orientation-preserving ring2, position, score/progress) actually split
the error aliases before any new predictor is built.

Heldout outcomes are used only to identify/describe falsifiers.  No heldout
feature choice or model update occurs here; promotion is forbidden.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_low_confidence_goal_manifold_veto_225 as r225
import public_ft09_coarse_local_target_gate_227 as r227

RUNG=228; GAME='ft09-0d8bbf25'

def pnum(p:Path):
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1

def gp(b):return [x[:] for x in b[:-1]]
def pos(r):
    r0,c0,_,_,_=r['bbox'];return (r0//8,c0//8)

def mech(r,lm):
    if gp(r['before'])==gp(r['after']):return ('identity',None)
    if lm and lm['level_after']>lm['level_before']:return ('completion',None)
    if r227.is_local_only(r):return ('local',int(r['target']))
    return ('other',None)

def sigs(r,lm):
    cur,four,_=r['base'];lvl=int(lm['level_before']) if lm else -1;score=int(lm['score_before']) if lm else -1
    coarse=r227.feat('current_ring2hist',r,lm)
    return {
      'coarse':coarse,
      'coarse_level':(coarse,lvl),
      'coarse_pos':(coarse,pos(r)),
      'coarse_level_pos':(coarse,lvl,pos(r)),
      'exact_ring':(cur,tuple(r['ring2'])),
      'exact_ring_level':(cur,tuple(r['ring2']),lvl),
      'oriented_four_level':(cur,tuple(four),lvl),
      'coarse_level_score':(coarse,lvl,score),
      'level_pos':(lvl,pos(r)),
      'level_pos_current':(lvl,pos(r),cur),
    }

def training_index(paths):
    idx={name:defaultdict(Counter) for name in (
      'coarse','coarse_level','coarse_pos','coarse_level_pos','exact_ring','exact_ring_level',
      'oriented_four_level','coarse_level_score','level_pos','level_pos_current')}
    trace_support={name:defaultdict(lambda:defaultdict(set)) for name in idx}
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            lm=meta.get(r['step0']);lab=mech(r,lm)
            for name,k in sigs(r,lm).items():
                kk=repr(k);idx[name][kk][repr(lab)]+=1;trace_support[name][kk][repr(lab)].add(r['path'])
    return idx,trace_support

def compact(idx,ts,name,key):
    kk=repr(key);c=idx[name].get(kk,Counter());sup=ts[name].get(kk,{})
    return {'counts':dict(c),'trace_support':{k:len(v) for k,v in sup.items()}}

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    selected,cands=r227.select(ps[:5],ps[5:10])
    assert selected=='current_ring2hist|t2',selected
    tab,_=r227.fit(train,'current_ring2hist',2);m=r221.build_models(train)
    idx,ts=training_index(train);wrongs=[];s=Counter()
    for p in held:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            lm=meta.get(r['step0'])
            pred,_=r221.r218_predict(r,lm,m)
            if pred is None:pred,_=r221.r219_predict(r,lm,m)
            if pred is None:pred,_,_=r225.lowbase_goal_veto(r,lm,m)
            if pred is not None:continue
            tgt=tab.get(repr(r227.feat('current_ring2hist',r,lm)))
            if tgt is None:continue
            if r227.goal_veto(r,lm,tgt,m) is not None:continue
            pred=gp(r212.recolor_bbox(r['before'],r['bbox'],tgt))
            if pred==gp(r['after']):continue
            s['wrong']+=1
            sg=sigs(r,lm)
            wrongs.append({
              'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],
              'predicted_target':tgt,'actual_target':int(r['target']),
              'actual_mechanism':mech(r,lm),'level_before':lm['level_before'] if lm else None,
              'level_after':lm['level_after'] if lm else None,'score_before':lm['score_before'] if lm else None,
              'bbox_pos':pos(r),'current':r['current'],'four':list(r['base'][1]),'ring2':list(r['ring2']),
              'training_matches':{name:compact(idx,ts,name,key) for name,key in sg.items()},
            })
    assert s['wrong']==4,dict(s)
    return {'schema':'deus/arc3-ft09-r227-wrong-discriminant/1','rung':RUNG,'game':GAME,
      'frozen_r227':{'selected':selected,'expected_wrong':4},'wrong_falsifiers':wrongs,
      'promotion':{'diagnostic_only':True,'solver_promotion':False,'coverage_expert_promotion':False,'kaggle_packaging':False,
                   'next_gate':'choose one discriminant grounded by p0-p9 match tables; freeze separate candidate before new heldout evaluation'},
      'truth':{'public_trace_only':True,'p0_p9_is_only_evidence_database':True,
               'heldout_used_only_to_identify_and_describe_r227_falsifiers':True,
               'heldout_updates_model':False,'predictor_selected_here':False,
               'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'frozen':d['frozen_r227'],'wrongs':d['wrong_falsifiers'],'promotion':d['promotion']},sort_keys=True))
if __name__=='__main__':main()
