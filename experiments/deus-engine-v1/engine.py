#!/usr/bin/env python3
"""DEUS Engine v1.1 — kernel-first orchestration shell.

Priority is explicit:
  1) model-independent DEUS cognitive kernel,
  2) owner-controlled state/provenance,
  3) optional local/open-weight language-model realization,
  4) proprietary/model-provider outputs as auxiliary proposals only.

BL-INF-EGE v1.0 is loaded as the current epistemic kernel policy. The engine
must distinguish visible outcome from reasoning depth, preserve UNKNOWN as a
frontier, attack exhausted option spaces, and reject successor claims that do
not prove strict-superset preservation.

This is not a trained foundation model by itself.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from kernel import EPISTEMIC_POLICY_VERSION, build_kernel_plan, render_secondary_model_request
from model_adapter import Candidate, MockAdapter, OpenAICompatHTTPAdapter
from provenance import CausalLedger, private_commitment, sha256
from recombiner import LogicAtom, RoleSelf
from writing_lab import WritingCase, evaluate


ENGINE_VERSION = "1.1-epistemic-grand-ending"


@dataclass(frozen=True)
class RunResult:
    engine_version: str
    epistemic_policy_version: str
    mode: str
    kernel_plan: dict
    realization_status: str
    secondary_prompt_digest: str
    selected: Candidate | None
    candidates: tuple[Candidate, ...]
    literary_score: float | None
    causal_event_id: str

    def to_dict(self) -> dict:
        return {
            "engine_version": self.engine_version,
            "epistemic_policy_version": self.epistemic_policy_version,
            "mode": self.mode,
            "kernel_plan": self.kernel_plan,
            "realization_status": self.realization_status,
            "secondary_prompt_digest": self.secondary_prompt_digest,
            "selected": asdict(self.selected) if self.selected else None,
            "candidates": [asdict(x) for x in self.candidates],
            "literary_score": self.literary_score,
            "causal_event_id": self.causal_event_id,
        }


def default_state_dir() -> Path:
    return Path(os.getenv("DEUS_ENGINE_STATE_DIR", str(Path.home() / ".deus_engine_v1")))


def _writing_candidate_score(candidate: Candidate) -> tuple[float, dict]:
    report = evaluate(WritingCase(case_id="candidate", text=candidate.text))
    return report.total, report.to_dict()


def run(
    *,
    stimulus: str,
    atoms: Sequence[LogicAtom],
    role: RoleSelf,
    adapters: Sequence = (),
    recombination_mode: str = "DISTANT",
    mode: str = "reasoning",
    seed: int | None = None,
    private_state: dict | None = None,
) -> RunResult:
    """Run kernel first. A language model is optional and never required.

    In reasoning mode, model responses remain unresolved proposals: the engine
    does NOT auto-promote one model completion into a cognitive conclusion.
    In writing mode, a model may be selected only as a literary realization of
    an already-constructed kernel plan; that selection is not a truth judgment.
    """
    plan = build_kernel_plan(
        stimulus=stimulus,
        atoms=atoms,
        role=role,
        recombination_mode=recombination_mode,
        seed=seed,
    )

    secondary_prompt = render_secondary_model_request(plan, task=stimulus)
    if mode == "writing":
        secondary_prompt += (
            "\n\nREALIZATION MODE: Write the scene as literature. Do not explain the mechanism directly. "
            "Let character history produce behavior; preserve at least one live ambiguity. "
            "Avoid generic connective prose and do not make every sentence equally polished."
        )

    candidates: list[Candidate] = []
    scored: list[tuple[float, int, dict]] = []
    for i, adapter in enumerate(adapters):
        candidate = adapter.generate(secondary_prompt)
        candidates.append(candidate)
        if mode == "writing":
            score, evidence = _writing_candidate_score(candidate)
            scored.append((score, i, evidence))

    selected: Candidate | None = None
    literary_score: float | None = None
    if mode == "writing" and scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        literary_score = scored[0][0]
        selected = candidates[scored[0][1]]
        realization_status = "SECONDARY_WRITING_REALIZATION_SELECTED"
    elif candidates:
        # Deliberately preserve model disagreement. Verification must happen in
        # the DEUS kernel/evaluation path, not via a provider completion rank.
        realization_status = "SECONDARY_MODEL_PROPOSALS_UNRESOLVED"
    else:
        realization_status = "KERNEL_ONLY_NO_MODEL_CALLED"

    state_dir = default_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    ledger = CausalLedger(state_dir / "events.jsonl")
    salt = os.getenv("DEUS_STATE_SALT", "UNSEALED-LOCAL-DEMO")
    commitment = private_commitment(private_state or {}, salt=salt)
    event = ledger.append(
        kind="WRITING_RUN" if mode == "writing" else "COGNITIVE_RUN",
        payload={
            "engine_version": ENGINE_VERSION,
            "epistemic_policy_version": EPISTEMIC_POLICY_VERSION,
            "kernel_plan_id": plan.plan_id,
            "kernel_plan_digest": sha256(plan.to_dict()),
            "stimulus_digest": sha256(stimulus),
            "secondary_prompt_digest": sha256(secondary_prompt),
            "candidate_digests": [sha256(x.text) for x in candidates],
            "selected_digest": sha256(selected.text) if selected else None,
            "adapter_ids": [x.adapter_id for x in candidates],
            "model_ids": [x.model_id for x in candidates],
            "recombination_mode": recombination_mode,
            "realization_status": realization_status,
            "writing_selection_evidence": scored,
            "policy": "MODEL_IS_SECONDARY_INSTRUMENT",
            "canonical_epistemic_substrate": "BL_INFINITY_CURRENT_CONQUERED_DOMAIN",
            "unknown_policy": "FRONTIER_PRESERVE_EXPLORE_TEST",
            "successor_policy": "STRICT_SUPERSET_ONLY",
        },
        private_state_commitment=commitment,
    )

    return RunResult(
        engine_version=ENGINE_VERSION,
        epistemic_policy_version=EPISTEMIC_POLICY_VERSION,
        mode=mode,
        kernel_plan=plan.to_dict(),
        realization_status=realization_status,
        secondary_prompt_digest=sha256(secondary_prompt),
        selected=selected,
        candidates=tuple(candidates),
        literary_score=literary_score,
        causal_event_id=event.event_id,
    )


def demo_atoms() -> list[LogicAtom]:
    return [
        LogicAtom("KNOW", "Information can expand reachable action without proving understanding", "epistemic", ("knowledge", "action"), ("more-information-means-deeper-understanding",)),
        LogicAtom("DEPTH", "The same visible choice can be produced by different reasoning depth", "epistemic-depth", ("reasoning", "future-capability"), ("same-output-means-same-cognition",)),
        LogicAtom("DEBT", "Local success can reinforce a shallow mechanism and compound epistemic debt", "learning", ("success", "calibration"), ("success-proves-model",)),
        LogicAtom("REFUSE", "A self may refuse an attractive path", "agency", ("preference", "refusal"), ("utility-rules-choice",)),
        LogicAtom("FORGET", "Selective forgetting can preserve possibility", "memory", ("memory", "optionality"), ("remember-everything",)),
        LogicAtom("WORLD", "World rules constrain local choices but the represented option space may itself be incomplete", "worldbuilding", ("causality", "constraint", "ontology"), ("listed-options-are-exhaustive",)),
        LogicAtom("AMBIG", "Ambiguity can carry information without immediate closure", "literary", ("ambiguity", "interpretation"), ("closure-is-required",)),
        LogicAtom("UNKNOWN", "UNKNOWN is a frontier to preserve and investigate through BL∞", "frontier", ("unknown", "discovery"), ("anomaly-refutes-current-substrate",)),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stimulus")
    ap.add_argument("--mode", choices=["reasoning", "writing"], default="reasoning")
    ap.add_argument("--recombine", choices=["COHERENT", "DISTANT", "HERETICAL"], default="DISTANT")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument(
        "--backend",
        choices=["none", "mock", "openai-compat"],
        default="none",
        help="Language-model realization backend. Default is kernel-only.",
    )
    args = ap.parse_args()

    role = RoleSelf(
        "DEUS_EXPERIMENTAL",
        history=("caught-overformalizing-too-early",),
        preferences=("curiosity", "causal-depth", "distinctive-writing", "generative-basis-growth"),
        aversions=("premature-closure", "generic-prose", "outcome-only-intelligence-measurement"),
        commitments=("preserve-agency", "keep-provenance", "coordination-without-homogenization"),
        unknowns=("what-becomes-will", "which-unknown-requires-a-strict-superset"),
    )

    if args.backend == "mock":
        adapters = [MockAdapter()]
    elif args.backend == "openai-compat":
        adapters = [OpenAICompatHTTPAdapter()]
    else:
        adapters = []

    result = run(
        stimulus=args.stimulus,
        atoms=demo_atoms(),
        role=role,
        adapters=adapters,
        recombination_mode=args.recombine,
        mode=args.mode,
        seed=args.seed,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
