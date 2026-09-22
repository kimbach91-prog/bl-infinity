#!/usr/bin/env python3
"""R240: source-compiled temporal FSM for FT09 level-0 animation.

R239 raises the source-assisted public transition expert from 1762 to 1827 exact
predictions (0 wrong) and leaves 136 level0_animation_click + 19 non_mouse
abstentions.  The pinned MIT source shows that the level-0 Ycb animation has a
four-action hidden countdown: a non-node/non-clue mouse click starts our=4
without changing the visible frame; each subsequent mouse action decrements
`our` and recolors the non-transparent Ycb pixels to 0/2 alternately.

R240 compiles only the static Ycb mask/position and constants at build time,
deletes the source, then runs a stateful deterministic FSM over each trace.
R234/R239 remain precedence anchors whenever the FSM is idle.  Non-mouse actions
remain fail-closed because source action-id 0 has separate semantics and the
string parser intentionally does not infer protected/internal action ids.

Truth boundary: source-assisted public-development transition evidence only.
Not independent generalization, hidden Kaggle score, provider execution, or a
competition submission.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path

import public_ft09_compiled_observation_mechanism_234 as r234
import public_ft09_source_compiled_nonnode_noop_239 as r239

RUNG=240
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def compile_animation(source:Path, base_manifest:Path, output:Path):
    manifest=json.loads(base_manifest.read_text())
    mod=r234.load_source(source)
    game=mod.Ft09(); game.set_level(0)
    z=game.zth
    if z is None: raise RuntimeError('level0 Ycb animation sprite missing')
    px=[[int(v) for v in row] for row in z.pixels.tolist()]
    manifest['animation_fsm']={
      'level_index':0,'x':int(z.x),'y':int(z.y),
      'mask':[[1 if v>-1 else 0 for v in row] for row in px],
      'start_count':4,'odd_color':0,'even_color':2,
      'source_semantics':'our=4 on idle nonnode/nonclue mouse click; mouse ticks decrement then recolor; action-id0 excluded',
    }
    manifest['schema']='deus/arc3-ft09-compiled-observation-mechanism-plus-animation/1'
    manifest['truth']['animation_fsm_compiled_from_pinned_source']=True
    output.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'animation_fsm':manifest['animation_fsm'],'source':manifest['source']},sort_keys=True))

def paint_animation(board, spec, color):
    out=r234.clone_board(board)
    x=int(spec['x']); y=int(spec['y']); mask=spec['mask']
    for j,row in enumerate(mask):
        for i,on in enumerate(row):
            if not int(on): continue
            for dr in (0,1):
                for dc in (0,1):
                    rr=2*(y+j)+dr; cc=2*(x+i)+dc
                    if 0<=rr<64 and 0<=cc<64: out[rr][cc]=int(color)
    return out

def evaluate(paths,manifest):
    levels=manifest['levels']; anim=manifest['animation_fsm']
    tot=Counter(); branches=Counter(); reasons=Counter(); inc=Counter(); wrong=[]; examples=[]; nonmouse=Counter(); per=[]
    for p in sorted(paths,key=pnum):
        ev=r234.load_events(p); pre=None; our=0; s=Counter()
        for e in ev:
            if e.get('board') is None: continue
            if e.get('type')!='action': pre=e; continue
            if pre is None: pre=e; continue
            before=pre['board']; expected=e['board']; action=r234.action_name(e)
            tot['eligible']+=1; s['eligible']+=1
            lev,ident=r234.identify_level(before,levels)
            if lev is None:
                pred=None; meta={'abstain':'level_identification',**ident}; stage='none'
            else:
                li=int(lev['index'])
                if li!=0: our=0
                mc=r234.parse_mouse(action)
                if mc is None:
                    # Source checks action id 0 before the animation countdown.
                    # We do not infer action ids from arbitrary display strings.
                    pred=None; meta={'abstain':'non_mouse','level':li,'our':our}; stage='none'; nonmouse[action]+=1
                elif li==0 and our>0:
                    our-=1
                    color=int(anim['odd_color'] if our%2==1 else anim['even_color'])
                    pred=paint_animation(before,anim,color)
                    meta={'level':0,'branch':'compiled_animation_tick','our_after':our,'color':color}
                    stage='r240'
                else:
                    pred,meta=r234.predict(before,action,levels); stage='r234'
                    if pred is None and meta.get('abstain')=='click_not_unique_node':
                        pred2,meta2=r239.fill_nonnode_noop(before,action,levels)
                        if pred2 is not None:
                            pred,meta,stage=pred2,meta2,'r239'
                        elif meta2.get('abstain')=='level0_animation_click' and li==0:
                            # Idle source branch sets our=4 and returns before any
                            # visible mutation. The start action itself is exact no-op.
                            pred=r234.clone_board(before); our=int(anim['start_count'])
                            meta={'level':0,'branch':'compiled_animation_start','our_after':our}
                            stage='r240'
                        else:
                            pred,meta,stage=None,meta2,'none'
            if pred is None:
                tot['abstain']+=1; s['abstain']+=1; reasons[meta.get('abstain','unknown')]+=1; pre=e; continue
            ok=(pred[:-1]==expected[:-1])
            tot['predictions']+=1; s['predictions']+=1; tot['correct' if ok else 'wrong']+=1; s['correct' if ok else 'wrong']+=1
            branches[meta.get('branch','unknown')]+=1
            if stage in ('r234','r239'):
                tot['anchor_predictions']+=1; tot['anchor_correct' if ok else 'anchor_wrong']+=1
            else:
                inc['predictions']+=1; inc['correct' if ok else 'wrong']+=1
                if len(examples)<100: examples.append({'trace':p.name,'action':action,'branch':meta.get('branch'),'correct':ok,'meta':meta})
            if not ok and len(wrong)<60:
                diff=sum(a!=b for ra,rb in zip(pred[:-1],expected[:-1]) for a,b in zip(ra,rb))
                wrong.append({'trace':p.name,'action':action,'stage':stage,'meta':meta,'diff_gameplay_cells':diff})
            pre=e
        per.append({'trace':p.name,**dict(s),'fsm_our_end':our})
    p=tot['predictions']; e=tot['eligible']; cc=inc['correct']; cp=inc['predictions']; cw=inc['wrong']
    aggregate={**dict(tot),'accuracy':round(tot['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    gate=bool(cp>0 and cw==0 and tot['wrong']==0 and tot['anchor_wrong']==0)
    return {
      'schema':'deus/arc3-ft09-source-compiled-animation-fsm/1','rung':RUNG,'game':GAME,
      'aggregate':aggregate,'branches':dict(branches),'abstain_reasons':dict(reasons),
      'incremental':{'predictions':cp,'correct':cc,'wrong':cw,'examples':examples},
      'non_mouse_action_names':dict(nonmouse),'per_trace':per,'wrong_examples':wrong,
      'source_assisted_zero_wrong_gain_gate_pass':gate,
      'decision':{
        'source_assisted_transition_expert_promotion':gate,'solver_promotion':False,
        'independent_generalization_promotion':False,'kaggle_packaging':False,
        'next_gate':'if zero-wrong, freeze R240 and inspect only non_mouse residual semantics; otherwise retain R239 and diagnose the first FSM mismatch',
      },
      'truth':{
        'public_source_assisted_manifest':True,'r234_r239_precedence_when_idle':True,
        'temporal_state_initialized_per_trace':True,'animation_source_removed_before_evaluation':True,
        'non_mouse_actions_fail_closed':True,'gameplay_rows0_62_exact_scoring':True,
        'independent_generalization_claim':False,'hidden_kaggle_score':False,
        'competition_submission':False,'submission_quota_spent':False,
      },
    }

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('compile'); c.add_argument('--source',type=Path,required=True); c.add_argument('--base-manifest',type=Path,required=True); c.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('evaluate'); e.add_argument('--manifest',type=Path,required=True); e.add_argument('--input',type=Path,action='append',default=[]); e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=='compile': compile_animation(a.source,a.base_manifest,a.output); return
    d=evaluate(a.input,json.loads(a.manifest.read_text())); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'aggregate':d['aggregate'],'incremental':{k:v for k,v in d['incremental'].items() if k!='examples'},'branches':d['branches'],'abstain_reasons':d['abstain_reasons'],'non_mouse_action_names':d['non_mouse_action_names'],'gate':d['source_assisted_zero_wrong_gain_gate_pass'],'wrong':d['wrong_examples']},sort_keys=True))
if __name__=='__main__': main()
