#!/usr/bin/env python3
"""R242: source-compiled macro-step closure for FT09 level-0 animation.

R240 falsified the hypothesis that the public trace carries Ft09.self.our across
external actions.  The source branch that starts animation returns without
complete_action(); subsequent step() calls belong to the same in-flight action
until our reaches zero and complete_action() fires.  Therefore the correct
public transition abstraction is a macro-step closure, not a cross-action hidden
FSM.

For ONLY the R239 residual `level0_animation_click`, R242 compiles the level-0
Ycb sprite mask and source constants, then applies the complete internal closure:
our=4 -> 3(color0) -> 2(color2) -> 1(color0) -> 0(color2, complete_action).
Thus the externally completed gameplay frame has the Ycb non-transparent mask
painted final color 2 while all other gameplay cells are preserved.

R234/R239 retain precedence. No public outcome is consulted at inference.
Truth boundary remains source-assisted public-development evidence only.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_compiled_observation_mechanism_234 as r234
import public_ft09_source_compiled_nonnode_noop_239 as r239

RUNG=242
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name); return int(m.group(1)) if m else -1

def compile_animation(source:Path,base_manifest:Path,out:Path):
    m=json.loads(base_manifest.read_text()); mod=r234.load_source(source); g=mod.Ft09(); g.set_level(0); z=g.zth
    if z is None: raise RuntimeError('level0 Ycb missing')
    px=[[int(v) for v in row] for row in z.pixels.tolist()]
    m['animation_macrostep']={'level_index':0,'x':int(z.x),'y':int(z.y),'mask':[[1 if v>-1 else 0 for v in row] for row in px],
                              'start_count':4,'final_color':2,'internal_sequence':[0,2,0,2],
                              'completion_boundary':'same_external_action_until_complete_action'}
    m['schema']='deus/arc3-ft09-compiled-observation-plus-animation-macrostep/1'
    m['truth']['animation_macrostep_compiled_from_pinned_source']=True
    out.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'animation_macrostep':m['animation_macrostep'],'source':m['source']},sort_keys=True))

def paint_final(board,spec):
    out=r234.clone_board(board); x=int(spec['x']); y=int(spec['y']); color=int(spec['final_color'])
    for j,row in enumerate(spec['mask']):
        for i,on in enumerate(row):
            if not int(on): continue
            for dr in (0,1):
                for dc in (0,1):
                    rr=2*(y+j)+dr; cc=2*(x+i)+dc
                    if 0<=rr<64 and 0<=cc<64: out[rr][cc]=color
    return out

def evaluate(paths,manifest):
    levels=manifest['levels']; spec=manifest['animation_macrostep']; tot=Counter(); inc=Counter(); reasons=Counter(); branches=Counter(); wrong=[]; examples=[]
    for p in sorted(paths,key=pnum):
        ev=r234.load_events(p); pre=None
        for e in ev:
            if e.get('board') is None: continue
            if e.get('type')!='action': pre=e; continue
            if pre is None: pre=e; continue
            before=pre['board']; expected=e['board']; action=r234.action_name(e); tot['eligible']+=1
            pred,meta=r234.predict(before,action,levels); stage='r234'
            if pred is None and meta.get('abstain')=='click_not_unique_node':
                pred2,meta2=r239.fill_nonnode_noop(before,action,levels)
                if pred2 is not None: pred,meta,stage=pred2,meta2,'r239'
                elif meta2.get('abstain')=='level0_animation_click':
                    pred=paint_final(before,spec); meta={'branch':'compiled_animation_macrostep_final2','level':0}; stage='r242'
                else: pred,meta,stage=None,meta2,'none'
            if pred is None:
                tot['abstain']+=1; reasons[meta.get('abstain','unknown')]+=1; pre=e; continue
            ok=(pred[:-1]==expected[:-1]); tot['predictions']+=1; tot['correct' if ok else 'wrong']+=1; branches[meta.get('branch','unknown')]+=1
            if stage in ('r234','r239'):
                tot['anchor_predictions']+=1; tot['anchor_correct' if ok else 'anchor_wrong']+=1
            else:
                inc['predictions']+=1; inc['correct' if ok else 'wrong']+=1
                if len(examples)<80: examples.append({'trace':p.name,'action':action,'correct':ok})
            if not ok and len(wrong)<60:
                diff=sum(a!=b for ra,rb in zip(pred[:-1],expected[:-1]) for a,b in zip(ra,rb))
                wrong.append({'trace':p.name,'action':action,'stage':stage,'diff_gameplay_cells':diff})
            pre=e
    assert tot['anchor_predictions']==1827,dict(tot); assert tot['anchor_correct']==1827 and tot['anchor_wrong']==0,dict(tot)
    p=tot['predictions']; e=tot['eligible']; gate=bool(inc['predictions']>0 and inc['wrong']==0 and tot['wrong']==0)
    return {'schema':'deus/arc3-ft09-source-compiled-animation-macrostep/1','rung':RUNG,'game':GAME,
      'aggregate':{**dict(tot),'accuracy':round(tot['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0},
      'incremental':{'predictions':inc['predictions'],'correct':inc['correct'],'wrong':inc['wrong'],'examples':examples},
      'branches':dict(branches),'abstain_reasons':dict(reasons),'wrong_examples':wrong,
      'source_assisted_zero_wrong_gain_gate_pass':gate,
      'decision':{'source_assisted_transition_expert_promotion':gate,'solver_promotion':False,'independent_generalization_promotion':False,'kaggle_packaging':False,
                  'next_gate':'if zero-wrong, compose with any separately verified RESET gate; otherwise retain R239 and prove observable ambiguity before further animation repair'},
      'truth':{'r239_precedence_preserved':True,'macrostep_closes_before_next_external_action':True,'no_cross_action_hidden_state':True,
               'source_removed_before_evaluation':True,'public_outcomes_do_not_update_manifest':True,'gameplay_rows0_62_exact_scoring':True,
               'independent_generalization_claim':False,'hidden_kaggle_score':False,'competition_submission':False,'submission_quota_spent':False}}

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('compile'); c.add_argument('--source',type=Path,required=True); c.add_argument('--base-manifest',type=Path,required=True); c.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('evaluate'); e.add_argument('--manifest',type=Path,required=True); e.add_argument('--input',type=Path,action='append',default=[]); e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=='compile': compile_animation(a.source,a.base_manifest,a.output); return
    d=evaluate(a.input,json.loads(a.manifest.read_text())); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'aggregate':d['aggregate'],'incremental':{k:v for k,v in d['incremental'].items() if k!='examples'},'branches':d['branches'],'abstain_reasons':d['abstain_reasons'],'gate':d['source_assisted_zero_wrong_gain_gate_pass'],'wrong':d['wrong_examples']},sort_keys=True))
if __name__=='__main__': main()
