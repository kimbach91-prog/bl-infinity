#!/usr/bin/env python3
from __future__ import annotations
import collections,hashlib,json,pathlib,sys
files=sorted(pathlib.Path("batch-artifacts").glob("synergy-marker-batch-*.json"))
batches=[]
for p in files:
    try:batches.append(json.loads(p.read_text()))
    except Exception as e:print("bad",p,e,file=sys.stderr)
rows=[r for b in batches for r in b.get("rows",[])]
ids=[r["task_id"] for r in rows];counter=collections.Counter(ids);dup=[x for x,c in counter.items() if c>1]
expected=100;arms="ABCDE"
tot={a:sum(int(r[a]["correct"]) for r in rows) for a in arms}
marker={a:sum(int(r[a]["marker_valid"]) for r in rows) for a in arms}
families={}
for r in rows:
    f=families.setdefault(r["family"],{"n":0,**{a:0 for a in arms},"marker_valid":{a:0 for a in arms},"E_only":0,"A_only":0,"C_only":0,"D_only":0,"oracle_union_ACDE":0,"latency_ms":{a:0 for a in arms},"semantic_packet_latency_ms":0})
    f["n"]+=1
    for a in arms:
        f[a]+=int(r[a]["correct"]);f["marker_valid"][a]+=int(r[a]["marker_valid"]);f["latency_ms"][a]+=int(r[a].get("latency_ms",0) or 0)
    f["semantic_packet_latency_ms"]+=int(r.get("semantic_packet_latency_ms",0) or 0)
    f["E_only"]+=int(r["E"]["correct"] and not any(r[a]["correct"] for a in "ACD"))
    f["A_only"]+=int(r["A"]["correct"] and not any(r[a]["correct"] for a in "CDE"))
    f["C_only"]+=int(r["C"]["correct"] and not any(r[a]["correct"] for a in "ADE"))
    f["D_only"]+=int(r["D"]["correct"] and not any(r[a]["correct"] for a in "ACE"))
    f["oracle_union_ACDE"]+=int(any(r[a]["correct"] for a in "ACDE"))
for f in families.values():
    f["accuracy"]={a:(f[a]/f["n"] if f["n"] else None) for a in arms}
    f["synergy_gain_E_vs_best_A_C_D"]=f["E"]-max(f["A"],f["C"],f["D"])
    f["E_minus_A"]=f["E"]-f["A"]
    f["D_minus_best_single"]=f["D"]-max(f["A"],f["C"])
complete=(len(set(ids))==expected and len(rows)==expected and len(batches)==17 and not dup)
identity_exact=bool(batches) and all(b.get("identity",{}).get("all_calls_exact_identity") for b in batches)
served=sorted({m for b in batches for m in b.get("identity",{}).get("served_models",[])})
marker_clean=complete and all(marker[a]==expected for a in arms)
regress=[k for k,v in families.items() if v["E"]<v["A"]]
superpos=[k for k,v in families.items() if v["E"]>max(v["A"],v["C"],v["D"])]
if not complete:gate="INCOMPLETE_BATCH_SET"
elif not identity_exact:gate="INCONCLUSIVE_MODEL_IDENTITY"
elif not marker_clean:gate="INCONCLUSIVE_MARKER_PROTOCOL"
elif regress:gate="VALID_NEGATIVE_OR_MIXED_NO_GLOBAL_PROMOTION"
elif superpos:gate="PROMOTE_SYNERGY_SCOPED_BY_FAMILY"
else:gate="VALID_TIED_NO_SUPERADDITIVITY"
out={"schema":"deus/cognitive-synergy-full-marker-suite/2","protocol":"FINAL_XML_MARKER_ONLY","task_count_unique":len(set(ids)),"row_count":len(rows),"batch_count":len(batches),"duplicate_task_ids":dup,"missing_task_count":max(0,expected-len(set(ids))),"quality_correct":tot,"marker_valid":marker,"accuracy":{a:(tot[a]/expected if complete else (tot[a]/len(rows) if rows else None)) for a in arms},"families":families,"negative_E_vs_A_families":regress,"superadditive_E_vs_best_A_C_D_families":superpos,"identity":{"all_batches_exact_identity":identity_exact,"served_models":served},"promotion_gate":gate,"truth":{"taskbank_frozen_before_execution":True,"marker_protocol_arm_neutral":True,"family_wise_quality_first":True,"no_posthoc_task_deletion":True,"global_IQ_scalar_claim":False}}
raw=json.dumps(out,indent=2,sort_keys=True)+"\n";pathlib.Path("synergy-full-marker-suite-aggregate.json").write_text(raw);pathlib.Path("AGGREGATE_SHA256.txt").write_text(hashlib.sha256(raw.encode()).hexdigest()+"  synergy-full-marker-suite-aggregate.json\n")
print(json.dumps({k:out[k] for k in ["task_count_unique","batch_count","quality_correct","marker_valid","accuracy","negative_E_vs_A_families","superadditive_E_vs_best_A_C_D_families","identity","promotion_gate"]},indent=2))
raise SystemExit(0 if not gate.startswith(("INCOMPLETE","INCONCLUSIVE")) else 2)
