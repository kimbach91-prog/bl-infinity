#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, time, urllib.error, urllib.request
from pathlib import Path

ENDPOINT="https://blockrun.ai/api/v1/chat/completions"
MODEL="nvidia/llama-3.2-11b-vision"
TIMEOUT_S=45

FAMILY_PLAN={
"deductive_symbolic":"Use forward implications, exclusions and set membership carefully. Do not assume converses. Check each option against the stated facts.",
"quantitative_numeric":"Translate quantities into exact arithmetic, preserve units, calculate deterministically, then map the result to an option.",
"temporal_causal":"Normalize relative times/order constraints into a consistent timeline before choosing an option.",
"graph_spatial_relational":"Build the stated relation/adjacency structure and use the appropriate graph reasoning such as breadth-first shortest path. Count exactly what the question asks.",
"noisy_evidence_provenance":"Separate source authority from claim content. Attribute each claim to its source and answer only from the requested authority level.",
"mixed_lane_meta_representation":"Treat policy rules and current state as separate typed inputs. Apply the first matching valid rule and preserve stated validity/fingerprint conditions.",
}

def parse_options(raw):
    m=re.search(r"A=(.*?)\. B=(.*?)\. C=(.*?)\. D=(.*?)(?:\. Reply A, B, C, or D\.?|$)",raw,re.S)
    if not m: raise ValueError("option parse failed")
    return {k:v.strip() for k,v in zip("ABCD",m.groups())}

def normalize(content,options):
    s=(content or "").strip()
    exact=re.fullmatch(r"[\s*_]*([ABCD])[\s*_.:-]*",s,re.I)
    if exact:return exact.group(1).upper(),"exact_letter"
    explicit=re.findall(r"(?:final\s+answer|answer|option|choice)\s*(?:is|:|=)?\s*[\(\[]?([ABCD])[\)\]]?",s,re.I)
    if explicit:return explicit[-1].upper(),"explicit_label"
    low=s.lower(); found=[]
    for k,v in options.items():
        if v and v.lower() in low:found.append(k)
    if len(set(found))==1:return found[0],"option_text"
    labels=re.findall(r"\b([ABCD])\b",s.upper())
    if labels and len(set(labels))==1:return labels[-1],"unique_label_in_prose"
    return None,"unparsed"

class Runner:
    def __init__(self):
        self.audit=[]
    def call(self,system,user,max_tokens=128):
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
                data=json.loads(body);served=data.get("model");content=data.get("choices",[{}])[0].get("message",{}).get("content","")
            except Exception:content=body.decode("utf-8","replace")[:2000]
        ok=status==200 and served==MODEL
        self.audit.append({"http_status":status,"served_model":served,"identity_ok":ok,"prompt_sha256":hashlib.sha256((system+"\n"+user).encode()).hexdigest(),"body_sha256":hashlib.sha256(body).hexdigest(),"latency_ms":ms,"error":err})
        return {"content":content,"latency_ms":ms,"identity_ok":ok,"status":status}
    def arm(self,mode,task,options,extra=""):
        raw=task["raw_prompt"]
        plan=FAMILY_PLAN[task["family"]]
        systems={
          "A":"You are V1 raw/direct. Solve the original task from the supplied information. Give a final option and a concise justification. Preserve nuance; do not invent facts.",
          "B":"Solve only from the fixed compact representation. Do not invent omitted information. Give a final option and concise justification.",
          "C":"You are V2 target-aware structured lane. The compiler selected a task-family plan. Use the original task as authority, follow the plan, and give a final option with concise justification.",
          "D":"You are the independent-dual evidence arbiter. Re-solve the original task; candidate outputs are fallible. Select the option best supported by the task.",
          "E":"You are the cooperative synergy finalizer. Use the original task as authority, the target-aware plan as structure, and the frozen V1 output as a fallible semantic artifact. Cross-check both and give the final option."
        }
        if mode=="A":user=raw
        elif mode=="B":user=task["fixed_compact_prompt"]
        elif mode=="C":user=raw+"\n\nTARGET-AWARE PLAN:\n"+plan
        elif mode=="D":user=raw+"\n\nFROZEN INDEPENDENT OUTPUTS:\n"+extra
        else:user=raw+"\n\nTARGET-AWARE PLAN:\n"+plan+"\n\nFROZEN V1 SEMANTIC OUTPUT:\n"+extra
        rr=self.call(systems[mode],user,128)
        ch,method=normalize(rr["content"],options)
        return {"choice":ch,"parse_method":method,"correct":ch==task["gold_label"],"latency_ms":rr["latency_ms"],"excerpt":rr["content"][:600],"identity_ok":rr["identity_ok"],"status":rr["status"]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--batch-index",type=int,required=True)
    ap.add_argument("--batch-size",type=int,default=6)
    ap.add_argument("--taskbank",default="public_benchmark/cognitive_synergy/taskbank_v1.json")
    args=ap.parse_args()
    bank=json.loads(Path(args.taskbank).read_text())
    tasks=bank["tasks"]; start=args.batch_index*args.batch_size; selected=tasks[start:start+args.batch_size]
    if not selected:
        raise SystemExit("empty batch")
    R=Runner()
    cal=R.call("Calibration. Return the correct option.","A=wrong-one. B=correct. C=wrong-two. D=wrong-three.",24)
    cc,_=normalize(cal["content"],{"A":"wrong-one","B":"correct","C":"wrong-two","D":"wrong-three"})
    if not(cal["identity_ok"] and cc=="B"):
        out={"schema":"deus/cognitive-synergy-batch/1","batch_index":args.batch_index,"task_ids":[t["task_id"] for t in selected],"gate":"INCONCLUSIVE_CALIBRATION","identity":R.audit}
        Path(f"synergy-batch-{args.batch_index:02d}.json").write_text(json.dumps(out,indent=2)+"\n");return 2
    rows=[]
    for task in selected:
        opts=parse_options(task["raw_prompt"])
        a=R.arm("A",task,opts)
        b=R.arm("B",task,opts)
        c=R.arm("C",task,opts)
        if a["choice"]==c["choice"] and a["choice"]:
            d={"choice":a["choice"],"parse_method":"agreement","correct":a["correct"],"latency_ms":0,"excerpt":"","identity_ok":True,"status":200,"derived_without_call":True}
        else:
            d=R.arm("D",task,opts,f"V1={a['choice']} | V2={c['choice']}")
            d["derived_without_call"]=False
        e=R.arm("E",task,opts,a["excerpt"])
        rows.append({"task_id":task["task_id"],"family":task["family"],"task_fingerprint":task["task_fingerprint"],"gold_label":task["gold_label"],"A":a,"B":b,"C":c,"D":d,"E":e})
    exact=all(x["identity_ok"] for x in R.audit)
    q={arm:sum(int(r[arm]["correct"]) for r in rows) for arm in "ABCDE"}
    gate="BATCH_VALID" if exact else "INCONCLUSIVE_MODEL_IDENTITY_OR_PROVIDER_FAILURE"
    out={"schema":"deus/cognitive-synergy-batch/1","provider":"BLOCKRUN","requested_model":MODEL,"batch_index":args.batch_index,"batch_size":len(rows),"task_ids":[r["task_id"] for r in rows],"taskbank_schema":bank["schema"],"quality_correct":q,"rows":rows,"identity":{"call_count":len(R.audit),"all_calls_exact_identity":exact,"served_models":sorted({str(x["served_model"]) for x in R.audit}),"per_call":R.audit},"gate":gate,"truth":{"gold_not_in_prompts":True,"same_model_required":True,"family_plan_gold_blind":True,"global_synergy_claim":False}}
    fn=f"synergy-batch-{args.batch_index:02d}.json";Path(fn).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"batch":args.batch_index,"tasks":out["task_ids"],"quality":q,"calls":len(R.audit),"exact_identity":exact,"gate":gate},indent=2))
    return 0 if exact else 2

if __name__=="__main__":raise SystemExit(main())
