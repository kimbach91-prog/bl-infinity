#!/usr/bin/env python3
import argparse, hashlib, json, os, pathlib, subprocess, sys, time

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(pathlib.Path(p).read_text())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--solver-cmd", default=os.environ.get("DEUS_BENCH_SOLVER_CMD",""))
    ap.add_argument("--solver-argv-file", default="")
    ap.add_argument("--out", default="receipts/general-reasoning-receipt.json")
    args=ap.parse_args()
    task=load(args.task)
    required=["task_id","benchmark","benchmark_version","task_ref","allowed_tools","budget","evaluator_ref","authority_ref"]
    miss=[k for k in required if k not in task]
    if miss: raise SystemExit("missing:"+",".join(miss))
    pathlib.Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    task_bytes=pathlib.Path(args.task).read_bytes()
    started=time.time()

    solver_argv=None
    if args.solver_argv_file:
        solver_argv=load(args.solver_argv_file)
        if not isinstance(solver_argv,list) or not solver_argv or not all(isinstance(x,str) and x for x in solver_argv):
            raise SystemExit("invalid solver argv file")
    elif args.solver_cmd:
        # Legacy compatibility only; benchmark path should prefer argv file.
        solver_argv=None

    if not solver_argv and not args.solver_cmd:
        receipt={
          "schema":"DEUS_BENCH_EXECUTOR_RECEIPT_V1",
          "task_id":task["task_id"],
          "executor_id":"DEUS_BENCH_EXECUTOR_V1",
          "executor_version":"1.1.0",
          "input_digest":sha256_bytes(task_bytes),
          "execution_state":"HOLD_NO_BOUND_SOLVER_COMMAND",
          "result_ref":None,
          "result_digest":None,
          "started_at":started,
          "finished_at":time.time(),
          "receipt_id":"RCP-"+task["task_id"]+"-NO-SOLVER",
          "claim_boundary":"Contract/router admission exists; semantic execution has not occurred."
        }
        pathlib.Path(args.out).write_text(json.dumps(receipt,indent=2)+"\n")
        print(json.dumps(receipt,indent=2))
        return 3

    env=os.environ.copy()
    env["DEUS_TASK_FILE"]=str(pathlib.Path(args.task).resolve())
    if solver_argv:
        proc=subprocess.run(solver_argv,shell=False,env=env,capture_output=True,text=True)
    else:
        proc=subprocess.run(args.solver_cmd,shell=True,env=env,capture_output=True,text=True)

    result={"stdout":proc.stdout,"stderr":proc.stderr,"returncode":proc.returncode}
    result_path=pathlib.Path(args.out).with_name("general-reasoning-result.json")
    result_path.write_text(json.dumps(result,indent=2)+"\n")
    rb=result_path.read_bytes()
    receipt={
      "schema":"DEUS_BENCH_EXECUTOR_RECEIPT_V1",
      "task_id":task["task_id"],
      "executor_id":"DEUS_BENCH_EXECUTOR_V1",
      "executor_version":"1.1.0",
      "input_digest":sha256_bytes(task_bytes),
      "execution_state":"EXECUTED" if proc.returncode==0 else "EXECUTED_FAILED",
      "result_ref":str(result_path),
      "result_digest":sha256_bytes(rb),
      "started_at":started,
      "finished_at":time.time(),
      "receipt_id":"RCP-"+task["task_id"]+"-"+sha256_bytes(rb)[:16],
      "claim_boundary":"Execution receipt only; independent evaluator determines verification/promotion."
    }
    pathlib.Path(args.out).write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))
    return proc.returncode

if __name__=="__main__":
    raise SystemExit(main())
