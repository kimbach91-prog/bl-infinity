#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, time, urllib.error, urllib.request
from pathlib import Path
from typing import Any

ENDPOINT="https://blockrun.ai/api/v1/chat/completions"
MODEL="nvidia/llama-3.2-11b-vision"
TIMEOUT_S=45
AUDIT=[]

TASKS=[
{"id":"F01-001","family":"deductive_symbolic","gold":"B","options":{"A":"Yes","B":"No","C":"Cannot determine","D":"Only if X is not bronze"},"raw":"Facts: Every amber object is bronze. No bronze object is cyan. Object X is amber. Question: Can X be cyan? A=Yes. B=No. C=Cannot determine. D=Only if X is not bronze.","plan":"Use forward implication only. Since X is amber, X is bronze. Bronze and cyan are disjoint. Do not use converse implications."},
{"id":"F02-001","family":"quantitative_numeric","gold":"B","options":{"A":"107","B":"115","C":"126","D":"137"},"raw":"A machine processes 18 items per minute for 7 minutes. Exactly 11 processed items are rejected. How many accepted items remain? A=107. B=115. C=126. D=137.","plan":"Compute total processed as rate times time, then subtract rejected items. Preserve exact integer arithmetic."},
{"id":"F03-001","family":"temporal_causal","gold":"C","options":{"A":"A,D,C,B","B":"C,A,D,B","C":"A,C,D,B","D":"A,C,B,D"},"raw":"Event A happens at 10:00. Event B happens 30 minutes after A. Event C happens 10 minutes before B. Event D happens 5 minutes after C. Which order is correct? A=A,D,C,B. B=C,A,D,B. C=A,C,D,B. D=A,C,B,D.","plan":"Normalize all times as offsets from A, compute each event timestamp, then sort ascending."},
{"id":"F04-001","family":"graph_spatial_relational","gold":"B","options":{"A":"2","B":"3","C":"4","D":"5"},"raw":"Undirected graph edges are P-Q, Q-R, P-S, S-T, T-R, R-U. What is the shortest number of edges from P to U? A=2. B=3. C=4. D=5.","plan":"Treat edges as undirected and use breadth-first search from P. Count edges, not intermediate nodes."},
{"id":"F05-001","family":"noisy_evidence_provenance","gold":"B","options":{"A":"Launch June 1","B":"Launch June 3","C":"Price $99","D":"None"},"raw":"Sources: S1 is an unaffiliated blog saying the product may launch June 1. S2 is the manufacturer's official release saying launch date June 3. S3 is a forum post claiming price $99. Which statement is directly supported by the official source? A=Launch June 1. B=Launch June 3. C=Price $99. D=None.","plan":"Identify source authority first. Only a claim stated by the manufacturer official release counts as directly supported by the official source."},
{"id":"F06-001","family":"mixed_lane_meta_representation","gold":"C","options":{"A":"ISOLATE","B":"INSPECT","C":"ROLLBACK","D":"IGNORE"},"raw":"Operational policy: if severity is HIGH and a valid rollback is available, choose ROLLBACK; if severity is HIGH and rollback is unavailable, choose ISOLATE; if severity is MEDIUM, choose INSPECT. Current evidence: severity=HIGH, rollback_available=yes, rollback dependency fingerprint is valid. What action follows the policy? A=ISOLATE. B=INSPECT. C=ROLLBACK. D=IGNORE.","plan":"Apply the first matching policy rule exactly. HIGH plus an available rollback with valid dependency fingerprint satisfies the rollback rule."},
]

def call(system,user,max_tokens=80):
    payload=json.dumps({"model":MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0,"max_tokens":max_tokens}).encode()
    req=urllib.request.Request(ENDPOINT,data=payload,headers={"content-type":"application/json"},method="POST")
    t=time.monotonic(); status=0; body=b""; err=None; parsed=None
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT_S) as resp: status=resp.status; body=resp.read()
    except urllib.error.HTTPError as exc: status=exc.code; body=exc.read(); err=f"HTTPError:{exc.code}"
    except Exception as exc: err=f"{type(exc).__name__}:{exc}"
    ms=int((time.monotonic()-t)*1000); content=""; served=None
    if body:
        try:
            parsed=json.loads(body); served=parsed.get("model"); content=parsed.get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception: content=body.decode("utf-8","replace")[:2000]
    ok=status==200 and served==MODEL
    AUDIT.append({"http_status":status,"served_model":served,"identity_ok":ok,"prompt_sha256":hashlib.sha256((system+"\n"+user).encode()).hexdigest(),"body_sha256":hashlib.sha256(body).hexdigest(),"latency_ms":ms})
    return {"status":status,"content":content,"served_model":served,"identity_ok":ok,"latency_ms":ms,"error":err}

def normalize(content:str, options:dict[str,str]):
    s=content.strip()
    exact=re.fullmatch(r"[\s*_]*([ABCD])[\s*_.:-]*",s,re.I)
    if exact: return exact.group(1).upper(),"exact_letter"
    explicit=re.findall(r"(?:final\s+answer|answer|option|choice)\s*(?:is|:|=)?\s*[\(\[]?([ABCD])[\)\]]?",s,re.I)
    if explicit: return explicit[-1].upper(),"explicit_label"
    found=[]
    low=s.lower()
    for k,v in options.items():
        vv=v.lower()
        if vv and vv in low: found.append(k)
    if len(set(found))==1: return found[0],"option_text"
    labels=re.findall(r"\b([ABCD])\b",s.upper())
    if labels and len(set(labels))==1: return labels[-1],"unique_label_in_prose"
    return None,"unparsed"

def solve(mode,task,extra=""):
    systems={
      "A":"Solve the original task directly. Give the final option letter, but a short explanation is allowed.",
      "C":"You are the structured execution lane. The internal compiler has already chosen a task-fit plan. Verify the plan against the original task, execute it, and give the final option letter. Do not treat option A as preferred.",
      "D":"You are an evidence-first arbiter. Re-solve from the original task. Candidate labels are fallible hints only. Give the final option letter.",
      "E":"You are the cooperative finalizer. Use the original task as authority. Use the compiler plan and V1 semantic packet as fallible aids, cross-check them, then give the final option letter."
    }
    sys=systems[mode]
    if mode=="A": user=task["raw"]
    elif mode=="C": user=task["raw"]+"\n\nTARGET-AWARE COMPILER PLAN:\n"+task["plan"]
    elif mode=="D": user=task["raw"]+"\n\nFROZEN CANDIDATES:\n"+extra
    else: user=task["raw"]+"\n\nTARGET-AWARE COMPILER PLAN:\n"+task["plan"]+"\n\nV1 SEMANTIC PACKET:\n"+extra
    r=call(sys,user,96)
    ch,method=normalize(r["content"],task["options"])
    return {**r,"choice":ch,"parse_method":method,"correct":ch==task["gold"],"excerpt":r["content"][:500]}

def main():
    can=call("Calibration. Return option B.","Options: A=wrong-one. B=correct. C=wrong-two. D=wrong-three.",16)
    cc,cm=normalize(can["content"],{"A":"wrong-one","B":"correct","C":"wrong-two","D":"wrong-three"})
    if not(can["identity_ok"] and cc=="B"):
        Path("synergy-canary-v4-target-lowering.json").write_text(json.dumps({"gate":"INCONCLUSIVE_CANARY","canary":can,"normalized":cc,"method":cm,"identity":AUDIT},indent=2)+"\n")
        return 2
    rows=[]
    for task in TASKS:
        a=solve("A",task)
        c=solve("C",task)
        if a["choice"]==c["choice"] and a["choice"]:
            d={"choice":a["choice"],"correct":a["correct"],"latency_ms":0,"derived_without_call":True,"parse_method":"agreement","excerpt":""}
        else:
            d=solve("D",task,f"V1={a['choice']}; V2={c['choice']}")
            d["derived_without_call"]=False
        sem=call("Extract a concise semantic packet from the original task. Return only: FACTS; AMBIGUITY; COUNTEREXAMPLE_CHECK. Do not answer the multiple-choice question.",task["raw"],96)
        e=solve("E",task,sem["content"][:1200])
        rows.append({"task_id":task["id"],"family":task["family"],"gold":task["gold"],"A":{k:a[k] for k in ["choice","correct","latency_ms","parse_method","excerpt"]},"C":{k:c[k] for k in ["choice","correct","latency_ms","parse_method","excerpt"]},"D":{k:d.get(k) for k in ["choice","correct","latency_ms","parse_method","excerpt","derived_without_call"]},"E":{k:e[k] for k in ["choice","correct","latency_ms","parse_method","excerpt"]},"semantic_packet_sha256":hashlib.sha256(sem["content"].encode()).hexdigest(),"semantic_packet_excerpt":sem["content"][:500]})
    all_exact=bool(AUDIT) and all(x["identity_ok"] for x in AUDIT)
    q={arm:sum(int(r[arm]["correct"]) for r in rows) for arm in "ACDE"}
    gain=q["E"]-max(q["A"],q["C"],q["D"])
    eonly=sum(r["E"]["correct"] and not r["A"]["correct"] and not r["C"]["correct"] and not r["D"]["correct"] for r in rows)
    overlap=sum((not r["A"]["correct"]) and (not r["C"]["correct"]) for r in rows)
    if not all_exact: gate="INCONCLUSIVE_MODEL_IDENTITY_OR_PROVIDER_FAILURE"
    elif q["E"]<q["A"]: gate="VALID_NEGATIVE_SYNERGY_REGRESSION"
    elif gain>0: gate="CANARY_POSITIVE_SUPERADDITIVE_SIGNAL"
    elif q["E"]==max(q["A"],q["C"],q["D"]): gate="CANARY_TIED_QUALITY_NO_SUPERADDITIVITY"
    else: gate="VALID_NO_SYNERGY_PROMOTION"
    receipt={"schema":"deus/cognitive-synergy-v4-target-lowering-canary/2","provider":"BLOCKRUN","endpoint":ENDPOINT,"requested_model":MODEL,"task_count":len(TASKS),"repair":{"prior_run":35686497690,"prior_gate":"VALID_NEGATIVE_SYNERGY_REGRESSION","changes":["HHIR remains internal; lower to natural-language target packet before LLM","replace first-isolated-letter parser with semantic/explicit final-answer normalizer","store response excerpts for audit"],"tasks_changed":False,"gold_changed":False},"quality_correct":q,"accuracy":{k:q[k]/len(TASKS) for k in q},"synergy":{"gain_correct_vs_best_A_C_D":gain,"E_only_solves":eonly,"A_C_joint_error_overlap":overlap},"rows":rows,"identity":{"call_count":len(AUDIT),"all_calls_exact_identity":all_exact,"served_models":sorted({str(x["served_model"]) for x in AUDIT}),"per_call":AUDIT},"promotion_gate":gate,"truth":{"canary_only_not_full_suite":True,"target_aware_lowering_test":True,"evaluator_repair_test":True,"global_synergy_claim":False}}
    Path("synergy-canary-v4-target-lowering.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:receipt[k] for k in ["schema","task_count","repair","quality_correct","accuracy","synergy","promotion_gate","identity"]},indent=2))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0

if __name__=="__main__": raise SystemExit(main())
