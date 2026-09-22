#!/usr/bin/env python3
"""R234: compile public FT09 source into an observation-only local mechanism.

Two-stage truth boundary:
  compile  : AST-parse pinned MIT source -> static JSON spec.
  evaluate : receives ONLY the compiled JSON spec + observations/traces.
             The source file is not imported/executed/read at inference.

The compiled mechanism implements only the source-grounded local click operator:
  - visible Hkx tile: all palette-colored pixels cycle to next palette color;
  - visible NTi tile: pixels with value 6 are fixed, all other current-color
    pixels cycle to the next palette color;
  - palette is inferred from visible tile-center colors, not trace level metadata;
  - source-derived goal manifolds are NOT rendered here; existing p0-p9 learned
    goal-manifold veto blocks candidate local predictions that would enter a
    known completion manifold.

R234 is diagnostic/source-assisted only. Reused p10-p19 metrics cannot promote.
"""
from __future__ import annotations
import argparse,ast,hashlib,json,re
from collections import Counter
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_goal_manifold_veto_225 as r225

RUNG=234
GAME='ft09-0d8bbf25'
VISIBLE_PALETTE_VALUES={8,9,11,12,14,15}

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def compile_source(source:Path)->dict:
    raw=source.read_bytes()
    tree=ast.parse(raw.decode())
    levels_node=None;step_node=None;cgj_node=None
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='levels' for t in n.targets):
            levels_node=n.value
        if isinstance(n,ast.ClassDef) and n.name=='Ft09':
            for m in n.body:
                if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef)) and m.name=='step': step_node=m
                if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef)) and m.name=='cgj': cgj_node=m
    if not isinstance(levels_node,ast.List) or step_node is None or cgj_node is None:
        raise ValueError('expected levels list and Ft09.step/cgj')

    levels=[]
    for i,node in enumerate(levels_node.elts):
        if not isinstance(node,ast.Call): continue
        kw={k.arg:k.value for k in node.keywords if k.arg}
        data=ast.literal_eval(kw['data'])
        name=ast.literal_eval(kw['name'])
        levels.append({
          'index':i,'name':name,
          'timer_max':int(data.get('kCv') or 0),
          'palette':[int(x) for x in data.get('cwU') or []],
          'click_kernel':data.get('elp'),
        })

    step_text=ast.unparse(step_node)
    cgj_text=ast.unparse(cgj_node)
    checks={
      'mouse_action6':"self.action.id.value == 6" in step_text,
      'tile_hkx':"'Hkx'" in step_text,
      'tile_nti':"'NTi'" in step_text,
      'palette_index_cycle':"self.gqb.index" in step_text and "% len(self.gqb)" in step_text,
      'completion_call':"self.cgj()" in step_text,
      'completion_bsT':"'bsT'" in cgj_text or "self.gig" in cgj_text,
      'completion_neighbor_stride4':cgj_text.count('4')>=8,
    }
    if not all(checks.values()):
        raise ValueError({'semantic_checks':checks})

    palettes=[]
    for lv in levels:
        p=tuple(lv['palette'])
        if p and p not in palettes: palettes.append(p)
    spec={
      'schema':'deus/arc3-ft09-observation-mechanism-spec/1',
      'source_sha256':hashlib.sha256(raw).hexdigest(),
      'source_commit':'41b87fe1ea8d9819a44eea35172ffe28d6c5ffe6',
      'levels':levels,
      'palettes':[list(p) for p in palettes],
      'local_operator':{
        'tile_logical_size':[3,3],
        'render_scale':2,
        'fixed_nti_value':6,
        'cycle':'replace pixels equal to current center color with next palette color',
        'visible_hkx_rule':'logical 3x3 all current color',
        'visible_nti_rule':'logical 3x3 values subset of {current,6}',
      },
      'semantic_checks':checks,
      'truth':{
        'source_ast_parsed_not_imported':True,
        'compiled_spec_static':True,
        'source_runtime_not_required_by_evaluator':True,
      },
    }
    return spec

def downsample6(board,bb):
    r0,c0,r1,c1,_=bb
    if (r1-r0+1,c1-c0+1)!=(6,6): return None
    out=[]
    for j in range(3):
        row=[]
        for i in range(3):
            vals=[board[r0+2*j+dr][c0+2*i+dc] for dr in (0,1) for dc in (0,1)]
            if len(set(vals))!=1: return None
            row.append(vals[0])
        out.append(row)
    return out

def visible_tile_centers(board):
    h=len(board)-1;w=len(board[0]);counts=Counter()
    for r0 in range(0,h-5,2):
        for c0 in range(0,w-5,2):
            logical=[]
            ok=True
            for j in range(3):
                row=[]
                for i in range(3):
                    vals=[board[r0+2*j+dr][c0+2*i+dc] for dr in (0,1) for dc in (0,1)]
                    if len(set(vals))!=1:
                        ok=False;break
                    row.append(vals[0])
                if not ok:break
                logical.append(row)
            if not ok: continue
            cur=logical[1][1]
            if cur not in VISIBLE_PALETTE_VALUES: continue
            vals={x for row in logical for x in row}
            if vals.issubset({cur,6}):
                counts[int(cur)]+=1
    return counts

def infer_palette(board,spec,current):
    seen=set(visible_tile_centers(board))
    cands=[]
    for p0 in spec['palettes']:
        p=tuple(int(x) for x in p0)
        if current not in p: continue
        overlap=len(seen.intersection(p))
        outside=len(seen.difference(p))
        missing=len(set(p).difference(seen))
        cands.append(((outside,-overlap,missing,len(p)),p))
    if not cands:return None
    cands.sort(key=lambda x:x[0])
    if len(cands)>1 and cands[0][0]==cands[1][0]:
        return None
    if cands[0][0][0]>0:
        return None
    return cands[0][1]

def local_source_prediction(r,spec):
    logical=downsample6(r['before'],r['bbox'])
    if logical is None:return None,'bbox_not_scaled3'
    current=int(logical[1][1])
    if current not in VISIBLE_PALETTE_VALUES:return None,'center_not_palette'
    vals={int(x) for row in logical for x in row}
    if not vals.issubset({current,6}):return None,'clicked_not_hkx_nti_visual'
    palette=infer_palette(r['before'],spec,current)
    if palette is None:return None,'palette_ambiguous'
    nxt=palette[(palette.index(current)+1)%len(palette)]
    out=[row[:] for row in r['before']]
    r0,c0,r1,c1,_=r['bbox']
    changed=0
    for rr in range(r0,r1+1):
        for cc in range(c0,c1+1):
            if out[rr][cc]==current:
                out[rr][cc]=nxt;changed+=1
    if changed==0:return None,'no_current_pixels'
    return gp(out),'source_local_visible'

def evaluate(paths,spec,train):
    m=r221.build_models(train)
    s=Counter();reasons=Counter();added=[];wrong=[];vetoes=Counter()
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            pred,_=r221.r218_predict(r,lm,m)
            if pred is None: pred,_=r221.r219_predict(r,lm,m)
            if pred is None: pred,_,_=r225.r225_predict(r,lm,m)
            if pred is not None:
                s['incumbent_predictions']+=1
                continue
            pred,reason=local_source_prediction(r,spec)
            if pred is None:
                reasons[reason]+=1;s['abstain']+=1;continue

            # preserve p0-p9 learned goal-manifold veto
            virtual=[row[:] for row in pred]
            # r217/r218 key helpers expect full board; restore HUD from before
            full=virtual+[r['before'][-1][:]]
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
            if len(added)<80:
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'correct':ok})
            if not ok and len(wrong)<40:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action']})
    cp=s['candidate_predictions'];cc=s['candidate_correct'];cw=s['candidate_wrong']
    return {
      **dict(s),
      'candidate_accuracy':round(cc/cp,6) if cp else None,
      'veto_counts':dict(vetoes),
      'abstain_reasons':dict(reasons),
      'added_examples':added,'wrong_examples':wrong,
    }

def run(paths,spec):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];dev=ps[10:]
    tr=evaluate(train,spec,train)
    dv=evaluate(dev,spec,train)
    return {
      'schema':'deus/arc3-ft09-source-compiled-visible-local-audit/1',
      'rung':RUNG,'game':GAME,
      'compiler':{
        'source_sha256':spec['source_sha256'],
        'source_commit':spec['source_commit'],
        'palettes':spec['palettes'],
        'semantic_checks':spec['semantic_checks'],
      },
      'p0_p9_source_assisted_validation':tr,
      'p10_p19_reused_development_only':dv,
      'decision':{
        'source_mechanism_compiled':True,
        'source_assisted_expert_promotion':False,
        'solver_promotion':False,
        'kaggle_packaging':False,
        'next_gate':'predeclared source-runtime canary for compiled local operator plus visible-level/palette ambiguity audit before any source-assisted expert promotion',
      },
      'truth':{
        'compile_stage_ast_only':True,
        'evaluate_stage_does_not_read_or_execute_source':True,
        'observation_only_local_operator':True,
        'trace_level_metadata_not_used_for_palette_or_local_transition':True,
        'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT',
        'independent_generalization_claim':False,
        'competition_execution':False,'competition_submission':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('compile');c.add_argument('--source',type=Path,required=True);c.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('evaluate');e.add_argument('--spec',type=Path,required=True);e.add_argument('--input',type=Path,action='append',default=[]);e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=='compile':
        d=compile_source(a.source);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'schema':d['schema'],'source_sha256':d['source_sha256'],'palettes':d['palettes'],'checks':d['semantic_checks']},sort_keys=True))
    else:
        spec=json.loads(a.spec.read_text());d=run(a.input,spec);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'train':d['p0_p9_source_assisted_validation'],'dev':d['p10_p19_reused_development_only'],'decision':d['decision']},sort_keys=True))
if __name__=='__main__':main()
