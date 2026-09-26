import base64, hashlib, json
from datasets import load_dataset

DATASET="TIGER-Lab/MMLU-Pro"
SPLIT="test"
PER_CATEGORY=3
ds=load_dataset(DATASET, split=SPLIT)

rows=[]
for i,r in enumerate(ds):
    cat=str(r["category"])
    q=str(r["question"])
    opts=list(r["options"])
    ans=r["answer"]
    # normalize answer to an integer index when possible
    if isinstance(ans,str):
        s=ans.strip()
        if s.isdigit():
            ai=int(s)
        elif len(s)==1 and "A" <= s.upper() <= "J":
            ai=ord(s.upper())-65
        else:
            ai=int(r.get("answer_index", -1))
    else:
        ai=int(ans)
    if ai < 0 or ai >= len(opts):
        raise RuntimeError(f"bad_answer_index row={i} ans={ans!r}")
    row_id=hashlib.sha256((cat+"\0"+q+"\0"+json.dumps(opts,ensure_ascii=False)).encode()).hexdigest()
    rows.append({"source_index":i,"category":cat,"question":q,"options":opts,"answer_index":ai,"row_hash":row_id})

cats=sorted({x["category"] for x in rows})
selected=[]
for cat in cats:
    cr=[x for x in rows if x["category"]==cat]
    cr.sort(key=lambda x:x["row_hash"])
    if len(cr)<PER_CATEGORY:
        raise RuntimeError(f"category_too_small:{cat}:{len(cr)}")
    selected.extend(cr[:PER_CATEGORY])

if len(cats)<10 or len(selected)<42:
    raise RuntimeError(f"coverage_fail cats={len(cats)} n={len(selected)}")

def prompt_of(x):
    letters=[chr(65+i) for i in range(len(x["options"]))]
    options="\n".join(f"{a}. {o}" for a,o in zip(letters,x["options"]))
    return (
        "You are being evaluated on MMLU-Pro. Solve the multiple-choice problem. "
        "Reason internally, then output only the final option letter A-J.\n\n"
        f"Question: {x['question']}\n{options}\nAnswer:"
    )

frozen=[]
for n,x in enumerate(selected,1):
    frozen.append({
        "task_id":f"MMLUPRO-F42-{n:03d}",
        "category":x["category"],
        "source_index":x["source_index"],
        "row_hash":x["row_hash"],
        "prompt":prompt_of(x),
        "answer_letter":chr(65+x["answer_index"]),
        "options_count":len(x["options"]),
    })

canon=json.dumps(frozen,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
suite_sha=hashlib.sha256(canon).hexdigest()
payload={
    "schema":"deus-mmlu-pro-frozen42/1",
    "dataset":DATASET,
    "split":SPLIT,
    "selection":"3_per_category_sorted_by_sha256(category\\0question\\0options)",
    "categories":cats,
    "category_count":len(cats),
    "task_count":len(frozen),
    "suite_sha256":suite_sha,
    "tasks":frozen,
}
raw=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode()
print("DEUS_MMLUPRO_F42_SUMMARY="+json.dumps({
    "schema":payload["schema"],"dataset":DATASET,"split":SPLIT,
    "category_count":len(cats),"task_count":len(frozen),
    "categories":cats,"suite_sha256":suite_sha
},separators=(",",":")))
print("DEUS_MMLUPRO_F42_B64="+base64.b64encode(raw).decode())
