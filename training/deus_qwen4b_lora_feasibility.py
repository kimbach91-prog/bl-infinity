from __future__ import annotations
import gc, hashlib, json, os, platform, time, traceback
from pathlib import Path
import psutil
import torch
import transformers, peft
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

MODEL_ID="Qwen/Qwen3-4B"
OUT=Path("training/qwen4b-feasibility-output")
OUT.mkdir(parents=True,exist_ok=True)

def sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def mem():
    v=psutil.virtual_memory()
    return {"total_gib":v.total/2**30,"available_gib":v.available/2**30,"used_gib":v.used/2**30,"percent":v.percent}

receipt={"schema":"deus-qwen4b-lora-feasibility/1","model":MODEL_ID,"method":"LoRA","status":"STARTING","memory_before":mem(),"python":platform.python_version(),"torch":torch.__version__,"transformers":transformers.__version__,"peft":peft.__version__}
t0=time.time()
try:
    # 4B BF16/FP16 weights are ~8 GiB; require safety headroom before download/load.
    if receipt["memory_before"]["available_gib"] < 11.0:
        raise RuntimeError("PRECHECK_INSUFFICIENT_AVAILABLE_RAM_LT_11_GIB")
    tok=AutoTokenizer.from_pretrained(MODEL_ID)
    if tok.pad_token is None: tok.pad_token=tok.eos_token
    dtype=torch.bfloat16
    base=AutoModelForCausalLM.from_pretrained(MODEL_ID,torch_dtype=dtype,low_cpu_mem_usage=True)
    base.config.use_cache=False
    if hasattr(base,"gradient_checkpointing_enable"): base.gradient_checkpointing_enable()
    receipt["memory_after_load"]=mem()
    cfg=LoraConfig(r=2,lora_alpha=4,lora_dropout=0.0,bias="none",task_type="CAUSAL_LM",target_modules=["q_proj","v_proj"])
    model=get_peft_model(base,cfg)
    trainable=[p for p in model.parameters() if p.requires_grad]
    receipt["trainable_parameters"]=sum(p.numel() for p in trainable)
    text="DEUS keeps claims receipt-bound."
    enc=tok(text,return_tensors="pt",truncation=True,max_length=24)
    ids=enc["input_ids"]; mask=enc["attention_mask"]
    model.train()
    opt=torch.optim.AdamW(trainable,lr=1e-3)
    opt.zero_grad(set_to_none=True)
    loss=model(input_ids=ids,attention_mask=mask,labels=ids).loss
    pre=float(loss.detach().float().cpu())
    loss.backward()
    opt.step()
    receipt["memory_after_step"]=mem()
    receipt["loss_step_1"]=pre
    ad=OUT/"adapter"; model.save_pretrained(ad,safe_serialization=True); tok.save_pretrained(ad)
    af=next(iter(ad.glob("adapter_model.*")))
    receipt.update({"status":"PASS","passed":True,"adapter_file":str(af),"adapter_sha256":sha(af),"adapter_bytes":af.stat().st_size})
except Exception as e:
    receipt.update({"status":"MEASURED_BLOCKER","passed":False,"error":repr(e),"traceback_tail":traceback.format_exc()[-6000:],"memory_at_failure":mem()})
finally:
    receipt["elapsed_s"]=time.time()-t0
    (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    print(json.dumps(receipt,separators=(",",":")))
