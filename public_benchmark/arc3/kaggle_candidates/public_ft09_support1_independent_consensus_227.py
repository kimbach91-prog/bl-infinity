#!/usr/bin/env python3
"""R227: independently confirmed support-1 fallback for ft09.

R226 diagnostically found 73 heldout R225 abstentions whose full-training base
key has support exactly 1. Those heldout outcomes are NOT used to select this
rule.

R227 builds a second, independent pre-action context model from p0-p9 only.
During leave-one-trace-out CV on p0-p9, a candidate may fire only when:
  1) the primary deterministic base key has support exactly 1 in the fold train,
  2) the secondary context key is deterministic with >=2 distinct trace support,
  3) secondary target agrees with the primary base target.

Family + minimum secondary support are selected solely by p0-p9 LOTO CV,
prioritizing zero wrong then useful coverage.

Frozen p10-p19 execution occurs only after R225 abstains. The same p0-p9 goal
manifold veto is applied before exact gameplay-frame rows0..62 scoring.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212ff
import public_ft09_macro_neighbor_rule_207 as r207
import public_ft09_ring2_relational_gate_211 as r211
import public_ft09_cv_support_ensemble_212 as cv212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_goal_manifold_veto_225 as r225
import public_ft09_context_qualified_residual_expert_224 as r224

RUNG=227
GAME='ft09-0d8bbf25'
FAMILIES=(
  'current_four','current_eight','current_pos','four_pos','eight_pos',
  'current_hist','four_hist','current_ring2','four_parity',
)
MIN_SUPPORTS=(2,3,4,5,6)

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def enrich(path:Path):
    for r in r212ff.all_rows(path):
        if not r['eligible']:
            continue
        ctx=r207.macro_context(r['before'],r['bbox'])
        yield {
          **r,
          'changed':r['target']!=r['current'],
          'four':ctx['four'],
          'eight':ctx['eight'],
          'macro_pos':ctx['macro_pos'],
          'macro_parity':ctx['macro_parity'],
          'board_hist':r224.hist(r['before']),
        }

def feat(fam,r):
    if fam=='current_four': return (r['current'],r['four'])
    if fam=='current_eight': return (r['current'],r['eight'])
    if fam=='current_pos': return (r['current'],r['macro_pos'])
    if fam=='four_pos': return (r['current'],r['four'],r['macro_pos'])
    if fam=='eight_pos': return (r['current'],r['eight'],r['macro_pos'])
    if fam=='current_hist': return (r['current'],r['board_hist'])
    if fam=='four_hist': return (r['current'],r['four'],r['board_hist'])
    if fam=='current_ring2': return (r['current'],r['ring2'])
    if fam=='four_parity': return (r['current'],r['four'],r['macro_parity'])
    raise ValueError(fam)

def fit_secondary(rows,fam,min_support,min_traces=2):
    obs=defaultdict(lambda:{'targets':Counter(),'traces':set()})
    for r in rows:
        if not r['changed']:
            continue
        k=repr(feat(fam,r))
        obs[k]['targets'][r['target']]+=1
        obs[k]['traces'].add(r['path'])
    model={}
    for k,x in obs.items():
        if len(x['targets'])!=1: continue
        support=sum(x['targets'].values())
        if support<min_support or len(x['traces'])<min_traces: continue
        model[k]={'pred':next(iter(x['targets'])),'support':support,'trace_support':len(x['traces'])}
    return model

def cv_config(paths,fam,min_support):
    trace_en=[list(enrich(p)) for p in paths]
    trace_base=[list(r211.rows(p)) for p in paths]
    total=Counter();folds=[]
    for hold in range(10):
        tr_en=[r for i in range(10) if i!=hold for r in trace_en[i]]
        tr_base=[r for i in range(10) if i!=hold for r in trace_base[i]]
        te=trace_en[hold]
        primary=cv212.fit(tr_base,'base')
        secondary=fit_secondary(tr_en,fam,min_support,2)
        f=Counter()
        for r in te:
            b=primary.get(repr(r['base']))
            if b is None or int(b['support'])!=1:
                continue
            f['eligible_support1']+=1
            q=secondary.get(repr(feat(fam,r)))
            if q is None or int(q['pred'])!=int(b['pred']):
                f['abstain']+=1;continue
            f['predictions']+=1
            if int(q['pred'])==int(r['target']): f['correct']+=1
            else: f['wrong']+=1
        for k in ('eligible_support1','abstain','predictions','correct','wrong'):
            total[k]+=f[k]
        folds.append({'hold':hold,**{k:int(f[k]) for k in ('eligible_support1','predictions','correct','wrong')}})
    p=total['predictions'];e=total['eligible_support1']
    return {**dict(total),'accuracy':round(total['correct']/p,6) if p else None,
            'coverage_support1':round(p/e,6) if e else 0.0,'folds':folds}

def select_policy(train):
    cand={}
    for fam in FAMILIES:
        for sup in MIN_SUPPORTS:
            name=f'{fam}|s{sup}'
            cand[name]=cv_config(train,fam,sup)
    def key(item):
        name,x=item
        acc=x['accuracy'] or 0.0
        fam,ss=name.split('|');sup=int(ss[1:])
        return (x.get('wrong',0),-acc,-x.get('correct',0),-x.get('predictions',0),-sup,FAMILIES.index(fam),name)
    ranking=[name for name,_ in sorted(cand.items(),key=key)]
    sel=ranking[0];fam,ss=sel.split('|')
    return {'config':sel,'family':fam,'min_support':int(ss[1:]),
            'cv':cand[sel],'ranking':ranking,'candidates':cand}

def build_models(train):
    m=r221.build_models(train)
    pol=select_policy(train)
    all_en=[r for p in train for r in enrich(p)]
    m['support1_policy']=pol
    m['support1_secondary']=fit_secondary(all_en,pol['family'],pol['min_support'],2)
    return m

def support1_predict(r,lm,m):
    b=m['base'].get(repr(r['base']))
    if b is None or int(b['support'])!=1:
        return None,None,None
    z=None
    ctx=r207.macro_context(r['before'],r['bbox'])
    z={**r,'changed':r['target']!=r['current'],'four':ctx['four'],'eight':ctx['eight'],
       'macro_pos':ctx['macro_pos'],'macro_parity':ctx['macro_parity'],
       'board_hist':r224.hist(r['before'])}
    q=m['support1_secondary'].get(repr(feat(m['support1_policy']['family'],z)))
    if q is None or int(q['pred'])!=int(b['pred']):
        return None,None,None

    target=int(b['pred'])
    virtual=r212ff.recolor_bbox(r['before'],r['bbox'],target)
    if lm is not None:
        ek=r217.goal_key(lm['level_before'],virtual)
        if ek in m['exact_goal']:
            return None,'r227_veto_exact_goal','exact_goal'
        sk=r218.structural_key(m['fam'],lm['level_before'],virtual)
        if sk in m['struct_goal']:
            return None,'r227_veto_struct_goal','struct_goal'
    return gp(virtual),'r227_support1_consensus',None

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    m=build_models(train)

    s=Counter();stage=defaultdict(Counter);branches=Counter()
    vetoes=Counter();added=[];wrong=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1;lm=meta.get(r['step0'])

            pred,branch=r221.r218_predict(r,lm,m);stage_name='r218'
            if pred is None:
                pred,branch=r221.r219_predict(r,lm,m);stage_name='r219_base5'
            if pred is None:
                pred,branch,veto=r225.r225_predict(r,lm,m);stage_name='r225_lowbase_veto'
            if pred is None:
                pred,branch,veto=support1_predict(r,lm,m);stage_name='r227_support1'
                if veto is not None: vetoes[veto]+=1

            if pred is None:
                s['abstain']+=1;continue

            ok=pred==gp(r['after'])
            s['predictions']+=1;s['correct' if ok else 'wrong']+=1
            stage[stage_name]['predictions']+=1
            stage[stage_name]['correct' if ok else 'wrong']+=1
            branches[branch]+=1
            if stage_name=='r227_support1' and len(added)<100:
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'action':r['action'],'correct':ok})
            if not ok and len(wrong)<50:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'stage':stage_name,'branch':branch,'action':r['action']})

    assert stage['r218']['predictions']==290 and stage['r218']['correct']==290 and stage['r218']['wrong']==0
    assert stage['r219_base5']['predictions']==6 and stage['r219_base5']['correct']==6 and stage['r219_base5']['wrong']==0
    assert stage['r225_lowbase_veto']['predictions']==11 and stage['r225_lowbase_veto']['correct']==11 and stage['r225_lowbase_veto']['wrong']==0

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
             'coverage':round(p/e,6) if e else 0.0}
    inc=stage['r227_support1'];gain=metrics.get('coverage',0.0)-0.335886
    gate=bool(inc.get('predictions',0)>0 and inc.get('wrong',0)==0 and s.get('wrong',0)==0 and gain>0)
    pol=m['support1_policy']
    return {
      'schema':'deus/arc3-ft09-support1-independent-consensus/1','rung':RUNG,'game':GAME,
      'policy':{
        'config':pol['config'],'family':pol['family'],'min_support':pol['min_support'],
        'cv':{k:pol['cv'].get(k) for k in ('eligible_support1','predictions','correct','wrong','accuracy','coverage_support1')},
        'ranking':pol['ranking'][:16],
        'candidate_summary':{k:{x:v.get(x) for x in ('eligible_support1','predictions','correct','wrong','accuracy','coverage_support1')}
                             for k,v in pol['candidates'].items()},
      },
      'heldout':{
        'all':metrics,'stage_metrics':{k:dict(v) for k,v in stage.items()},
        'branch_counts':dict(branches),'veto_counts':dict(vetoes),
        'r227_added_examples':added,'wrong_examples':wrong,
        'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False,
                   'next_gate':'if zero-wrong gain, freeze R227 then address unseen-base residuals with a new representation; otherwise retain R225'},
      'truth':{
        'public_trace_only':True,'r225_precedence_preserved':True,
        'family_and_support_selected_p0_p9_loto_only':True,
        'secondary_requires_cross_trace_support':True,
        'support1_requires_primary_secondary_target_agreement':True,
        'r227_only_after_r225_abstain':True,
        'goal_manifold_veto_preserved':True,
        'heldout_never_updates_policy_or_models':True,
        'r226_heldout_support1_outcomes_not_used_for_selection':True,
        'exact_gameplay_rows0_62_scoring':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'policy':d['policy'],'heldout':d['heldout']['all'],
      'stages':d['heldout']['stage_metrics'],'vetoes':d['heldout']['veto_counts'],
      'added':d['heldout']['r227_added_examples'],'wrong':d['heldout']['wrong_examples'],
      'gain':d['heldout']['coverage_gain_abs'],'gate':d['zero_wrong_coverage_gain_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
