#!/usr/bin/env python3
"""R236: observation-only palette inference repair for compiled FT09 mechanism.

R235 falsified NTi as the cause of the remaining source-compiled errors: all
R234/R235 residual errors were Hkx-branch predictions. The remaining ambiguity
is palette identity.

The public source shows bsT target sprites encode a target color at their center
while their other logical pixels are from {0,2,3}. This is visible in the board.
R236 infers the active palette from these visible target-shape center colors,
plus Hkx/NTi dynamic centers as fallback. It never uses trace level metadata.

Compile stage is AST-only; evaluator runs after source deletion. Reused p10-p19
is diagnostic only and cannot promote a solver.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_source_compiled_visible_local_234 as r234
import public_ft09_source_compiled_nti_repair_235 as r235
import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_goal_manifold_veto_225 as r225

RUNG=236
GAME='ft09-0d8bbf25'
VISIBLE_PALETTE_VALUES=r234.VISIBLE_PALETTE_VALUES

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board): return [row[:] for row in board[:-1]]

def palette_evidence(board):
    h=len(board)-1;w=len(board[0])
    target=Counter();dynamic=Counter()
    for r0 in range(0,h-5,2):
        for c0 in range(0,w-5,2):
            logical=r235.logical6_at(board,r0,c0)
            if logical is None:continue
            cur=int(logical[1][1])
            if cur not in VISIBLE_PALETTE_VALUES:continue
            vals={int(x) for row in logical for x in row}
            if vals=={cur} or (vals.issubset({cur,6}) and 6 in vals):
                dynamic[cur]+=1
            elif vals.issubset({0,2,3,cur}) and bool(vals.intersection({0,2,3})):
                target[cur]+=1
    return target,dynamic

def infer_palette_v2(board,spec,current):
    target,dynamic=palette_evidence(board)
    evidence=set(target)
    source='target_shapes'
    if not evidence:
        evidence=set(dynamic);source='dynamic_fallback'
    candidates=[]
    for p0 in spec['palettes']:
        p=tuple(int(x) for x in p0)
        if current not in p:continue
        ps=set(p)
        outside=len(evidence-ps)
        missing=len(ps-evidence)
        target_support=sum(target[x] for x in ps)
        dyn_support=sum(dynamic[x] for x in ps)
        candidates.append(((outside,missing,-target_support,-dyn_support,len(p)),p))
    if not candidates:return None,{'source':source,'target':dict(target),'dynamic':dict(dynamic),'reason':'no_candidate'}
    candidates.sort(key=lambda x:x[0])
    if len(candidates)>1 and candidates[0][0]==candidates[1][0]:
        return None,{'source':source,'target':dict(target),'dynamic':dict(dynamic),'reason':'score_tie'}
    best=candidates[0]
    if best[0][0]>0:
        return None,{'source':source,'target':dict(target),'dynamic':dict(dynamic),'reason':'evidence_outside'}
    return best[1],{'source':source,'target':dict(target),'dynamic':dict(dynamic),'score':list(best[0])}

def source_prediction(r,spec):
    r0,c0,r1,c1,_=r['bbox']
    if (r1-r0+1,c1-c0+1)!=(6,6):return None,'bbox_not_scaled3',None
    logical=r235.logical6_at(r['before'],r0,c0)
    if logical is None:return None,'clicked_not_uniform_scale2',None
    kind=r235.tile_kind(logical)
    if kind is None:return None,'clicked_not_hkx_nti_visual',None
    current=int(logical[1][1])
    palette,diag=infer_palette_v2(r['before'],spec,current)
    if palette is None:return None,'palette_ambiguous_v2',diag
    out=[row[:] for row in r['before']]
    changed=0
    if kind=='Hkx':
        changed+=int(r235.cycle_tile(out,r0,c0,palette))
    else:
        for j in range(3):
            for i in range(3):
                if logical[j][i]==6:continue
                changed+=int(r235.cycle_tile(out,r0+(j-1)*8,c0+(i-1)*8,palette))
    if changed==0:return None,'no_visible_neighbor_tile',diag
    return gp(out),f'source_{kind.lower()}_palette_v2',diag

def evaluate(paths,spec,train):
    m=r221.build_models(train)
    s=Counter();reasons=Counter();branches=Counter();vetoes=Counter()
    added=[];wrong=[];palette_diags=[]
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
            pred,branch,diag=source_prediction(r,spec)
            if pred is None:
                reasons[branch]+=1;s['abstain']+=1
                if len(palette_diags)<30 and diag is not None:
                    palette_diags.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'diag':diag})
                continue
            full=[row[:] for row in pred]+[r['before'][-1][:]]
            if lm is not None:
                ek=r217.goal_key(lm['level_before'],full)
                if ek in m['exact_goal']:
                    vetoes['exact_goal']+=1;s['abstain']+=1;continue
                sk=r218.structural_key(m['fam'],lm['level_before'],full)
                if sk in m['struct_goal']:
                    vetoes['struct_goal']+=1;s['abstain']+=1;continue
            ok=pred==gp(r['after'])
            s['candidate_predictions']+=1;s['candidate_correct' if ok else 'candidate_wrong']+=1
            branches[branch]+=1
            if len(added)<100:
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'correct':ok,'palette_diag':diag})
            if not ok and len(wrong)<50:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'palette_diag':diag})
    cp=s['candidate_predictions'];cc=s['candidate_correct']
    return {**dict(s),'candidate_accuracy':round(cc/cp,6) if cp else None,
      'branch_counts':dict(branches),'veto_counts':dict(vetoes),'abstain_reasons':dict(reasons),
      'palette_diagnostics':palette_diags,'added_examples':added,'wrong_examples':wrong}

def run(paths,spec):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];dev=ps[10:]
    return {
      'schema':'deus/arc3-ft09-source-compiled-palette-repair-audit/1','rung':RUNG,'game':GAME,
      'compiler':{'source_sha256':spec['source_sha256'],'source_commit':spec['source_commit'],'palettes':spec['palettes']},
      'p0_p9_source_assisted_validation':evaluate(train,spec,train),
      'p10_p19_reused_development_only':evaluate(dev,spec,train),
      'decision':{'palette_observation_repair_compiled':True,'source_assisted_expert_promotion':False,
        'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'if source-assisted validation is zero-wrong, freeze mechanism spec and predeclare an untouched source-runtime canary; otherwise classify remaining observation/source mismatch'},
      'truth':{'compile_stage_ast_only':True,'evaluate_stage_does_not_read_or_execute_source':True,
        'palette_inferred_from_visible_target_and_dynamic_shapes_only':True,
        'trace_level_metadata_not_used_for_palette_or_local_transition':True,
        'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT',
        'independent_generalization_claim':False,'competition_execution':False,
        'competition_submission':False,'submission_quota_spent':False,'owner_score_claim':False}
    }

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('compile');c.add_argument('--source',type=Path,required=True);c.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('evaluate');e.add_argument('--spec',type=Path,required=True);e.add_argument('--input',type=Path,action='append',default=[]);e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=='compile':
        d=r234.compile_source(a.source);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'source_sha256':d['source_sha256'],'palettes':d['palettes']},sort_keys=True))
    else:
        spec=json.loads(a.spec.read_text());d=run(a.input,spec);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'train':d['p0_p9_source_assisted_validation'],'dev':d['p10_p19_reused_development_only'],'decision':d['decision']},sort_keys=True))
if __name__=='__main__':main()
