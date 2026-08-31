#!/usr/bin/env python3
"""DEUS Engine v1 — model-independent cognitive kernel.

The kernel runs BEFORE any language-model adapter.  It creates replayable
causal/recombination/counterfactual structure without requiring a text model.
Language models may later realize, criticize, translate or expand the plan, but
must not silently become the source of identity, preference, truth or canonical
state.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Sequence

from recombiner import (
    Experiment,
    LogicAtom,
    Recombiner,
    RoleSelf,
    counterfactual_rebirth,
)


def _digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class KernelProbe:
    kind: str
    target: str
    question: str
    branch_experiment_id: str | None = None


@dataclass(frozen=True)
class KernelPlan:
    plan_id: str
    state: str
    stimulus_digest: str
    primary: Experiment
    probes: tuple[KernelProbe, ...]
    unresolved: tuple[str, ...]
    invariants: tuple[str, ...]
    model_policy: str = "MODEL_IS_SECONDARY_INSTRUMENT"

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "state": self.state,
            "stimulus_digest": self.stimulus_digest,
            "primary": self.primary.to_dict(),
            "probes": [asdict(x) for x in self.probes],
            "unresolved": list(self.unresolved),
            "invariants": list(self.invariants),
            "model_policy": self.model_policy,
        }


def build_kernel_plan(
    *,
    stimulus: str,
    atoms: Sequence[LogicAtom],
    role: RoleSelf,
    recombination_mode: str = "DISTANT",
    seed: int | None = None,
    max_history_branches: int = 3,
) -> KernelPlan:
    """Build the cognitive structure without calling a language model.

    The output intentionally stops short of pretending to possess a universal
    answer.  It records what should be attacked, replayed or left unresolved.
    """
    recombiner = Recombiner(seed=seed)
    primary = recombiner.build(
        atoms,
        role,
        stimulus,
        mode=recombination_mode,
        count=min(4, len(atoms)),
    )

    probes: list[KernelProbe] = []

    # Counterfactual rebirth: remove a small number of history events one at a
    # time.  Branches never overwrite the original causal self.
    for idx, history_item in enumerate(role.history[:max_history_branches]):
        branch = counterfactual_rebirth(
            primary,
            history_drop=idx,
            role_id_suffix=f"DROP_{idx}",
        )
        probes.append(KernelProbe(
            kind="HISTORY_COUNTERFACTUAL",
            target=history_item,
            question="Would the same choice/interpretation survive if this history event never occurred?",
            branch_experiment_id=branch.experiment_id,
        ))

    # Regression targets: attack assumptions rather than accepting the question's
    # frame.  No numerical utility score is allowed to erase contradictions.
    seen_assumptions: set[str] = set()
    for atom in primary.atoms:
        for assumption in atom.assumptions:
            if assumption and assumption not in seen_assumptions:
                seen_assumptions.add(assumption)
                probes.append(KernelProbe(
                    kind="ASSUMPTION_REGRESSION",
                    target=assumption,
                    question="What must already be true for this assumption to hold, and what changes if it is false?",
                ))

    # Causal-direction attack for each selected atom.
    for atom in primary.atoms:
        probes.append(KernelProbe(
            kind="CAUSAL_DIRECTION_ATTACK",
            target=atom.atom_id,
            question="Is the stated direction generative, merely correlated, post-hoc, or reversible under another world model?",
        ))

    unresolved = tuple(dict.fromkeys((*role.unknowns, *(t for a in primary.atoms for t in a.tensions))))
    invariants = tuple(dict.fromkeys((*role.commitments,)))

    payload = {
        "stimulus_digest": _digest(stimulus),
        "primary": primary.to_dict(),
        "probes": [asdict(x) for x in probes],
        "unresolved": unresolved,
        "invariants": invariants,
    }
    return KernelPlan(
        plan_id=f"DKP-{_digest(payload)[:20]}",
        state="KERNEL_READY_NO_CONCLUSION",
        stimulus_digest=_digest(stimulus),
        primary=primary,
        probes=tuple(probes),
        unresolved=unresolved,
        invariants=invariants,
    )


def render_secondary_model_request(plan: KernelPlan, *, task: str) -> str:
    """Ask a replaceable model to work UNDER a kernel plan, not above it."""
    return (
        "You are a replaceable language-model instrument inside a larger cognitive kernel.\n"
        "Do not claim authority over identity, truth, preference or canonical state.\n"
        "Do not collapse unresolved branches merely to produce a neat answer.\n"
        "Use the kernel probes as required attacks/counterfactuals. Return a proposal for later verification.\n\n"
        f"TASK: {task}\n\nKERNEL_PLAN:\n"
        + json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    atoms = [
        LogicAtom("A", "Knowledge can improve action", "epistemic", ("knowledge",), ("more-is-better",)),
        LogicAtom("B", "A self can refuse", "agency", ("refusal",), ("utility-rules-choice",)),
    ]
    role = RoleSelf(
        "DEUS_DEMO",
        history=("overformalized-too-early",),
        preferences=("curiosity",),
        commitments=("preserve-agency",),
        unknowns=("what-becomes-will",),
    )
    print(json.dumps(build_kernel_plan(stimulus="demo", atoms=atoms, role=role, seed=7).to_dict(), ensure_ascii=False, indent=2))
