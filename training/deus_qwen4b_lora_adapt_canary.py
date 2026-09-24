from __future__ import annotations
import hashlib,json,platform,time,traceback
from pathlib import Path
import psutil,torch,transformers,peft
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import LoraConfig,get_peft_model

MODEL_ID="Qwen/Qwen3-4B"
OUT=Path("training/qwen4b-adapt-output");OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def mem():
 v=psutil.virtual_memory();return {"total_gib":v.total/2**30,"available_gib":v.available/2**30,"used_gib":v.used/2**30,"percent":v.percent}
def ev(model,ids,mask):
 model.eval()
 with torch.no_grad():return float(model(input_ids=ids,attention_mask=mask,labels=ids).loss.detach().float().cpu())
r={"schema":"deus-qwen4b-lora-adapt-canary/1","model":MODEL_ID,"method":"LoRA","steps":3,"status":"STARTING","memory_before":mem(),"python":platform.python_version(),"torch":torch.__version__,"transformers":transformers.__version__,"peft":peft.__version__}
t=time.time()
try:
 if r["memory_before"]["available_gib"]<11:raise RuntimeError("PRECHECK_INSUFFICIENT_AVAILABLE_RAM_LT_11_GIB")
 tok=AutoTokenizer.from_pretrained(MODEL_ID)
 if tok.pad_token is None:tok.pad_token=tok.eos_token
 base=AutoModelForCausalLM.from_pretrained(MODEL_ID,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True)
 base.config.use_cache=False
 if hasattr(base,"gradient_checkpointing_enable"):base.gradient_checkpointing_enable()
 cfg=LoraConfig(r=2,lora_alpha=4,lora_dropout=0.0,bias="none",task_type="CAUSAL_LM",target_modules=["q_proj","v_proj"])
 model=get_peft_model(base,cfg)
 text="DEUS distinguishes configured from executed and executed from verified. Receipts bind claims to evidence."
 enc=tok(text,return_tensors="pt",truncation=True,max_length=32);ids=enc["input_ids"];mask=enc["attention_mask"]
 r["memory_after_load"]=mem();r["trainable_parameters"]=sum(p.numel() for p in model.parameters() if p.requires_grad)
 pre=ev(model,ids,mask);r["pre_loss"]=pre
 opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1e-3)
 losses=[];model.train()
 for _ in range(3):
  opt.zero_grad(set_to_none=True);loss=model(input_ids=ids,attention_mask=mask,labels=ids).loss;loss.backward();opt.step();losses.append(float(loss.detach().float().cpu()))
 post=ev(model,ids,mask);r["train_losses"]=losses;r["post_loss"]=post;r["loss_decreased"]=post<pre;r["memory_after_steps"]=mem()
 ad=OUT/"adapter";model.save_pretrained(ad,safe_serialization=True);tok.save_pretrained(ad);af=next(iter(ad.glob("adapter_model.*")))
 r.update({"status":"PASS" if post<pre else "FAIL_NO_LOSS_IMPROVEMENT","passed":bool(post<pre),"adapter_file":str(af),"adapter_sha256":sha(af),"adapter_bytes":af.stat().st_size})
except Exception as e:
 r.update({"status":"MEASURED_BLOCKER","passed":False,"error":repr(e),"traceback_tail":traceback.format_exc()[-6000:],"memory_at_failure":mem()})
finally:
 r["elapsed_s"]=time.time()-t;(OUT/"receipt.json").write_text(json.dumps(r,indent=2),encoding="utf-8");print(json.dumps(r,separators=(",",":")))
 if r.get("status")=="FAIL_NO_LOSS_IMPROVEMENT":raise SystemExit(2)
