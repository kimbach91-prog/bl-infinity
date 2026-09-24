from __future__ import annotations
import argparse, hashlib, json, platform, time
from pathlib import Path
import torch
import transformers
import peft
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

def sha(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024), b""): h.update(c)
    return h.hexdigest()

def eval_loss(model, ids, mask):
    model.eval()
    with torch.no_grad():
        return float(model(input_ids=ids,attention_mask=mask,labels=ids).loss.detach().cpu())

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",default="training/qwen-canary-output"); args=ap.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    torch.manual_seed(11)
    model_id="Qwen/Qwen3-0.6B"
    tok=AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token is None: tok.pad_token=tok.eos_token
    base=AutoModelForCausalLM.from_pretrained(model_id,torch_dtype=torch.float32,low_cpu_mem_usage=True)
    base.config.use_cache=False
    cfg=LoraConfig(r=4,lora_alpha=8,lora_dropout=0.0,bias="none",task_type="CAUSAL_LM",target_modules=["q_proj","v_proj"])
    model=get_peft_model(base,cfg)
    text="DEUS distinguishes configured from executed and executed from verified. Receipts bound truth."
    enc=tok(text,return_tensors="pt",truncation=True,max_length=48)
    ids=enc["input_ids"]; mask=enc["attention_mask"]
    pre=eval_loss(model,ids,mask)
    trainable=[p for p in model.parameters() if p.requires_grad]
    count=sum(p.numel() for p in trainable)
    opt=torch.optim.AdamW(trainable,lr=2e-3)
    losses=[]; t0=time.time()
    model.train()
    for _ in range(3):
        opt.zero_grad(set_to_none=True)
        loss=model(input_ids=ids,attention_mask=mask,labels=ids).loss
        loss.backward(); opt.step(); losses.append(float(loss.detach().cpu()))
    post=eval_loss(model,ids,mask)
    ad=out/"adapter"; model.save_pretrained(ad,safe_serialization=True); tok.save_pretrained(ad)
    af=next(iter(ad.glob("adapter_model.*")))
    receipt={"schema":"deus-qwen-lora-canary/1","model":model_id,"method":"LoRA","steps":3,"pre_loss":pre,"post_loss":post,"loss_decreased":post<pre,"trainable_parameters":count,"elapsed_s":time.time()-t0,"adapter_file":str(af),"adapter_sha256":sha(af),"torch":torch.__version__,"transformers":transformers.__version__,"peft":peft.__version__,"python":platform.python_version(),"passed":bool(post<pre and count>0)}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    print(json.dumps(receipt,separators=(",",":")))
    if not receipt["passed"]: raise SystemExit(2)
if __name__=="__main__": main()
