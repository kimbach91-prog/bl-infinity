#!/usr/bin/env python3
import json, os, pathlib
task=json.loads(pathlib.Path(os.environ["DEUS_TASK_FILE"]).read_text())
p={"A":0.90,"B":0.80,"C":0.75,"D":0.60}
def success(q):
    ks=list(q)
    # exactly 4 + exactly 3
    prod=1.0
    for k in ks: prod*=q[k]
    s=prod
    for miss in ks:
        t=1.0-q[miss]
        for k in ks:
            if k!=miss: t*=q[k]
        s+=t
    return s
base=success(p)
vals={}
for k in p:
    q=dict(p); q[k]=min(1.0,q[k]+0.10); vals[k]=success(q)
best=max(vals,key=lambda k: vals[k]-base)
out={"baseline":base,**vals,"best":best,"best_probability":vals[best],"improvement":vals[best]-base}
print(json.dumps(out,sort_keys=True))
