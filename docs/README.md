# Documentation

Start here if you are new to **MISP Docker Lifecycle Manager**.

This documentation is organized around the operator journey: understand the model, decide whether the project fits your use case, install safely, verify the deployment, operate day to day, update carefully, back up, restore, and troubleshoot.

## Recommended reading path

1. [Support matrix](support-matrix.md) — confirm that your deployment model is supported.
2. [Getting started](getting-started.md) — perform a first install and verification pass.
3. [Operator guide](operator-guide.md) — follow the normal lifecycle of a managed deployment.
4. [Production deployment guide](production-deployment.md) — plan reverse proxy, host, secrets, and operational choices.
5. [Backup, restore, and rollback](backup-restore-and-rollback.md) — understand recovery before you need it.
6. [Upgrade path](upgrade-path.md) — update the manager and MISP components safely.
7. [Compatibility](compatibility.md) and [validation matrix](validation/matrix.md) — see which manager/component pairs are validated.
8. [Troubleshooting](troubleshooting.md) — diagnose failed installs, login issues, and update problems.

## Common tasks

| I want to... | Start here |
| --- | --- |
| understand what this project does | [Operator guide](operator-guide.md) |
| check whether my deployment is supported | [Support matrix](support-matrix.md) |
| install MISP for the first time | [Getting started](getting-started.md) |
| plan a reverse-proxy deployment | [Production deployment guide](production-deployment.md) |
| check which MISP versions are validated | [Compatibility](compatibility.md) |
| update MISP components | [Upgrade path](upgrade-path.md) |
| back up or restore MISP | [Backup, restore, and rollback](backup-restore-and-rollback.md) |
| recover from a failed update | [Backup, restore, and rollback](backup-restore-and-rollback.md#restore-based-rollback-after-failed-update) |
| understand secrets and privileges | [Security](security.md) |
| inspect every script and option | [Shell scripts reference](shell-scripts.md) |
| debug a failure | [Troubleshooting](troubleshooting.md) |
| contribute or cut a release | [Maintainer workflow](maintainer-workflow.md), then [release process](release/release-process.md) |

## Documentation types

The docs intentionally separate different kinds of information:

- **First path:** [Getting started](getting-started.md).
- **Operator journey:** [Operator guide](operator-guide.md).
- **How-to guides:** [Production deployment](production-deployment.md), [upgrade path](upgrade-path.md), [backup/restore/rollback](backup-restore-and-rollback.md), [troubleshooting](troubleshooting.md).
- **Explanation:** [Architecture](architecture.md), [security](security.md), [support matrix](support-matrix.md), [versioning](versioning.md).
- **Reference:** [Shell scripts](shell-scripts.md), [compatibility](compatibility.md), [validation matrix](validation/matrix.md).
- **Maintainer workflow:** [Maintainer workflow](maintainer-workflow.md), [release process](release/release-process.md).

## Current release-candidate status

`v1.0.0-rc.2` is validated compatible with the documented MISP Docker component set, but the project still keeps the public production warning until final `v1.0.0` is tagged and validated separately.

See [production readiness](production-readiness.md) for the current release-readiness state.

## What to read next

- New operator: continue with [Getting started](getting-started.md).
- Planning a real deployment: read [Support matrix](support-matrix.md), then [Production deployment guide](production-deployment.md).
- Reviewing release evidence: read [Compatibility](compatibility.md), then [Validation matrix](validation/matrix.md).
