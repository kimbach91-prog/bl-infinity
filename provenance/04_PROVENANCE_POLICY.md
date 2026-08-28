# Provenance Policy

## Evidence classes

Every historical claim should be tagged:

- contemporaneous artifact;
- cryptographically hashed artifact;
- public publication timestamp;
- chat timestamp;
- retrospective autobiographical testimony;
- inference from later behavior;
- external witness/source.

Do not silently upgrade autobiographical testimony into contemporaneous proof.

## Hash chain proposal

For ordered messages/events:

\[
H_i=SHA256(H_{i-1}\Vert timestamp_i\Vert actor_i\Vert content_i)
\]

The final root preserves order/integrity if raw inputs are later disclosed.

## Signature proposal

Each canonical release should sign a manifest containing:

- namespace;
- title;
- author identity;
- version;
- parent version hash;
- content root hash;
- date;
- canonical URL;
- repository commit/tag.

Git signed tags/commits provide one implementation layer; external archival timestamps can provide independent corroboration.
