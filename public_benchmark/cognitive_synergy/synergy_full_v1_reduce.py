#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, hashlib, collections, sys

files=sorted(pathlib.Path("batch-artifacts").glob("synergy-batch-*.json"))
batches=[]
for p in files:
    try:batches.append(json.loads(p.read_text()))
    except Exception as e:print("bad",p,e,file=sys.stderr)
rows=[]
for b in batches: rows.extend(b.get("rows",[]))
expected=100
ids=[r["task_id"] for r in rows]
dup=[x for x,c in collections.Counter(ids).items() if c>1]
missing_count=max(0,expected-len(set(ids)))
arms="ABCDE"
tot={a:sum(int(r[a]["correct"]) for r in rows) for a in arms}
lat={a:sum(int(r[a].get("latency_ms",0) or 0) for r in rows) for a in arms}
families={}
for r in rows:
    f=families.setdefault(r["family"],{"n":0,**{a:0 for a in arms},"E_only":0,"A_only":0,"C_only":0,"oracle_union":0,"latency_ms":{a:0 for a in arms}})
    f["n"]+=1
    for a in arms:
        f[a]+=int(r[a]["correct"]);f["latency_ms"][a]+=int(r[a].get("latency_ms",0) or 0)
    f["E_only"]+=int(r["E"]["correct"] and not any(r[a]["correct"] for a in "ACD"))
    f["A_only"]+=int(r["A"]["correct"] and not any(r[a]["correct"] for a in "CDE"))
    f["C_only"]+=int(r["C"]["correct"] and not any(r[a]["correct"] for a in "ADE"))
    f["oracle_union"]+=int(any(r[a]["correct"] for a in "ACDE"))
for f in families.values():
    f["synergy_gain_E_vs_best_A_C_D"]=f["E"]-max(f["A"],f["C"],f["D"])
    f["E_minus_A"]=f["E"]-f["A"]
    f["accuracy"]={a:(f[a]/f["n"] if f["n"] else None) for a in arms}
identity_exact=all(b.get("identity",{}).get("all_calls_exact_identity") for b in batches) if batches else False
served=sorted({m for b in batches for m in b.get("identity",{}).get("served_models",[])})
batch_gates={str(b.get("batch_index")):b.get("gate") for b in batches}
complete=(len(set(ids))==expected and not dup and len(batches)==17)
regress=[k for k,v in families.items() if v["E"]<v["A"]]
superpos=[k for k,v in families.items() if v["E"]>max(v["A"],v["C"],v["D"])]
if not complete:
    gate="INCOMPLETE_BATCH_SET"
elif not identity_exact:
    gate="INCONCLUSIVE_MODEL_IDENTITY_OR_PROVIDER_FAILURE"
elif regress:
    gate="VALID_NEGATIVE_OR_MIXED_NO_GLOBAL_PROMOTION"
elif superpos:
    gate="PROMOTE_SYNERGY_SCOPED_BY_FAMILY"
else:
    gate="VALID_TIED_NO_SUPERADDITIVITY"
aggregate={
 "schema":"deus/cognitive-synergy-full-suite/1",
 "task_count_unique":len(set(ids)),
 "row_count":len(rows),
 "batch_count":len(batches),
 "duplicate_task_ids":dup,
 "missing_task_count":missing_count,
 "quality_correct":tot,
 "accuracy":{a:(tot[a]/expected if complete else (tot[a]/len(rows) if rows else None)) for a in arms},
 "latency_ms_sum":lat,
 "families":families,
 "negative_E_vs_A_families":regress,
 "superadditive_E_vs_best_A_C_D_families":superpos,
 "identity":{"all_batches_exact_identity":identity_exact,"served_models":served},
 "batch_gates":batch_gates,
 "promotion_gate":gate,
 "truth":{"family_wise_quality_first":True,"no_posthoc_task_deletion":True,"taskbank_frozen_before_execution":True,"global_IQ_scalar_claim":False}
}
raw=json.dumps(aggregate,indent=2,sort_keys=True)+"\n"
path=pathlib.Path("synergy-full-suite-aggregate.json");path.write_text(raw)
pathlib.Path("AGGREGATE_SHA256.txt").write_text(hashlib.sha256(raw.encode()).hexdigest()+"  synergy-full-suite-aggregate.json\n")
print(json.dumps({k:aggregate[k] for k in ["task_count_unique","batch_count","quality_correct","accuracy","negative_E_vs_A_families","superadditive_E_vs_best_A_C_D_families","identity","promotion_gate"]},indent=2))
raise SystemExit(0 if gate not in ("INCOMPLETE_BATCH_SET","INCONCLUSIVE_MODEL_IDENTITY_OR_PROVIDER_FAILURE") else 2)
