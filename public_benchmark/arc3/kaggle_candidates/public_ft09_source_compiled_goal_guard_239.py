#!/usr/bin/env python3
"""R239: source-compiled cgj() goal guard for the FT09 local operator.

R238 narrowed the remaining source-assisted development errors to four exact
local-operator predictions.  The pinned public source applies the Hkx/NTi
operator and then calls cgj(); a solved board immediately advances level.  R238
modeled the local operator but not that post-action goal transition, so it could
emit a locally-correct frame when the real runtime had already changed scene.

R239 compiles only the static cgj relation tests from the pinned MIT source:
bsT target sprites, their center color, and equality/inequality relations to
neighboring Hkx/NTi cells.  The source file is removed before evaluation.
Inference uses only the visible pre-action board, compiled static spec, and the
candidate local edit.  If that edit would satisfy cgj(), R239 fails closed and
abstains instead of pretending to render the next level.

This is source-assisted public-development evidence.  It is not independent
generalization, provider execution, Kaggle score, or submission evidence.
"""
from __future__ import annotations
import argparse, ast, json, re
from collections import Counter
from pathlib import Path

import public_ft09_source_compiled_static_level_238 as r238
import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_goal_manifold_veto_225 as r225

RUNG=239
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board): return [row[:] for row in board[:-1]]

def compile_source(source:Path):
    base=r238.compile_source(source)
    raw=source.read_text(); tree=ast.parse(raw)
    sn=ln=None
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sprites' for t in n.targets): sn=n.value
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='levels' for t in n.targets): ln=n.value
    if not isinstance(sn,ast.Dict) or not isinstance(ln,ast.List): raise ValueError('source shape')

    sprites={}
    for k,v in zip(sn.keys,sn.values):
        if k is None or not isinstance(v,ast.Call): continue
        name=str(ast.literal_eval(k)); kw={x.arg:x.value for x in v.keywords if x.arg}
        if 'pixels' not in kw: continue
        pixels=ast.literal_eval(kw['pixels'])
        tags=list(ast.literal_eval(kw['tags'])) if 'tags' in kw else []
        sprites[name]={'pixels':pixels,'tags':tags}

    for idx,node in enumerate(ln.elts):
        if not isinstance(node,ast.Call): continue
        kw={x.arg:x.value for x in node.keywords if x.arg}
        lst=kw.get('sprites')
        dyn_by_xy={tuple(x['source_xy']):x for x in base['levels'][idx]['dynamic_tiles']}
        groups=[]
        for elt in lst.elts if isinstance(lst,ast.List) else []:
            ref=r238._sprite_ref(elt); pos=r238._position(elt)
            if ref is None or pos is None or ref not in sprites: continue
            sp=sprites[ref]
            if 'bsT' not in set(sp['tags']): continue
            pix=sp['pixels']
            if len(pix)<3 or any(len(row)<3 for row in pix): continue
            x,y=pos; center=int(pix[1][1]); tests=[]
            for j in range(3):
                for i in range(3):
                    if i==1 and j==1: continue
                    xy=(x+(i-1)*4,y+(j-1)*4)
                    ent=dyn_by_xy.get(xy)
                    if ent is None: continue
                    tests.append({
                        'render_top_left_rc':ent['render_top_left_rc'],
                        'relation':'eq' if int(pix[j][i])==0 else 'neq',
                    })
            groups.append({'sprite':ref,'source_xy':[x,y],'target_color':center,'tests':tests})
        base['levels'][idx]['goal_groups']=groups
    base['schema']='deus/arc3-ft09-static-level-goal-spec/1'
    base['truth'].update({
        'cgj_relations_compiled_static':True,
        'goal_evaluation_observation_only_after_candidate_edit':True,
        'next_level_frame_not_synthesized':True,
    })
    return base

def goal_satisfied(gameplay,lv):
    groups=lv.get('goal_groups') or []
    if not groups: return False
    for g in groups:
        tgt=int(g['target_color'])
        for t in g['tests']:
            r0,c0=map(int,t['render_top_left_rc'])
            if r0+2>=len(gameplay) or c0+2>=len(gameplay[0]): return False
            cur=int(gameplay[r0+2][c0+2])
            if t['relation']=='eq':
                if cur!=tgt: return False
            elif cur==tgt:
                return False
    return True

def evaluate(paths,spec,train):
    m=r221.build_models(train)
    s=Counter(); reasons=Counter(); branches=Counter(); vetoes=Counter(); added=[]; wrong=[]; guarded=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1; lm=meta.get(r['step0'])
            pred,_=r221.r218_predict(r,lm,m)
            if pred is None: pred,_=r221.r219_predict(r,lm,m)
            if pred is None: pred,_,_=r225.r225_predict(r,lm,m)
            if pred is not None:
                s['incumbent_predictions']+=1; continue

            pred,branch,diag=r238.source_prediction(r,spec)
            if pred is None:
                s['abstain']+=1; reasons[branch]+=1; continue

            li=diag.get('level_index') if isinstance(diag,dict) else None
            if li is None or not (0<=int(li)<len(spec['levels'])):
                s['abstain']+=1; reasons['unresolved_level_for_goal_guard']+=1; continue
            if goal_satisfied(pred,spec['levels'][int(li)]):
                s['abstain']+=1; reasons['would_advance_level']+=1
                if len(guarded)<40: guarded.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'level_index':int(li)})
                continue

            full=[row[:] for row in pred]+[r['before'][-1][:]]
            if lm is not None:
                ek=r217.goal_key(lm['level_before'],full)
                if ek in m['exact_goal']:
                    vetoes['exact_goal']+=1; s['abstain']+=1; continue
                sk=r218.structural_key(m['fam'],lm['level_before'],full)
                if sk in m['struct_goal']:
                    vetoes['struct_goal']+=1; s['abstain']+=1; continue

            ok=pred==gp(r['after'])
            s['candidate_predictions']+=1; s['candidate_correct' if ok else 'candidate_wrong']+=1; branches[branch]+=1
            if len(added)<80: added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'correct':ok})
            if not ok and len(wrong)<40: wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'branch':branch,'diag':diag})
    cp=s['candidate_predictions']; cc=s['candidate_correct']; cw=s['candidate_wrong']
    return {**dict(s),'candidate_accuracy':round(cc/cp,6) if cp else None,
            'zero_wrong_candidate':bool(cp>0 and cw==0),'branch_counts':dict(branches),'veto_counts':dict(vetoes),
            'abstain_reasons':dict(reasons),'goal_guarded_examples':guarded,'added_examples':added,'wrong_examples':wrong}

def run(paths,spec):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
    train=ps[:10]; dev=ps[10:]
    tr=evaluate(train,spec,train); dv=evaluate(dev,spec,train)
    gate=bool(dv.get('candidate_predictions',0)>0 and dv.get('candidate_wrong',0)==0)
    return {
      'schema':'deus/arc3-ft09-source-compiled-goal-guard-audit/1','rung':RUNG,'game':GAME,
      'compiler':{'source_sha256':spec['source_sha256'],'source_commit':spec['source_commit'],'levels':len(spec['levels'])},
      'p0_p9_source_assisted_validation':tr,'p10_p19_reused_development_only':dv,
      'decision':{
        'cgj_goal_guard_compiled':True,'source_assisted_zero_wrong_gate':gate,
        'source_assisted_expert_promotion':False,'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'if zero-wrong, predeclare a genuinely untouched runtime/provider canary; otherwise inspect only the remaining mismatch mechanism',
      },
      'truth':{
        'compile_stage_ast_only':True,'evaluate_stage_does_not_read_or_execute_source':True,
        'level_selected_from_visible_static_templates_only':True,'goal_guard_uses_compiled_relations_and_candidate_observation_only':True,
        'goal_transition_fails_closed_instead_of_synthesizing_next_level':True,
        'trace_level_metadata_not_used_for_palette_local_transition_or_goal_guard':True,
        'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT','independent_generalization_claim':False,
        'competition_execution':False,'competition_submission':False,'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('compile'); c.add_argument('--source',type=Path,required=True); c.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('evaluate'); e.add_argument('--spec',type=Path,required=True); e.add_argument('--input',type=Path,action='append',default=[]); e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=='compile':
        d=compile_source(a.source); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'levels':[{'i':x['index'],'name':x['name'],'goal_groups':len(x.get('goal_groups') or []),'goal_tests':sum(len(g['tests']) for g in x.get('goal_groups') or [])} for x in d['levels']]},sort_keys=True))
    else:
        spec=json.loads(a.spec.read_text()); d=run(a.input,spec); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'train':d['p0_p9_source_assisted_validation'],'dev':d['p10_p19_reused_development_only'],'decision':d['decision']},sort_keys=True))
if __name__=='__main__': main()
