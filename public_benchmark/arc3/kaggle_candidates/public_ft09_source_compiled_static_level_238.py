#!/usr/bin/env python3
"""R238: static-template level resolver + dynamic-position gate for FT09.

R237 falsifier showed six residual errors were attached to a weak resolver:
visually tile-like aliases made THR's 8 dynamic positions appear as a subset of
an observation containing 32 tile-like 6x6 blocks.

R238 compiles from pinned public source:
- exact small static sprite templates and positions per level,
- exact Hkx/NTi dynamic positions per level,
- each level palette.

At inference the source file is absent. Level is resolved from immutable visible
static templates, not trace level metadata. A click is modeled only when its
6x6 bbox top-left is one of the compiled Hkx/NTi positions for that resolved
level. This prevents static/target sprites that merely look tile-like from being
treated as dynamic Hkx.

Reused p10-p19 remains diagnostic only; no solver promotion.
"""
from __future__ import annotations
import argparse,ast,hashlib,json,re
from collections import Counter
from pathlib import Path

import public_ft09_source_compiled_nti_repair_235 as r235
import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_goal_manifold_veto_225 as r225

RUNG=238
GAME='ft09-0d8bbf25'
SCALE=2

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):return [row[:] for row in board[:-1]]

def _lit(n):return ast.literal_eval(n)

def _sprite_ref(node):
    cur=node
    while isinstance(cur,ast.Call) and isinstance(cur.func,ast.Attribute):
        cur=cur.func.value
    if isinstance(cur,ast.Subscript) and isinstance(cur.value,ast.Name) and cur.value.id=='sprites':
        try:return str(ast.literal_eval(cur.slice))
        except Exception:return None
    return None

def _position(node):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='set_position':
        if len(node.args)>=2:
            try:return (int(_lit(node.args[0])),int(_lit(node.args[1])))
            except Exception:return None
    return (0,0) if _sprite_ref(node) is not None else None

def compile_source(source:Path):
    raw=source.read_bytes();tree=ast.parse(raw.decode())
    sn=ln=None
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sprites' for t in n.targets):sn=n.value
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='levels' for t in n.targets):ln=n.value
    if not isinstance(sn,ast.Dict) or not isinstance(ln,ast.List):raise ValueError('source shape')

    sprites={}
    for k,v in zip(sn.keys,sn.values):
        if k is None or not isinstance(v,ast.Call):continue
        name=str(_lit(k));kw={x.arg:x.value for x in v.keywords if x.arg}
        if 'pixels' not in kw:continue
        pixels=_lit(kw['pixels'])
        tags=list(_lit(kw['tags'])) if 'tags' in kw else []
        sprites[name]={'pixels':pixels,'tags':tags}

    levels=[]
    for idx,node in enumerate(ln.elts):
        if not isinstance(node,ast.Call):continue
        kw={x.arg:x.value for x in node.keywords if x.arg}
        data=dict(_lit(kw['data']));name=str(_lit(kw['name']))
        dyn=[];static=[]
        lst=kw.get('sprites')
        for elt in lst.elts if isinstance(lst,ast.List) else []:
            ref=_sprite_ref(elt);pos=_position(elt)
            if ref is None or pos is None or ref not in sprites:continue
            sp=sprites[ref];tags=set(sp['tags']);x,y=pos
            ent={'sprite':ref,'source_xy':[x,y],'render_top_left_rc':[y*SCALE,x*SCALE],
                 'pixels':sp['pixels'],'tags':sorted(tags)}
            if 'Hkx' in tags or 'NTi' in tags or ref in ('Hkx','NTi'):
                ent['kind']='NTi' if ('NTi' in tags or ref=='NTi') else 'Hkx';dyn.append(ent)
            else:
                h=len(sp['pixels']);w=max((len(row) for row in sp['pixels']),default=0)
                nontrans=sum(1 for row in sp['pixels'] for val in row if int(val)!=-1)
                # Keep small, immutable visual anchors. Exclude known animation tag.
                if h<=5 and w<=5 and 1<=nontrans<=25 and 'Ycb' not in tags:
                    ent['nontransparent']=nontrans;static.append(ent)
        levels.append({'index':idx,'name':name,'palette':[int(x) for x in data.get('cwU') or []],
                       'dynamic_tiles':dyn,'static_anchors':static})
    if len(levels)!=6:raise ValueError('expected6')
    return {'schema':'deus/arc3-ft09-static-template-level-spec/1',
            'source_sha256':hashlib.sha256(raw).hexdigest(),
            'source_commit':'41b87fe1ea8d9819a44eea35172ffe28d6c5ffe6',
            'scale':SCALE,'levels':levels,
            'truth':{'source_ast_parsed_not_imported':True,'compiled_spec_static':True,
                     'level_resolution_observation_static_templates_only':True}}

def template_score(board,anchor):
    r0,c0=map(int,anchor['render_top_left_rc']);pix=anchor['pixels']
    h=len(board)-1;w=len(board[0]);matched=0;total=0
    for j,row in enumerate(pix):
        for i,val0 in enumerate(row):
            val=int(val0)
            if val==-1:continue
            for dr in range(SCALE):
                for dc in range(SCALE):
                    rr=r0+j*SCALE+dr;cc=c0+i*SCALE+dc
                    total+=1
                    if 0<=rr<h and 0<=cc<w and int(board[rr][cc])==val:matched+=1
    return matched,total

def resolve_level(board,spec):
    scored=[]
    for lv in spec['levels']:
        exact=0;matched=0;total=0;used=0
        for a in lv['static_anchors']:
            m,t=template_score(board,a)
            if t==0:continue
            used+=1;matched+=m;total+=t
            if m==t:exact+=1
        ratio=matched/total if total else 0.0
        scored.append(((-exact,-ratio,-matched,used),lv,{'exact':exact,'ratio':round(ratio,6),'matched':matched,'total':total,'anchors':used}))
    scored.sort(key=lambda x:x[0])
    best=scored[0]
    if best[2]['exact']==0:return None,{'reason':'no_exact_anchor','scores':[(x[1]['index'],x[2]) for x in scored]}
    if len(scored)>1 and scored[0][0]==scored[1][0]:return None,{'reason':'score_tie','scores':[(x[1]['index'],x[2]) for x in scored[:3]]}
    return best[1],{'level_index':best[1]['index'],'level_name':best[1]['name'],**best[2]}

def source_prediction(r,spec):
    lv,diag=resolve_level(r['before'],spec)
    if lv is None:return None,'level_static_ambiguous',diag
    r0,c0,r1,c1,_=r['bbox']
    dyn={(int(x['render_top_left_rc'][0]),int(x['render_top_left_rc'][1])):x['kind'] for x in lv['dynamic_tiles']}
    if (r0,c0) not in dyn:return None,'clicked_not_compiled_dynamic_position',diag
    logical=r235.logical6_at(r['before'],r0,c0)
    if logical is None:return None,'clicked_not_uniform_scale2',diag
    kind=dyn[(r0,c0)]
    palette=tuple(int(x) for x in lv['palette']);cur=int(logical[1][1])
    if cur not in palette:return None,'dynamic_center_not_palette',diag
    out=[row[:] for row in r['before']];changed=0
    if kind=='Hkx':
        changed+=int(r235.cycle_tile(out,r0,c0,palette))
    else:
        for j in range(3):
            for i in range(3):
                if logical[j][i]==6:continue
                changed+=int(r235.cycle_tile(out,r0+(j-1)*8,c0+(i-1)*8,palette))
    if changed==0:return None,'no_dynamic_effect',diag
    return gp(out),f'source_{kind.lower()}_static_level',diag

def evaluate(paths,spec,train):
    m=r221.build_models(train)
    s=Counter();reasons=Counter();branches=Counter();vetoes=Counter();added=[];wrong=[];diags=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            pred,_=r221.r218_predict(r,lm,m)
            if pred is None:pred,_=r221.r219_predict(r,lm,m)
            if pred is None:pred,_,_=r225.r225_predict(r,lm,m)
            if pred is not None:s['incumbent_predictions']+=1;continue
            pred,branch,diag=source_prediction(r,spec)
            if pred is None:
                s['abstain']+=1;reasons[branch]+=1
                if len(diags)<50:diags.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'reason':branch,'diag':diag})
                continue
            full=[row[:] for row in pred]+[r['before'][-1][:]]
            if lm is not None:
                ek=r217.goal_key(lm['level_before'],full)
                if ek in m['exact_goal']:vetoes['exact_goal']+=1;s['abstain']+=1;continue
                sk=r218.structural_key(m['fam'],lm['level_before'],full)
                if sk in m['struct_goal']:vetoes['struct_goal']+=1;s['abstain']+=1;continue
            ok=pred==gp(r['after'])
            s['candidate_predictions']+=1;s['candidate_correct' if ok else 'candidate_wrong']+=1;branches[branch]+=1
            if len(added)<100:added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'correct':ok,'diag':diag})
            if not ok and len(wrong)<50:wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'diag':diag})
    cp=s['candidate_predictions'];cc=s['candidate_correct']
    return {**dict(s),'candidate_accuracy':round(cc/cp,6) if cp else None,
            'branch_counts':dict(branches),'veto_counts':dict(vetoes),'abstain_reasons':dict(reasons),
            'resolver_diagnostics':diags,'added_examples':added,'wrong_examples':wrong}

def run(paths,spec):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];dev=ps[10:]
    return {'schema':'deus/arc3-ft09-source-compiled-static-level-audit/1','rung':RUNG,'game':GAME,
      'compiler':{'source_sha256':spec['source_sha256'],'source_commit':spec['source_commit'],'levels':len(spec['levels'])},
      'p0_p9_source_assisted_validation':evaluate(train,spec,train),
      'p10_p19_reused_development_only':evaluate(dev,spec,train),
      'decision':{'static_level_resolver_compiled':True,'source_assisted_expert_promotion':False,
                  'solver_promotion':False,'kaggle_packaging':False,
                  'next_gate':'if zero-wrong source-assisted validation, predeclare untouched runtime canary; otherwise repair static-template renderer mapping only'},
      'truth':{'compile_stage_ast_only':True,'evaluate_stage_does_not_read_or_execute_source':True,
               'level_selected_from_visible_static_templates_only':True,
               'dynamic_click_requires_compiled_source_position':True,
               'trace_level_metadata_not_used_for_palette_or_local_transition':True,
               'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT',
               'independent_generalization_claim':False,'competition_execution':False,
               'competition_submission':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('compile');c.add_argument('--source',type=Path,required=True);c.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('evaluate');e.add_argument('--spec',type=Path,required=True);e.add_argument('--input',type=Path,action='append',default=[]);e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=='compile':
        d=compile_source(a.source);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'levels':[{'i':x['index'],'name':x['name'],'palette':x['palette'],'dynamic':len(x['dynamic_tiles']),'static':len(x['static_anchors'])} for x in d['levels']]},sort_keys=True))
    else:
        spec=json.loads(a.spec.read_text());d=run(a.input,spec);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'train':d['p0_p9_source_assisted_validation'],'dev':d['p10_p19_reused_development_only'],'decision':d['decision']},sort_keys=True))
if __name__=='__main__':main()
