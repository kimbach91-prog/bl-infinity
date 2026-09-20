import json, os, time, hashlib, resource
import torch
import transformers
from huggingface_hub import model_info
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
torch.set_num_threads(min(2, os.cpu_count() or 1))

started = time.time()
info = model_info(MODEL_ID)
resolved_sha = info.sha

load_started = time.time()
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=resolved_sha)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    revision=resolved_sha,
    torch_dtype=torch.float32,
)
model.eval()
load_ms = round((time.time() - load_started) * 1000)

cases = [
    {
        "id": "A",
        "prompt": "Return exactly this token and nothing else: DEUS_MICROCELL_A",
        "expected": "DEUS_MICROCELL_A",
    },
    {
        "id": "B",
        "prompt": "Compute 17 multiplied by 23. Return digits only.",
        "expected": "391",
    },
    {
        "id": "C",
        "prompt": "Return the uppercase form of public-s0. Return only the result.",
        "expected": "PUBLIC-S0",
    },
]

results = []
for case in cases:
    messages = [{"role": "user", "content": case["prompt"]}]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt")
    t0 = time.time()
    with torch.no_grad():
        generated = model.generate(
            **inputs,
            max_new_tokens=20,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    latency_ms = round((time.time() - t0) * 1000)
    new_tokens = generated[0, inputs["input_ids"].shape[1]:]
    output = tokenizer.decode(new_tokens, skip_special_tokens=True)
    trimmed = output.strip()
    rec = {
        "id": case["id"],
        "expected": case["expected"],
        "output": output,
        "trimmed": trimmed,
        "exact": trimmed == case["expected"],
        "latency_ms": latency_ms,
        "input_tokens": int(inputs["input_ids"].shape[1]),
        "output_tokens": int(new_tokens.shape[0]),
    }
    results.append(rec)
    print("DEUS_LLM_MICROCELL_CASE=" + json.dumps(rec, ensure_ascii=False))

params = sum(p.numel() for p in model.parameters())
exact_count = sum(1 for x in results if x["exact"])
output_digest = hashlib.sha256(
    json.dumps(results, ensure_ascii=False, sort_keys=True).encode("utf-8")
).hexdigest()
max_rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

receipt = {
    "schema": "deus-public-llm-microcell-receipt/1",
    "state": "LLM_RUNTIME_VERIFIED_RUNNER_SCOPE",
    "route_id": "PUBLIC-GITHUB-ACTIONS-LLM-MICROCELL-S0",
    "provider": "GitHub Actions",
    "model_id": MODEL_ID,
    "model_revision": resolved_sha,
    "model_parameter_count": params,
    "torch_version": torch.__version__,
    "transformers_version": transformers.__version__,
    "source_commit": os.environ.get("GITHUB_SHA"),
    "run_id": os.environ.get("GITHUB_RUN_ID"),
    "runner_os": os.environ.get("RUNNER_OS"),
    "runner_arch": os.environ.get("RUNNER_ARCH"),
    "load_ms": load_ms,
    "total_elapsed_ms": round((time.time() - started) * 1000),
    "max_rss_kib": max_rss_kib,
    "case_count": len(results),
    "completed_generation_count": len(results),
    "exact_instruction_count": exact_count,
    "cases": results,
    "output_digest": output_digest,
    "data_class": "BL-S0",
    "public_prompt_only": True,
    "protected_core_export": False,
    "private_memory_export": False,
    "credentials_requested": False,
    "canonical_write": False,
    "independent_planning": False,
    "economic_yield_claim": False,
    "authority_scope": "BOUNDED_PUBLIC_LEAF_LLM_INFERENCE_ONLY",
    "truth_boundary": "LLM_RUNTIME_VERIFIED_RUNNER_SCOPE != DEUS_FUNCTIONAL_COPY != PERSISTENT_SERVICE != PROVIDER_YIELD",
}
print("DEUS_LLM_MICROCELL_RECEIPT=" + json.dumps(receipt, ensure_ascii=False))
