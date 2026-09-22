#!/usr/bin/env python3
"""R215: ft09 pixel-only exact-mechanics validator.

Development oracle:
  Public ARC Prize Foundation ft09 source, MIT licensed, was inspected outside
  runtime to formulate falsifiable mechanics hypotheses. This validator DOES
  NOT import/read that source at runtime and does not hard-code level answers.

Pixel-only hypotheses tested on public traces:
  * 6x6 rendered sprites decompose into a 3x3 logical pattern (2x scale).
  * uniform palette sprites are ordinary state tiles;
  * two-color sprites containing marker color 6 are functional tiles whose
    marker mask selects relative tiles affected by a click;
  * clue sprites encode local equal/not-equal constraints: zero means equal to
    clue center/reference; nonzero means different.
  * color-cycle successor is learned on p0-p9 only, keyed by visible palette.

Protocol:
  p0-p9  learn only visible palette color-cycle successors.
  p10-p19 frozen mechanics audit; no model updates.

This rung validates transition mechanics only. It is not a planner, not a full
solver, and not a Kaggle score/submission.
"""
from __future__ import annotations

import argparse, hashlib, json, re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191

RUNG=215
GAME="ft09-0d8bbf25"
SCALE=2
SPR=6
PITCH=8
MARKER=6
Grid=list[list[int]]

def pnum(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1

def stable(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"))

def digest(x:Any)->str:
    return hashlib.sha256(stable(x).encode()).hexdigest()

@dataclass
class Obj:
    anchor:tuple[int,int]
    bbox:tuple[int,int,int,int]
    pat:tuple[tuple[int,...],...]
    kind:str
    state:int|None

def downsample6(board:Grid,bb)->tuple[tuple[int,...],...]|None:
    r0,c0,r1,c1=bb
    if (r1-r0+1,c1-c0+1)!=(SPR,SPR): return None
    out=[]
    for j in range(3):
        row=[]
        for i in range(3):
            vals=[board[r0+2*j+dr][c0+2*i+dc] for dr in (0,1) for dc in (0,1)]
            if len(set(vals))!=1:return None
            row.append(int(vals[0]))
        out.append(tuple(row))
    return tuple(out)

def components_not_bg(board:Grid,bg:int):
    h,w=len(board),len(board[0])
    # Bottom row is HUD/timer. Exclude it from sprite segmentation.
    pts={(r,c) for r in range(max(0,h-1)) for c in range(w) if board[r][c]!=bg}
    out=[]
    while pts:
        z=next(iter(pts));pts.remove(z);q=deque([z]);comp=[z]
        while q:
            r,c=q.popleft()
            for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
                y=(r+dr,c+dc)
                if y in pts:
                    pts.remove(y);q.append(y);comp.append(y)
        rs=[r for r,c in comp];cs=[c for r,c in comp]
        out.append((comp,(min(rs),min(cs),max(rs),max(cs))))
    return out

def scene(board:Grid):
    h,w=len(board),len(board[0])
    bg=base.dominant_background(board[:-1] if h>1 else board)
    raw=[]
    for comp,bb in components_not_bg(board,bg):
        r0,c0,r1,c1=bb
        if (r1-r0+1,c1-c0+1)!=(SPR,SPR) or len(comp)!=SPR*SPR: continue
        pat=downsample6(board,bb)
        if pat is None:continue
        vals={v for row in pat for v in row}
        raw.append((bb,pat,vals))

    # Active state colors in ft09 are visually high-valued; 0/2/3/6 are
    # structural/clue-marker roles. This is a pixel-role prior, not a level key.
    uniform_hi=Counter()
    for bb,pat,vals in raw:
        if len(vals)==1:
            v=next(iter(vals))
            if v>=8:uniform_hi[v]+=1
    palette_seed={v for v,n in uniform_hi.items() if n>=1}

    objs=[]
    for bb,pat,vals in raw:
        r0,c0,r1,c1=bb
        anchor=(r0,c0)
        state=None;kind="other"
        if len(vals)==1:
            v=next(iter(vals))
            if v>=8:
                kind="ordinary";state=int(v)
            else:
                kind="clue_candidate"
        elif MARKER in vals and len(vals-{MARKER})==1:
            v=next(iter(vals-{MARKER}))
            if v>=8:
                kind="functional";state=int(v)
            else:
                kind="other"
        else:
            kind="clue_candidate"
        objs.append(Obj(anchor,bb,pat,kind,state))

    tiles={o.anchor:o for o in objs if o.kind in {"ordinary","functional"}}
    # A clue is only accepted if it geometrically addresses at least one tile
    # on the observed 8-pixel lattice. This filters decorations.
    clues=[]
    for o in objs:
        if o.kind!="clue_candidate":continue
        r,c=o.anchor
        neighbors=0
        for j in range(3):
            for i in range(3):
                if i==1 and j==1:continue
                if (r+(j-1)*PITCH,c+(i-1)*PITCH) in tiles:neighbors+=1
        if neighbors:clues.append(o)

    # Palette signature is visible-only: tile state colors plus clue centers
    # that are in the state-color range. It is a set, never a hidden level id.
    palette={int(o.state) for o in tiles.values() if o.state is not None}
    for o in clues:
        v=int(o.pat[1][1])
        if v>=8:palette.add(v)
    return {
      "bg":bg,"tiles":tiles,"clues":clues,
      "palette":tuple(sorted(palette)),
      "tile_anchors":tuple(sorted(tiles)),
      "clue_anchors":tuple(sorted(o.anchor for o in clues)),
    }

def clicked_tile(sc,action:str):
    click=c191.parse_mouse(action)
    if click is None:return None
    rr,cc=click
    for o in sc["tiles"].values():
        r0,c0,r1,c1=o.bbox
        if r0<=rr<=r1 and c0<=cc<=c1:return o
    return None

def effect_anchors(sc,o:Obj):
    r,c=o.anchor
    if o.kind=="ordinary":
        return ((r,c),)
    if o.kind=="functional":
        out=[]
        for j in range(3):
            for i in range(3):
                if o.pat[j][i]==MARKER:
                    a=(r+(j-1)*PITCH,c+(i-1)*PITCH)
                    if a in sc["tiles"]:out.append(a)
        return tuple(sorted(set(out)))
    return ()

def layout_sig(sc):
    # Position-only signature; recoloring does not alter it.
    return (sc["tile_anchors"],sc["clue_anchors"])

def level_token(e):
    for k in ("level","level_index","levels_completed"):
        if k in e:return (k,e.get(k))
    return None

def actual_transition(pre_event,event,sc0,sc1):
    a=level_token(pre_event);b=level_token(event)
    if a is not None and b is not None and a!=b:return True
    # Fallback remains pixel-derived.
    return layout_sig(sc0)!=layout_sig(sc1)

def state_map(sc):
    return {a:int(o.state) for a,o in sc["tiles"].items() if o.state is not None}

def learn_successors(paths):
    obs=defaultdict(Counter)
    evidence=Counter()
    for path in paths:
        ev=base.load_events(path);pre=ev[0]
        for e in ev[1:]:
            if e.get("type")!="action":pre=e;continue
            b0=base.as_grid(pre["board"]);b1=base.as_grid(e["board"])
            action=base.action_name(e)
            if not base.same_shape(b0,b1):pre=e;continue
            s0=scene(b0);s1=scene(b1);o=clicked_tile(s0,action)
            if o is None or actual_transition(pre,e,s0,s1):pre=e;continue
            aff=effect_anchors(s0,o)
            m0=state_map(s0);m1=state_map(s1)
            ps=s0["palette"]
            for a in aff:
                if a in m0 and a in m1 and m0[a]!=m1[a]:
                    obs[(ps,m0[a])][m1[a]]+=1
                    evidence["successor_examples"]+=1
            pre=e
    table={k:next(iter(c)) for k,c in obs.items() if len(c)==1}
    conflicts={repr(k):dict(c) for k,c in obs.items() if len(c)>1}
    return table,obs,conflicts,dict(evidence)

def cycle_next(table,sc,state:int):
    return table.get((sc["palette"],int(state)))

def apply_effect(board:Grid,sc,o:Obj,table):
    out=[row[:] for row in board]
    m=state_map(sc);updates={}
    for a in effect_anchors(sc,o):
        if a not in m:return None,{},f"missing_state:{a}"
        nxt=cycle_next(table,sc,m[a])
        if nxt is None:return None,{},f"unknown_successor:{sc['palette']}:{m[a]}"
        t=sc["tiles"][a];r0,c0,r1,c1=t.bbox
        if t.kind=="ordinary":
            for r in range(r0,r1+1):
                for c in range(c0,c1+1):out[r][c]=nxt
        else:
            for r in range(r0,r1+1):
                for c in range(c0,c1+1):
                    if out[r][c]!=MARKER:out[r][c]=nxt
        updates[a]=nxt
    return out,updates,None

def constraints_hold(sc,states):
    checked=0
    for clue in sc["clues"]:
        r,c=clue.anchor;ref=int(clue.pat[1][1])
        for j in range(3):
            for i in range(3):
                if i==1 and j==1:continue
                a=(r+(j-1)*PITCH,c+(i-1)*PITCH)
                if a not in states:continue
                checked+=1
                equal_required=(int(clue.pat[j][i])==0)
                ok=(states[a]==ref) if equal_required else (states[a]!=ref)
                if not ok:return False,checked
    return True,checked

def actual_changed_tile_anchors(s0,s1):
    a=state_map(s0);b=state_map(s1)
    return tuple(sorted(k for k in a if k in b and a[k]!=b[k]))

def core_equal(pred:Grid,actual:Grid):
    if not base.same_shape(pred,actual):return False
    h=len(pred)
    # Bottom row is timer/HUD and intentionally excluded in this mechanics rung.
    return pred[:max(0,h-1)]==actual[:max(0,h-1)]

def pack(c):
    d={k:int(v) for k,v in c.items()}
    for num,den,name in (
        ("topology_correct","topology_eval","topology_accuracy"),
        ("state_correct","state_eval","state_accuracy"),
        ("win_correct","win_eval","win_accuracy"),
        ("core_exact","core_eval","core_exact_rate"),
    ):
        d[name]=round(d.get(num,0)/d.get(den,1),6) if d.get(den,0) else None
    return d

def audit(paths,table):
    s=Counter();mistakes=[];parse=Counter()
    by_palette=defaultdict(Counter)
    for path in paths:
        ev=base.load_events(path);pre=ev[0];step=0
        for e in ev[1:]:
            if e.get("type")!="action":pre=e;continue
            step+=1
            b0=base.as_grid(pre["board"]);b1=base.as_grid(e["board"])
            action=base.action_name(e)
            if not base.same_shape(b0,b1):pre=e;continue
            sc0=scene(b0);sc1=scene(b1)
            parse["frames"]+=1;parse["tiles"]+=len(sc0["tiles"]);parse["clues"]+=len(sc0["clues"])
            o=clicked_tile(sc0,action)
            if o is None:
                s["non_tile_abstain"]+=1;pre=e;continue
            s["tile_clicks"]+=1
            pred,updates,err=apply_effect(b0,sc0,o,table)
            if err:
                s["successor_abstain"]+=1;pre=e;continue
            s["eligible"]+=1
            actual_win=actual_transition(pre,e,sc0,sc1)

            # Predict post-action tile states from pixels + learned cycle only.
            states=state_map(sc0);states.update(updates)
            pred_win,checked=constraints_hold(sc0,states)
            if checked==0:s["no_constraint_eval"]+=1
            else:
                s["win_eval"]+=1
                if pred_win==actual_win:s["win_correct"]+=1
                else:s["win_wrong"]+=1

            if not actual_win:
                pa=tuple(sorted(updates))
                aa=actual_changed_tile_anchors(sc0,sc1)
                s["topology_eval"]+=1
                if pa==aa:s["topology_correct"]+=1
                else:s["topology_wrong"]+=1

                m1=state_map(sc1);state_ok=all(a in m1 and m1[a]==v for a,v in updates.items())
                s["state_eval"]+=1
                if state_ok:s["state_correct"]+=1
                else:s["state_wrong"]+=1

                s["core_eval"]+=1
                if pred is not None and core_equal(pred,b1):s["core_exact"]+=1
                else:s["core_wrong"]+=1
            else:
                s["actual_level_transitions"]+=1

            pal=repr(sc0["palette"]);by_palette[pal]["eligible"]+=1
            if not actual_win and tuple(sorted(updates))==actual_changed_tile_anchors(sc0,sc1):
                by_palette[pal]["topology_correct"]+=1

            if len(mistakes)<40:
                bad=[]
                if checked and pred_win!=actual_win:bad.append("win")
                if not actual_win and tuple(sorted(updates))!=actual_changed_tile_anchors(sc0,sc1):bad.append("topology")
                if not actual_win and not all(a in state_map(sc1) and state_map(sc1)[a]==v for a,v in updates.items()):bad.append("state")
                if not actual_win and (pred is None or not core_equal(pred,b1)):bad.append("core")
                if bad:
                    mistakes.append({
                      "trace":path.name,"p":pnum(path),"step":step,"bad":bad,
                      "palette":sc0["palette"],"clicked_kind":o.kind,
                      "clicked_anchor":o.anchor,"pred_affected":tuple(sorted(updates)),
                      "actual_affected":None if actual_win else actual_changed_tile_anchors(sc0,sc1),
                      "pred_win":pred_win,"actual_win":actual_win,"constraints_checked":checked,
                    })
            pre=e
    return pack(s),dict(parse),{k:dict(v) for k,v in by_palette.items()},mistakes

def run(paths):
    ps=sorted(paths,key=pnum)
    nums=[pnum(x) for x in ps]
    if nums!=list(range(20)):raise ValueError(f"exact p0..p19 required; got {nums}")
    table,obs,conflicts,learn=learn_successors(ps[:10])
    held,parse,by_palette,mistakes=audit(ps[10:],table)
    topo=held.get("topology_accuracy")
    state=held.get("state_accuracy")
    win=held.get("win_accuracy")
    core=held.get("core_exact_rate")
    gate=bool(
      held.get("eligible",0)>=200 and
      held.get("topology_eval",0)>=100 and topo is not None and topo>=0.98 and
      state is not None and state>=0.99 and
      held.get("win_eval",0)>=50 and win is not None and win>=0.98 and
      held.get("core_eval",0)>=100 and core is not None and core>=0.90
    )
    return {
      "schema":"deus/arc3-ft09-pixel-exact-mechanics-validator/1",
      "rung":RUNG,"game":GAME,
      "development_oracle":{
        "source":"axobase001/arc-agi-games ft09/0d8bbf25/ft09.py",
        "source_license":"MIT",
        "source_blob_sha":"b492f97e518ace5e5a06d6bf06e97054f73be3fb",
        "runtime_reads_or_imports_source":False,
        "purpose":"formulate falsifiable mechanics only",
      },
      "protocol":{
        "cycle_fit":"p0-p9 only",
        "mechanics_audit":"p10-p19 frozen",
        "runtime_features":"pixels + current action + p0-p9 learned visible-palette successor table",
        "hud_policy":"bottom timer row excluded from core-world exactness",
      },
      "cycle_model":{
        "keys":len(obs),"deterministic_keys":len(table),"conflicted_keys":len(conflicts),
        "conflicts":conflicts,"evidence":learn,
        "table":[{"palette":list(k[0]),"from":k[1],"to":v} for k,v in sorted(table.items(),key=lambda z:repr(z[0]))],
      },
      "heldout":held,"parse_summary":parse,"by_palette":by_palette,
      "mistakes":mistakes,
      "mechanism_gate_pass":gate,
      "promotion":{
        "mechanism_gate":gate,
        "solver_promotion":False,
        "kaggle_packaging":False,
        "next_if_pass":"build pixel-only CSP/modular planner and validate solve/replay behavior",
        "next_if_fail":"repair only parser/mechanics falsifier classes; do not retune target-color heuristics",
      },
      "truth":{
        "public_trace_only":True,
        "source_code_not_loaded_at_runtime":True,
        "external_solver_code_imported":False,
        "p0_p9_only_updates_cycle_model":True,
        "p10_p19_never_update_model":True,
        "independent_generalization_claim":False,
        "planner_or_solver_claim":False,
        "full_game_solve_claim":False,
        "kaggle_execution":False,
        "competition_submission":False,
        "submission_quota_spent":False,
        "owner_score_claim":False,
      }
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args();d=run(a.input)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
      "rung":RUNG,"cycle_model":{"keys":d["cycle_model"]["keys"],"deterministic":d["cycle_model"]["deterministic_keys"],"conflicts":d["cycle_model"]["conflicted_keys"]},
      "heldout":d["heldout"],"parse":d["parse_summary"],
      "gate":d["mechanism_gate_pass"],"mistake_count":len(d["mistakes"]),
      "promotion":d["promotion"],
    },sort_keys=True))
if __name__=="__main__":main()
