#!/usr/bin/env python3
"""R272: generic p5-p9 selector + p0-p9 refit stability gate for static UI masking.

R268 established a source-assisted static UI-mask representation idea; R270/R271
froze and independently audited its p0-p4 -> p10-p19 signal on 14 games. R272
asks the next discriminating question: can the selector be recomputed from
p0-p4/p5-p9 for all public games, then refit on p0-p9 without introducing
heldout errors on p10-p19?

This remains PUBLIC_OFFLINE source-side evidence. p10-p19 never changes selector,
mask, or model. It is a representation/planning-state gate, not full-frame solver
or Kaggle score.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268

RUNG=272
EXPECTED_SIGNAL_GAMES={
'ar25-0c556536','ft09-0d8bbf25','ka59-38d34dbb','lf52-271a04aa',
'lp85-305b61c3','r11l-495a7899','re86-8af5384d','s5i5-18d95033',
'su15-1944f8ab','tn36-ef4dde99','tr87-cd924810','tu93-0768757b',
'vc33-5430563c','wa30-ee6fef47'}
R270_MASK_HOLDOUT={'predictions':5066,'correct':5066,'wrong':0,'abstain':12119,'transitions':17185}


def eval_game(paths:list[Path])->dict[str,Any]:
    ps=sorted(paths,key=r246.pnum)
    nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise ValueError(f'exact p0..p19 required, got {nums}')
    tr=r268.rows(ps[:5]); va=r268.rows(ps[5:10]); refit=r268.rows(ps[:10]); ho=r268.rows(ps[10:])
    tr_tables={}; val={}
    for mode in ('raw','ui_mask'):
        tab,stats=r268.fit_table(tr,mode)
        tr_tables[mode]={'fit':stats,'validation':r268.evaluate(va,tab,mode)}
        val[mode]=tr_tables[mode]['validation']
    select_ui=bool(int(val['ui_mask'].get('correct',0))>int(val['raw'].get('correct',0)) and int(val['ui_mask'].get('wrong',0))==0)
    selected='ui_mask' if select_ui else 'raw'
    raw_tab,raw_fit=r268.fit_table(refit,'raw')
    sel_tab,sel_fit=r268.fit_table(refit,selected)
    return {
      'selection':selected,
      'selection_uses':'p0-p4 fit / p5-p9 validation only',
      'diagnostic':tr_tables,
      'refit':{'raw':raw_fit,'selected':sel_fit},
      'holdout':{'raw':r268.evaluate(ho,raw_tab,'raw'),'selected':r268.evaluate(ho,sel_tab,selected)},
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if len(by)!=25: raise SystemExit(f'expected 25 games, got {len(by)}')
    games={g:eval_game(ps) for g,ps in sorted(by.items())}
    signal={g for g,x in games.items() if x['selection']=='ui_mask'}
    selector_match=signal==EXPECTED_SIGNAL_GAMES
    agg=Counter(); raw_agg=Counter()
    for g in sorted(signal):
        s=games[g]['holdout']['selected']; r=games[g]['holdout']['raw']
        for k in ('transitions','predictions','correct','wrong','abstain'):
            agg[k]+=int(s.get(k,0) or 0); raw_agg[k]+=int(r.get(k,0) or 0)
    p=agg['predictions']; rp=raw_agg['predictions']
    aggregate={
      'selected_game_count':len(signal),
      'ui_refit_transitions':agg['transitions'],'ui_refit_predictions':agg['predictions'],'ui_refit_correct':agg['correct'],'ui_refit_wrong':agg['wrong'],'ui_refit_abstain':agg['abstain'],
      'ui_refit_accuracy':round(agg['correct']/p,6) if p else None,
      'raw_refit_predictions_same_games':raw_agg['predictions'],'raw_refit_correct_same_games':raw_agg['correct'],'raw_refit_wrong_same_games':raw_agg['wrong'],'raw_refit_accuracy_same_games':round(raw_agg['correct']/rp,6) if rp else None,
      'correct_gain_vs_r270_p0_p4_mask':agg['correct']-R270_MASK_HOLDOUT['correct'],
      'wrong_delta_vs_r270_p0_p4_mask':agg['wrong']-R270_MASK_HOLDOUT['wrong'],
    }
    promote=bool(selector_match and len(signal)==14 and agg['wrong']==0 and agg['correct']>R270_MASK_HOLDOUT['correct'])
    out={
      'schema':'deus/arc3-r272-ui-mask-selector-refit-gate/1','rung':RUNG,
      'lineage':{'r268':'run35802450526/artifact10726568095','r270':'run35804180491/artifact10727555733','r271_audit':'run35804725324/artifact10727231440'},
      'protocol':{'selector':'p0-p4 fit / p5-p9 zero-wrong gain','refit':'p0-p9','frozen_eval':'p10-p19','p10_p19_updates_selector':False,'p10_p19_updates_model':False,'expected_signal_set_used_for':'implementation QA only; not selection'},
      'selector_matches_r268_receipt':selector_match,'signal_games':sorted(signal),'aggregate':aggregate,'games':games,
      'verdict':'PROMOTE_REFIT_REPRESENTATION' if promote else 'NO_PROMOTION',
      'truth':{'public_trace_only':True,'source_assisted_representation_idea':True,'independent_generalization_claim':False,'full_frame_solver_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r272':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'selector_match':selector_match,'signal_games':sorted(signal),'aggregate':aggregate,'verdict':out['verdict']},sort_keys=True))

if __name__=='__main__': main()
