#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, time, uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
import arc_agi
from arc_agi import OperationMode

SHEET_ID=os.environ.get("DEUS_LIVEBUS_SPREADSHEET_ID","1pVtDbKFGECbogSR0-nrVDEecF8xQNelCux6GFUEmVrQ")
ARC_KEY=os.environ["ARC_API_KEY"]
SA_JSON=os.environ["DEUS_GOOGLE_SERVICE_ACCOUNT_JSON"]
GAME=os.environ.get("DEUS_ARC_GAME","ls20")
MAX_TURNS=int(os.environ.get("DEUS_ARC_MAX_TURNS","48"))
POLL_SECONDS=float(os.environ.get("DEUS_ARC_POLL_SECONDS","1.0"))
JOB_TIMEOUT=int(os.environ.get("DEUS_ARC_JOB_TIMEOUT_SECONDS","75"))
SOURCE_URL="https://github.com/kimbach91-prog/bl-infinity/tree/deus/arc-scorecard-ab-20260926/public_benchmark/arc-agi-3"

creds=service_account.Credentials.from_service_account_info(
    json.loads(SA_JSON),
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
gs=AuthorizedSession(creds)

HEADERS=[
"JOB_ID","TARGET_NODE","STATE","CREATED_AT_UTC","NOT_BEFORE_UTC","EXPIRES_AT_UTC","AUTHORITY_REF",
"COMMAND_MODE","COMMAND_TEXT","ARGS_JSON","WORKDIR_REL","ENV_JSON","TIMEOUT_S","MAX_OUTPUT_BYTES",
"LEASE_OWNER","LEASE_ACQUIRED_AT_UTC","LEASE_UNTIL_UTC","STARTED_AT_UTC","FINISHED_AT_UTC","EXIT_CODE",
"STDOUT_SHA256","STDERR_SHA256","STDOUT_PREVIEW","STDERR_PREVIEW","RESULT_REF","RECEIPT_ID","ATTEMPT","NOTES"
]

def now():
    return datetime.now(timezone.utc)

def frame_grid(frame):
    if hasattr(frame,"tolist"):
        frame=frame.tolist()
    if isinstance(frame,dict):
        for k in ("frame","grid","data"):
            if k in frame:
                return frame_grid(frame[k])
    if not isinstance(frame,(list,tuple)):
        return []
    out=[]
    for row in frame:
        if hasattr(row,"tolist"):
            row=row.tolist()
        if isinstance(row,(list,tuple)):
            out.append([int(x) for x in row])
    return out

def grid_text(grid):
    if not grid:
        return "<no-grid>"
    # Compact single-character alphabet for public ARC color values.
    alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    rows=[]
    for row in grid:
        rows.append("".join(alphabet[v] if 0<=v<len(alphabet) else "?" for v in row))
    return "\n".join(rows)

def diff_count(a,b):
    if not a or not b or len(a)!=len(b) or len(a[0])!=len(b[0]):
        return None
    return sum(1 for y,row in enumerate(a) for x,v in enumerate(row) if b[y][x]!=v)

def append_chat_job(prompt, turn):
    created=now()
    expires=created+timedelta(seconds=max(120,JOB_TIMEOUT+60))
    job_id=f"JOB-DEUS-ARC3-V6-ONLINE-{int(created.timestamp()*1000)}-{uuid.uuid4().hex[:8].upper()}"
    row=[
        job_id,"workstation-win-001","QUEUED",created.isoformat().replace("+00:00","Z"),"",
        expires.isoformat().replace("+00:00","Z"),"AUTH-GMAIL-REMOTE-EXEC-1a0ce128e8726a83",
        "NATIVE_INFERENCE_SCOPED","CHAT_V1",json.dumps([prompt],separators=(",",":")),
        "arc3-v6-online-fresh-agent","{}",str(JOB_TIMEOUT),"65536",
        "","","","","","","","","","","","","0",
        f"DEUS V6 fresh ARC ONLINE decision turn {turn}; owner scorecard lane; no replay route."
    ]
    rng=quote("84_WORKSTATION_REMOTE_JOBS!A:AB",safe="!:")
    url=f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{rng}:append"
    resp=gs.post(url,params={"valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"},json={"values":[row]},timeout=20)
    resp.raise_for_status()
    updated=resp.json()["updates"]["updatedRange"]
    m=re.search(r"!(?:A)?(\d+):",updated)
    if not m:
        raise RuntimeError(f"cannot parse append row: {updated}")
    return job_id,int(m.group(1))

def read_job_row(row_num):
    rng=quote(f"84_WORKSTATION_REMOTE_JOBS!A{row_num}:AB{row_num}",safe="!:")
    url=f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{rng}"
    resp=gs.get(url,timeout=20)
    resp.raise_for_status()
    vals=(resp.json().get("values") or [[]])[0]
    vals=vals+[""]*(28-len(vals))
    return dict(zip(HEADERS,vals[:28]))

def infer(prompt,turn):
    jid,row=append_chat_job(prompt,turn)
    deadline=time.monotonic()+JOB_TIMEOUT+35
    last=None
    while time.monotonic()<deadline:
        rec=read_job_row(row)
        state=rec["STATE"]
        last=rec
        if state in ("SUCCEEDED","FAILED","REJECTED","EXPIRED","CANCELLED"):
            if state!="SUCCEEDED" or str(rec["EXIT_CODE"]) not in ("","0"):
                raise RuntimeError(f"Brain3 job {jid} {state} exit={rec['EXIT_CODE']} err={rec['STDERR_PREVIEW'][:300]}")
            payload=json.loads(rec["STDOUT_PREVIEW"])
            return payload.get("content",""),{
                "job_id":jid,"row":row,"receipt_id":rec["RECEIPT_ID"],
                "model":payload.get("model"),"latency_s":payload.get("latency_s"),
                "usage":payload.get("usage")
            }
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"Brain3 job timeout {jid}; last={last and last['STATE']}")

def parse_decision(text,legal,w,h,turn):
    obj=None
    try:
        obj=json.loads(text.strip())
    except Exception:
        m=re.search(r"\{.*\}",text,re.S)
        if m:
            try: obj=json.loads(m.group(0))
            except Exception: obj=None
    if isinstance(obj,dict):
        a=str(obj.get("action","")).upper()
        if a in legal:
            data={}
            if legal[a].is_complex():
                try:
                    x=max(0,min(w-1,int(obj.get("x",w//2))))
                    y=max(0,min(h-1,int(obj.get("y",h//2))))
                    data={"x":x,"y":y}
                except Exception:
                    data={"x":w//2,"y":h//2}
            return a,data,str(obj.get("memory",""))[:1200],False
    # deterministic fail-closed exploration fallback
    names=sorted(legal)
    simple=[n for n in names if not legal[n].is_complex()]
    complexs=[n for n in names if legal[n].is_complex()]
    if simple and (turn < len(simple)*2 or not complexs):
        a=simple[turn%len(simple)]
        return a,{},"fallback simple probe",True
    a=(complexs or simple)[turn%len(complexs or simple)]
    data={"x":(turn*7)%max(1,w),"y":(turn*11)%max(1,h)} if legal[a].is_complex() else {}
    return a,data,"fallback geometry probe",True

def main():
    arcade=arc_agi.Arcade(arc_api_key=ARC_KEY,operation_mode=OperationMode.ONLINE)
    card=arcade.create_scorecard(
        tags=["deus-v6","fresh-agent","brain3-qwen-strong","owner-bound","no-route-replay"],
        source_url=SOURCE_URL,
        opaque={
            "system":"DEUS V6 fresh agent",
            "solver":"Brain3 Qwen3-4B strong via receipt-gated Drive remote jobs",
            "truth_boundary":"public-development owner-bound scorecard; not semi-private verification",
        },
    )
    env=None
    obs=None
    receipts=[]
    history=[]
    memory=""
    fallbacks=0
    started=time.monotonic()
    try:
        env=arcade.make(GAME,scorecard_id=card,save_recording=True,include_frame_data=True)
        if env is None: raise RuntimeError("ARC environment unavailable")
        obs=env.observation_space
        if obs is None: obs=env.reset()
        for turn in range(MAX_TURNS):
            state=getattr(obs.state,"name",str(obs.state))
            if state in ("WIN","GAME_OVER"): break
            grid=frame_grid(obs.frame)
            h=len(grid); w=len(grid[0]) if h else 1
            legal={a.name:a for a in env.action_space}
            if not legal: break
            actions={n:{"complex":bool(a.is_complex())} for n,a in legal.items()}
            recent=history[-4:]
            prompt=(
                "You are the DEUS V6 ARC-AGI-3 decision cortex. This is a fresh live run; do not assume or replay a memorized route. "
                "Infer action semantics only from visible observations and transition history. Complete the current level first, then minimize actions. "
                "Return EXACTLY one JSON object and no markdown: "
                "{\"action\":\"ACTION1\",\"x\":0,\"y\":0,\"memory\":\"short observed hypothesis\"}. "
                "For simple actions x/y are ignored. Use only an action listed as legal.\n"
                f"turn={turn} state={state} levels_completed={int(obs.levels_completed)} size={w}x{h}\n"
                f"legal_actions={json.dumps(actions,separators=(',',':'))}\n"
                f"memory={memory[:1000]}\nrecent={json.dumps(recent,separators=(',',':'))}\n"
                "grid_rows_top_to_bottom:\n"+grid_text(grid)
            )
            text,rcpt=infer(prompt,turn)
            receipts.append(rcpt)
            action_name,data,memory,fb=parse_decision(text,legal,w,h,turn)
            fallbacks+=int(fb)
            before_levels=int(obs.levels_completed)
            before=grid
            if data:
                nxt=env.step(legal[action_name],data=data)
            else:
                nxt=env.step(legal[action_name])
            if nxt is None: raise RuntimeError("ARC action returned no observation")
            obs=nxt
            after=frame_grid(obs.frame)
            history.append({
                "turn":turn,"action":action_name,"data":data,
                "changed":diff_count(before,after),
                "levels_before":before_levels,"levels_after":int(obs.levels_completed),
                "state":getattr(obs.state,"name",str(obs.state)),
                "brain3_job":rcpt["job_id"],"receipt":rcpt["receipt_id"],
            })
        final=arcade.close_scorecard(scorecard_id=card)
        if final is None: raise RuntimeError("ARC did not return finalized scorecard")
        dump=final.model_dump(mode="json")
        result={
            "schema":"deus-arc3-v6-online-fresh-agent/1",
            "card_id":card,
            "scorecard_url":f"https://arcprize.org/scorecards/{card}",
            "game":GAME,
            "score":dump.get("score"),
            "levels_completed":dump.get("total_levels_completed"),
            "total_levels":dump.get("total_levels"),
            "actions":dump.get("total_actions"),
            "turns":len(history),
            "brain3_calls":len(receipts),
            "fallbacks":fallbacks,
            "elapsed_s":time.monotonic()-started,
            "last_state":getattr(obs.state,"name",str(obs.state)) if obs is not None else None,
            "model_sha256":"7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5",
            "route_replay":False,
            "semi_private_claim":False,
            "history_tail":history[-8:],
            "brain3_receipts":[r["receipt_id"] for r in receipts if r.get("receipt_id")],
        }
        print("DEUS_ARC3_V6_RESULT="+json.dumps(result,ensure_ascii=True,separators=(",",":")))
        return 0
    except Exception as e:
        try:
            final=arcade.close_scorecard(scorecard_id=card)
        except Exception:
            final=None
        err={
            "schema":"deus-arc3-v6-online-fresh-agent/1",
            "state":"FAILED",
            "card_id":card,
            "scorecard_url":f"https://arcprize.org/scorecards/{card}",
            "error_type":type(e).__name__,
            "error":str(e)[:1000],
            "turns":len(history),"brain3_calls":len(receipts),"fallbacks":fallbacks,
            "history_tail":history[-5:],
        }
        print("DEUS_ARC3_V6_RESULT="+json.dumps(err,ensure_ascii=True,separators=(",",":")))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
