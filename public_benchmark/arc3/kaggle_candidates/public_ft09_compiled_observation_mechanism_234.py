#!/usr/bin/env python3
"""R234: compile public MIT FT09 source into a standalone observation mechanism.

Compile phase (source-assisted, build time only):
  * import pinned public ft09.py under arcengine==0.9.3;
  * extract level-local node positions, special click masks, goal clues,
    color cycles, timer maxima, and exact initial rendered frames;
  * write a static JSON manifest.

Evaluation phase (standalone, inference-like):
  * requires only Python stdlib + the compiled JSON manifest;
  * does NOT import arcengine, game source, or project solver helpers;
  * identifies the current level from immutable visible pixels;
  * parses MOUSE(row,col), simulates Hkx/NTi click-cycle mechanics,
    evaluates source-derived goal constraints, and predicts either the local
    post-action gameplay frame or the next compiled initial scene;
  * scores exact public gameplay rows 0..62.

This is explicitly public-source-assisted. It is not independent hidden-game
generalization or a Kaggle score.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

GAME="ft09-0d8bbf25"
RUNG=234

def load_source(path:Path):
    spec=importlib.util.spec_from_file_location("ft09_r234_compile",path)
    if spec is None or spec.loader is None: raise RuntimeError("cannot load source")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def matrix(x):
    return [[int(v) for v in row] for row in x.tolist()]

def sprite_rec(s,kind):
    px=matrix(s.pixels)
    rec={"kind":kind,"x":int(s.x),"y":int(s.y),"pixels":px}
    if kind=="special":
        rec["click_mask"]=[[1 if int(v)!=6 else 0 for v in row] for row in px]
    return rec

def region_for_sprite(s):
    h,w=s.pixels.shape
    return {"x":int(s.x),"y":int(s.y),"w":int(w),"h":int(h)}

def current_frame(game):
    return [[int(v) for v in row] for row in game.camera.render(game.current_level.get_sprites()).tolist()]

def compile_manifest(source:Path,out:Path):
    mod=load_source(source)
    game=mod.Ft09()
    levels=[]
    nlevels=len(mod.levels)
    for idx in range(nlevels):
        if int(game.level_index)!=idx:
            raise RuntimeError(f"level desync {game.level_index} != {idx}")
        nodes=[sprite_rec(s,"regular") for s in game.fhc]
        nodes += [sprite_rec(s,"special") for s in game.mou]
        clues=[sprite_rec(s,"clue") for s in game.gig]
        animation=None
        if getattr(game,"zth",None) is not None:
            animation=region_for_sprite(game.zth)
        level={
          "index":idx,
          "name":str(game.current_level.name),
          "cycle":[int(x) for x in game.gqb],
          "default_click_mask":[[int(x) for x in row] for row in game.irw],
          "timer_max":int(game.lpw.oro),
          "nodes":nodes,
          "clues":clues,
          "animation_dynamic_region":animation,
          "initial_frame":current_frame(game),
        }
        levels.append(level)
        if idx<nlevels-1:
            game.next_level()
    manifest={
      "schema":"deus/arc3-ft09-compiled-observation-mechanism/1",
      "game":GAME,"rung":RUNG,
      "source":{
        "repo":"axobase001/arc-agi-games",
        "commit":"41b87fe1ea8d9819a44eea35172ffe28d6c5ffe6",
        "path":"ft09/0d8bbf25/ft09.py",
        "license":"MIT",
        "sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "compile_runtime":"arcengine==0.9.3",
      },
      "levels":levels,
      "truth":{
        "public_source_assisted_compile":True,
        "source_runtime_required_at_inference":False,
        "internet_required_at_inference":False,
        "independent_generalization_claim":False,
        "kaggle_score_claim":False,
      },
    }
    out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"compiled_levels":len(levels),"source_sha256":manifest["source"]["sha256"],
                      "nodes":[len(x["nodes"]) for x in levels],
                      "clues":[len(x["clues"]) for x in levels],
                      "cycles":[x["cycle"] for x in levels]},sort_keys=True))

def load_events(p:Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]

def action_name(e):
    for k in ("action_display","action_name","action"):
        v=e.get(k)
        if isinstance(v,str): return v
    return ""

def parse_mouse(name):
    m=re.search(r"MOUSE\s*\(\s*row\s*=\s*(-?\d+)\s*,\s*col\s*=\s*(-?\d+)\s*\)",name)
    if m:return int(m.group(1)),int(m.group(2))
    return None

def clone_board(b):
    return [list(map(int,row)) for row in b]

def dynamic_cells(level):
    z=set()
    for n in level["nodes"]:
        for rr in range(2*n["y"],2*(n["y"]+len(n["pixels"]))):
            for cc in range(2*n["x"],2*(n["x"]+len(n["pixels"][0]))):
                if 0<=rr<64 and 0<=cc<64:z.add((rr,cc))
    a=level.get("animation_dynamic_region")
    if a:
        for rr in range(2*a["y"],2*(a["y"]+a["h"])):
            for cc in range(2*a["x"],2*(a["x"]+a["w"])):
                if 0<=rr<64 and 0<=cc<64:z.add((rr,cc))
    for cc in range(64):z.add((63,cc))
    return z

def identify_level(board,levels):
    scored=[]
    for lev in levels:
        dyn=dynamic_cells(lev);ref=lev["initial_frame"];bad=0;seen=0
        for rr in range(min(64,len(board),len(ref))):
            for cc in range(min(64,len(board[rr]),len(ref[rr]))):
                if (rr,cc) in dyn:continue
                seen+=1
                if int(board[rr][cc])!=int(ref[rr][cc]):bad+=1
        scored.append((bad,-seen,lev["index"]))
    scored.sort()
    if not scored:return None,{"reason":"no_levels"}
    best=scored[0]
    # Static pixels should be exact within a level. Fail closed otherwise.
    if best[0]!=0:return None,{"reason":"static_mismatch","best_bad":best[0],"ranking":scored[:3]}
    return levels[best[2]],{"best_bad":best[0],"ranking":scored[:3]}

def node_map(level):
    return {(int(n["x"]),int(n["y"])):n for n in level["nodes"]}

def clicked_node(level,row,col):
    # Frame is a 2x rendering of the 32x32 source grid.
    gy=row/2.0;gx=col/2.0
    hits=[]
    for n in level["nodes"]:
        h=len(n["pixels"]);w=len(n["pixels"][0])
        if n["x"]<=gx<n["x"]+w and n["y"]<=gy<n["y"]+h:
            hits.append(n)
    return hits[0] if len(hits)==1 else None

def node_center_color(board,n):
    rr=2*(int(n["y"])+1);cc=2*(int(n["x"])+1)
    return int(board[rr][cc])

def next_color(cycle,v):
    if v not in cycle:return None
    return int(cycle[(cycle.index(v)+1)%len(cycle)])

def paint_node(board,n,new_color):
    px=n["pixels"]
    for j,row in enumerate(px):
        for i,orig in enumerate(row):
            val=6 if n["kind"]=="special" and int(orig)==6 else int(new_color)
            for dr in (0,1):
                for dc in (0,1):
                    rr=2*(int(n["y"])+j)+dr;cc=2*(int(n["x"])+i)+dc
                    if 0<=rr<64 and 0<=cc<64:board[rr][cc]=val

def goal_satisfied(board,level):
    nm=node_map(level)
    for clue in level["clues"]:
        pat=clue["pixels"];target=int(pat[1][1])
        for j in range(3):
            for i in range(3):
                if i==1 and j==1:continue
                pos=(int(clue["x"])+(i-1)*4,int(clue["y"])+(j-1)*4)
                n=nm.get(pos)
                if n is None:continue
                cur=node_center_color(board,n)
                want_equal=(int(pat[j][i])==0)
                if want_equal and cur!=target:return False
                if not want_equal and cur==target:return False
    return True

def predict(board,action,levels):
    lev,ident=identify_level(board,levels)
    if lev is None:return None,{"abstain":"level_identification",**ident}
    mc=parse_mouse(action)
    if mc is None:return None,{"abstain":"non_mouse","level":lev["index"]}
    row,col=mc;n=clicked_node(lev,row,col)
    if n is None:return None,{"abstain":"click_not_unique_node","level":lev["index"]}
    out=clone_board(board);nm=node_map(lev)
    mask=n["click_mask"] if n["kind"]=="special" else lev["default_click_mask"]
    affected=[]
    for j in range(3):
        for i in range(3):
            if int(mask[j][i])!=1:continue
            pos=(int(n["x"])+(i-1)*4,int(n["y"])+(j-1)*4)
            q=nm.get(pos)
            if q is None:continue
            cur=node_center_color(out,q);nxt=next_color(lev["cycle"],cur)
            if nxt is None:return None,{"abstain":"node_color_outside_cycle","level":lev["index"],"value":cur}
            paint_node(out,q,nxt);affected.append(pos)
    if not affected:return None,{"abstain":"no_affected_nodes","level":lev["index"]}
    if goal_satisfied(out,lev):
        if int(lev["index"])+1>=len(levels):
            return None,{"abstain":"final_level_completion","level":lev["index"]}
        # The next scene is source-compiled static external data. This remains
        # source-assisted and is never presented as independent generalization.
        out=clone_board(levels[int(lev["index"])+1]["initial_frame"])
        return out,{"level":lev["index"],"branch":"compiled_next_scene","affected":affected}
    return out,{"level":lev["index"],"branch":"compiled_local_transition","affected":affected}

def evaluate(paths,manifest):
    levels=manifest["levels"];tot={"eligible":0,"predictions":0,"correct":0,"wrong":0,"abstain":0}
    branches={};reasons={};examples=[];per=[]
    for p in sorted(paths,key=lambda x:int(re.search(r"_p(\d+)_",x.name).group(1))):
        ev=load_events(p);pre=None;s={"actions":0,"predictions":0,"correct":0,"wrong":0,"abstain":0}
        for e in ev:
            if e.get("board") is None:continue
            if e.get("type")!="action":
                pre=e;continue
            if pre is None:
                pre=e;continue
            before=pre["board"];expected=e["board"];name=action_name(e)
            s["actions"]+=1;tot["eligible"]+=1
            pred,meta=predict(before,name,levels)
            if pred is None:
                s["abstain"]+=1;tot["abstain"]+=1
                k=meta.get("abstain","unknown");reasons[k]=reasons.get(k,0)+1
            else:
                s["predictions"]+=1;tot["predictions"]+=1
                br=meta.get("branch","unknown");branches[br]=branches.get(br,0)+1
                # gameplay rows0..62 exact; HUD row63 deliberately excluded.
                ok=(pred[:-1]==expected[:-1])
                if ok:s["correct"]+=1;tot["correct"]+=1
                else:
                    s["wrong"]+=1;tot["wrong"]+=1
                    if len(examples)<40:
                        diff=sum(a!=b for ra,rb in zip(pred[:-1],expected[:-1]) for a,b in zip(ra,rb))
                        examples.append({"trace":p.name,"action":name,"meta":meta,"diff_gameplay_cells":diff})
            pre=e
        per.append({"trace":p.name,**s})
    p=tot["predictions"];e=tot["eligible"]
    metrics={**tot,"accuracy":round(tot["correct"]/p,6) if p else None,
             "coverage":round(p/e,6) if e else 0.0}
    zero_wrong_gate=bool(p>0 and tot["wrong"]==0)
    return {
      "schema":"deus/arc3-ft09-compiled-observation-mechanism-eval/1",
      "rung":RUNG,"game":GAME,
      "manifest_source":manifest["source"],
      "aggregate":metrics,"branches":branches,"abstain_reasons":reasons,
      "per_trace":per,"wrong_examples":examples,
      "source_assisted_zero_wrong_transition_gate":zero_wrong_gate,
      "decision":{
        "source_assisted_transition_expert":zero_wrong_gate,
        "solver_promotion":False,
        "independent_generalization_promotion":False,
        "kaggle_packaging":False,
        "next_gate":"if transition gate passes, add source-compiled constraint planner while retaining public-source-assisted truth label",
      },
      "truth":{
        "public_source_assisted_manifest":True,
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
    sub=ap.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("compile");c.add_argument("--source",type=Path,required=True);c.add_argument("--output",type=Path,required=True)
    e=sub.add_parser("evaluate");e.add_argument("--manifest",type=Path,required=True);e.add_argument("--input",type=Path,action="append",default=[]);e.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=="compile":compile_manifest(a.source,a.output);return
    m=json.loads(a.manifest.read_text());d=evaluate(a.input,m);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"aggregate":d["aggregate"],"branches":d["branches"],"abstain":d["abstain_reasons"],
                      "gate":d["source_assisted_zero_wrong_transition_gate"],"decision":d["decision"]},sort_keys=True))
if __name__=="__main__":main()
