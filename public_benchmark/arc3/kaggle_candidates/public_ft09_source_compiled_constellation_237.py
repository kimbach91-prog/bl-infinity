#!/usr/bin/env python3
"""R237: source-compiled visible constellation resolver for FT09.

Compile-time:
- AST-parse pinned MIT source.
- Extract sprite tags/pixels.
- Extract each level's static Hkx/NTi-tagged sprite positions and cwU palette.
- Emit a static JSON mechanism spec.

Inference/evaluation:
- source file is deleted before evaluator starts.
- infer the current source level ONLY from visible Hkx/NTi tile top-left
  coordinates in the rendered observation (source positions rendered at scale2).
- resolve palette from the uniquely matched static constellation.
- apply the source-compiled Hkx/NTi click operator.
- never use trace level metadata to select palette or local transition.

This remains source-assisted diagnostic evidence. Reused p10-p19 cannot promote.
"""
from __future__ import annotations
import argparse,ast,hashlib,json,re
from collections import Counter
from pathlib import Path

import public_ft09_source_compiled_visible_local_234 as r234
import public_ft09_source_compiled_nti_repair_235 as r235
import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_goal_manifold_veto_225 as r225

RUNG=237
GAME='ft09-0d8bbf25'
SCALE=2
VISIBLE_PALETTE_VALUES=r234.VISIBLE_PALETTE_VALUES

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board): return [row[:] for row in board[:-1]]

def _lit(node):
    return ast.literal_eval(node)

def _sprite_ref(node):
    """Return sprite dict key through sprites['x'].clone().set_position(...) chains."""
    cur=node
    while isinstance(cur,ast.Call) and isinstance(cur.func,ast.Attribute):
        cur=cur.func.value
    if isinstance(cur,ast.Subscript) and isinstance(cur.value,ast.Name) and cur.value.id=='sprites':
        sl=cur.slice
        try:return str(ast.literal_eval(sl))
        except Exception:return None
    return None

def _position(node):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='set_position':
        if len(node.args)>=2:
            try:return (int(_lit(node.args[0])),int(_lit(node.args[1])))
            except Exception:return None
    return None

def compile_source(source:Path)->dict:
    raw=source.read_bytes();tree=ast.parse(raw.decode())
    sprites_node=None;levels_node=None
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sprites' for t in n.targets):
            sprites_node=n.value
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='levels' for t in n.targets):
            levels_node=n.value
    if not isinstance(sprites_node,ast.Dict) or not isinstance(levels_node,ast.List):
        raise ValueError('expected sprites dict and levels list')

    sprites={}
    for kn,vn in zip(sprites_node.keys,sprites_node.values):
        if kn is None or not isinstance(vn,ast.Call):continue
        name=str(_lit(kn));kw={k.arg:k.value for k in vn.keywords if k.arg}
        try:pixels=_lit(kw['pixels'])
        except Exception:continue
        try:tags=list(_lit(kw['tags'])) if 'tags' in kw else []
        except Exception:tags=[]
        sprites[name]={'pixels':pixels,'tags':tags}

    levels=[]
    for idx,node in enumerate(levels_node.elts):
        if not isinstance(node,ast.Call):continue
        kw={k.arg:k.value for k in node.keywords if k.arg}
        name=str(_lit(kw['name']))
        data=dict(_lit(kw['data']))
        entries=[]
        for elt in getattr(kw.get('sprites'),'elts',[]) if isinstance(kw.get('sprites'),ast.List) else []:
            ref=_sprite_ref(elt);pos=_position(elt)
            if ref is None:continue
            tags=sprites.get(ref,{}).get('tags',[])
            entries.append({'sprite':ref,'position':list(pos) if pos else None,'tags':tags})
        dyn=[]
        for e in entries:
            if e['position'] is None:continue
            tags=set(e['tags'])
            if 'Hkx' in tags or 'NTi' in tags or e['sprite'] in ('Hkx','NTi'):
                x,y=e['position']
                dyn.append({'sprite':e['sprite'],'source_xy':[x,y],'render_top_left_rc':[y*SCALE,x*SCALE],
                            'kind':'NTi' if 'NTi' in tags or e['sprite']=='NTi' else 'Hkx'})
        levels.append({
          'index':idx,'name':name,'palette':[int(x) for x in data.get('cwU') or []],
          'timer_max':int(data.get('kCv') or 0),'dynamic_tiles':dyn,
        })

    if len(levels)!=6 or any(not x['palette'] for x in levels):
        raise ValueError('unexpected level extraction')
    if any(not x['dynamic_tiles'] for x in levels):
        raise ValueError('missing dynamic tile constellation')

    return {
      'schema':'deus/arc3-ft09-visible-constellation-spec/1',
      'source_sha256':hashlib.sha256(raw).hexdigest(),
      'source_commit':'41b87fe1ea8d9819a44eea35172ffe28d6c5ffe6',
      'scale':SCALE,'levels':levels,
      'truth':{'source_ast_parsed_not_imported':True,'compiled_spec_static':True,
               'level_resolution_requires_observation_constellation_only':True}
    }

def observed_dynamic_positions(board):
    h=len(board)-1;w=len(board[0]);out=set()
    # source dynamic sprites are 3x3, rendered scale2 => exact 6x6 blocks.
    # Scan even top-lefts only.
    for r0 in range(0,h-5,2):
        for c0 in range(0,w-5,2):
            logical=r235.logical6_at(board,r0,c0)
            if logical is None:continue
            if r235.tile_kind(logical) is not None:
                out.add((r0,c0))
    return out

def resolve_level(board,spec):
    obs=observed_dynamic_positions(board)
    scored=[]
    for lv in spec['levels']:
        exp={(int(x['render_top_left_rc'][0]),int(x['render_top_left_rc'][1])) for x in lv['dynamic_tiles']}
        # Dynamic tile colors change, positions do not. Require exact expected-set
        # containment, tolerate extra uniform visual aliases elsewhere.
        missing=len(exp-obs);extra=len(obs-exp)
        scored.append(((missing,extra),lv))
    scored.sort(key=lambda z:(z[0][0],z[0][1],z[1]['index']))
    if not scored:return None,{'reason':'no_levels'}
    best=scored[0]
    if best[0][0]!=0:
        return None,{'reason':'missing_expected','best':best[0],'scores':[(a,b['index']) for a,b in scored]}
    if len(scored)>1 and scored[1][0]==best[0]:
        return None,{'reason':'score_tie','best':best[0]}
    return best[1],{'level_index':best[1]['index'],'level_name':best[1]['name'],'score':list(best[0]),
                    'observed_dynamic_count':len(obs),'expected_dynamic_count':len(best[1]['dynamic_tiles'])}

def source_prediction(r,spec):
    lv,diag=resolve_level(r['before'],spec)
    if lv is None:return None,'level_constellation_ambiguous',diag
    palette=tuple(int(x) for x in lv['palette'])
    r0,c0,r1,c1,_=r['bbox']
    if (r1-r0+1,c1-c0+1)!=(6,6):return None,'bbox_not_scaled3',diag
    logical=r235.logical6_at(r['before'],r0,c0)
    if logical is None:return None,'clicked_not_uniform_scale2',diag
    kind=r235.tile_kind(logical)
    if kind is None:return None,'clicked_not_hkx_nti_visual',diag
    cur=int(logical[1][1])
    if cur not in palette:return None,'clicked_color_not_palette',diag
    out=[row[:] for row in r['before']];changed=0
    if kind=='Hkx':
        changed+=int(r235.cycle_tile(out,r0,c0,palette))
    else:
        for j in range(3):
            for i in range(3):
                if logical[j][i]==6:continue
                changed+=int(r235.cycle_tile(out,r0+(j-1)*8,c0+(i-1)*8,palette))
    if changed==0:return None,'no_visible_neighbor_tile',diag
    return gp(out),f'source_{kind.lower()}_constellation',diag

def evaluate(paths,spec,train):
    m=r221.build_models(train)
    s=Counter();reasons=Counter();branches=Counter();vetoes=Counter()
    added=[];wrong=[];resolve_diags=[]
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
                if len(resolve_diags)<40:resolve_diags.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'reason':branch,'diag':diag})
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
            if len(added)<100:added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'correct':ok,'diag':diag})
            if not ok and len(wrong)<50:wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'diag':diag})
    cp=s['candidate_predictions'];cc=s['candidate_correct']
    return {**dict(s),'candidate_accuracy':round(cc/cp,6) if cp else None,
            'branch_counts':dict(branches),'veto_counts':dict(vetoes),'abstain_reasons':dict(reasons),
            'resolver_diagnostics':resolve_diags,'added_examples':added,'wrong_examples':wrong}

def run(paths,spec):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];dev=ps[10:]
    return {
      'schema':'deus/arc3-ft09-source-compiled-constellation-audit/1','rung':RUNG,'game':GAME,
      'compiler':{'source_sha256':spec['source_sha256'],'source_commit':spec['source_commit'],
                  'level_count':len(spec['levels']),'scale':spec['scale']},
      'p0_p9_source_assisted_validation':evaluate(train,spec,train),
      'p10_p19_reused_development_only':evaluate(dev,spec,train),
      'decision':{'visible_constellation_resolver_compiled':True,'source_assisted_expert_promotion':False,
                  'solver_promotion':False,'kaggle_packaging':False,
                  'next_gate':'if source-assisted validation is zero-wrong, predeclare untouched runtime canary; otherwise repair observation-to-source coordinate/template mapping only'},
      'truth':{'compile_stage_ast_only':True,'evaluate_stage_does_not_read_or_execute_source':True,
               'level_palette_selected_from_visible_dynamic_constellation_only':True,
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
        d=compile_source(a.source);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'source_sha256':d['source_sha256'],'levels':[{'index':x['index'],'name':x['name'],'palette':x['palette'],'n_dynamic':len(x['dynamic_tiles'])} for x in d['levels']]},sort_keys=True))
    else:
        spec=json.loads(a.spec.read_text());d=run(a.input,spec);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'train':d['p0_p9_source_assisted_validation'],'dev':d['p10_p19_reused_development_only'],'decision':d['decision']},sort_keys=True))
if __name__=='__main__':main()
