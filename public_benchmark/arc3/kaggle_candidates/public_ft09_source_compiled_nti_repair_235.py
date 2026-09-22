#!/usr/bin/env python3
"""R235: repair R234 source-compiled local mechanism with exact NTi neighborhood mask.

R234 falsifier:
- source-compiled, source-deleted evaluator was directionally correct;
- after incumbent R225 it added 596/602 correct on reused p10-p19, but 6 wrong;
- on p0-p9 its 3 candidate predictions were all wrong.
The omitted source mechanism is explicit: clicking an NTi tile constructs a
3x3 mask from visible logical pixels != 6 and cycles the corresponding
neighbor Hkx/NTi tiles at grid stride 4 (render stride 8). Hkx clicks use the
default center-only kernel.

R235 implements that operator from a static compiled spec + observation only.
The source file is not read/imported/executed during evaluation. This remains
source-assisted diagnostic evidence; no solver/Kaggle promotion is allowed.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_source_compiled_visible_local_234 as r234
import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_goal_manifold_veto_225 as r225

RUNG=235
GAME='ft09-0d8bbf25'
VISIBLE_PALETTE_VALUES=r234.VISIBLE_PALETTE_VALUES
RENDER_NEIGHBOR_STRIDE=8

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board): return [row[:] for row in board[:-1]]

def logical6_at(board,r0,c0):
    h=len(board)-1;w=len(board[0])
    if r0<0 or c0<0 or r0+5>=h or c0+5>=w:return None
    out=[]
    for j in range(3):
        row=[]
        for i in range(3):
            vals=[board[r0+2*j+dr][c0+2*i+dc] for dr in (0,1) for dc in (0,1)]
            if len(set(vals))!=1:return None
            row.append(int(vals[0]))
        out.append(row)
    return out

def tile_kind(logical):
    cur=int(logical[1][1]);vals={x for row in logical for x in row}
    if cur not in VISIBLE_PALETTE_VALUES:return None
    if vals=={cur}:return 'Hkx'
    if vals.issubset({cur,6}) and 6 in vals:return 'NTi'
    return None

def cycle_tile(out,r0,c0,palette):
    logical=logical6_at(out,r0,c0)
    if logical is None:return False
    kind=tile_kind(logical)
    if kind is None:return False
    cur=int(logical[1][1])
    if cur not in palette:return False
    nxt=int(palette[(palette.index(cur)+1)%len(palette)])
    changed=False
    for rr in range(r0,r0+6):
        for cc in range(c0,c0+6):
            if out[rr][cc]==cur:
                out[rr][cc]=nxt;changed=True
    return changed

def source_local_prediction(r,spec):
    r0,c0,r1,c1,_=r['bbox']
    if (r1-r0+1,c1-c0+1)!=(6,6):return None,'bbox_not_scaled3'
    logical=logical6_at(r['before'],r0,c0)
    if logical is None:return None,'clicked_not_uniform_scale2'
    kind=tile_kind(logical)
    if kind is None:return None,'clicked_not_hkx_nti_visual'
    current=int(logical[1][1])
    palette=r234.infer_palette(r['before'],spec,current)
    if palette is None:return None,'palette_ambiguous'

    out=[row[:] for row in r['before']]
    changed_tiles=0
    if kind=='Hkx':
        changed_tiles+=int(cycle_tile(out,r0,c0,palette))
    else:
        for j in range(3):
            for i in range(3):
                if logical[j][i]==6:
                    continue
                nr0=r0+(j-1)*RENDER_NEIGHBOR_STRIDE
                nc0=c0+(i-1)*RENDER_NEIGHBOR_STRIDE
                changed_tiles+=int(cycle_tile(out,nr0,nc0,palette))
    if changed_tiles==0:return None,'no_visible_neighbor_tile'
    return gp(out),f'source_{kind.lower()}_operator'

def evaluate(paths,spec,train):
    m=r221.build_models(train)
    s=Counter();reasons=Counter();branches=Counter();vetoes=Counter();added=[];wrong=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            pred,_=r221.r218_predict(r,lm,m)
            if pred is None:pred,_=r221.r219_predict(r,lm,m)
            if pred is None:pred,_,_=r225.r225_predict(r,lm,m)
            if pred is not None:
                s['incumbent_predictions']+=1;continue

            pred,branch=source_local_prediction(r,spec)
            if pred is None:
                reasons[branch]+=1;s['abstain']+=1;continue

            full=[row[:] for row in pred]+[r['before'][-1][:]]
            if lm is not None:
                ek=r217.goal_key(lm['level_before'],full)
                if ek in m['exact_goal']:
                    vetoes['exact_goal']+=1;s['abstain']+=1;continue
                sk=r218.structural_key(m['fam'],lm['level_before'],full)
                if sk in m['struct_goal']:
                    vetoes['struct_goal']+=1;s['abstain']+=1;continue

            ok=pred==gp(r['after'])
            s['candidate_predictions']+=1
            s['candidate_correct' if ok else 'candidate_wrong']+=1
            branches[branch]+=1
            if len(added)<100:
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'correct':ok})
            if not ok and len(wrong)<50:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch})
    cp=s['candidate_predictions'];cc=s['candidate_correct']
    return {**dict(s),'candidate_accuracy':round(cc/cp,6) if cp else None,
            'branch_counts':dict(branches),'veto_counts':dict(vetoes),
            'abstain_reasons':dict(reasons),'added_examples':added,'wrong_examples':wrong}

def run(paths,spec):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];dev=ps[10:]
    return {
      'schema':'deus/arc3-ft09-source-compiled-nti-repair-audit/1',
      'rung':RUNG,'game':GAME,
      'compiler':{'source_sha256':spec['source_sha256'],'source_commit':spec['source_commit'],'palettes':spec['palettes']},
      'p0_p9_source_assisted_validation':evaluate(train,spec,train),
      'p10_p19_reused_development_only':evaluate(dev,spec,train),
      'decision':{
        'nti_neighborhood_operator_compiled':True,
        'source_assisted_expert_promotion':False,'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'predeclare untouched source-runtime canary and verify compiled observation-only operator there before any source-assisted expert promotion',
      },
      'truth':{
        'compile_stage_ast_only':True,'evaluate_stage_does_not_read_or_execute_source':True,
        'observation_only_local_operator':True,'nti_mask_inferred_from_visible_pixels_only':True,
        'palette_inferred_from_visible_observation_only':True,
        'trace_level_metadata_not_used_for_local_transition':True,
        'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT',
        'independent_generalization_claim':False,'competition_execution':False,
        'competition_submission':False,'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('compile');c.add_argument('--source',type=Path,required=True);c.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('evaluate');e.add_argument('--spec',type=Path,required=True);e.add_argument('--input',type=Path,action='append',default=[]);e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=='compile':
        d=r234.compile_source(a.source);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'source_sha256':d['source_sha256'],'palettes':d['palettes'],'checks':d['semantic_checks']},sort_keys=True))
    else:
        spec=json.loads(a.spec.read_text());d=run(a.input,spec);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'train':d['p0_p9_source_assisted_validation'],'dev':d['p10_p19_reused_development_only'],'decision':d['decision']},sort_keys=True))
if __name__=='__main__':main()
