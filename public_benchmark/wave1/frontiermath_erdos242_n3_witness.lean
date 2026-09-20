import FormalConjecturesUtil

open scoped Topology

namespace Erdos242

/-- A concrete n = 3 witness for the Erdős–Straus statement.
    This does not solve the full conjecture; it closes the attempted n=3 disproof branch. -/
theorem erdos_242_n3_witness :
    ∃ x y z : ℕ, 1 ≤ x ∧ x < y ∧ y < z ∧
      (4 / 3 : ℚ) = 1 / x + 1 / y + 1 / z := by
  refine ⟨1, 4, 12, ?_, ?_, ?_, ?_⟩
  · norm_num
  · norm_num
  · norm_num
  · norm_num

end Erdos242
