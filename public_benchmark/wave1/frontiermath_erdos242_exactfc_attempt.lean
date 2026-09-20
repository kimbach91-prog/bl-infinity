import FormalConjecturesUtil

open scoped Topology

namespace Erdos242

/--
For every n > 2 there exist distinct integers 1 ≤ x < y < z such that
4/n = 1/x + 1/y + 1/z.
-/
theorem erdos_242 (n : ℕ) (hn : 2 < n) :
    ∃ x y z : ℕ, 1 ≤ x ∧ x < y ∧ y < z ∧
      (4 / n : ℚ) = 1 / x + 1 / y + 1 / z := by
  sorry

end Erdos242

theorem Erdos242.erdos_242.disproof : ¬ (type_of% @Erdos242.erdos_242) := by
  intro h
  have h3 := h 3 (by norm_num)
  rcases h3 with ⟨x, y, z, hx, hxy, hyz, heq⟩
  norm_num at heq
