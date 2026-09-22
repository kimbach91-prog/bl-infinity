import FormalConjecturesUtil

open scoped Topology

namespace Erdos242

/-- Every even denominator n = 2*k with k ≥ 2 satisfies the Erdős–Straus
    three-distinct-unit-fraction conclusion via
    x = k, y = k+1, z = k*(k+1).

    This is a strict public partial-family result. It does not prove the full
    Erdős–Straus conjecture and is not a FrontierMath benchmark solve. -/
theorem erdos_242_even_family (k : ℕ) (hk : 2 ≤ k) :
    ∃ x y z : ℕ, 1 ≤ x ∧ x < y ∧ y < z ∧
      (4 / (2 * k) : ℚ) = 1 / x + 1 / y + 1 / z := by
  refine ⟨k, k + 1, k * (k + 1), ?_, ?_, ?_, ?_⟩
  · omega
  · omega
  · nlinarith
  · have hk0_nat : k ≠ 0 := by omega
    have hk1_nat : k + 1 ≠ 0 := by omega
    have hk0 : (k : ℚ) ≠ 0 := by exact_mod_cast hk0_nat
    have hk1 : ((k + 1 : ℕ) : ℚ) ≠ 0 := by exact_mod_cast hk1_nat
    push_cast
    field_simp [hk0, hk1]
    ring

end Erdos242
