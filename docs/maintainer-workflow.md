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

Recommended support labels:

| Label | Use for |
| --- | --- |
| `needs-sos-report` | bug reports that need a reviewed anonymous SOS report before maintainers can reproduce or classify the issue |

## SOS report triage

Use [anonymous SOS reports](sos-report.md) to reproduce normal public bugs without asking users to paste raw logs or private deployment details.

### First safety pass

Before debugging, inspect the issue for public-safety problems:

- secrets, tokens, passwords, private keys, or API keys;
- `.env` contents or full `.installer-state.json` contents;
- real hostnames, IP addresses, internal domains, or topology;
- raw logs, raw Docker Compose config, screenshots, database dumps, backup contents, generated config archives, or MISP data.

If any of those appear, do not quote them back in public. Ask the reporter to edit/redact the issue. If the content suggests a vulnerability or cannot be discussed safely in public, move the conversation to [`SECURITY.md`](../SECURITY.md) and private vulnerability reporting.

### When to request an SOS report

Apply `needs-sos-report` and ask for an anonymous SOS report when a public bug lacks enough safe detail to reproduce, especially for install, update, backup, restore, rollback, reset, doctor, status, or login-check failures.

Use a short request such as:

```text
Could you generate and review an anonymous SOS report, then paste only the public-safe content here?

sudo ./installer/sos-report.sh --install-dir /opt/misp-docker --output ./misp-sos-report.md
less ./misp-sos-report.md

If the report cannot be made public-safe, please use SECURITY.md instead.
```

### Triage the report

Read the report in this order:

1. **Safety notice and redaction summary** — confirm it is public-safe.
2. **Manager version/ref and report format** — identify whether the affected manager release/ref is known and whether the report schema is current.
3. **Affected workflow** — classify as install, update, backup, restore, rollback, reset, doctor/status, login-check, documentation, or other.
4. **Environment and installation shape** — check support matrix fit and whether expected files exist.
5. **Component versions** — compare with compatibility and validation evidence.
6. **Health and command summaries** — use pass/fail/unavailable status, not raw logs, to choose the next reproduction step.
7. **Reproduction prompt** — ask for missing expected/actual behavior or sanitized command shape when needed.

### Decide the next action

- **Incomplete but public-safe:** keep `needs-sos-report` or ask one focused follow-up question.
- **Unsupported deployment model:** point to the support matrix and decide whether docs need clarification.
- **Known compatibility gap:** link compatibility evidence and decide whether validation needs a follow-up run.
- **Likely docs issue:** label `type: docs` / `area: docs` and fix docs through PR.
- **Likely code issue:** label the affected `area:*`, reproduce with sanitized values, add regression coverage, and open a focused PR.
- **Potential security issue:** stop public debugging and direct the reporter to private vulnerability reporting.

Remove `needs-sos-report` once the issue has a reviewed report or enough equivalent public-safe reproduction detail.

## Automation

The repository uses low-noise automation:

- Dependabot for GitHub Actions updates;
- CodeQL for Python analysis;
- ShellCheck for installer shell scripts;
- scheduled upstream MISP Docker drift monitoring.

### GitHub Actions maintenance

When GitHub Actions annotations report deprecations, treat them as maintenance work even if checks still pass. For pinned actions:

1. Identify the replacement major version from the upstream action release notes.
2. Resolve the replacement tag to an immutable commit SHA.
3. Update the workflow `uses:` pin and keep a nearby comment with the human-readable major version.
4. Keep static tests SHA-enforcing so Dependabot can still update pins safely.
5. Re-run the workflow and confirm annotations no longer include the targeted deprecation warning.

### Official MISP Docker upstream drift PRs

The scheduled upstream monitor opens `Review upstream MISP Docker changes` PRs when lifecycle-sensitive official `MISP/misp-docker` inputs change. Treat those PRs as review prompts, not as compatibility proof. A new upstream commit by itself is comparison context and does not open a PR; this keeps unrelated upstream work from creating noise.

Use this classification:

| Class | Upstream change | Default response |
| --- | --- | --- |
| A | Component tag defaults changed, such as `CORE_TAG`, `MODULES_TAG`, or `GUARD_TAG` | Review changelogs/release notes, update compatibility/readiness docs to pending for the new component set if needed, then run compatibility validation before marking validated. |
| B | `docker-compose.yml` service blocks, image expressions, interpolation keys, ports, volumes, health/readiness behavior, dependency/profile structure, upstream entrypoint/configuration scripts, or critical/minimum environment definitions changed | Inspect installer assumptions and run targeted code/docs tests. Patch manager code if assumptions changed. Full validation is likely needed before compatibility claims. |
| C | `template.env` key inventory/defaults or selected README operator guidance changed without obvious compose/service changes | Review config generation and documentation. Patch generated `.env` handling or docs if defaults/required variables changed. Validation scope depends on whether runtime behavior changed. |

Combination handling:

- **A only:** validation/docs response first; code changes only if tags expose a manager assumption.
- **B only:** code-assumption review first; validate after any patch.
- **C only:** config/docs review first; validate if install/update/runtime behavior changes.
- **A+B:** treat as high impact. Patch assumptions first, then run full compatibility validation for the new component set.
- **A+C:** update config/docs and run compatibility validation for the new component set.
- **B+C:** patch code/config/docs, then run targeted validation at minimum; full validation if install/update/readiness is affected.
- **A+B+C:** treat as release-impacting upstream drift. Patch, document, and run full compatibility validation before any validated-compatible claim.

For every upstream review PR:

1. Read `.upstream/reports/misp-docker-upstream-review.md`.
2. Open the upstream compare link and inspect the actual upstream diff.
3. Read the detected A/B/C classes and structured service/environment deltas, then inspect the upstream diff rather than treating hashes as a complete explanation.
4. Check entrypoint/configuration, critical/minimum environment definitions, and selected operator-guidance sections when listed.
5. Decide whether this repo needs a manager code PR, docs-only PR, validation-only follow-up, or no change.
6. Never merge the upstream lockfile PR as "validated compatible" evidence by itself.
7. If compatibility status changes, update public compatibility docs only after validation passes.
8. Keep all public comments sanitized; no private validation infrastructure details.

If the scheduled workflow reports success but no upstream review PR is visible, check for the review branch manually:

```text
automation/upstream-misp-docker-review
```

A pushed review branch without an open PR still means upstream drift exists. Open the branch as a PR manually, then investigate why `peter-evans/create-pull-request` did not return a PR number. The workflow should fail loudly when drift is detected but no PR number is produced, so a silent branch-only state is treated as an automation defect, not as "nothing to review."

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
