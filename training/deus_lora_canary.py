from __future__ import annotations
import argparse, hashlib, json, os, platform, time
from pathlib import Path

import torch
import transformers
import peft
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def loss_value(model, ids, mask):
    model.eval()
    with torch.no_grad():
        out=model(input_ids=ids,attention_mask=mask,labels=ids)
    return float(out.loss.detach().cpu())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output", default="training/canary-output")
    args=ap.parse_args()
    outdir=Path(args.output)
    outdir.mkdir(parents=True,exist_ok=True)

    torch.manual_seed(7)
    model_id="sshleifer/tiny-gpt2"
    tokenizer=AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token=tokenizer.eos_token

    base=AutoModelForCausalLM.from_pretrained(model_id)
    base.config.use_cache=False
    cfg=LoraConfig(
        r=4,
        lora_alpha=8,
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["c_attn"],
    )
    model=get_peft_model(base,cfg)

    text=("DEUS truth is receipt bound. "
          "DEUS verifies execution with receipts. "
          "Canonical state and runtime truth are distinct. ")
    enc=tokenizer(text,return_tensors="pt",truncation=True,max_length=64)
    ids=enc["input_ids"].repeat(4,1)
    mask=enc["attention_mask"].repeat(4,1)

    pre=loss_value(model,ids,mask)
    trainable=[p for p in model.parameters() if p.requires_grad]
    trainable_count=sum(p.numel() for p in trainable)
    opt=torch.optim.AdamW(trainable,lr=5e-3)
    losses=[]
    t0=time.time()
    model.train()
    for step in range(30):
        opt.zero_grad(set_to_none=True)
        result=model(input_ids=ids,attention_mask=mask,labels=ids)
        result.loss.backward()
        opt.step()
        losses.append(float(result.loss.detach().cpu()))
    elapsed=time.time()-t0
    post=loss_value(model,ids,mask)

    adapter_dir=outdir/"adapter"
    model.save_pretrained(adapter_dir,safe_serialization=True)
    tokenizer.save_pretrained(adapter_dir)
    candidates=list(adapter_dir.glob("adapter_model.*"))
    if not candidates:
        raise RuntimeError("adapter artifact missing")
    adapter_file=candidates[0]
    adapter_sha=sha256_file(adapter_file)

    receipt={
        "schema":"deus-training-foundry-lora-canary/1",
        "model":model_id,
        "method":"LoRA",
        "steps":30,
        "seed":7,
        "pre_loss":pre,
        "post_loss":post,
        "absolute_improvement":pre-post,
        "loss_decreased":post < pre,
        "trainable_parameters":trainable_count,
        "elapsed_s":elapsed,
        "adapter_file":str(adapter_file),
        "adapter_sha256":adapter_sha,
        "torch":torch.__version__,
        "transformers":transformers.__version__,
        "peft":peft.__version__,
        "python":platform.python_version(),
        "passed":bool(post < pre and trainable_count > 0),
    }
    (outdir/"receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    print(json.dumps(receipt,separators=(",",":")))
    if not receipt["passed"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()
