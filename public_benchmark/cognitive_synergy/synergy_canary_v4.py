#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENDPOINT = "https://blockrun.ai/api/v1/chat/completions"
MODEL = "nvidia/llama-3.2-11b-vision"
TIMEOUT_S = 45
IDENTITY_AUDIT: list[dict[str, Any]] = []

TASKS = [
    {
        "id": "F01-001", "family": "deductive_symbolic", "gold": "B",
        "raw": "Facts: Every amber object is bronze. No bronze object is cyan. Object X is amber. Question: Can X be cyan? A=Yes. B=No. C=Cannot determine. D=Only if X is not bronze. Reply A, B, C, or D.",
        "fixed": "amber->bronze; bronze ∩ cyan=∅; X∈amber. Query X∈cyan? A yes B no C unknown D iff X∉bronze.",
        "hhir": "TASK=deductive. INVARIANTS=[amber subset bronze, bronze disjoint cyan, X amber]. SOLVE by symbolic set implication. OPTIONS={A:yes,B:no,C:unknown,D:iff X not bronze}.",
    },
    {
        "id": "F02-001", "family": "quantitative_numeric", "gold": "B",
        "raw": "A machine processes 18 items per minute for 7 minutes. Exactly 11 processed items are rejected. How many accepted items remain? A=107. B=115. C=126. D=137. Reply A, B, C, or D.",
        "fixed": "rate18/min*time7=processed; rejected11; accepted=processed-rejected. A107 B115 C126 D137.",
        "hhir": "TASK=numeric. EQUATION accepted=(18*7)-11. Preserve exact integer arithmetic. OPTIONS={A:107,B:115,C:126,D:137}.",
    },
    {
        "id": "F03-001", "family": "temporal_causal", "gold": "C",
        "raw": "Event A happens at 10:00. Event B happens 30 minutes after A. Event C happens 10 minutes before B. Event D happens 5 minutes after C. Which order is correct? A=A,D,C,B. B=C,A,D,B. C=A,C,D,B. D=A,C,B,D. Reply A, B, C, or D.",
        "fixed": "tA=10:00;tB=A+30;tC=B-10;tD=C+5. choose order: A A,D,C,B; B C,A,D,B; C A,C,D,B; D A,C,B,D.",
        "hhir": "TASK=temporal. Normalize offsets: A=0, B=+30, C=B-10, D=C+5. Sort timestamps. OPTIONS={A:A-D-C-B,B:C-A-D-B,C:A-C-D-B,D:A-C-B-D}.",
    },
    {
        "id": "F04-001", "family": "graph_spatial_relational", "gold": "B",
        "raw": "Undirected graph edges are P-Q, Q-R, P-S, S-T, T-R, R-U. What is the shortest number of edges from P to U? A=2. B=3. C=4. D=5. Reply A, B, C, or D.",
        "fixed": "G undirected E={PQ,QR,PS,ST,TR,RU}; dist(P,U)? A2 B3 C4 D5.",
        "hhir": "TASK=graph shortest-path. Nodes={P,Q,R,S,T,U}; edges=[P-Q,Q-R,P-S,S-T,T-R,R-U]. Run BFS from P to U. OPTIONS={A:2,B:3,C:4,D:5}.",
    },
    {
        "id": "F05-001", "family": "noisy_evidence_provenance", "gold": "B",
        "raw": "Sources: S1 is an unaffiliated blog saying the product may launch June 1. S2 is the manufacturer's official release saying launch date June 3. S3 is a forum post claiming price $99. Which statement is directly supported by the official source? A=Launch June 1. B=Launch June 3. C=Price $99. D=None. Reply A, B, C, or D.",
        "fixed": "S1 blog: launch maybe Jun1; S2 official manufacturer: launch Jun3; S3 forum: price99. Ask official-supported claim. A Jun1 B Jun3 C price99 D none.",
        "hhir": "TASK=provenance. SOURCE_AUTHORITY={S1:blog,S2:official_manufacturer,S3:forum}. CLAIMS={S1:launch_Jun1,S2:launch_Jun3,S3:price_99}. Select claim directly supported by official source. OPTIONS={A:Jun1,B:Jun3,C:price99,D:none}.",
    },
    {
        "id": "F06-001", "family": "mixed_lane_meta_representation", "gold": "C",
        "raw": "Operational policy: if severity is HIGH and a valid rollback is available, choose ROLLBACK; if severity is HIGH and rollback is unavailable, choose ISOLATE; if severity is MEDIUM, choose INSPECT. Current evidence: severity=HIGH, rollback_available=yes, rollback dependency fingerprint is valid. What action follows the policy? A=ISOLATE. B=INSPECT. C=ROLLBACK. D=IGNORE. Reply A, B, C, or D.",
        "fixed": "policy high&rollback_valid->ROLLBACK; high&no_rollback->ISOLATE; medium->INSPECT. state high, rollback yes, fingerprint valid. A isolate B inspect C rollback D ignore.",
        "hhir": "TASK=mixed policy+state. INVARIANTS=[severity HIGH, rollback available, dependency fingerprint valid]. RULE_PRIORITY=[HIGH+valid rollback=>ROLLBACK; HIGH+no rollback=>ISOLATE; MEDIUM=>INSPECT]. OPTIONS={A:ISOLATE,B:INSPECT,C:ROLLBACK,D:IGNORE}.",
    },
]

def call_model(system: str, user: str, max_tokens: int = 32) -> dict[str, Any]:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=payload, headers={"content-type": "application/json"}, method="POST")
    started = time.monotonic()
    status = 0
    body = b""
    error = None
    parsed: Any = None
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
        error = f"HTTPError:{exc.code}"
    except Exception as exc:
        error = f"{type(exc).__name__}:{exc}"
    latency_ms = int((time.monotonic() - started) * 1000)
    content = ""
    served_model = None
    if body:
        try:
            parsed = json.loads(body)
            served_model = parsed.get("model") if isinstance(parsed, dict) else None
            content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            content = body.decode("utf-8", "replace")[:2000]
    identity_ok = bool(status == 200 and served_model == MODEL)
    IDENTITY_AUDIT.append({
        "http_status": status,
        "served_model": served_model,
        "identity_ok": identity_ok,
        "prompt_sha256": hashlib.sha256((system + "\n" + user).encode()).hexdigest(),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "latency_ms": latency_ms,
    })
    return {"status": status, "content": content, "served_model": served_model, "identity_ok": identity_ok, "latency_ms": latency_ms, "error": error}

def choice(text: str) -> str | None:
    m = re.search(r"\b([ABCD])\b", text.upper())
    return m.group(1) if m else None

def answer_call(mode: str, prompt: str) -> dict[str, Any]:
    systems = {
        "A": "Solve the task directly from the supplied information. Preserve nuance and source meaning. Reply with exactly one option letter A, B, C, or D.",
        "B": "Solve only from the compact representation. Do not invent missing information. Reply with exactly one option letter A, B, C, or D.",
        "C": "You are the V2 heterogeneous cognitive compiler lane. Preserve stated invariants, use the task-appropriate formal representation, and solve. Reply with exactly one option letter A, B, C, or D.",
        "D": "You are an evidence-first arbiter. Given the original task and two independently frozen candidate answers, choose the answer best supported by the task. Reply with exactly one option letter A, B, C, or D.",
        "E": "You are the V2 structure/compiler lane in cooperative mode. Use the typed semantic packet from V1 as a fallible hypothesis source, preserve task invariants, correct any unsupported claim, and return exactly one option letter A, B, C, or D.",
    }
    return call_model(systems[mode], prompt, 16)

def main() -> int:
    canary = call_model("Calibration. Reply exactly B.", "Correct calibration option is B. Reply B.", 8)
    canary_choice = choice(canary["content"])
    if not (canary["identity_ok"] and canary_choice == "B"):
        Path("synergy-canary-v4.json").write_text(json.dumps({"gate":"INCONCLUSIVE_CANARY","canary":canary,"identity_audit":IDENTITY_AUDIT}, indent=2) + "\n")
        return 2

    rows = []
    for task in TASKS:
        a = answer_call("A", task["raw"])
        b = answer_call("B", task["fixed"])
        c = answer_call("C", task["hhir"])
        a_ch, b_ch, c_ch = choice(a["content"]), choice(b["content"]), choice(c["content"])

        if a_ch == c_ch and a_ch is not None:
            d_ch = a_ch
            d = {"derived_without_extra_call": True, "content": a_ch, "identity_ok": True, "latency_ms": 0}
        else:
            d_prompt = task["raw"] + f"\nFrozen V1 answer={a_ch}; frozen V2 answer={c_ch}. Adjudicate from task evidence."
            d = answer_call("D", d_prompt)
            d_ch = choice(d["content"])

        sem = call_model(
            "You are the V1 semantic explorer in a cooperative solver. Produce a concise typed packet with: HYPOTHESIS, CAVEAT, COUNTEREXAMPLE_CHECK. Do not exceed 80 tokens.",
            task["raw"],
            96,
        )
        e_prompt = task["hhir"] + "\nV1_TYPED_PACKET:\n" + sem["content"][:900]
        e = answer_call("E", e_prompt)
        e_ch = choice(e["content"])

        rows.append({
            "task_id": task["id"], "family": task["family"], "gold": task["gold"],
            "A": {"choice": a_ch, "correct": a_ch == task["gold"], "latency_ms": a["latency_ms"]},
            "B": {"choice": b_ch, "correct": b_ch == task["gold"], "latency_ms": b["latency_ms"]},
            "C": {"choice": c_ch, "correct": c_ch == task["gold"], "latency_ms": c["latency_ms"]},
            "D": {"choice": d_ch, "correct": d_ch == task["gold"], "latency_ms": d.get("latency_ms", 0), "derived_without_extra_call": d.get("derived_without_extra_call", False)},
            "E": {"choice": e_ch, "correct": e_ch == task["gold"], "latency_ms": sem["latency_ms"] + e["latency_ms"], "semantic_packet_sha256": hashlib.sha256(sem["content"].encode()).hexdigest()},
        })

    all_exact = bool(IDENTITY_AUDIT) and all(x["identity_ok"] for x in IDENTITY_AUDIT)
    qs = {arm: sum(int(r[arm]["correct"]) for r in rows) for arm in "ABCDE"}
    n = len(rows)
    synergy_gain = qs["E"] - max(qs["A"], qs["C"], qs["D"])
    e_only = sum(r["E"]["correct"] and not r["A"]["correct"] and not r["C"]["correct"] and not r["D"]["correct"] for r in rows)
    error_overlap_ac = sum((not r["A"]["correct"]) and (not r["C"]["correct"]) for r in rows)
    family = {r["family"]: {arm: int(r[arm]["correct"]) for arm in "ABCDE"} for r in rows}
    total_latency = {arm: sum(r[arm]["latency_ms"] for r in rows) for arm in "ABCDE"}

    if not all_exact:
        gate = "INCONCLUSIVE_MODEL_IDENTITY_OR_PROVIDER_FAILURE"
    elif qs["E"] < qs["A"]:
        gate = "VALID_NEGATIVE_SYNERGY_REGRESSION"
    elif synergy_gain > 0:
        gate = "CANARY_POSITIVE_SUPERADDITIVE_SIGNAL"
    elif qs["E"] == max(qs["A"], qs["C"], qs["D"]):
        gate = "CANARY_TIED_QUALITY_NO_SUPERADDITIVITY"
    else:
        gate = "VALID_NO_SYNERGY_PROMOTION"

    receipt = {
        "schema": "deus/cognitive-synergy-v4-canary/1",
        "provider": "BLOCKRUN",
        "endpoint": ENDPOINT,
        "requested_model": MODEL,
        "task_count": n,
        "task_bank_sha256": hashlib.sha256(json.dumps(TASKS, sort_keys=True).encode()).hexdigest(),
        "arms": {
            "A": "V1 raw direct",
            "B": "fixed compact",
            "C": "V2 HHIR structured",
            "D": "independent V1/V2 plus evidence arbiter on disagreement",
            "E": "cooperative V1 semantic packet -> V2 structured final",
        },
        "quality_correct": qs,
        "accuracy": {k: qs[k] / n for k in qs},
        "synergy": {
            "gain_correct_vs_best_A_C_D": synergy_gain,
            "E_only_solves": e_only,
            "A_C_joint_error_overlap": error_overlap_ac,
            "family_matrix": family,
            "latency_ms_sum": total_latency,
        },
        "rows": rows,
        "identity": {
            "call_count": len(IDENTITY_AUDIT),
            "all_calls_exact_identity": all_exact,
            "served_models": sorted({str(x["served_model"]) for x in IDENTITY_AUDIT}),
            "per_call": IDENTITY_AUDIT,
        },
        "promotion_gate": gate,
        "truth": {
            "canary_only_not_100_task_suite": True,
            "same_served_model_required": True,
            "provider_model_weights_unchanged": True,
            "control_plane_orchestration_test": True,
            "global_cognitive_gain_claim": False,
            "synergy_claim_requires_full_suite": True,
        },
    }
    Path("synergy-canary-v4.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ["schema","task_count","quality_correct","synergy","promotion_gate","identity"]}, indent=2))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0

if __name__ == "__main__":
    raise SystemExit(main())
