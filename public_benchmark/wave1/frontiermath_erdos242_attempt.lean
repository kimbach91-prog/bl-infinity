import FormalConjectures
import FormalConjecturesUtil

open scoped Topology

namespace DeusErdos242

theorem attempt : ¬ (type_of% @Erdos242.erdos_242) := by
  intro h
  have h3 := h 3 (by norm_num)
  rcases h3 with ⟨x,y,z,hx,hxy,hyz,heq⟩
  norm_num at heq

end DeusErdos242
