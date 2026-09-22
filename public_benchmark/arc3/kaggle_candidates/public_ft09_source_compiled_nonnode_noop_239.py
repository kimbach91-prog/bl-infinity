#!/usr/bin/env python3
"""R239: source-compiled non-node no-op completion for FT09.

Verified R234 repaired source-assisted expert predicts 1762/1982 public actions
exactly with zero wrong. Its 220 abstentions are:
  - 201 click_not_unique_node
  - 19 non_mouse

Pinned FT09 source has a precise branch for ACTION6 clicks that hit no Hkx/NTi:
  * if level 0 has the Ycb animation and the click is NOT on bsT, start the
    animation -> R239 keeps abstaining because that branch is temporal;
  * otherwise complete_action() with no gameplay-state change.

R239 compiles the same pinned MIT source manifest at build time via R234, then
evaluates source-free. It fills ONLY zero-dynamic-hit no-op cases. It never
treats multiple dynamic hits as no-op and it leaves level0 animation clicks
unpredicted.

Truth boundary: source-assisted transition expert only; not independent
generalization, hidden Kaggle score, or competition submission.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_compiled_observation_mechanism_234 as r234

RUNG=239
GAME="ft09-0d8bbf25"

def pnum(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1

def sprite_hits(sprites,row,col):
    gy=row/2.0;gx=col/2.0
    out=[]
    for s in sprites:
        px=s["pixels"];h=len(px);w=len(px[0]) if px else 0
        if int(s["x"])<=gx<int(s["x"])+w and int(s["y"])<=gy<int(s["y"])+h:
            out.append(s)
    return out

def fill_nonnode_noop(board,action,levels):
    lev,ident=r234.identify_level(board,levels)
    if lev is None:
        return None,{"abstain":"level_identification",**ident}
    mc=r234.parse_mouse(action)
    if mc is None:
        return None,{"abstain":"non_mouse","level":lev["index"]}
    row,col=mc
    dyn=sprite_hits(lev["nodes"],row,col)
    if len(dyn)>1:
        return None,{"abstain":"multiple_dynamic_hits","level":lev["index"],"hits":len(dyn)}
    if len(dyn)==1:
        return None,{"abstain":"dynamic_hit_owned_by_r234","level":lev["index"]}

    # Source step(): if level0 animation exists and clicked point is not bsT,
    # self.our=4 and returns without complete_action. Preserve as abstain.
    clue_hits=sprite_hits(lev["clues"],row,col)
    if int(lev["index"])==0 and lev.get("animation_dynamic_region") and not clue_hits:
        return None,{"abstain":"level0_animation_click","level":lev["index"]}

    # All other no-dynamic-node clicks call complete_action with no gameplay
    # mutation. HUD timing is outside rows0..62 and is intentionally excluded.
    return r234.clone_board(board),{
      "level":lev["index"],
      "branch":"compiled_nonnode_noop",
      "clue_hit":bool(clue_hits),
    }

def evaluate(paths,manifest):
    levels=manifest["levels"]
    s=Counter();branches=Counter();reasons=Counter()
    inc=Counter();examples=[];wrong=[]
    for p in sorted(paths,key=pnum):
        ev=r234.load_events(p);pre=None
        for e in ev:
            if e.get("board") is None: continue
            if e.get("type")!="action":
                pre=e;continue
            if pre is None:
                pre=e;continue
            before=pre["board"];expected=e["board"];action=r234.action_name(e)
            s["eligible"]+=1
            pred,meta=r234.predict(before,action,levels)
            stage="r234"
            if pred is None and meta.get("abstain")=="click_not_unique_node":
                pred,meta=fill_nonnode_noop(before,action,levels)
                stage="r239"
            if pred is None:
                s["abstain"]+=1
                reasons[meta.get("abstain","unknown")]+=1
                pre=e;continue
            ok=(pred[:-1]==expected[:-1])
            s["predictions"]+=1
            s["correct" if ok else "wrong"]+=1
            br=meta.get("branch","unknown");branches[br]+=1
            if stage=="r234":
                s["anchor_predictions"]+=1
                s["anchor_correct" if ok else "anchor_wrong"]+=1
            else:
                inc["predictions"]+=1;inc["correct" if ok else "wrong"]+=1
                if len(examples)<80:
                    examples.append({
                      "trace":p.name,"action":action,"correct":ok,
                      "level":meta.get("level"),"clue_hit":meta.get("clue_hit"),
                    })
            if not ok and len(wrong)<40:
                diff=sum(a!=b for ra,rb in zip(pred[:-1],expected[:-1]) for a,b in zip(ra,rb))
                wrong.append({"trace":p.name,"action":action,"stage":stage,
                              "meta":meta,"diff_gameplay_cells":diff})
            pre=e

    assert s["anchor_predictions"]==1762,dict(s)
    assert s["anchor_correct"]==1762 and s["anchor_wrong"]==0,dict(s)
    p=s["predictions"];e=s["eligible"]
    metrics={**dict(s),"accuracy":round(s["correct"]/p,6) if p else None,
             "coverage":round(p/e,6) if e else 0.0}
    gate=bool(inc["predictions"]>0 and inc["wrong"]==0 and s["wrong"]==0)
    return {
      "schema":"deus/arc3-ft09-source-compiled-nonnode-noop/1",
      "rung":RUNG,"game":GAME,
      "aggregate":metrics,
      "branches":dict(branches),
      "abstain_reasons":dict(reasons),
      "incremental":{"predictions":inc["predictions"],"correct":inc["correct"],
                     "wrong":inc["wrong"],"examples":examples},
      "wrong_examples":wrong,
      "source_assisted_zero_wrong_gain_gate_pass":gate,
      "decision":{
        "source_assisted_transition_expert_promotion":gate,
        "solver_promotion":False,
        "independent_generalization_promotion":False,
        "kaggle_packaging":False,
        "next_gate":"if zero-wrong, freeze R239 after R234 and model only level0 animation/non-mouse residuals; otherwise retain R234",
      },
      "truth":{
        "public_source_assisted_manifest":True,
        "r234_precedence_preserved":True,
        "nonnode_semantics_compiled_from_pinned_source":True,
        "multiple_dynamic_hits_never_assumed_noop":True,
        "level0_animation_branch_abstains":True,
        "evaluator_imports_game_source":False,
        "evaluator_requires_arcengine":False,
        "evaluator_requires_internet":False,
        "public_trace_outcomes_do_not_update_manifest":True,
        "gameplay_rows0_62_exact_scoring":True,
        "independent_generalization_claim":False,
        "hidden_kaggle_score":False,
        "competition_submission":False,
        "submission_quota_spent":False,
      },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    manifest=json.loads(a.manifest.read_text())
    d=evaluate(a.input,manifest)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
      "aggregate":d["aggregate"],
      "incremental":{k:v for k,v in d["incremental"].items() if k!="examples"},
      "branches":d["branches"],
      "abstain_reasons":d["abstain_reasons"],
      "gate":d["source_assisted_zero_wrong_gain_gate_pass"],
      "wrong":d["wrong_examples"],
    },sort_keys=True))
if __name__=="__main__":
    main()
