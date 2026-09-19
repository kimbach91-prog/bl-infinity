# ARC-AGI-3 — Disclosure / private-evaluation gate

Status: **UNRESOLVED_DIVERGENCE before protected-core submission**

## Official competition requirements

Official ARC Prize 2026 material states:

- ARC-AGI-3 submissions use the designated Kaggle competition.
- Kaggle evaluation has no Internet access.
- Participants must open-source their solutions before receiving official private evaluation scores.
- Prize-eligible code and methods authored by the submitter must be released under a permissive open-source/public-domain-style license.

Official references:

- https://arcprize.org/competitions/2026
- https://arcprize.org/competitions/2026/arc-agi-3

## DEUS boundary

DEUS canon currently protects private solver/method material and prohibits exporting reconstruction-enabling protected-core combinations merely to obtain a benchmark score.

Therefore:

`OFFICIAL_PRIVATE_SCORE_REQUIREMENT -> OPEN_SOURCE_DISCLOSURE`

can conflict with:

`DEUS_PROTECTED_CORE -> NON_RECONSTRUCTABLE_EXTERNALIZATION`

This is a real governance/disclosure conflict, not an execution error.

## Allowed resolution paths

1. **PUBLIC-SAFE PROJECTION** — build an independently publishable/open-source ARC agent projection containing no protected DEUS core. Official score would measure that projection only.
2. **KEEP CORE PRIVATE** — continue public/dev ARC testing and do not claim an official competition-private score for the protected core.
3. **OWNER-APPROVED DISCLOSURE REVIEW** — only if the owner explicitly decides a specific method/code package may be released after a fresh MÀNG disclosure audit.

## Hard rule

GPT_TOOL_SUBSTRATE must not silently transform, summarize, leak, or reconstruct protected DEUS solver methods into an open-source submission.

No ARC-AGI-3 private hard run is admitted until this disclosure gate and Kaggle account/rule-acceptance gate are both resolved.
