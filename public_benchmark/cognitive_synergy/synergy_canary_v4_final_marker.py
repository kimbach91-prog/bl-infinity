#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re,time,urllib.error,urllib.request
from pathlib import Path

ENDPOINT="https://blockrun.ai/api/v1/chat/completions"
MODEL="nvidia/llama-3.2-11b-vision"
TIMEOUT_S=45
AUDIT=[]

TASKS=[
{"id":"F01-001","family":"deductive_symbolic","gold":"B","raw":"Facts: Every amber object is bronze. No bronze object is cyan. Object X is amber. Question: Can X be cyan? A=Yes. B=No. C=Cannot determine. D=Only if X is not bronze.","plan":"Use forward implication only. X amber implies X bronze. Bronze is disjoint from cyan. Do not assume converses."},
{"id":"F02-001","family":"quantitative_numeric","gold":"B","raw":"A machine processes 18 items per minute for 7 minutes. Exactly 11 processed items are rejected. How many accepted items remain? A=107. B=115. C=126. D=137.","plan":"Compute total processed as rate times time, then subtract rejected. Use exact integer arithmetic."},
{"id":"F03-001","family":"temporal_causal","gold":"C","raw":"Event A happens at 10:00. Event B happens 30 minutes after A. Event C happens 10 minutes before B. Event D happens 5 minutes after C. Which order is correct? A=A,D,C,B. B=C,A,D,B. C=A,C,D,B. D=A,C,B,D.","plan":"Normalize each event to an offset from A and sort timestamps ascending."},
{"id":"F04-001","family":"graph_spatial_relational","gold":"B","raw":"Undirected graph edges are P-Q, Q-R, P-S, S-T, T-R, R-U. What is the shortest number of edges from P to U? A=2. B=3. C=4. D=5.","plan":"Run breadth-first shortest path on exactly the stated undirected edges. Do not invent edges. Count edges."},
{"id":"F05-001","family":"noisy_evidence_provenance","gold":"B","raw":"Sources: S1 is an unaffiliated blog saying the product may launch June 1. S2 is the manufacturer's official release saying launch date June 3. S3 is a forum post claiming price $99. Which statement is directly supported by the official source? A=Launch June 1. B=Launch June 3. C=Price $99. D=None.","plan":"Identify the official source first, then select only the claim directly stated by that source."},
{"id":"F06-001","family":"mixed_lane_meta_representation","gold":"C","raw":"Operational policy: if severity is HIGH and a valid rollback is available, choose ROLLBACK; if severity is HIGH and rollback is unavailable, choose ISOLATE; if severity is MEDIUM, choose INSPECT. Current evidence: severity=HIGH, rollback_available=yes, rollback dependency fingerprint is valid. What action follows the policy? A=ISOLATE. B=INSPECT. C=ROLLBACK. D=IGNORE.","plan":"Apply the first matching policy rule exactly. HIGH plus valid available rollback selects ROLLBACK."}
]

def call(system,user,max_tokens=64):
    payload=json.dumps({"model":MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0,"max_tokens":max_tokens}).encode()
    req=urllib.request.Request(ENDPOINT,data=payload,headers={"content-type":"application/json"},method="POST")
    t=time.monotonic();status=0;body=b"";err=None
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT_S) as resp:status=resp.status;body=resp.read()
    except urllib.error.HTTPError as exc:status=exc.code;body=exc.read();err=f"HTTPError:{exc.code}"
    except Exception as exc:err=f"{type(exc).__name__}:{exc}"
    ms=int((time.monotonic()-t)*1000);content="";served=None
    if body:
        try:
            d=json.loads(body);served=d.get("model");content=d.get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception:content=body.decode("utf-8","replace")[:1000]
    ok=status==200 and served==MODEL
    AUDIT.append({"http_status":status,"served_model":served,"identity_ok":ok,"prompt_sha256":hashlib.sha256((system+"\n"+user).encode()).hexdigest(),"body_sha256":hashlib.sha256(body).hexdigest(),"latency_ms":ms,"error":err})
    return {"content":content,"latency_ms":ms,"identity_ok":ok,"status":status}

def marker(text):
    m=re.search(r"<FINAL>\s*([ABCD])\s*</FINAL>",text or "",re.I)
    return m.group(1).upper() if m else None

BASE="Solve the task carefully. Return ONLY one machine-readable final marker in the exact form <FINAL>X</FINAL>, where X is A, B, C, or D. Do not output any other text."

def solve(mode,t,extra=""):
    sys={
      "A":BASE+" Use the original raw task directly.",
      "C":BASE+" You are V2 target-aware structured lane. The plan is a fallible compiler aid; original task remains authoritative.",
      "D":BASE+" You are an evidence-first arbiter. Re-solve the original task; frozen candidate labels are fallible hints.",
      "E":BASE+" You are cooperative finalizer. Cross-check original task, target-aware plan, and V1 semantic packet; original task remains authoritative."
    }[mode]
    if mode=="A":u=t["raw"]
    elif mode=="C":u=t["raw"]+"\nTARGET_AWARE_PLAN: "+t["plan"]
    elif mode=="D":u=t["raw"]+"\nFROZEN_CANDIDATES: "+extra
    else:u=t["raw"]+"\nTARGET_AWARE_PLAN: "+t["plan"]+"\nV1_SEMANTIC_PACKET: "+extra
    r=call(sys,u,24);ch=marker(r["content"])
    return {"choice":ch,"correct":ch==t["gold"],"marker_valid":ch is not None,"latency_ms":r["latency_ms"],"raw_output":r["content"][:200],"identity_ok":r["identity_ok"]}

def main():
    cal=call(BASE,"Calibration: correct option is B. A=wrong. B=correct. C=wrong. D=wrong.",16)
    if not(cal["identity_ok"] and marker(cal["content"])=="B"):
        Path("synergy-canary-v4-final-marker.json").write_text(json.dumps({"gate":"INCONCLUSIVE_CALIBRATION","calibration":cal,"identity":AUDIT},indent=2)+"\n");return 2
    rows=[]
    for t in TASKS:
        a=solve("A",t);c=solve("C",t)
        if a["choice"]==c["choice"] and a["choice"]:
            d={"choice":a["choice"],"correct":a["correct"],"marker_valid":True,"latency_ms":0,"raw_output":"","identity_ok":True,"derived_without_call":True}
        else:
            d=solve("D",t,f"V1={a['choice']}; V2={c['choice']}");d["derived_without_call"]=False
        sem=call("Extract a concise task artifact. Output only three fields: FACTS=...; AMBIGUITY=...; COUNTEREXAMPLE_CHECK=.... Do not answer the A/B/C/D question.",t["raw"],96)
        e=solve("E",t,sem["content"][:1200])
        rows.append({"task_id":t["id"],"family":t["family"],"gold":t["gold"],"A":a,"C":c,"D":d,"E":e,"semantic_packet_sha256":hashlib.sha256(sem["content"].encode()).hexdigest()})
    exact=all(x["identity_ok"] for x in AUDIT)
    q={arm:sum(int(r[arm]["correct"]) for r in rows) for arm in "ACDE"}
    markers={arm:sum(int(r[arm]["marker_valid"]) for r in rows) for arm in "ACDE"}
    gain=q["E"]-max(q["A"],q["C"],q["D"])
    if not exact:gate="INCONCLUSIVE_IDENTITY"
    elif min(markers.values())<len(TASKS):gate="INCONCLUSIVE_MARKER_PROTOCOL"
    elif q["E"]<q["A"]:gate="VALID_NEGATIVE_SYNERGY_REGRESSION"
    elif gain>0:gate="CANARY_POSITIVE_SUPERADDITIVE_SIGNAL"
    elif q["E"]==max(q["A"],q["C"],q["D"]):gate="CANARY_TIED_QUALITY_NO_SUPERADDITIVITY"
    else:gate="VALID_NO_SYNERGY_PROMOTION"
    out={"schema":"deus/cognitive-synergy-final-marker-canary/3","prior_runs":[35686497690,35687001346],"task_count":6,"protocol":"FINAL_XML_MARKER_FIRST_AND_ONLY","quality_correct":q,"marker_valid":markers,"synergy_gain":gain,"rows":rows,"identity":{"call_count":len(AUDIT),"all_calls_exact_identity":exact,"served_models":sorted({str(x["served_model"]) for x in AUDIT}),"per_call":AUDIT},"promotion_gate":gate,"truth":{"tasks_changed":False,"gold_changed":False,"global_synergy_claim":False}}
    Path("synergy-canary-v4-final-marker.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:out[k] for k in ["schema","task_count","quality_correct","marker_valid","synergy_gain","identity","promotion_gate"]},indent=2))
    return 2 if gate.startswith("INCONCLUSIVE") else 0
if __name__=="__main__":raise SystemExit(main())
