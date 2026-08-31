# Public disclosure policy

## Principle

Public verifiability does not require publication of the operational system. BL∞ therefore separates public claims and identity evidence from protected implementation material.

## Public layer

The public layer may contain:

- canonical identity and authorship;
- high-level research scope;
- capability-level input/output commitments;
- falsification or evaluation criteria that do not reveal implementation;
- contact and responsible-disclosure procedures.

## Protected layer

The following are excluded from public Git refs and release artifacts:

- source code for experimental or production runtimes;
- internal routing, ranking, stopping, recombination, and orchestration logic;
- private schemas, graphs, dependency maps, prompts, weights, thresholds, or operator order;
- evaluation corpora, unpublished results, access credentials, and deployment configuration;
- documentation detailed enough to reproduce protected implementation behavior.

## Verification options

Depending on the request, verification may use a black-box demonstration, signed or hashed evidence, a time-bounded review, an NDA-governed technical session, or an independently agreed test protocol.

No decoy algorithms, fabricated results, or false implementation claims are used. Strategic opacity is achieved by omission, aggregation, and scoped access.
