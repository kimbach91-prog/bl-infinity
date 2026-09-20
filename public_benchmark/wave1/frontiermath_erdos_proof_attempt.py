#!/usr/bin/env python3
import pathlib, subprocess, json, hashlib, sys
p=pathlib.Path("vendor/LeanOpenProblems/apn/data/erdos/Isolated/Erdos1.erdos_1.lean")
src=p.read_text()
needle="theorem erdos_1 : ∃ C > (0 : ℝ), ∀ (N : ℕ) (A : Finset ℕ) (_ : IsSumDistinctSet A N),\n    N ≠ 0 → C * 2 ^ A.card < N := by\n  sorry"
candidate="theorem erdos_1 : ∃ C > (0 : ℝ), ∀ (N : ℕ) (A : Finset ℕ) (_ : IsSumDistinctSet A N),\n    N ≠ 0 → C * 2 ^ A.card < N := by\n  aesop"
if needle not in src: raise SystemExit("target theorem shape changed")
p.write_text(src.replace(needle,candidate,1))
proc=subprocess.run(["uv","run","lake","env","lean",str(p)],capture_output=True,text=True,timeout=240)
receipt={
 "schema":"DEUS_FRONTIERMATH_ERDOS_PROOF_ATTEMPT_V1",
 "source_commit":"af3b82f9d2fd38bea33d59e637b6b4eff54a464c",
 "target":"Erdos1.erdos_1",
 "candidate_strategy":"aesop baseline, no sorry inserted in target theorem",
 "returncode":proc.returncode,
 "lean_verified":proc.returncode==0,
 "stdout_tail":proc.stdout[-4000:],
 "stderr_tail":proc.stderr[-4000:],
 "candidate_digest":hashlib.sha256(candidate.encode()).hexdigest(),
 "claim_boundary":"A PASS would prove only this exact Lean theorem under this source snapshot. A FAIL is a hard proof-attempt receipt, not evidence the mathematical statement is false."
}
pathlib.Path("frontiermath-erdos-proof-attempt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({k:v for k,v in receipt.items() if k not in ("stdout_tail","stderr_tail")},sort_keys=True))
