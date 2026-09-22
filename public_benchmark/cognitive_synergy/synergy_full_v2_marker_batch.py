#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,time,urllib.error,urllib.request
from pathlib import Path

ENDPOINT="https://blockrun.ai/api/v1/chat/completions"
MODEL="nvidia/llama-3.2-11b-vision"
TIMEOUT_S=45
BASE="Solve carefully. Return ONLY one machine-readable marker in the exact form <FINAL>X</FINAL>, where X is A, B, C, or D. Do not output any other text."

FAMILY_PLAN={
"deductive_symbolic":"Use only stated implications/exclusions/membership; do not assume converse implications. Test each option against the facts.",
"quantitative_numeric":"Translate quantities into exact arithmetic with units, calculate deterministically, and map the result to an option.",
"temporal_causal":"Normalize all relative time/order constraints to a consistent timeline, then sort/compare exactly.",
"graph_spatial_relational":"Use exactly the stated graph/relations. For shortest paths use breadth-first reasoning and count edges exactly; invent no edge.",
"noisy_evidence_provenance":"Separate source authority from claim content. Attribute each claim before selecting what the requested authority directly supports.",
"mixed_lane_meta_representation":"Treat policy rules and current state as typed inputs; apply the first matching valid rule and preserve validity/fingerprint conditions."
}

def marker(s):
    m=re.search(r"<FINAL>\s*([ABCD])\s*</FINAL>",s or "",re.I)
    return m.group(1).upper() if m else None

class Runner:
    def __init__(self): self.audit=[]
    def call(self,system,user,max_tokens=32):
        p=json.dumps({"model":MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0,"max_tokens":max_tokens}).encode()
        req=urllib.request.Request(ENDPOINT,data=p,headers={"content-type":"application/json"},method="POST")
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
        self.audit.append({"http_status":status,"served_model":served,"identity_ok":ok,"prompt_sha256":hashlib.sha256((system+"\n"+user).encode()).hexdigest(),"body_sha256":hashlib.sha256(body).hexdigest(),"latency_ms":ms,"error":err})
        return {"content":content,"latency_ms":ms,"identity_ok":ok,"status":status}
    def scored(self,system,user,gold):
        r=self.call(system,user,24);ch=marker(r["content"])
        return {"choice":ch,"correct":ch==gold,"marker_valid":ch is not None,"latency_ms":r["latency_ms"],"identity_ok":r["identity_ok"],"status":r["status"],"output_sha256":hashlib.sha256(r["content"].encode()).hexdigest()}
    def semantic(self,raw):
        return self.call("Extract only a concise task artifact: FACTS=...; AMBIGUITY=...; COUNTEREXAMPLE_CHECK=.... Do not answer the A/B/C/D question.",raw,96)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--batch-index",type=int,required=True);ap.add_argument("--batch-size",type=int,default=6);ap.add_argument("--taskbank",default="public_benchmark/cognitive_synergy/taskbank_v1.json");args=ap.parse_args()
    bank=json.loads(Path(args.taskbank).read_text());start=args.batch_index*args.batch_size;tasks=bank["tasks"][start:start+args.batch_size]
    if not tasks:raise SystemExit("empty batch")
    R=Runner()
    cal=R.scored(BASE,"Calibration only: A=wrong. B=correct. C=wrong. D=wrong.","B")
    if not(cal["identity_ok"] and cal["marker_valid"] and cal["correct"]):
        out={"schema":"deus/cognitive-synergy-marker-batch/2","batch_index":args.batch_index,"task_ids":[t["task_id"] for t in tasks],"gate":"INCONCLUSIVE_CALIBRATION","identity":{"call_count":len(R.audit),"all_calls_exact_identity":all(x["identity_ok"] for x in R.audit),"served_models":sorted({str(x["served_model"]) for x in R.audit})},"calibration":cal}
        Path(f"synergy-marker-batch-{args.batch_index:02d}.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,indent=2));return 2
    rows=[]
    for t in tasks:
        raw=t["raw_prompt"];fixed=t["fixed_compact_prompt"];plan=FAMILY_PLAN[t["family"]];gold=t["gold_label"]
        a=R.scored(BASE+" Use the original raw task directly.",raw,gold)
        b=R.scored(BASE+" Use only the fixed compact representation; do not invent omitted facts.",fixed,gold)
        c=R.scored(BASE+" You are V2 target-aware structured lane. Original raw task is authoritative; the plan is a fallible aid.",raw+"\nTARGET_AWARE_PLAN: "+plan,gold)
        if a["choice"]==c["choice"] and a["choice"]:
            d={"choice":a["choice"],"correct":a["correct"],"marker_valid":True,"latency_ms":0,"identity_ok":True,"status":200,"output_sha256":"DERIVED_AGREEMENT","derived_without_call":True}
        else:
            d=R.scored(BASE+" You are an evidence-first independent-dual arbiter. Re-solve original task; frozen candidate labels are fallible hints.",raw+f"\nFROZEN_CANDIDATES: V1={a['choice']}; V2={c['choice']}",gold);d["derived_without_call"]=False
        sem=R.semantic(raw)
        e=R.scored(BASE+" You are cooperative synergy finalizer. Original task is authority. Cross-check target-aware plan and frozen V1 semantic packet as fallible artifacts.",raw+"\nTARGET_AWARE_PLAN: "+plan+"\nV1_SEMANTIC_PACKET: "+sem["content"][:1200],gold)
        rows.append({"task_id":t["task_id"],"family":t["family"],"task_fingerprint":t["task_fingerprint"],"gold_label":gold,"A":a,"B":b,"C":c,"D":d,"E":e,"semantic_packet_sha256":hashlib.sha256(sem["content"].encode()).hexdigest(),"semantic_packet_latency_ms":sem["latency_ms"]})
    exact=all(x["identity_ok"] for x in R.audit)
    q={arm:sum(int(r[arm]["correct"]) for r in rows) for arm in "ABCDE"}
    mv={arm:sum(int(r[arm]["marker_valid"]) for r in rows) for arm in "ABCDE"}
    gate="BATCH_VALID" if exact and min(mv.values())==len(rows) else ("INCONCLUSIVE_MODEL_IDENTITY" if not exact else "INCONCLUSIVE_MARKER_PROTOCOL")
    out={"schema":"deus/cognitive-synergy-marker-batch/2","provider":"BLOCKRUN","requested_model":MODEL,"protocol":"FINAL_XML_MARKER_ONLY","batch_index":args.batch_index,"batch_size":len(rows),"task_ids":[r["task_id"] for r in rows],"taskbank_schema":bank["schema"],"quality_correct":q,"marker_valid":mv,"rows":rows,"identity":{"call_count":len(R.audit),"all_calls_exact_identity":exact,"served_models":sorted({str(x["served_model"]) for x in R.audit}),"per_call":R.audit},"gate":gate,"truth":{"gold_not_in_prompts":True,"taskbank_frozen":True,"same_model_required":True,"global_synergy_claim":False}}
    fn=f"synergy-marker-batch-{args.batch_index:02d}.json";Path(fn).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"batch":args.batch_index,"tasks":out["task_ids"],"quality":q,"marker_valid":mv,"calls":len(R.audit),"exact_identity":exact,"gate":gate},indent=2))
    return 0 if gate=="BATCH_VALID" else 2
if __name__=="__main__":raise SystemExit(main())
