# GitHub Main-Branch Protection Requirement

BL Compute Federation relies on CI as a Reality Veto before merge, but repository-side enforcement must exist independently of operator discipline.

## Verified current state

At the v0.8 hardening checkpoint, GitHub reported for `main`:

```text
protected: false
required status checks: off
repository rulesets: none
```

The connected GitHub integration can read this state but does not expose an administrative write action for branch protection/rulesets in this session. Therefore this repository-side control is **not implemented by the runtime code** and must not be described as enabled.

## Required target state

Configure GitHub so `main` requires, at minimum:

- changes through pull requests;
- `Federation Runtime Tests` to pass before merge when federation paths are touched;
- branch to be up to date or merge queue equivalent before merge;
- force pushes disabled;
- branch deletion disabled;
- stale approvals dismissed when security-sensitive code changes, if reviews are used;
- administrators included unless there is a documented break-glass process.

For broader repository protection, consider a ruleset that covers all critical runtime/configuration paths rather than only one workflow.

## Why code cannot substitute for this

A workflow triggered **after** a direct push can report failure, but it cannot retroactively prevent the unreviewed commit from becoming `main`. CODEOWNERS without branch protection similarly does not enforce a merge gate.

Therefore:

```text
CI discipline != server-side branch protection
```

Both are required for a production-shaped repository governance model.

## Verification after enabling

After an owner/admin enables protection, re-read the GitHub branch/ruleset state and record evidence that:

```text
main protected = true
required Federation Runtime Tests = enabled
force push = blocked
PR requirement = enabled
```

Do not close this control gap based only on a screenshot or intended configuration; verify the API-visible state.
