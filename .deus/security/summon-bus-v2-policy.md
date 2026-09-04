# DEUS SUMMON BUS V2 — Trust & Evidence Policy

Status: ACTIVE

## Security boundary

- The legacy SUMMON_BUS is **QUARANTINED / NON-CANONICAL** whenever anonymous or link-based write access exists.
- `60_SUMMON_BUS_V2_SECURE` is the canonical Drive transport only while its root and operational lanes have **no anonymous writer** permission.
- Do not place secrets, API keys, BLACK CORE material, private user data, or unrestricted credentials in task packets.

## State semantics

- `DISPATCHED`: a task packet exists in a target inbox.
- `READ`: an authenticated/authorized consumer produced a direct receipt tied to the task.
- `EXECUTED`: execution evidence exists and is bound to the task.
- `RETURNED`: a return artifact exists in the target return lane and passes provenance checks.
- Inbox presence alone MUST NOT be upgraded to READ, EXECUTED, or RETURNED.

## Minimum ACK / RETURN provenance

A receipt is evidence only when it contains, or is otherwise directly bound to:

1. `task_id`
2. `node_id`
3. `source_packet_hash` or equivalent immutable source reference
4. `status`
5. `observed_at`
6. `consumer_identity` or authorized service identity
7. an evidence pointer to the returned artifact/log

If provenance is missing or contradictory, classify the receipt as `UNVERIFIED` and route it to quarantine.

## Writer policy

- Anonymous/link-based writers are forbidden on the canonical bus.
- Writers must be explicit authorized users or service identities.
- A consumer may be revoked without invalidating historical evidence already copied into the audit lane.
- Watchers are observers, not proof of execution; they may report state transitions but cannot fabricate ACKs.

## Auxiliary compute

- Auxiliary cloud workers may process only bounded payloads allowed by their disclosure class.
- Default auxiliary-compute smoke tests use synthetic/LOW-disclosure payloads and read-only repository permissions.
- Successful cloud compute does not imply an external LLM node consumed a SUMMON_BUS task. These are separate capabilities and must be evidenced separately.

## Cutover rule

Operational automation and human review should treat V2 as canonical and the legacy bus as historical/quarantine. A legacy artifact may be imported only after provenance review and explicit reclassification.
