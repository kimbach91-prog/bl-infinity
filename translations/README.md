# Translation layer

BL∞ uses a provenance-bound translation layer. A translation is a derivative representation of the public research object, not a new independent theory version.

## Current language roles

- Vietnamese (`vi`) is the full canonical public reading source.
- English (`en`) is currently a core research edition. It is bilingual infrastructure with explicit coverage metadata, not yet a line-by-line translation of every Vietnamese section.

## Required metadata

Every maintained translation must record:

- source version and source file set;
- source hash(es);
- target locale;
- translator/model identity class;
- review status;
- translation hash(es);
- terminology decisions;
- known omissions, compression or unresolved wording.

`translations/translation-index.json` is the source registry. The build emits `machine/translation-status.json` with calculated hashes so crawlers and reviewers can see what was translated from what.

## Integrity rules

1. Translation never changes authorship, origin or chronology.
2. A compressed translation must say that it is compressed.
3. An English passage must not be quoted as a verbatim translation of a Vietnamese passage that has not been translated line by line.
4. If wording, scope, priority or provenance differs materially, the full Vietnamese public source controls until the English passage is reviewed.
5. A translation cannot silently upgrade a conjecture, proposal or inference into a stronger truth state.
6. Translation files pass the same BL-CPR disclosure and security gates as every other public artifact.
