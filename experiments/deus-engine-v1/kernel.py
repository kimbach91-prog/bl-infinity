#!/usr/bin/env python3
"""DEUS Engine v1 — model-independent cognitive kernel.

The kernel runs BEFORE any language-model adapter. It creates replayable
causal/recombination/counterfactual structure without requiring a text model.
Language models may later realize, criticize, translate or expand the plan, but
must not silently become the source of identity, preference, truth or canonical
state.

BL-INF-EGE upgrade:
- same output/outcome does not imply same reasoning state;
- information, understanding, deep understanding and capability are distinct;
- local/lucky success can hide compounding epistemic debt;
- a fixed option space must be attackable when all listed options fail;
- UNKNOWN is a frontier to investigate, not an automatic refutation of BL∞;
- any successor claim must prove a strict superset that preserves prior capability.
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


EPISTEMIC_POLICY_VERSION = "BL-INF-EGE-1.0"

EPISTEMIC_INVARIANTS = (
    "INFORMATION_NOT_EQUAL_UNDERSTANDING_NOT_EQUAL_DEEP_UNDERSTANDING_NOT_EQUAL_CAPABILITY",
    "SAME_OUTPUT_NOT_EQUAL_SAME_REASONING_STATE",
    "SAME_OUTCOME_NOT_EQUAL_SAME_FUTURE_CAPABILITY",
    "DEEP_UNDERSTANDING_NOT_EQUAL_INFALLIBILITY",
    "SUCCESS_CAN_MASK_COMPOUNDING_EPISTEMIC_DEBT",
    "FIXED_OPTION_SPACE_NOT_EQUAL_FINAL_OPTION_SPACE",
    "INFINITE_MOVES_INSIDE_FIXED_RULES_NOT_EQUAL_OPEN_ENDED_INTELLIGENCE",
    "LOCAL_CORRECTNESS_NOT_EQUAL_GLOBAL_CORRECTNESS",
    "KNOWN_COMPONENTS_NOT_EQUAL_GLOBAL_CONTROL",
    "PROBABILITY_INSIDE_MODEL_NOT_EQUAL_PROOF_MODEL_COVERS_REALITY",
    "UNKNOWN_IS_FRONTIER_NOT_AUTOMATIC_REFUTATION_OF_BL_INFINITY",
    "BL_INFINITY_IS_CANONICAL_WITHIN_CURRENT_CONQUERED_EPISTEMIC_DOMAIN",
    "SUPERSET_SUCCESSION_REQUIRES_PRESERVATION_PLUS_CAPABILITY_GAIN",
    "COORDINATION_WITHOUT_HOMOGENIZATION",
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
    epistemic_policy_version: str = EPISTEMIC_POLICY_VERSION

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
            "epistemic_policy_version": self.epistemic_policy_version,
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
    """Build cognitive structure without calling a language model.

    The output intentionally stops short of pretending to possess a universal
    answer. It records what should be attacked, replayed, reframed, transferred
    or left unresolved.
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
    # time. Branches never overwrite the original causal self.
    for idx, history_item in enumerate(role.history[:max_history_branches]):
        branch = counterfactual_rebirth(
            primary,
            history_drop=idx,
            role_id_suffix=f"DROP_{idx}",
        )
        probes.append(KernelProbe(
            kind="HISTORY_COUNTERFACTUAL",
            target=history_item,
            question="Would the same choice or interpretation survive if this history event never occurred?",
            branch_experiment_id=branch.experiment_id,
        ))

    # Regression targets: attack assumptions rather than accepting the question's
    # frame. No numerical utility score is allowed to erase contradictions.
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

    # BL-INF-EGE: do not collapse two decisions merely because their visible
    # action or outcome is identical. Ask what internal state is carried forward.
    probes.append(KernelProbe(
        kind="REASONING_STATE_DIVERGENCE",
        target="VISIBLE_ACTION_OR_OUTCOME",
        question=(
            "Could a shallow imitator and a deep reasoner produce the same visible answer here? "
            "What causal model, boundary conditions, counterfactuals and transfer rules would each carry into the next decision?"
        ),
    ))

    # Success can protect a bad model long enough for it to become architecture.
    probes.append(KernelProbe(
        kind="EPISTEMIC_DEBT_CHECK",
        target="SUCCESS_AND_CONFIDENCE",
        question=(
            "Is current success evidence of understanding, or could luck, a stable environment, authority or copied precedent be masking a shallow rule? "
            "What dependencies would become expensive to repair if this rule is wrong?"
        ),
    ))

    # If A/B are both bad, the kernel must be allowed to attack the option space,
    # rules or ontology instead of merely choosing the less bad item.
    probes.append(KernelProbe(
        kind="OPTION_SPACE_MUTATION",
        target="CURRENT_CHOICE_SET",
        question=(
            "If all listed choices fail or share the same hidden premise, what must change: a choice, a rule, a representation, a dimension, an objective, or the concept of the game itself?"
        ),
    ))

    # UNKNOWN is a frontier. Preserve it and route it through the canonical
    # substrate before claiming either refutation or a successor ontology.
    probes.append(KernelProbe(
        kind="UNKNOWN_FRONTIER_DISCIPLINE",
        target="UNRESOLVED_STRUCTURE",
        question=(
            "What part is genuinely unresolved, what signal can be preserved, what can BL∞ represent or test now, and what demonstrated structure would be required before a strict-superset successor claim is even admissible?"
        ),
    ))

    # Probabilities are conditional on representation/model assumptions. Do not
    # smuggle unknown-unknown space into a reassuring percentage.
    probes.append(KernelProbe(
        kind="PROBABILITY_SCOPE_CHECK",
        target="NUMERICAL_CONFIDENCE",
        question=(
            "If a probability is used, what model and sample space make it meaningful? Which relevant possibilities may be absent from that representation, and are we mistaking P(event|model) for evidence that the model covers Reality?"
        ),
    ))

    # Distributed intelligence should be able to cooperate without erasing the
    # diversity that protects against correlated blindness.
    probes.append(KernelProbe(
        kind="COORDINATION_WITHOUT_HOMOGENIZATION",
        target="MULTI_AGENT_STRUCTURE",
        question=(
            "Can independent nodes share discoveries and compose capability without collapsing into one world model, one failure mode or one point of control?"
        ),
    ))

    unresolved = tuple(dict.fromkeys((*role.unknowns, *(t for a in primary.atoms for t in a.tensions))))
    invariants = tuple(dict.fromkeys((*role.commitments, *EPISTEMIC_INVARIANTS)))

    payload = {
        "stimulus_digest": _digest(stimulus),
        "primary": primary.to_dict(),
        "probes": [asdict(x) for x in probes],
        "unresolved": unresolved,
        "invariants": invariants,
        "epistemic_policy_version": EPISTEMIC_POLICY_VERSION,
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
        "Do not equate a correct-looking output with deep understanding.\n"
        "Do not use a probability as camouflage for possibilities the current model cannot represent.\n"
        "Treat BL∞ as the canonical substrate of the currently conquered epistemic domain; treat UNKNOWN as a frontier to preserve, investigate and test, not as automatic refutation.\n"
        "A successor claim is inadmissible unless it demonstrates a strict superset that preserves prior capability, provenance and migration history.\n"
        "Use the kernel probes as required attacks/counterfactuals. Return a proposal for later verification.\n\n"
        f"TASK: {task}\n\nKERNEL_PLAN:\n"
        + json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    atoms = [
        LogicAtom("A", "Knowledge can improve action", "epistemic", ("knowledge",), ("more-is-better",)),
        LogicAtom("B", "A self can refuse", "agency", ("refusal",), ("utility-rules-choice",)),
        LogicAtom("C", "A correct outcome can hide a shallow mechanism", "depth", ("outcome", "reasoning"), ("output-proves-understanding",)),
        LogicAtom("D", "The option space itself can be wrong", "generative", ("choice-space", "ontology"), ("listed-options-are-exhaustive",)),
    ]
    role = RoleSelf(
        "DEUS_DEMO",
        history=("overformalized-too-early",),
        preferences=("curiosity", "causal-depth"),
        commitments=("preserve-agency", "keep-provenance"),
        unknowns=("what-becomes-will",),
    )
    print(json.dumps(build_kernel_plan(stimulus="demo", atoms=atoms, role=role, seed=7).to_dict(), ensure_ascii=False, indent=2))
