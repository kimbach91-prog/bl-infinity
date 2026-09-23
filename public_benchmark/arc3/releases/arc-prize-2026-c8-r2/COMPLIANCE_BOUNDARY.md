# Competition compliance boundary

## Included in the public ARC solution surface

- exact competition notebook source
- builder/packaging code needed for the candidate
- serving and teardown patches used by the candidate
- output audit code
- pinned model/runtime/source identities
- runtime settings
- reproducibility procedure
- upstream attribution and license
- provider-output hashes and audit receipts
- Kaggle submission reference

## Not part of the ARC solver release

Unless independently required by competition rules, the following are not necessary to reproduce this submission and are outside this competition package:

- DEUS canonical memory
- authority roots
- MÀNG/security-root state
- credentials, tokens, keys, service-account secrets
- private topology
- unrelated daemons/control-plane internals
- unrelated research branches and business data

## Security rule

Secrets must never be committed to the public repository or embedded in the notebook.

## Evidence rule

Public-development, source-assisted and provider-hidden evidence remain separate. This package does not convert a public-development result into a Kaggle hidden-test claim.
