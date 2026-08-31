#!/usr/bin/env python3
"""Public GitHub issue/comment renderer for the model-independent kernel.

This is a thin public control-plane smoke surface. It renders an auditable
kernel plan and deliberately excludes private lineage/identity material.
"""
from __future__ import annotations

import argparse
from engine import run, demo_atoms
from recombiner import RoleSelf


def default_role() -> RoleSelf:
    return RoleSelf(
        "PUBLIC_KERNEL_EXPERIMENT",
        history=("overformalized-too-early",),
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
        "<!-- KERNEL_LAB_CONSOLE_V1 -->",
        "### Kernel lab response",
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
        "> Public kernel-only smoke mode intentionally stops before a polished conversational answer. "
        "Private conversational realization belongs on owner-controlled/private infrastructure.",
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
