#!/usr/bin/env python3
"""DEUS Engine v1 — orchestration shell.

This is a provider-neutral cognitive/writing engine around replaceable model
adapters. It is not a trained foundation model by itself.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Sequence

from model_adapter import Candidate, MockAdapter, OpenAICompatHTTPAdapter
from provenance import CausalLedger, private_commitment, sha256
from recombiner import LogicAtom, Recombiner, RoleSelf, render_model_prompt
from writing_lab import WritingCase, evaluate


@dataclass(frozen=True)
class RunResult:
    mode: str
    prompt_digest: str
    selected: Candidate
    candidates: tuple[Candidate, ...]
    experiment_id: str
    literary_score: float | None
    causal_event_id: str

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "prompt_digest": self.prompt_digest,
            "selected": asdict(self.selected),
            "candidates": [asdict(x) for x in self.candidates],
            "experiment_id": self.experiment_id,
            "literary_score": self.literary_score,
            "causal_event_id": self.causal_event_id,
        }


def default_state_dir() -> Path:
    return Path(os.getenv("DEUS_ENGINE_STATE_DIR", str(Path.home() / ".deus_engine_v1")))


def _candidate_score(candidate: Candidate, mode: str) -> tuple[float, dict]:
    if mode != "writing":
        # No fake universal truth score. Prefer non-empty responses and preserve
        # model disagreement for later verification.
        score = 1.0 if candidate.text.strip() else 0.0
        return score, {"nonempty": bool(candidate.text.strip())}
    report = evaluate(WritingCase(case_id="candidate", text=candidate.text))
    return report.total, report.to_dict()


def run(*, stimulus: str, atoms: Sequence[LogicAtom], role: RoleSelf,
        adapters: Sequence, recombination_mode: str = "DISTANT",
        mode: str = "reasoning", seed: int | None = None,
        private_state: dict | None = None) -> RunResult:
    if not adapters:
        raise ValueError("at least one model adapter is required")

    recombiner = Recombiner(seed=seed)
    exp = recombiner.build(atoms, role, stimulus, mode=recombination_mode,
                           count=min(4, len(atoms)))
    base_prompt = render_model_prompt(exp)
    if mode == "writing":
        base_prompt += (
            "\n\nWrite the scene as literature. Do not explain the mechanism directly. "
            "Let character history produce behavior; preserve at least one live ambiguity. "
            "Avoid generic connective prose and avoid making every sentence equally polished."
        )

    candidates: list[Candidate] = []
    scored: list[tuple[float, int, dict]] = []
    for i, adapter in enumerate(adapters):
        candidate = adapter.generate(base_prompt)
        candidates.append(candidate)
        score, evidence = _candidate_score(candidate, mode)
        scored.append((score, i, evidence))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = candidates[scored[0][1]]
    literary_score = scored[0][0] if mode == "writing" else None

    state_dir = default_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    ledger = CausalLedger(state_dir / "events.jsonl")
    salt = os.getenv("DEUS_STATE_SALT", "UNSEALED-LOCAL-DEMO")
    commitment = private_commitment(private_state or {}, salt=salt)
    event = ledger.append(
        kind="WRITING_RUN" if mode == "writing" else "COGNITIVE_RUN",
        payload={
            "experiment_id": exp.experiment_id,
            "stimulus_digest": sha256(stimulus),
            "prompt_digest": sha256(base_prompt),
            "candidate_digests": [sha256(x.text) for x in candidates],
            "selected_digest": sha256(selected.text),
            "adapter_ids": [x.adapter_id for x in candidates],
            "model_ids": [x.model_id for x in candidates],
            "recombination_mode": recombination_mode,
            "selection_evidence": scored,
        },
        private_state_commitment=commitment,
    )

    return RunResult(
        mode=mode,
        prompt_digest=sha256(base_prompt),
        selected=selected,
        candidates=tuple(candidates),
        experiment_id=exp.experiment_id,
        literary_score=literary_score,
        causal_event_id=event.event_id,
    )


def demo_atoms() -> list[LogicAtom]:
    return [
        LogicAtom("KNOW", "Knowledge can expand reachable action", "epistemic", ("knowledge", "action"), ("more-is-better",)),
        LogicAtom("REFUSE", "A self may refuse an attractive path", "agency", ("preference", "refusal"), ("utility-rules-choice",)),
        LogicAtom("FORGET", "Selective forgetting can preserve possibility", "memory", ("memory", "optionality"), ("remember-everything",)),
        LogicAtom("WORLD", "World rules constrain local choices", "worldbuilding", ("causality", "constraint"), ("rules-are-visible",)),
        LogicAtom("AMBIG", "Ambiguity can carry information without immediate closure", "literary", ("ambiguity", "interpretation"), ("closure-is-required",)),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stimulus")
    ap.add_argument("--mode", choices=["reasoning", "writing"], default="reasoning")
    ap.add_argument("--recombine", choices=["COHERENT", "DISTANT", "HERETICAL"], default="DISTANT")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()

    role = RoleSelf(
        "DEUS_EXPERIMENTAL",
        history=("caught-overformalizing-too-early",),
        preferences=("curiosity", "causal-depth", "distinctive-writing"),
        aversions=("premature-closure", "generic-prose"),
        commitments=("preserve-agency", "keep-provenance"),
        unknowns=("what-becomes-will",),
    )
    adapters = [MockAdapter()] if args.mock else [OpenAICompatHTTPAdapter()]
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
