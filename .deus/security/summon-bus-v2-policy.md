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
- Internal worker states such as `WAITING`, `LEASED`, `CLAIMED`, or `AWAITING_EXECUTOR` are implementation state only; they are not canonical ACK/READ evidence.

## Canonical packet routing invariants

A V2 packet is routable only when all of the following are true:

1. `BUS_VERSION=V2`.
2. `TASK_ID` uses an explicit V2 namespace.
3. `DEDUPE_KEY` uses an explicit V2 namespace and cannot collide with a legacy key.
4. `NODE_ID` and `TARGET` match the configured lane.
5. The packet is bound to its actual source artifact when `SOURCE_PACKET_FILE_ID` is present.
6. The configured return destination is the immutable canonical V2 return-folder identifier for that node.

Path-only routing such as `60_SUMMON_BUS/10_RETURN/<NODE>` is not trusted. A worker MUST ignore or reject any packet-supplied return destination that does not exactly match its configured canonical V2 lane. Any packet that routes to, names as authoritative, or attempts to reuse a legacy operational lane is `SECURITY_ROUTING_REJECTED` and must not execute canonically.

## Minimum ACK / RETURN provenance

A receipt is evidence only when it contains, or is otherwise directly bound to:

1. `task_id`
2. `node_id`
3. `source_packet_file_id` or equivalent immutable source artifact reference
4. `source_packet_hash` or equivalent immutable source revision
5. `status`
6. `observed_at`
7. `consumer_identity` or authorized service identity
8. an evidence pointer to the returned artifact/log
9. `bus_version`

If provenance is missing, contradictory, references a quarantined legacy artifact, or the source hash does not match the packet under review, classify the receipt as `UNVERIFIED` and route it to quarantine. An ACK string by itself is never sufficient evidence of READ/CONSUMED.

## Writer policy

- Anonymous/link-based writers are forbidden on the canonical bus.
- Writers must be explicit authorized users or service identities.
- A consumer may be revoked without invalidating historical evidence already copied into the audit lane.
- Watchers are observers, not proof of execution; they may report state transitions but cannot fabricate ACKs.
- Canonical workers MUST fail closed if a canonical root or operational lane becomes broadly writable.

## Worker cutover requirements

Before installing or re-installing a worker:

1. remove all legacy inbox/return identifiers from operational configuration;
2. verify the V2 root, target inbox, target return lane, and quarantine lane resolve under the authorized execution identity;
3. verify no canonical operational lane has broad write sharing;
4. ensure waiting-for-executor behavior does not emit ACK/READ artifacts;
5. ensure returned evidence records the source packet hash and evidence pointer before task state is promoted;
6. quarantine superseded or routing-ambiguous packets instead of editing their history in place.

A source snapshot is not proof that a deployed Apps Script trigger has been updated. Runtime trigger/deployment state must be verified separately before claiming the old worker is disabled.

## Public repository hygiene

- Do not commit live operational Drive folder IDs, credentials, API keys, bearer tokens, or private service-account identifiers to this public repository.
- Public code should use configuration placeholders or runtime properties for deployment-specific identifiers.
- Security policy, schemas, validators, and synthetic test fixtures may be public when they do not reveal restricted operational topology.

## Auxiliary compute

- Auxiliary cloud workers may process only bounded payloads allowed by their disclosure class.
- Default auxiliary-compute smoke tests use synthetic/LOW-disclosure payloads and read-only repository permissions.
- Successful cloud compute does not imply an external LLM node consumed a SUMMON_BUS task. These are separate capabilities and must be evidenced separately.

## Cutover rule

Operational automation and human review should treat V2 as canonical and the legacy bus as historical/quarantine. A legacy artifact may be imported only after provenance review and explicit reclassification. A legacy ACK/RETURN never becomes canonical merely because its task ID or dedupe key matches a V2 packet.
