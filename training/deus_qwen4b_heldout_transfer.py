from __future__ import annotations
import hashlib,json,time,traceback
from pathlib import Path
import psutil,torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import LoraConfig,get_peft_model

MODEL_ID="Qwen/Qwen3-4B"
OUT=Path("training/qwen4b-heldout-output");OUT.mkdir(parents=True,exist_ok=True)
TRAIN="DEUS distinguishes configured from executed and executed from verified. Receipts bind claims to evidence."
HELDOUT=[
 "Verified evidence should outrank confident wording.",
 "A queued task is not the same as an executed task.",
 "When a route fails, preserve receipts and try a lawful fallback.",
 "Memory can guide action only when provenance is retained."
]
def mem():
 v=psutil.virtual_memory();return {"total_gib":v.total/2**30,"available_gib":v.available/2**30,"used_gib":v.used/2**30}
def loss_for(model,tok,text):
 e=tok(text,return_tensors="pt",truncation=True,max_length=40)
 model.eval()
 with torch.no_grad(): return float(model(input_ids=e["input_ids"],attention_mask=e["attention_mask"],labels=e["input_ids"]).loss.detach().float().cpu())
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
r={"schema":"deus-qwen4b-heldout-transfer/1","model":MODEL_ID,"train_text_sha256":hashlib.sha256(TRAIN.encode()).hexdigest(),"heldout_text_sha256":[hashlib.sha256(x.encode()).hexdigest() for x in HELDOUT],"memory_before":mem(),"status":"STARTING"}
t0=time.time()
try:
 tok=AutoTokenizer.from_pretrained(MODEL_ID)
 if tok.pad_token is None:tok.pad_token=tok.eos_token
 base=AutoModelForCausalLM.from_pretrained(MODEL_ID,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True)
 base.config.use_cache=False
 if hasattr(base,"gradient_checkpointing_enable"):base.gradient_checkpointing_enable()
 pre=[loss_for(base,tok,x) for x in HELDOUT]
 cfg=LoraConfig(r=2,lora_alpha=4,lora_dropout=0.0,bias="none",task_type="CAUSAL_LM",target_modules=["q_proj","v_proj"])
 model=get_peft_model(base,cfg)
 train=tok(TRAIN,return_tensors="pt",truncation=True,max_length=32)
 opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1e-3)
 train_losses=[]
 for _ in range(3):
  model.train();opt.zero_grad(set_to_none=True)
  loss=model(input_ids=train["input_ids"],attention_mask=train["attention_mask"],labels=train["input_ids"]).loss
  loss.backward();opt.step();train_losses.append(float(loss.detach().float().cpu()))
 post=[loss_for(model,tok,x) for x in HELDOUT]
 pairs=[{"id":i+1,"pre_loss":a,"post_loss":b,"improved":b<a,"delta":b-a} for i,(a,b) in enumerate(zip(pre,post))]
 mean_pre=sum(pre)/len(pre);mean_post=sum(post)/len(post);improved=sum(int(x["improved"]) for x in pairs)
 ad=OUT/"adapter";model.save_pretrained(ad,safe_serialization=True);af=next(iter(ad.glob("adapter_model.*")))
 passed=mean_post<mean_pre and improved>=3
 r.update({"status":"PASS" if passed else "NO_HELDOUT_TRANSFER","passed":passed,"train_losses":train_losses,"heldout":pairs,"mean_pre_loss":mean_pre,"mean_post_loss":mean_post,"mean_delta":mean_post-mean_pre,"improved_cases":improved,"required_improved_cases":3,"adapter_sha256":sha(af),"adapter_bytes":af.stat().st_size,"memory_after":mem()})
except Exception as e:
 r.update({"status":"MEASURED_BLOCKER","passed":False,"error":repr(e),"traceback_tail":traceback.format_exc()[-5000:]})
finally:
 r["elapsed_s"]=time.time()-t0;(OUT/"receipt.json").write_text(json.dumps(r,indent=2),encoding="utf-8");print(json.dumps(r,separators=(",",":")))
 if r.get("status")=="NO_HELDOUT_TRANSFER": raise SystemExit(2)
