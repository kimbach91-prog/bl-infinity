#!/usr/bin/env python3
import json,re,time,urllib.request,urllib.error
from datasets import load_dataset

N=5
ds=load_dataset("cais/hle",split="test")
qs=[x for x in ds if not x.get("image")][:N]
def norm(s):
    return re.sub(r"[^a-z0-9.+-]+","",str(s).lower())
def ask(q):
    payload=json.dumps({
      "model":"default",
      "messages":[
        {"role":"system","content":"Answer the expert question. End with a line exactly: Answer: <final answer>"},
        {"role":"user","content":q["question"]}
      ],
      "temperature":0
    }).encode()
    req=urllib.request.Request("https://api.llm7.io/v1/chat/completions",data=payload,headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=120) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]
rows=[]
for i,q in enumerate(qs):
    try:
        out=ask(q)
        m=re.findall(r"Answer:\s*(.+)",out,re.I)
        extracted=m[-1].strip() if m else out.strip().splitlines()[-1]
        exact=norm(extracted)==norm(q["answer"])
        rows.append({"id":q["id"],"response":out,"extracted":extracted,"correct_answer":q["answer"],"strict_exact":exact})
    except Exception as e:
        rows.append({"id":q["id"],"error":type(e).__name__+":"+str(e),"strict_exact":False})
    if i+1<len(qs): time.sleep(1.2)
n=len(rows); c=sum(bool(x.get("strict_exact")) for x in rows)
receipt={
 "schema":"DEUS_HLE_PUBLIC_SUBSET_SCORE_V1",
 "dataset":"cais/hle",
 "official_repo_commit":"73ae974b1844c3ffa64c3f4343d9f1f259575700",
 "subset_rule":"first 5 text-only examples in public test split",
 "worker_route":"LLM7 anonymous default",
 "worker_is_deus_core":False,
 "judge":"strict normalized exact-answer match; NOT official HLE LLM judge",
 "n":n,"correct":c,"strict_exact_accuracy_pct":100*c/n if n else 0,
 "rows":rows,
 "claim_boundary":"Real public HLE subset execution under DEUS orchestration with disclosed external worker. Not an official HLE/HLE-Rolling leaderboard score and not evidence of DEUS-core standalone capability."
}
open("hle-public-subset-score.json","w").write(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({k:v for k,v in receipt.items() if k!="rows"},sort_keys=True))
