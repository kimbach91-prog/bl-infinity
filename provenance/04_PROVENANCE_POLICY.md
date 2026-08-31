# Provenance Policy

**Public disclosure class:** `OPEN/P0 — POLICY`

## Evidence classes

Every historical or attribution claim should distinguish, when applicable:

- contemporaneous artifact;
- cryptographically hashed artifact;
- public publication timestamp;
- retrospective autobiographical/owner testimony;
- source-derived synthesis;
- AI formalization;
- inference from later behavior;
- external witness/source;
- unknown.

Do not silently upgrade autobiographical or retrospective testimony into contemporaneous proof. Do not convert AI synthesis/formalization into a verbatim historical quote by the human origin actor.

## Public/private boundary

Public provenance must contain enough information to assess authorship class, version, chronology boundaries, evidence status and supersession of a **public claim**.

Raw conversations, detailed private reasoning traces, operator handoffs, production prompts, private diagnostics and private corpora are `PROTECTED/P2` unless their disclosure is genuinely necessary to verify the public claim. They belong in a private provenance archive, not in the public repository.

If protected material becomes necessary for a truth-status decision, use one of four responses:

1. publish a safe evidentiary extract;
2. arrange controlled review;
3. narrow or downgrade the claim;
4. withhold the claim.

Secrecy is never a substitute for evidence.

## Integrity chain

For protected ordered records, an internal archive may use a chain such as:

\[
H_i=SHA256(H_{i-1}\Vert timestamp_i\Vert actor_i\Vert content_i)
\]

A public release may publish a non-sensitive integrity root only when doing so does not become a locator, reconstruction aid or disclosure channel for protected payloads.

## Release signature

A canonical public release may sign a manifest containing:

- namespace;
- title;
- public author/provenance identity;
- version;
- parent public version hash;
- public content root hash;
- date;
- canonical URL;
- public repository commit/tag.

Git signed tags/commits can provide one implementation layer; independent archival timestamps can provide additional corroboration.

## Non-implications

```text
Hash != Truth
Hash != Authorship proof by itself
Timestamp != Novelty
Provenance != Novelty
Private archive != Logical immunity
```

The public research object must remain criticizable without exposing production runtime.
