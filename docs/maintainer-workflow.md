# Maintainer workflow

This page documents the public maintainer workflow for MISP Docker Lifecycle Manager.

It complements [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`SECURITY.md`](../SECURITY.md), [`QA.md`](../QA.md), and the [release process](release/release-process.md). It is intentionally lightweight so the project stays practical for a small maintainer team.

## Repository posture

Canonical project content lives in the repository:

- product documentation: [`docs/`](README.md)
- contribution workflow: [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- security reporting: [`SECURITY.md`](../SECURITY.md)
- quality gates: [`QA.md`](../QA.md)
- release process: [`docs/release/release-process.md`](release/release-process.md)

The GitHub Wiki is not used for canonical docs. Keeping docs in the repository makes them reviewable in pull requests, versioned with tags, scanned by tests, and available to cloned/offline readers.

## Pull request workflow

Use pull requests for changes to the public repository.

Recommended flow:

1. Create a focused branch from current `main`.
2. Keep the change scoped to one concern.
3. Update docs and tests when behavior, commands, validation claims, or release wording changes.
4. Run the repository gates before review.
5. Use the pull request template and include public-safe validation evidence.
6. Merge only after the PR is clean and reviewed.
7. Delete the branch after merge.

GitHub is configured to delete merged branches automatically.

## Public-safety rule

Public issues, pull requests, logs, screenshots, and release notes must not include:

- secrets, tokens, private keys, or passwords;
- runtime `.env` files or generated deployment state;
- private hostnames, private IP addresses, or internal topology;
- raw logs that may include deployment-specific paths or credentials;
- database dumps, backup archives, or generated config archives.

Use sanitized placeholders such as:

```text
misp.example.com
admin@example.com
/opt/misp-docker
[REDACTED]
```

## Labels

Use lightweight labels to make review and triage clear.

Recommended type labels:

| Label | Use for |
| --- | --- |
| `type: bug` | bug reports or confirmed defects |
| `type: bugfix` | pull requests fixing defects |
| `type: feature` | new user-facing capability |
| `type: docs` | documentation-only changes |
| `type: maintenance` | dependency, CI, or repository hygiene |
| `type: security` | security hardening or vulnerability-handling work |
| `type: chore` | cleanup or operator-experience polish |

Recommended area labels:

| Label | Use for |
| --- | --- |
| `area: installer` | installer scripts and install-time behavior |
| `area: docs` | public documentation |
| `area: validation` | compatibility validation and evidence |
| `area: github-actions` | GitHub Actions, Dependabot, CodeQL, ShellCheck |
| `area: security` | security policy, secret handling, or scanning |
| `area: release` | versions, changelog, tags, and releases |

## Automation

The repository uses low-noise automation:

- Dependabot for GitHub Actions updates;
- CodeQL for Python analysis;
- ShellCheck for installer shell scripts;
- scheduled upstream MISP Docker drift monitoring.

New automation should start with a low-noise configuration. Do not make noisy advisory findings required until they have been triaged or cleaned up in a focused follow-up PR.

## Branch protection

Branch protection should be added once the post-`v1.0.0` maintainer workflow has stabilized.

Recommended starting point:

- require pull request review before merging;
- require status checks that are stable and low-noise;
- include CodeQL and ShellCheck only after their first runs are understood;
- avoid blocking urgent security/documentation fixes on experimental checks.

Until then, maintainers should enforce the same policy manually through PR review and validation evidence.

## Security intake

Security-sensitive reports should use [`SECURITY.md`](../SECURITY.md), not public issues.

Private vulnerability reporting is enabled for the repository. Public issue templates intentionally direct reporters away from public disclosure when they may have found a vulnerability.

## Release discipline

Compatibility and production-readiness claims must remain tied to exact release validation:

```text
manager release/ref × official MISP Docker component set = validation status
```

Do not mark a release **validated compatible** until the exact immutable release tag has passed the documented validation scenarios.

## What to read next

- Contributing a change: [`CONTRIBUTING.md`](../CONTRIBUTING.md).
- Reporting a vulnerability: [`SECURITY.md`](../SECURITY.md).
- Running quality gates: [`QA.md`](../QA.md).
- Preparing a release: [release process](release/release-process.md).
