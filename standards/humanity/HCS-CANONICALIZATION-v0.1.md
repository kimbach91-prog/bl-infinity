# HCS Canonicalization & Version Negotiation v0.1

Status: DRAFT NORMATIVE PROFILE

## Purpose
Independent implementations must derive the same integrity input from the same logical HCS envelope.

## Canonical JSON profile
HCS JSON integrity input uses **RFC 8785 JSON Canonicalization Scheme (JCS)** as the canonicalization base profile.

Conforming HCS implementations MUST therefore:

1. accept only data representable in the I-JSON constraints required by JCS;
2. reject duplicate object property names before canonicalization;
3. preserve Unicode string data exactly as supplied to the HCS envelope — HCS canonicalization MUST NOT apply NFC/NFD or other Unicode normalization;
4. serialize JSON primitive values according to the RFC 8785 / ECMAScript-compatible rules;
5. preserve array element order;
6. sort object property names as required by RFC 8785;
7. emit no insignificant whitespace;
8. reject NaN, Infinity and other values not representable by the JCS input model;
9. represent values requiring precision outside the interoperable JSON number model using schema-defined strings rather than implementation-specific numeric extensions;
10. produce the RFC 8785 UTF-8 canonical byte sequence for hashing/signing.

HCS profile identifier for this draft is:

`urn:hcs:canonicalization:rfc8785-jcs`

### Language-layer normalization
A language or application profile MAY normalize text *before* constructing an HCS envelope when its own semantics require that behavior. Such preprocessing is part of that profile and MUST NOT be confused with HCS integrity canonicalization.

For example, a VTTN implementation may define normalization rules for concept resolution, while the HCS envelope still canonicalizes the resulting JSON according to RFC 8785 without altering its strings.

## Integrity binding
An integrity record MUST identify:
- canonicalization profile/version;
- digest algorithm;
- digest value;
- signature/proof method when present.

A receiver MUST NOT verify a signature against a different canonicalization profile than the sender declared.

HCS v0.1 RECOMMENDS `sha-256` as the baseline digest identifier for conformance vectors. This recommendation does not make SHA-256 the only future digest supported by HCS.

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
For any HCS envelope E whose input is valid under RFC 8785, and conformant implementations A and B:

`canonical(A,E) == canonical(B,E)`

and therefore, for the same digest algorithm:

`digest(A,E) == digest(B,E)`.

## Reference
Normative canonicalization reference for this profile: RFC 8785, JSON Canonicalization Scheme (JCS).
