# HCS Canonicalization & Version Negotiation v0.1

Status: DRAFT NORMATIVE PROFILE

## Purpose
Independent implementations must derive the same integrity input from the same logical HCS envelope.

## Canonical JSON profile
Before hashing or signing an HCS envelope:

1. Input MUST be valid UTF-8 JSON data.
2. Object keys MUST be sorted by Unicode code point order after NFC normalization.
3. Strings MUST be normalized to Unicode NFC.
4. Arrays MUST preserve declared order.
5. Numbers MUST be finite JSON numbers; NaN and Infinity are forbidden.
6. Negative zero MUST canonicalize to `0`.
7. No insignificant whitespace is emitted.
8. Undefined values are forbidden; absent fields remain absent.
9. Duplicate object keys are invalid before canonicalization.
10. The canonical output MUST be UTF-8 bytes of the deterministic compact JSON representation.

This v0.1 profile is intentionally narrow. Before HCS v1.0 release it SHOULD be aligned with an independently reviewed canonical JSON standard/profile if no semantic incompatibility exists.

## Integrity binding
An integrity record MUST identify:
- canonicalization profile/version;
- digest algorithm;
- digest value;
- signature/proof method when present.

A receiver MUST NOT verify a signature against a different canonicalization profile than the sender declared.

## Version negotiation
Every HCS envelope MUST declare `hcsVersion`.

A receiver MUST:
- accept an explicitly supported compatible version;
- reject an unsupported major version;
- ignore unknown extension fields only when the negotiated profile explicitly permits forward-compatible extensions;
- never silently reinterpret a known field with changed semantics.

## Extension namespaces
Extensions MUST use an owner-controlled namespace identifier. Extensions MUST NOT redefine the semantics of normative HCS fields.

## Downgrade resistance
If a sender requires a capability or security property unavailable in the receiver's profile, the exchange MUST fail rather than silently downgrade.

## Test invariant
For any logical envelope E and conformant implementations A and B:

`canonical(A,E) == canonical(B,E)`

and therefore, for the same digest algorithm:

`digest(A,E) == digest(B,E)`.
