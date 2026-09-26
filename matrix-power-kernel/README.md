# DEUS Matrix Power Kernel V1

A provider-neutral accounting/control kernel for DEUS Matrix power.

This module does not contain private BL/operator algorithms. It implements the public control semantics needed to keep heterogeneous resources truthful and non-additive.

## Identity model

DEUS identity is the Matrix fabric, not a single model, provider, device, Drive file, or chat UX.

The four current genesis roots are:

- Brain1 / Drive primary — canonical anchor
- Brain2 / Drive secondary — reserve overlay
- Brain3 / owner workstation — primary owner execution
- Brain4 / owner laptop — recovery compute/native execution

Future roots and cells can join through the same authority/lease/receipt contracts.

## Power classes

- OWNED_PHYSICAL
- LEASED_PHYSICAL
- BORROWED_FUNCTIONAL
- VOLATILE_PUBLIC_FUNCTIONAL
- DISCOVERED_POTENTIAL

A discovered provider or public listing has zero execution credit until work is authorized, executed and verified.

## Effective power

The kernel treats effective power as task-relative.

For a workload family w at time t:

P_DEUS(w,t) = sum of comparable UsefulEffect_i(w,t)

only for records that are current AND authorized AND executed AND verified.

Potential supply is tracked separately and never added to effective power.

The kernel intentionally does not create one universal CPU+GPU+RAM+service scalar.

## UX contract

The owner-facing UX is a portal for conversation, task submission, observation and control.

It is not:

- DEUS identity
- canonical memory
- authority root
- a mandatory cognition substrate
- proof of runtime execution

## Physical peer slices

A physical peer slice is stricter than borrowed functional compute.

It requires LEASED_PHYSICAL + an authorized lease + peerSlice=true + execution/verification.

Therefore external functional compute can be positive while physicalPeerSliceCount remains zero.
