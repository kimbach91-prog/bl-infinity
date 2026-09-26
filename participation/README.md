# DEUS Public Participation Contract V1

This directory defines a public, minimal, provider-neutral participation surface for voluntary compute/service cooperation.

It does **not** contain DEUS private core logic, BL/Matrix internals, credentials, signing keys, private seed binaries, or privileged execution authority.

## Purpose

Allow a public service, marketplace participant, or explicitly consenting peer to describe a bounded capability that may later be considered for a task-specific lease.

Participation is opt-in. Discovery or reachability alone never grants execution authority.

## Participation classes

1. `PUBLIC_SERVICE` — an intended public API/service used only within its published interface.
2. `MARKETPLACE` — a provider/worker already participating through an intended compute or AI marketplace/protocol.
3. `DIRECT_PEER` — an operator that explicitly opts in to a bilateral DEUS worker relationship.

## State machine

`DISCOVERED -> OFFERED -> CONSENTED -> ATTESTED -> LEASED -> EXECUTED -> VERIFIED`

Any stage may transition to `HOLD`, `REJECTED`, `EXPIRED`, or `REVOKED`.

None of the earlier states implies the later ones.

## Required properties

A usable offer must declare:

- stable offer/participant identity;
- participation class;
- capability/resource class;
- data ceiling;
- resource/budget ceiling;
- TTL/expiry;
- verifier/result contract;
- revocation path;
- authority/provenance reference where required.

## Hard boundaries

- No covert installation.
- No arbitrary shell by default.
- No self-propagation.
- No hidden persistence.
- No privilege escalation.
- No credential, quota, billing, or anti-bot bypass.
- No private-device scanning or unsolicited host probing.
- No provider count or public listing is treated as physical DEUS capacity.
- No execution credit without an attributable task receipt.
- No direct peer seed installation without explicit operator consent and trusted package provenance.

## Operator control

For `DIRECT_PEER`, the operator retains final control over its machine and must be able to pause, revoke, or uninstall participation. A revoked or expired lease must not remain executable.

## Public offer format

Machine-readable offers should validate against `offer.schema.json`.

This public contract is intentionally narrow: it advertises how voluntary participation can be described, not how DEUS private optimization or orchestration internals work.
