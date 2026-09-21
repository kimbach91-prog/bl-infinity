#!/usr/bin/env python3
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--plan",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()

    plan_receipt=json.loads(Path(args.plan).read_text())
    matrix=plan_receipt.get("matrix") or []
    expected={str(x["id"]):float(x["guide_dist"]) for x in matrix}
    files=sorted(Path(args.root).rglob("DIGE_C33_VISUAL_METRICS.json"))
    rows=[json.loads(p.read_text()) for p in files]
    if not rows:
        raise SystemExit("NO_C34_METRICS_FOUND")

    observed={str(r["candidate_id"]):float(r["guide_dist_m"]) for r in rows}
    missing=sorted(set(expected)-set(observed))
    extra=sorted(set(observed)-set(expected))
    if missing or extra:
        raise SystemExit(f"C34_CANDIDATE_SET_MISMATCH missing={missing} extra={extra}")

    for cid,dist in expected.items():
        if abs(observed[cid]-dist)>1e-9:
            raise SystemExit(f"C34_GUIDE_DIST_MISMATCH {cid}")

    passed=[r for r in rows if r.get("hard_gate_pass")]
    ranked=sorted(passed,key=lambda r:(float(r["score"]),-float(r["guide_dist_m"])),reverse=True)
    selected=ranked[0] if ranked else None
    ordered=sorted(expected.items(),key=lambda x:x[1])
    boundary_ids={ordered[0][0],ordered[-1][0]}
    refine_recommended=(selected is None) or (selected["candidate_id"] in boundary_ids)

    out={
      "schema":"DIGE_C34_LOGICAL_RESOURCE_REDUCER_V1",
      "resource_plan_digest":plan_receipt["plan"]["planDigest"],
      "resource_execution_mode":plan_receipt["runtimeDevice"],
      "candidate_count":len(rows),
      "hard_gate_pass_count":len(passed),
      "selected_id":selected["candidate_id"] if selected else None,
      "selected_guide_dist_m":selected["guide_dist_m"] if selected else None,
      "selected_score":selected["score"] if selected else None,
      "ranked_passes":[
        {"candidate_id":r["candidate_id"],"guide_dist_m":r["guide_dist_m"],"score":r["score"]}
        for r in ranked
      ],
      "all_candidates":rows,
      "refine_recommended":bool(refine_recommended),
      "state":"SELECTED" if selected else "HOLD_NO_VISUAL_GATE_PASS",
      "planned_search_avoided_candidates":plan_receipt["plan"].get("optimization",{}).get("avoidedCandidates"),
      "planned_search_avoided_fraction":plan_receipt["plan"].get("optimization",{}).get("avoidedFraction"),
      "truth_boundary":"COMPILER_DRIVEN_COARSE_PRESELECTION__REFINE_IF_BOUNDARY_OR_NO_PASS__FINAL_HUMAN_VISUAL_AUDIT_REQUIRED"
    }
    Path(args.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
