#!/usr/bin/env python3
"""R224: context-qualified residual target expert for ft09.

R223 falsified support-count-only confidence: p0-p9 LOTO chose {2,3} with
79/79 zero-wrong target CV, yet two frozen support3 contexts failed.

R224 changes representation instead of tuning the heldout threshold. It
enumerates richer PRE-ACTION context keys over the R219-abstain residual domain:
  - ordered 8-neighbor macro context,
  - base + macro position,
  - base + macro parity,
  - base + ring2,
  - base + gameplay color histogram,
  - base + quadrant color histograms,
  - eight + macro position,
  - eight + gameplay color histogram.

Candidate family + minimum support are selected by leave-one-trace-out p0-p9
target CV only. Heldout candidate fires only after verified R218 and R219
abstain, renders clicked-6x6 local recolor only, and is exact-scored on gameplay
rows0..62. HUD row63 is excluded.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212ff
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_macro_neighbor_rule_207 as r207
import public_ft09_ring2_relational_gate_211 as r211
import public_ft09_cv_support_ensemble_212 as cv212
import public_ft09_low_support_base_abstain_union_221 as r221

RUNG=224
GAME='ft09-0d8bbf25'
BASE5=5
FAMILIES=(
 'eight','base_pos','base_parity','base_ring2',
 'base_hist','base_quadrants','eight_pos','eight_hist'
)
MIN_SUPPORTS=(1,2,3,4)

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def hist(board):
    c=Counter(v for row in gp(board) for v in row)
    return tuple(sorted((int(k),int(v)) for k,v in c.items()))

def region_hist(g,r0,r1,c0,c1):
    c=Counter(g[r][c0:c1][j] for r in range(r0,r1) for j in range(c1-c0))
    return tuple(sorted((int(k),int(v)) for k,v in c.items()))

def quadrants(board):
    g=gp(board);h=len(g);w=len(g[0]);rm=h//2;cm=w//2
    return (
      region_hist(g,0,rm,0,cm), region_hist(g,0,rm,cm,w),
      region_hist(g,rm,h,0,cm), region_hist(g,rm,h,cm,w),
    )

def rich_rows(path:Path):
    for r in r212ff.all_rows(path):
        if not r['eligible']:continue
        ctx=r207.macro_context(r['before'],r['bbox'])
        yield {
          **r,
          'changed':r['target']!=r['current'],
          'eight':ctx['eight'],
          'macro_pos':ctx['macro_pos'],
          'macro_parity':ctx['macro_parity'],
          'board_hist':hist(r['before']),
          'quadrants':quadrants(r['before']),
        }

def feat(fam,r):
    if fam=='eight':
        return (r['current'],r['eight'],r['base'][2])
    if fam=='base_pos':
        return (r['base'],r['macro_pos'])
    if fam=='base_parity':
        return (r['base'],r['macro_parity'])
    if fam=='base_ring2':
        return (r['base'],r['ring2'])
    if fam=='base_hist':
        return (r['base'],r['board_hist'])
    if fam=='base_quadrants':
        return (r['base'],r['quadrants'])
    if fam=='eight_pos':
        return (r['current'],r['eight'],r['base'][2],r['macro_pos'])
    if fam=='eight_hist':
        return (r['current'],r['eight'],r['base'][2],r['board_hist'])
    raise ValueError(fam)

def fit_candidate(rows,fam,min_support):
    obs=defaultdict(Counter)
    for r in rows:
        if not r['changed']:continue
        obs[repr(feat(fam,r))][r['target']]+=1
    model={}
    for k,c in obs.items():
        if len(c)==1 and sum(c.values())>=min_support:
            model[k]=next(iter(c))
    return model

def cv_candidate(paths,fam,min_support):
    rich=[list(rich_rows(p)) for p in paths]
    base=[list(r211.rows(p)) for p in paths]
    s=Counter();folds=[]
    for hold in range(10):
        train_r=[r for i in range(10) if i!=hold for r in rich[i]]
        train_b=[r for i in range(10) if i!=hold for r in base[i]]
        test=rich[hold]
        bt=cv212.fit(train_b,'base')
        model=fit_candidate(train_r,fam,min_support)
        f=Counter()
        for r in test:
            f['eligible']+=1
            b=bt.get(repr(r['base']))
            if b and int(b['support'])>=BASE5:
                f['incumbent_base5']+=1;continue
            pred=model.get(repr(feat(fam,r)))
            if pred is None:
                f['abstain']+=1;continue
            f['predictions']+=1
            if pred==r['target']:f['correct']+=1
            else:f['wrong']+=1
        for k in ('eligible','incumbent_base5','abstain','predictions','correct','wrong'):s[k]+=f[k]
        folds.append({'hold':hold,**{k:int(f[k]) for k in ('predictions','correct','wrong')}})
    p=s['predictions'];e=s['eligible']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
            'coverage_all':round(p/e,6) if e else 0.0,'folds':folds}

def select_candidate(train):
    cand={}
    for fam in FAMILIES:
        for sup in MIN_SUPPORTS:
            name=f'{fam}|s{sup}'
            cand[name]=cv_candidate(train,fam,sup)
    def key(item):
        name,x=item
        acc=x['accuracy'] or 0.0
        fam,sp=name.split('|');sup=int(sp[1:])
        # zero wrong first, then precision/correct coverage; higher support wins ties.
        return (x.get('wrong',0),-acc,-x.get('correct',0),-x.get('predictions',0),-sup,FAMILIES.index(fam),name)
    ranking=[name for name,_ in sorted(cand.items(),key=key)]
    sel=ranking[0];fam,sp=sel.split('|')
    return {'config':sel,'family':fam,'min_support':int(sp[1:]),
            'cv':cand[sel],'ranking':ranking,'candidates':cand}

def build_models(train):
    m=r221.build_models(train)
    pol=select_candidate(train)
    allrich=[r for p in train for r in rich_rows(p)]
    m['context_policy']=pol
    m['context_model']=fit_candidate(allrich,pol['family'],pol['min_support'])
    return m

def context_local_only(r,m):
    # Enrich the current row in exactly the same pre-action way.
    ctx=r207.macro_context(r['before'],r['bbox'])
    z={**r,'changed':r['target']!=r['current'],'eight':ctx['eight'],
       'macro_pos':ctx['macro_pos'],'macro_parity':ctx['macro_parity'],
       'board_hist':hist(r['before']),'quadrants':quadrants(r['before'])}
    pred=m['context_model'].get(repr(feat(m['context_policy']['family'],z)))
    if pred is None:return None,None
    board=r212ff.recolor_bbox(r['before'],r['bbox'],pred)
    return gp(board),'r224_context_local_only'

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:];m=build_models(train)

    s=Counter();stage=defaultdict(Counter);added=[];wrong=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            pred,branch=r221.r218_predict(r,lm,m);stage_name='r218'
            if pred is None:
                pred,branch=r221.r219_predict(r,lm,m);stage_name='r219_base5'
            if pred is None:
                pred,branch=context_local_only(r,m);stage_name='r224_context'
            if pred is None:
                s['abstain']+=1;continue
            ok=pred==gp(r['after'])
            s['predictions']+=1;s['correct' if ok else 'wrong']+=1
            stage[stage_name]['predictions']+=1;stage[stage_name]['correct' if ok else 'wrong']+=1
            if stage_name=='r224_context' and len(added)<80:
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'action':r['action'],'correct':ok})
            if not ok and len(wrong)<40:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'stage':stage_name,'action':r['action']})

    assert stage['r218']['predictions']==290 and stage['r218']['correct']==290 and stage['r218']['wrong']==0,dict(stage['r218'])
    assert stage['r219_base5']['predictions']==6 and stage['r219_base5']['correct']==6 and stage['r219_base5']['wrong']==0,dict(stage['r219_base5'])

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
             'coverage':round(p/e,6) if e else 0.0}
    inc=stage['r224_context'];gain=metrics.get('coverage',0.0)-0.323851
    gate=bool(inc.get('predictions',0)>0 and inc.get('wrong',0)==0 and
              s.get('wrong',0)==0 and gain>0)
    pol=m['context_policy']
    return {
      'schema':'deus/arc3-ft09-context-qualified-residual-expert/1',
      'rung':RUNG,'game':GAME,
      'policy':{
        'config':pol['config'],'family':pol['family'],'min_support':pol['min_support'],
        'cv':{k:pol['cv'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage_all')},
        'ranking':pol['ranking'][:16],
        'candidate_summary':{k:{x:v.get(x) for x in ('predictions','correct','wrong','accuracy','coverage_all')}
                             for k,v in pol['candidates'].items()},
      },
      'heldout':{
        'all':metrics,'stage_metrics':{k:dict(v) for k,v in stage.items()},
        'r224_added_examples':added,'wrong_examples':wrong,
        'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False},
      'truth':{
        'public_trace_only':True,'r218_precedence_preserved':True,
        'r219_base5_precedence_preserved':True,
        'context_family_and_support_selected_p0_p9_loto_only':True,
        'r224_only_after_r218_r219_abstain':True,
        'r224_pre_action_features_only':True,'r224_local_recolor_only':True,
        'heldout_never_updates_policy_or_models':True,
        'exact_gameplay_rows0_62_scoring':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'policy':d['policy'],'heldout':d['heldout']['all'],
                      'stages':d['heldout']['stage_metrics'],'added':d['heldout']['r224_added_examples'],
                      'wrong':d['heldout']['wrong_examples'],'gain':d['heldout']['coverage_gain_abs'],
                      'gate':d['zero_wrong_coverage_gain_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
