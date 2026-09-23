#!/usr/bin/env python3
"""R336: source-free p0-p4 falsifier for frozen R335 relational/phase grammar.

The detector is generic and game-ID blind. It activates only when a board exposes:
- two vertically separated long 7-high strips with the same slot geometry,
- a cursor marker in the gap,
- repeated 7x7 legend boxes whose border colors match the two strips,
- a unique source-token -> target-token relation under D4-canonical glyph identity.

Action semantics are learned only from four public traces and evaluated on the fifth.
No p5-p19 files are staged or read. Ambiguity => abstain.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_generic_relational_transducer_335 as r335

SCHEMA="deus/arc3-r336-r335-sourcefree-p0p4/1"
IDEMPOTENCY="R336-R335-SOURCEFREE-P0P4-20260923-001"

@dataclass(frozen=True)
class Rect:
    top:int; left:int; bottom:int; right:int; color:int
    @property
    def h(self): return self.bottom-self.top+1
    @property
    def w(self): return self.right-self.left+1

def runs(row):
    out=[]
    if not row: return out
    s=0
    for i in range(1,len(row)+1):
        if i==len(row) or row[i]!=row[s]:
            out.append((s,i-1,int(row[s])))
            s=i
    return out

def find_border_rects(board):
    h=len(board); w=len(board[0]) if h else 0
    found=set()
    # ARC TR87-style panels are 7 cells high, but no color, location, game ID,
    # action name, or slot count is hard-coded.
    for top in range(0,max(0,h-6)):
        bottom=top+6
        for left,right,color in runs(board[top]):
            width=right-left+1
            if width < 7 or width%7:
                continue
            if any(int(board[bottom][c])!=color for c in range(left,right+1)):
                continue
            if any(int(board[r][left])!=color or int(board[r][right])!=color for r in range(top,bottom+1)):
                continue
            interior=[int(board[r][c]) for r in range(top+1,bottom) for c in range(left+1,right)]
            if not interior or all(v==color for v in interior):
                continue
            found.add((top,left,bottom,right,color))
    return [Rect(*x) for x in sorted(found)]

def strip_tokens(board, rect):
    if rect.h!=7 or rect.w<21 or rect.w%7:
        return None
    n=rect.w//7
    toks=[]
    for i in range(n):
        # Five-cell glyph body at each seven-cell station.
        c0=rect.left+1+i*7
        pts=[]
        for rr in range(rect.top+1,rect.top+6):
            for cc in range(c0,min(c0+5,rect.right)):
                if int(board[rr][cc])!=rect.color:
                    pts.append((rr-(rect.top+1),cc-c0))
        toks.append(r335.d4_canonical(pts))
    return tuple(toks)

def box_token(board, rect):
    if rect.h!=7 or rect.w!=7:
        return None
    pts=[]
    for rr in range(rect.top+1,rect.bottom):
        for cc in range(rect.left+1,rect.right):
            if int(board[rr][cc])!=rect.color:
                pts.append((rr-(rect.top+1),cc-(rect.left+1)))
    return r335.d4_canonical(pts)

def infer_long_pair(board, rects):
    longs=[r for r in rects if r.w>=21 and r.w%7==0]
    cands=[]
    for a in longs:
        for b in longs:
            if b.top<=a.bottom: continue
            if a.left!=b.left or a.w!=b.w or a.color==b.color: continue
            gap=b.top-a.bottom-1
            if not (1<=gap<=12): continue
            ta=strip_tokens(board,a); tb=strip_tokens(board,b)
            if ta is None or tb is None or len(ta)!=len(tb) or len(ta)<2: continue
            cands.append((gap,a,b,ta,tb))
    if not cands: return None
    cands.sort(key=lambda x:(x[0],-x[1].w,x[1].top,x[1].left))
    best=cands[0]
    # Ambiguous geometry at identical priority => abstain.
    ties=[x for x in cands if (x[0],-x[1].w)==(best[0],-best[1].w)]
    if len(ties)>1:
        sig={(x[1].top,x[1].left,x[2].top,x[2].left) for x in ties}
        if len(sig)>1: return None
    return best

def infer_legend_relation(board, rects, src_color, dst_color, long_tops):
    small=[r for r in rects if r.w==7 and r.top not in long_tops]
    src=[r for r in small if r.color==src_color]
    dst=[r for r in small if r.color==dst_color]
    pairs=[]
    for s in src:
        same=[d for d in dst if d.top==s.top and d.left>s.right and 1<=d.left-s.right-1<=6]
        if not same: continue
        d=min(same,key=lambda x:x.left)
        pairs.append((s,d))
    if len(pairs)<2: return None
    mp={}
    for s,d in pairs:
        st=box_token(board,s); dt=box_token(board,d)
        if not st or not dt: return None
        k=(st,)
        v=(dt,)
        if k in mp and mp[k]!=v: return None
        mp[k]=v
    if len(mp)<2: return None
    return r335.Relation(mp)

def infer_cursor(board, upper, lower, slots):
    r0=upper.bottom+1; r1=lower.top
    if r1<=r0: return None
    cells=[int(board[r][c]) for r in range(r0,r1) for c in range(upper.left,upper.right+1)]
    if not cells: return None
    bg=Counter(cells).most_common(1)[0][0]
    pts=[]
    for r in range(r0,r1):
        for c in range(upper.left,upper.right+1):
            if int(board[r][c])!=bg:
                pts.append((r,c))
    if not pts: return None
    # Keep x columns supported by the marker; take median column.
    cols=sorted(c for r,c in pts)
    x=cols[len(cols)//2]
    centers=[upper.left+3+i*7 for i in range(slots)]
    idx=min(range(slots),key=lambda i:abs(centers[i]-x))
    # Marker must actually be near the selected station.
    if abs(centers[idx]-x)>4: return None
    return idx

def parse_state(board):
    rects=find_border_rects(board)
    lp=infer_long_pair(board,rects)
    if lp is None: return None
    gap,upper,lower,input_tokens,answer_tokens=lp
    rel=infer_legend_relation(board,rects,upper.color,lower.color,{upper.top,lower.top})
    if rel is None: return None
    target=rel.relate(input_tokens)
    if target is None or len(target)!=len(answer_tokens): return None
    cursor=infer_cursor(board,upper,lower,len(answer_tokens))
    if cursor is None: return None
    return {
        "input":input_tokens,
        "answer":answer_tokens,
        "target":target,
        "cursor":cursor,
        "slots":len(answer_tokens),
        "src_color":upper.color,
        "dst_color":lower.color,
    }

def event_rows(path):
    ev=r246.load_events(path)
    rows=[]
    pre=ev[0]
    for e in ev[1:]:
        if e.get("type")!="action":
            pre=e; continue
        b=parse_state(pre["board"]); a=parse_state(e["board"])
        rows.append({
            "trace":path.name,
            "action":r246.action_name(e),
            "before":b,"after":a,
            "reward":float(e.get("reward",0) or 0),
            "level_before":int(pre.get("level",0) or 0),
            "level_after":int(e.get("level",0) or 0),
            "state_after":str(e.get("state","")),
        })
        pre=e
    return rows

def fit_model(train_rows):
    edits=defaultdict(lambda:defaultdict(Counter))
    edit_support=defaultdict(lambda:defaultdict(lambda:defaultdict(set)))
    moves=defaultdict(lambda:defaultdict(Counter))
    move_support=defaultdict(lambda:defaultdict(lambda:defaultdict(set)))
    stats=Counter()
    for row in train_rows:
        b=row["before"]; a=row["after"]
        if b is None or a is None: continue
        if b["input"]!=a["input"] or b["target"]!=a["target"] or b["slots"]!=a["slots"]:
            continue
        dif=[i for i,(x,y) in enumerate(zip(b["answer"],a["answer"])) if x!=y]
        act=row["action"]; tr=row["trace"]
        if len(dif)==1 and b["cursor"]==a["cursor"]==dif[0]:
            old=b["answer"][dif[0]]; new=a["answer"][dif[0]]
            edits[act][old][new]+=1
            edit_support[act][old][new].add(tr)
            stats["edit_observations"]+=1
        elif len(dif)==0:
            old=b["cursor"]; new=a["cursor"]
            moves[act][old][new]+=1
            move_support[act][old][new].add(tr)
            stats["move_observations"]+=1

    edit_map={}
    for act,byold in edits.items():
        for old,cnt in byold.items():
            if len(cnt)!=1: continue
            new=next(iter(cnt))
            if len(edit_support[act][old][new])>=2:
                edit_map[(act,old)]=new

    move_map={}
    for act,byold in moves.items():
        for old,cnt in byold.items():
            if len(cnt)!=1: continue
            new=next(iter(cnt))
            if len(move_support[act][old][new])>=2:
                move_map[(act,old)]=new
    return edit_map,move_map,dict(stats)

def predict(row,edit_map,move_map):
    b=row["before"]
    if b is None: return None
    act=row["action"]
    key=(act,b["answer"][b["cursor"]])
    if key in edit_map:
        ans=list(b["answer"]); ans[b["cursor"]]=edit_map[key]
        return (b["input"],tuple(ans),b["target"],b["cursor"],b["slots"])
    mk=(act,b["cursor"])
    if mk in move_map:
        return (b["input"],b["answer"],b["target"],move_map[mk],b["slots"])
    return None

def actual_tuple(s):
    if s is None:return None
    return (s["input"],s["answer"],s["target"],s["cursor"],s["slots"])

def run_game(paths):
    ps=sorted(paths,key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(5)):
        raise SystemExit("exact p0-p4 required")
    rows_by=[event_rows(p) for p in ps]
    total=Counter(); folds=[]; relation_goal_frames=0; reward_confirmed=0
    for held in range(5):
        train=[r for i,rs in enumerate(rows_by) if i!=held for r in rs]
        test=rows_by[held]
        em,mm,fitstats=fit_model(train)
        m=Counter()
        for row in test:
            if row["before"] is not None: m["parsed_before"]+=1
            if row["after"] is not None:
                m["parsed_after"]+=1
                if row["after"]["answer"]==row["after"]["target"]:
                    m["target_match_after"]+=1
                    if row["reward"]>0 or row["level_after"]>row["level_before"] or "FINISHED" in row["state_after"].upper():
                        m["target_match_reward_or_level"]+=1
            pred=predict(row,em,mm)
            if pred is None:
                m["abstain"]+=1; continue
            m["predicted"]+=1
            if pred==actual_tuple(row["after"]): m["correct"]+=1
            else: m["wrong"]+=1
        for k,v in m.items(): total[k]+=v
        folds.append({
            "held_trace":held,
            "fit":{"edit_rules":len(em),"move_rules":len(mm),**fitstats},
            "eval":dict(m),
        })
    verdict="ABSTAIN"
    if total["predicted"]>0 and total["wrong"]==0:
        verdict="SOURCEFREE_DYNAMICS_ZERO_WRONG"
    elif total["wrong"]>0:
        verdict="SOURCEFREE_DYNAMICS_FALSIFIED"
    return {
        "schema":SCHEMA,
        "idempotency_key":IDEMPOTENCY,
        "protocol":{
            "data":"public p0-p4 only",
            "outer_eval":"5-fold leave-one-trace-out",
            "game_id_branching":False,
            "p5_p9_staged_or_read":False,
            "p10_p19_staged_or_read":False,
            "ambiguity_policy":"abstain",
        },
        "metrics":dict(total),
        "folds":folds,
        "verdict":verdict,
        "truth":{
            "source_free_runtime_logic":True,
            "public_offline_only":True,
            "game_source_read":False,
            "provider_execution":False,
            "kaggle_submission":False,
            "whole_game_solver_promotion":False,
        },
    }

def aggregate(paths):
    rows=[json.loads(p.read_text()) for p in paths]
    c=Counter(); verdicts=Counter()
    for d in rows:
        assert d["schema"]==SCHEMA and d["idempotency_key"]==IDEMPOTENCY
        assert d["protocol"]["p5_p9_staged_or_read"] is False
        assert d["protocol"]["p10_p19_staged_or_read"] is False
        verdicts[d["verdict"]]+=1
        for k,v in d["metrics"].items(): c[k]+=int(v)
    active=sum(1 for d in rows if d["metrics"].get("predicted",0)>0)
    zero_wrong=sum(1 for d in rows if d["metrics"].get("predicted",0)>0 and d["metrics"].get("wrong",0)==0)
    if c["predicted"]>0 and c["wrong"]==0:
        verdict="R335_SOURCEFREE_P0P4_ZERO_WRONG_SIGNAL"
    elif c["wrong"]>0:
        verdict="R335_SOURCEFREE_P0P4_FALSIFIED"
    else:
        verdict="R335_SOURCEFREE_P0P4_NO_SIGNAL"
    return {
        "schema":"deus/arc3-r336-r335-sourcefree-p0p4-aggregate/1",
        "idempotency_key":IDEMPOTENCY,
        "game_count":len(rows),
        "active_games":active,
        "zero_wrong_active_games":zero_wrong,
        "metrics":dict(c),
        "game_verdicts":dict(verdicts),
        "verdict":verdict,
        "truth":{
            "public_offline_only":True,
            "p5_p19_unread":True,
            "independent_hidden_generalization_claim":False,
            "kaggle_execution":False,
            "competition_submission":False,
        },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--aggregate-dir",type=Path)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    if a.aggregate_dir:
        d=aggregate(sorted(a.aggregate_dir.glob("r336-game-*.json")))
    else:
        d=run_game(a.input)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "verdict":d["verdict"],
        "metrics":d.get("metrics"),
        "active_games":d.get("active_games"),
        "zero_wrong_active_games":d.get("zero_wrong_active_games"),
    },sort_keys=True))

if __name__=="__main__":
    main()
