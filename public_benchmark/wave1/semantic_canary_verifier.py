#!/usr/bin/env python3
import argparse, hashlib, json, pathlib
ap=argparse.ArgumentParser(); ap.add_argument("--candidate",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
cand=json.loads(pathlib.Path(a.candidate).read_text())
raw=cand.get("stdout","").strip()
try: x=json.loads(raw)
except Exception as e: raise SystemExit("candidate stdout not json")
p={"A":0.90,"B":0.80,"C":0.75,"D":0.60}
def success(q):
    ks=list(q); s=1.0
    for k in ks: s*=q[k]
    for miss in ks:
        t=1-q[miss]
        for k in ks:
            if k!=miss: t*=q[k]
        s+=t
    return s
base=success(p); vals={}
for k in p:
    q=dict(p); q[k]=min(1.0,q[k]+0.10); vals[k]=success(q)
best=max(vals,key=lambda k: vals[k]-base)
exp={"baseline":base,**vals,"best":best,"best_probability":vals[best],"improvement":vals[best]-base}
ok=all(abs(float(x[k])-float(exp[k]))<1e-12 for k in ["baseline","A","B","C","D","best_probability","improvement"]) and x["best"]==exp["best"]
receipt={"schema":"DEUS_P09_SEMANTIC_CANARY_QA_V1","verdict":"PASS" if ok else "FAIL","candidate_digest":hashlib.sha256(pathlib.Path(a.candidate).read_bytes()).hexdigest(),"expected":exp,"observed":x}
pathlib.Path(a.out).write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,sort_keys=True))
raise SystemExit(0 if ok else 2)
