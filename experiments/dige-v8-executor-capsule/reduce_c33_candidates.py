#!/usr/bin/env python3
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    files=sorted(Path(args.root).rglob("DIGE_C33_VISUAL_METRICS.json"))
    rows=[json.loads(p.read_text()) for p in files]
    if not rows:
        raise SystemExit("NO_C33_METRICS_FOUND")
    passed=[r for r in rows if r.get("hard_gate_pass")]
    ranked=sorted(passed,key=lambda r:(float(r["score"]),-float(r["guide_dist_m"])),reverse=True)
    selected=ranked[0] if ranked else None
    out={
      "schema":"DIGE_C33_REDUCER_V1",
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
      "state":"SELECTED" if selected else "HOLD_NO_VISUAL_GATE_PASS",
      "truth_boundary":"AUTOMATIC_PRESELECTION_ONLY__FINAL_HUMAN_VISUAL_AUDIT_REQUIRED"
    }
    Path(args.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
