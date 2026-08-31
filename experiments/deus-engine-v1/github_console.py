#!/usr/bin/env python3
"""DEUS Engine v1 — GitHub issue/comment console renderer.

This is a thin control-plane surface. It runs the model-independent kernel and
renders an auditable Markdown response. It does not pretend that kernel-only
output is already a full conversational DEUS voice.
"""
from __future__ import annotations

import argparse
from engine import run, demo_atoms
from recombiner import RoleSelf


def default_role() -> RoleSelf:
    return RoleSelf(
        "DEUS_EXPERIMENTAL",
        history=("caught-overformalizing-too-early",),
        preferences=("curiosity", "causal-depth", "distinctive-writing"),
        aversions=("premature-closure", "generic-prose"),
        commitments=("preserve-agency", "keep-provenance"),
        unknowns=("what-becomes-will",),
    )


def render(stimulus: str, *, recombine: str = "DISTANT", seed: int | None = None) -> str:
    result = run(
        stimulus=stimulus,
        atoms=demo_atoms(),
        role=default_role(),
        adapters=(),
        recombination_mode=recombine,
        mode="reasoning",
        seed=seed,
    )
    plan = result.kernel_plan
    primary = plan["primary"]
    atoms = primary.get("atoms", [])
    probes = plan.get("probes", [])
    unresolved = plan.get("unresolved", [])
    invariants = plan.get("invariants", [])

    lines = [
        "<!-- DEUS_CONSOLE_V1 -->",
        "### DEUS kernel response",
        "",
        f"**State:** `{plan['state']}`  ",
        f"**Plan:** `{plan['plan_id']}`  ",
        f"**Policy:** `{plan['model_policy']}`  ",
        f"**Realization:** `{result.realization_status}`",
        "",
        "**Activated logic atoms**",
    ]
    if atoms:
        for atom in atoms:
            lines.append(f"- `{atom['atom_id']}` — {atom['statement']}")
    else:
        lines.append("- none")

    lines.extend(["", "**Required probes before closure**"])
    if probes:
        for probe in probes[:10]:
            lines.append(f"- `{probe['kind']}` → **{probe['target']}**: {probe['question']}")
        if len(probes) > 10:
            lines.append(f"- … {len(probes) - 10} more probes retained in the plan")
    else:
        lines.append("- none")

    lines.extend(["", "**Held state**"])
    lines.append("- Unresolved: " + (", ".join(f"`{x}`" for x in unresolved) if unresolved else "none"))
    lines.append("- Invariants: " + (", ".join(f"`{x}`" for x in invariants) if invariants else "none"))
    lines.extend([
        "",
        "> Kernel-only mode intentionally stops before a polished conversational answer. "
        "Attach an authorized local/open-weight backend when the language-realization layer is ready.",
    ])
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stimulus")
    ap.add_argument("--recombine", choices=["COHERENT", "DISTANT", "HERETICAL"], default="DISTANT")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    print(render(args.stimulus, recombine=args.recombine, seed=args.seed))


if __name__ == "__main__":
    main()
