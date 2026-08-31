#!/usr/bin/env python3
"""DEUS Engine v1 — logic recombination + counterfactual role laboratory.

Experimental only. This module does not claim consciousness or autonomous agency.
It creates replayable thought experiments from explicit logic atoms and role-state
snapshots so that a later model adapter can explore them without silently erasing
causal history.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field, asdict, replace
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class LogicAtom:
    atom_id: str
    statement: str
    family: str
    tags: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    tensions: tuple[str, ...] = ()
    source_ref: str = "UNKNOWN"


@dataclass(frozen=True)
class RoleSelf:
    role_id: str
    history: tuple[str, ...] = ()
    preferences: tuple[str, ...] = ()
    aversions: tuple[str, ...] = ()
    commitments: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    mode: str
    seed: int
    stimulus: str
    role: RoleSelf
    atoms: tuple[LogicAtom, ...]
    mutations: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "mode": self.mode,
            "seed": self.seed,
            "stimulus": self.stimulus,
            "role": asdict(self.role),
            "atoms": [asdict(x) for x in self.atoms],
            "mutations": list(self.mutations),
            "questions": list(self.questions),
        }


MODES = {"COHERENT", "DISTANT", "HERETICAL"}
HERETICAL_MUTATIONS = (
    "NEGATE_ASSUMPTION",
    "INVERT_PRIORITY",
    "REMOVE_GOAL",
    "SWAP_CAUSE_EFFECT",
    "PRESERVE_CONTRADICTION",
)


def _token_set(atom: LogicAtom) -> set[str]:
    return {
        x.lower()
        for x in (*atom.tags, atom.family, *atom.assumptions, *atom.tensions)
        if x
    }


def _jaccard(a: LogicAtom, b: LogicAtom) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def _stable_id(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class Recombiner:
    def __init__(self, seed: int | None = None):
        self.seed = int(seed if seed is not None else random.SystemRandom().randrange(2**63))
        self.rng = random.Random(self.seed)

    def _coherent(self, atoms: Sequence[LogicAtom], count: int) -> list[LogicAtom]:
        anchor = self.rng.choice(list(atoms))
        rest = [x for x in atoms if x.atom_id != anchor.atom_id]
        rest.sort(key=lambda x: (_jaccard(anchor, x), self.rng.random()), reverse=True)
        return [anchor, *rest[: max(0, count - 1)]]

    def _distant(self, atoms: Sequence[LogicAtom], count: int) -> list[LogicAtom]:
        anchor = self.rng.choice(list(atoms))
        rest = [x for x in atoms if x.atom_id != anchor.atom_id]
        rest.sort(key=lambda x: (_jaccard(anchor, x), self.rng.random()))
        return [anchor, *rest[: max(0, count - 1)]]

    def _heretical(self, atoms: Sequence[LogicAtom], count: int) -> tuple[list[LogicAtom], list[str]]:
        chosen = self._distant(atoms, count)
        target_i = self.rng.randrange(len(chosen))
        target = chosen[target_i]
        mutation = self.rng.choice(HERETICAL_MUTATIONS)

        if mutation == "NEGATE_ASSUMPTION" and target.assumptions:
            i = self.rng.randrange(len(target.assumptions))
            assumptions = list(target.assumptions)
            assumptions[i] = f"NOT({assumptions[i]})"
            target = replace(target, assumptions=tuple(assumptions))
        elif mutation == "INVERT_PRIORITY":
            target = replace(target, statement=f"INVERT_PRIORITY({target.statement})")
        elif mutation == "REMOVE_GOAL":
            target = replace(target, statement=f"WITHOUT_DEFAULT_GOAL({target.statement})")
        elif mutation == "SWAP_CAUSE_EFFECT":
            target = replace(target, statement=f"REVERSE_CAUSAL_PROBE({target.statement})")
        else:
            target = replace(target, tensions=tuple((*target.tensions, "DO_NOT_RESOLVE_EARLY")))

        chosen[target_i] = target
        return chosen, [f"{mutation}:{target.atom_id}"]

    def build(
        self,
        atoms: Sequence[LogicAtom],
        role: RoleSelf,
        stimulus: str,
        *,
        mode: str = "DISTANT",
        count: int = 3,
    ) -> Experiment:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {sorted(MODES)}")
        if not atoms:
            raise ValueError("atoms must not be empty")
        count = max(1, min(int(count), len(atoms)))

        mutations: list[str] = []
        if mode == "COHERENT":
            selected = self._coherent(atoms, count)
        elif mode == "DISTANT":
            selected = self._distant(atoms, count)
        else:
            selected, mutations = self._heretical(atoms, count)

        questions = (
            "What does this role choose before explaining the choice?",
            "Which part of the explanation is causal and which part may be post-hoc rationalization?",
            "What single history edit would most likely change the choice?",
            "Would the role keep the choice after seeing a bad outcome? Why?",
            "Which uncertainty should remain unresolved instead of being optimized away?",
        )
        payload = {
            "mode": mode,
            "seed": self.seed,
            "stimulus": stimulus,
            "role": asdict(role),
            "atoms": [asdict(x) for x in selected],
            "mutations": mutations,
        }
        return Experiment(
            experiment_id=f"DXR-{_stable_id(payload)}",
            mode=mode,
            seed=self.seed,
            stimulus=stimulus,
            role=role,
            atoms=tuple(selected),
            mutations=tuple(mutations),
            questions=questions,
        )


def counterfactual_rebirth(exp: Experiment, *, history_drop: int | None = None,
                           history_add: str | None = None,
                           role_id_suffix: str = "REBIRTH") -> Experiment:
    """Create a branch, never overwrite the original role history."""
    history = list(exp.role.history)
    mutations = list(exp.mutations)
    if history_drop is not None and history:
        idx = history_drop % len(history)
        removed = history.pop(idx)
        mutations.append(f"HISTORY_DROP:{removed}")
    if history_add:
        history.append(history_add)
        mutations.append(f"HISTORY_ADD:{history_add}")

    role = replace(
        exp.role,
        role_id=f"{exp.role.role_id}::{role_id_suffix}",
        history=tuple(history),
    )
    payload = exp.to_dict()
    payload["role"] = asdict(role)
    payload["mutations"] = mutations
    return Experiment(
        experiment_id=f"DXR-{_stable_id(payload)}",
        mode=exp.mode,
        seed=exp.seed,
        stimulus=exp.stimulus,
        role=role,
        atoms=exp.atoms,
        mutations=tuple(mutations),
        questions=exp.questions,
    )


def render_model_prompt(exp: Experiment) -> str:
    """Render an experiment for any replaceable language-model adapter."""
    return (
        "Run this as a causal role experiment, not as a request for the globally best answer.\n"
        "Choose first from the role's local history/preferences; explain second. Preserve uncertainty.\n\n"
        + json.dumps(exp.to_dict(), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    atoms = [
        LogicAtom("A", "More knowledge can improve action", "epistemic", ("knowledge", "action"), ("knowledge-is-useful",)),
        LogicAtom("B", "A self may refuse a high-utility path", "agency", ("preference", "refusal"), ("choice-is-not-proof",)),
        LogicAtom("C", "Forgetting can protect future possibility", "memory", ("forgetting", "optionality"), ("memory-is-always-good",)),
        LogicAtom("D", "Commitment can survive uncertainty", "identity", ("commitment", "unknown"), ("certainty-before-action",)),
    ]
    role = RoleSelf("DEMO", ("failed-after-overexplaining",), ("curiosity",), ("premature-closure",), ("preserve-agency",), ("what-is-will",))
    r = Recombiner(seed=7)
    e = r.build(atoms, role, "Choose whether to continue a seemingly optimal task", mode="HERETICAL", count=3)
    print(render_model_prompt(e))
