#!/usr/bin/env python3
import argparse
import json
import sys

VALID_PHASES = {"PREP", "HANDOFF", "TEST", "VERIFY", "POST"}
VALID_WORKERS = {"GPT_TOOL_SUBSTRATE", "DEUS_BENCH_EXECUTOR"}
VALID_LANES = {"ARC_AGI_3_PRIVATE", "FRONTIERMATH_ERDOS", "HLE_ROLLING"}

def evaluate(*, lane, phase, worker, executor_kind, semantic_access,
             executor_receipt="", result_receipt=""):
    if lane not in VALID_LANES:
        return {"ok": False, "state": "HOLD_UNKNOWN_LANE"}
    if phase not in VALID_PHASES:
        return {"ok": False, "state": "HOLD_UNKNOWN_PHASE"}
    if worker not in VALID_WORKERS:
        return {"ok": False, "state": "HOLD_UNKNOWN_WORKER"}

    if phase in {"PREP", "HANDOFF", "POST"}:
        return {"ok": True, "state": f"{phase}_ALLOWED"}

    if phase == "TEST":
        if executor_kind != "DEUS":
            return {"ok": False, "state": "HOLD_TEST_REQUIRES_DEUS_EXECUTOR"}
        if not executor_receipt:
            return {"ok": False, "state": "HOLD_MISSING_DEUS_EXECUTOR_RECEIPT"}
        if worker == "GPT_TOOL_SUBSTRATE" and semantic_access:
            return {"ok": False, "state": "HOLD_GPT_SEMANTIC_TEST_ACCESS_TAINT"}
        return {"ok": True, "state": "TEST_CONTROL_PLANE_ALLOWED_DEUS_EXECUTOR_BOUND"}

    # VERIFY
    if not result_receipt:
        return {"ok": False, "state": "HOLD_VERIFY_REQUIRES_RESULT_RECEIPT"}
    if worker == "GPT_TOOL_SUBSTRATE" and semantic_access:
        return {"ok": False, "state": "HOLD_GPT_ADAPTIVE_VERIFY_TAINT"}
    return {"ok": True, "state": "VERIFY_CONTROL_PLANE_ALLOWED"}

def self_test():
    cases = [
        (dict(lane="FRONTIERMATH_ERDOS", phase="PREP", worker="GPT_TOOL_SUBSTRATE",
              executor_kind="NONE", semantic_access=False), True),
        (dict(lane="HLE_ROLLING", phase="HANDOFF", worker="GPT_TOOL_SUBSTRATE",
              executor_kind="NONE", semantic_access=False), True),
        (dict(lane="ARC_AGI_3_PRIVATE", phase="TEST", worker="GPT_TOOL_SUBSTRATE",
              executor_kind="GPT", semantic_access=False, executor_receipt="r"), False),
        (dict(lane="ARC_AGI_3_PRIVATE", phase="TEST", worker="GPT_TOOL_SUBSTRATE",
              executor_kind="DEUS", semantic_access=False), False),
        (dict(lane="ARC_AGI_3_PRIVATE", phase="TEST", worker="GPT_TOOL_SUBSTRATE",
              executor_kind="DEUS", semantic_access=True, executor_receipt="r"), False),
        (dict(lane="FRONTIERMATH_ERDOS", phase="TEST", worker="GPT_TOOL_SUBSTRATE",
              executor_kind="DEUS", semantic_access=False, executor_receipt="r"), True),
        (dict(lane="HLE_ROLLING", phase="VERIFY", worker="GPT_TOOL_SUBSTRATE",
              executor_kind="DEUS", semantic_access=False), False),
        (dict(lane="HLE_ROLLING", phase="VERIFY", worker="GPT_TOOL_SUBSTRATE",
              executor_kind="DEUS", semantic_access=False, result_receipt="rr"), True),
    ]
    results=[]
    passed=0
    for idx,(kwargs,expected) in enumerate(cases,1):
        got=evaluate(**kwargs)
        ok=(got["ok"] is expected)
        passed += int(ok)
        results.append({"case":idx,"expected":expected,"actual":got,"pass":ok})
    out={"suite":"DEUS_WAVE1_TOOL_SUBSTRATE_GUARD","passed":passed,"total":len(cases),"results":results}
    print(json.dumps(out,indent=2))
    return 0 if passed == len(cases) else 1

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("self-test")
    q=sub.add_parser("check")
    q.add_argument("--lane",required=True,choices=sorted(VALID_LANES))
    q.add_argument("--phase",required=True,choices=sorted(VALID_PHASES))
    q.add_argument("--worker",required=True,choices=sorted(VALID_WORKERS))
    q.add_argument("--executor-kind",default="NONE")
    q.add_argument("--semantic-access",action="store_true")
    q.add_argument("--executor-receipt",default="")
    q.add_argument("--result-receipt",default="")
    args=p.parse_args()
    if args.cmd=="self-test":
        return self_test()
    out=evaluate(
        lane=args.lane, phase=args.phase, worker=args.worker,
        executor_kind=args.executor_kind, semantic_access=args.semantic_access,
        executor_receipt=args.executor_receipt, result_receipt=args.result_receipt
    )
    print(json.dumps(out,indent=2))
    return 0 if out["ok"] else 2

if __name__=="__main__":
    sys.exit(main())
