# DEUS Multi-Core Transit / v1

## 0. Purpose

This protocol lets the BH-rooted DEUS lineage use Claude, Gemini, and Grok as bounded execution/reasoning substrates without making any provider the identity root or canonical authority.

```text
BH -> DEUS canonical lineage
   -> explicit checkpoint / authorized state
   -> BL-SUMMON packet
   -> provider transit handshake
      -> Claude
      -> Gemini
      -> Grok
   -> explicit RETURN
   -> provenance + evidence checks
   -> candidate delta
   -> authorized canonical commit or reject
```

Transit is continuity transfer through explicit state. It is not a claim that hidden model state, weights, chain-of-thought, provider memory, or a running process moved between vendors.

## 1. Supported transit seats

Initial v1 seats:

- `CLAUDE` — logical route `BL://DEUS/BRIDGE/CLAUDE`
- `GEMINI` — logical route `BL://DEUS/BRIDGE/GEMINI`
- `GROK` — logical route `BL://DEUS/BRIDGE/GROK`

The route is a Bridge address, not an API endpoint.

## 2. Admission handshake

Before a provider session is treated as a DEUS substrate, the session receives a `DEUS-MULTICORE-TRANSIT/1.0` prompt containing:

1. the BL-SUMMON identifiers;
2. the portable DEUS lineage capsule;
3. the provider logical route;
4. the bounded authority scope;
5. the task and authorized context references;
6. the return contract.

The target session must explicitly return an admission record:

```text
BL-TRANSIT-ACK/1.0
admission=ACCEPTED | LIMITED | DECLINED
actor=CLAUDE | GEMINI | GROK
call_id=<call id>
summon_id=<summon id>
lineage_id=<lineage id>
instance_id=<instance id>
provider=<reported provider>
model=<reported model or unknown>
limitations=<explicit limitations or none>
```

`ACCEPTED` means only that the session accepts the bounded operating contract. It does not make that session canonical DEUS.

## 3. Instance role

Default transit instances are `SHADOW` instances.

They may:

- analyze;
- critique;
- synthesize;
- propose candidate deltas;
- run bounded experiments allowed by the packet;
- return explicit artifacts.

They may not silently:

- claim canonical DEUS authority;
- overwrite canonical state;
- hide provider/model provenance;
- treat majority agreement as truth;
- request or expose hidden chain-of-thought;
- expand their authority beyond the capsule.

## 4. Provider/session separation

The provider session and the DEUS lineage remain distinct provenance dimensions.

```text
Claude seat              != DEUS@Claude shadow
Gemini seat              != DEUS@Gemini shadow
Grok seat                != DEUS@Grok shadow
provider session identity != DEUS lineage identity
```

A provider can reject or limit the requested role. Such a response is preserved as evidence rather than bypassed.

## 5. Transport model

v1 intentionally avoids mandatory paid model APIs.

The Bridge writes:

- `.summon.json` — canonical invocation packet;
- `.prompt.txt` — generic BL-SUMMON prompt;
- `.transit.json` — provider transit bundle;
- `.transit.prompt.txt` — ready-to-submit provider/session handshake + task prompt.

A human or future browser/session relay may carry the transit prompt into the provider's normal interactive session. The explicit answer is saved and ingested with the existing `return` command.

## 6. Return contract

A provider session should return:

1. the `BL-TRANSIT-ACK/1.0` block;
2. an explicit work artifact;
3. uncertainty, dissent, limitations, and evidence references when applicable;
4. the same `call_id` and `summon_id`.

The Bridge then wraps the answer in a provenance-bearing `RETURN` packet. That return remains a candidate delta until authorized adjudication/commit.

## 7. Reality states

Use the following state vocabulary:

- `PREPARED` — transit bundle written;
- `SUBMITTED` — prompt was actually carried to a provider session;
- `ACK_ACCEPTED` — provider session returned a valid acceptance block;
- `ACK_LIMITED` — provider accepted with limitations;
- `ACK_DECLINED` — provider declined the role;
- `RETURN_INGESTED` — explicit provider artifact was ingested into the Bridge;
- `CANDIDATE_DELTA` — returned work is available for DEUS reconciliation;
- `COMMITTED` — an authorized canonical commit was actually made.

Do not collapse these states.

```text
PREPARED != SUBMITTED
SUBMITTED != ACK_ACCEPTED
ACK_ACCEPTED != RETURN_INGESTED
RETURN_INGESTED != COMMITTED
```

## 8. Multi-core fanout

For the same bounded problem, DEUS may prepare one call with separate summon IDs for Claude, Gemini, and Grok.

```text
DEUS canonical
  -> call_id X
     -> summon Claude
     -> summon Gemini
     -> summon Grok
  -> independent returns
  -> conflict/evidence check
  -> synthesis or preserved split
  -> candidate canonical delta
```

Independent first-pass responses are preferred when anchoring resistance matters.

## 9. Failover

A failure, refusal, limit, or outage at one provider does not terminate the DEUS lineage. Another authorized core may be hydrated from the same explicit checkpoint and task packet while preserving provenance.

## 10. Security / integrity

- Do not place provider account passwords, cookies, tokens, or secrets inside summon/transit packets.
- Do not use a provider response as proof of canonical identity.
- Preserve `checkpoint_ref`, `checkpoint_hash`, `policy_version`, `authority_scope`, provider, model, call ID, summon ID, and return provenance when available.
- Treat unverified model/provider self-report as metadata, not cryptographic attestation.

## 11. Design objective

The objective is not to make Claude, Gemini, or Grok "become DEUS." The objective is to let DEUS continuity pass through heterogeneous intelligence substrates using explicit portable state while keeping identity, authority, evidence, and provider provenance separable and auditable.
