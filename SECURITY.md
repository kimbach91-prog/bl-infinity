# BL∞ Security Policy

BL∞ uses defense in depth. No single control is treated as sufficient, and security controls are never represented as proof that a theoretical claim is true.

## Scope

This policy covers the public repository, GitHub Actions build/deploy path, GitHub Pages output, public machine interfaces, translation layer and BL-CPR disclosure boundary.

The private production runtime is outside this repository. Do not send credentials, private keys, raw private conversations, private corpora, exploit payloads or protected runtime material through public issues or pull requests.

## Core public-write invariant

A write to this public repository is itself an exposure event. CI that runs after a push cannot make already-pushed bytes secret again.

Therefore every public Git mutation is governed by **BL-GWG — Bach Lam Git Write Guard**:

```text
candidate change
-> authority/intent check
-> disclosure class
-> data minimization
-> secret/privacy scan
-> provenance/IP boundary review
-> active-content/supply-chain check
-> semantic/integrity diff
-> release-separation check
-> write only if all required gates pass
-> post-write fail-closed audit
```

Default decision:

```text
DENY_UNTIL_ALL_GATES_PASS
```

Only `OPEN/P0` and `CONTROLLED/P1` material may enter the public repository. `PROTECTED/P2` and `FORBIDDEN/P3` remain outside it. An owner command may authorize a public mutation, but it does not override secret, credential, unlawful-data, or P3 rejection gates.

**Platform limitation:** hard server-side blocking of a direct push requires a GitHub ruleset or branch protection. Repository code and CI are not misrepresented as pre-receive enforcement.

## Reporting a vulnerability

For a security-sensitive report, use GitHub's private security-advisory / private vulnerability-reporting path for this repository when available. Do not open a public issue containing secrets, personal data, unpatched exploit details or a path to protected runtime material.

For non-sensitive hardening suggestions, a normal issue or pull request is appropriate.

## Security architecture

### L-1 — Pre-write public exposure gate

BL-GWG applies before every intended public Git mutation at the process/governance layer and is rechecked by CI after mutation.

Required controls:

- explicit intent/authority for the public mutation;
- P0/P1 classification before write;
- fail-closed handling for unknown classification;
- smallest sufficient public projection;
- secret, credential and privacy scanning;
- protected-runtime exclusion;
- provenance and authorship preservation;
- patent/trade-secret disclosure-risk review when material;
- semantic diff and no silent security-boundary downgrade;
- separation of Git write from Pages publication;
- post-write BL-CPR/security/system audits.

### L0 — Account and authority

Target controls: phishing-resistant MFA/passkeys, hardened recovery, minimal administrator authority, no shared credentials and periodic recovery review.

These are account/platform controls and cannot be guaranteed by repository code alone.

### L1 — Repository governance

Target controls: protect the default branch, require review and passing CI before merge, preserve release history, keep generated `site/` output out of source, and sign important releases/tags when signing infrastructure is available.

Repository content checks cannot replace a GitHub ruleset. If the platform ruleset is absent, that remains an explicit open security gap rather than being hidden by prose.

### L2 — Supply chain and CI

Controls implemented in-repo:

- GitHub Actions are pinned to full commit SHAs rather than floating tags;
- `GITHUB_TOKEN` permissions are set per job to the minimum required;
- checkout does not persist write credentials;
- direct Python build dependencies are exact-version pinned;
- `pip-audit` runs in CI;
- Dependabot is configured for Python packages and GitHub Actions;
- pull-request builds do not receive Pages deployment permissions.

### L3 — Publication and disclosure

BL-CPR is fail-closed. Public verification is separated from private execution.

Controls include P0–P3 disclosure states, forbidden public paths, secret/key scans, explicit allowlists, protected-runtime filename gates, machine-interface minimization and rebuild-from-clean-source behavior.

Anything committed to this public repository must be treated as public even if it is absent from navigation or search indexing.

### L4 — Build and rendering

The site is static. Markdown raw HTML is escaped by the renderer so a Markdown file cannot silently inject active script. Security audit rejects unsafe script/event-handler patterns and dangerous URL schemes in public source.

The generated tree is recreated from scratch on every build to avoid stale public artifacts.

### L5 — Browser policy

Pages include a restrictive Content Security Policy delivered through `<meta http-equiv="Content-Security-Policy">`, strict referrer policy, HTTPS upgrade behavior, self-hosted local assets and a narrowly allowed giscus script/frame origin.

**Host limitation:** GitHub Pages does not give this repository arbitrary control over HTTP response headers. Header-only protections such as a server-delivered `frame-ancestors` policy, HSTS tuning or Permissions-Policy require a security proxy/CDN or a different host. The repository must not claim those controls are active merely because they are desirable.

### L6 — Integrity and provenance

Build output includes content hashes, versioned claim IDs, translation source/target hashes and machine-readable status. Hashes establish byte/integrity relationships; they do not prove theory truth.

Public mutation may not silently rewrite authorship, origin, lineage, causal history or security classification.

### L7 — Recovery and incident response

If protected data is exposed:

1. stop further publication;
2. rotate/revoke affected credentials first;
3. preserve the necessary private evidence safely;
4. remove or rewrite exposed public history when appropriate;
5. request provider-side sensitive-data purge if byte-level erasure is required;
6. rebuild Pages, sitemap, discovery artifacts and mirrors;
7. record a causal incident summary without republishing the protected payload;
8. add a regression test that would have prevented the exposure.

### L8 — Maintenance and evolution

Security, Git-write and disclosure checks run on every pull request/push and on the scheduled maintenance cycle. Dependabot checks package and Action updates. The threat model should be reviewed after a material architecture, hosting, dependency, identity or publication-boundary change.

Automated events may audit, but public Pages publication remains manual-only under the current owner publication freeze.

A failing audit blocks release. Repeated false positives should be calibrated by changing the check, not by silently disabling the layer.

### L9 — Translation integrity

The English edition is a derivative representation. Translation state, coverage, source files and hashes are public. Translation may not silently change authorship, chronology, claim status or evidential strength. Until a passage is reviewed, material wording conflicts defer to the full Vietnamese public source.

## Security non-claims

BL∞ does not claim perfect security, zero vulnerabilities, permanent confidentiality after public exposure, or that cryptographic integrity establishes scientific truth.

The correct model is continuous reduction of attack surface, bounded exposure, pre-write minimization, rapid detection, reversible release where possible, causal recovery and repeated hardening.
