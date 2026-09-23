#!/usr/bin/env python3
"""R270: frozen UI-mask representation gate over all 25 public ARC-AGI-3 games.

Selection is based only on p0-p9:
- p0-p4 fit raw and UI-masked state/action -> next-state-key tables
- p5-p9 select UI-mask for a game only if it adds correct predictions and does
  not increase wrong predictions vs raw.

Frozen evaluation:
- refit both tables on p0-p9
- evaluate p10-p19 without retuning
- representation promotion requires UI-mask to have >=1 prediction, zero wrong,
  and strictly more correct predictions than raw on p10-p19.

This promotes only a state representation mechanism, not a full solver or Kaggle
score claim.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_ui_mask_markov_diag_268 as r268

RUNG=270

def rows(paths):
    return [r for p in paths for r in r251.prepare_rows([p])]

def eval_game(paths):
    ps=sorted(paths,key=r246.pnum)
    nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)):
        raise ValueError(f"expected p0..p19, got {nums}")
    tr=rows(ps[:5]); va=rows(ps[5:10]); fit=rows(ps[:10]); ho=rows(ps[10:])

    sel={}
    for mode in ("raw","ui_mask"):
        tab,meta=r268.fit_table(tr,mode)
        sel[mode]={"fit":meta,"validation":r268.evaluate(va,tab,mode)}
    rv=sel["raw"]["validation"]; mv=sel["ui_mask"]["validation"]
    selected=bool(
        int(mv.get("correct",0))>int(rv.get("correct",0))
        and int(mv.get("wrong",0))<=int(rv.get("wrong",0))
    )

    frozen={}
    for mode in ("raw","ui_mask"):
        tab,meta=r268.fit_table(fit,mode)
        frozen[mode]={"fit":meta,"heldout":r268.evaluate(ho,tab,mode)}

    rh=frozen["raw"]["heldout"]; mh=frozen["ui_mask"]["heldout"]
    promoted=bool(
        selected
        and int(mh.get("predictions",0))>0
        and int(mh.get("wrong",0))==0
        and int(mh.get("correct",0))>int(rh.get("correct",0))
    )
    return {
      "selected_p0_p9":selected,
      "selection":{"raw":rv,"ui_mask":mv},
      "frozen":{"raw":rh,"ui_mask":mh},
      "delta":{
        "correct":int(mh.get("correct",0))-int(rh.get("correct",0)),
        "wrong":int(mh.get("wrong",0))-int(rh.get("wrong",0)),
        "predictions":int(mh.get("predictions",0))-int(rh.get("predictions",0)),
      },
      "representation_promoted":promoted,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    games={g:eval_game(ps) for g,ps in sorted(by.items())}
    promoted=[g for g,x in games.items() if x["representation_promoted"]]
    selected=[g for g,x in games.items() if x["selected_p0_p9"]]
    agg={"game_count":len(games),"selected_count":len(selected),"promoted_count":len(promoted),
         "selected_games":selected,"promoted_games":promoted}
    out={
      "schema":"deus/arc3-r270-ui-mask-frozen-gate/1",
      "rung":RUNG,
      "protocol":{
        "selection_fit":"p0-p4","selection_eval":"p5-p9","refit":"p0-p9",
        "frozen_eval":"p10-p19","retune_on_p10_p19":False,
        "promotion_rule":"selected on p0-p9 + heldout predictions>0 + heldout wrong=0 + heldout correct>raw correct"
      },
      "aggregate":agg,"games":games,
      "truth":{
        "public_trace_only":True,"game_source_read":False,
        "p10_p19_never_updates_selection":True,
        "representation_only":True,
        "full_solver_claim":False,"independent_generalization_claim":False,
        "kaggle_execution":False,"competition_submission":False,"submission_quota_spent":False
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(agg,sort_keys=True))
if __name__=="__main__": main()
