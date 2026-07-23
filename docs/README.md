# Documentation

Start here if you are new to **MISP Docker Lifecycle Manager**.

The documentation is split by reader path so operators do not need to read maintainer/release material before they can install and operate a supported deployment.

## Choose your path

### Users and operators

Follow this path when you want to install, run, update, monitor, or recover a MISP deployment:

1. [Support matrix](support-matrix.md) — confirm that your deployment model is supported.
2. [Getting started](getting-started.md) — perform a first install and verification pass.
3. [Operator guide](operator-guide.md) — follow the normal lifecycle of a managed deployment.
4. [Production deployment guide](production-deployment.md) — plan reverse proxy, host, secrets, and operational choices.
5. [Backup, restore, and rollback](backup-restore-and-rollback.md) — understand recovery before you need it.
6. [Upgrade path](upgrade-path.md) — update the manager and MISP components safely.
7. [Monitoring](monitoring.md) — review the healthcheck contract and planned integrations.
8. [Troubleshooting](troubleshooting.md) — diagnose failed installs, login issues, and update problems.

### Contributors and maintainers

Follow this path when you want to contribute, review release evidence, or maintain the repository:

1. [`CONTRIBUTING.md`](../CONTRIBUTING.md) — public-safety rules, PR workflow, and contribution expectations.
2. [`AGENTS.md`](../AGENTS.md) — repository rules for automated contributors.
3. [Maintainer workflow](maintainer-workflow.md) — GitHub settings, labels, SOS triage, upstream monitoring, and release operations.
4. [Release process](release/release-process.md) — release PR, tagging, GitHub Release, and post-tag validation workflow.
5. [Release integrity policy](release/integrity-and-provenance.md) — artifact integrity controls and deferred provenance mechanisms.
6. [Upstream input policy](upstream-inputs.md) — upstream Git, component tag, and future digest identity rules.
7. [Compatibility](compatibility.md) and [validation matrix](validation/matrix.md) — validated manager/component evidence.

## Common user/operator tasks

| I want to... | Start here |
| --- | --- |
| check whether my deployment is supported | [Support matrix](support-matrix.md) |
| install MISP for the first time | [Getting started](getting-started.md) |
| follow the normal lifecycle | [Operator guide](operator-guide.md) |
| plan a reverse-proxy deployment | [Production deployment guide](production-deployment.md) |
| update MISP components | [Upgrade path](upgrade-path.md) |
| back up or restore MISP | [Backup, restore, and rollback](backup-restore-and-rollback.md) |
| plan monitoring integration | [Monitoring](monitoring.md) and [community testing issue #62](https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/issues/62) |
| recover from a failed update | [Backup, restore, and rollback](backup-restore-and-rollback.md#restore-based-rollback-after-failed-update) |
| understand secrets and privileges | [Security](security.md) |
| debug a failure | [Troubleshooting](troubleshooting.md) |
| report a reproducible bug safely | [Anonymous SOS reports](sos-report.md) |

## Common contributor/maintainer tasks

| I want to... | Start here |
| --- | --- |
| contribute code, docs, or integration testing | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| inspect every script and option | [Shell scripts reference](shell-scripts.md) |
| review compatibility evidence | [Compatibility](compatibility.md) and [validation matrix](validation/matrix.md) |
| understand release and upstream input identity | [Versioning](versioning.md), [Release integrity](release/integrity-and-provenance.md), and [Upstream input policy](upstream-inputs.md) |
| maintain the repository or cut a release | [Maintainer workflow](maintainer-workflow.md), then [release process](release/release-process.md) |
| update release/provenance policy | [Release integrity policy](release/integrity-and-provenance.md) and [Upstream input policy](upstream-inputs.md) |

## Documentation types

The docs intentionally separate different kinds of information:

- **First path:** [Getting started](getting-started.md).
- **Operator journey:** [Operator guide](operator-guide.md).
- **How-to guides:** [Production deployment](production-deployment.md), [upgrade path](upgrade-path.md), [backup/restore/rollback](backup-restore-and-rollback.md), [monitoring](monitoring.md), [troubleshooting](troubleshooting.md).
- **Explanation:** [Architecture](architecture.md), [security](security.md), [support matrix](support-matrix.md), [versioning](versioning.md), [upstream input policy](upstream-inputs.md).
- **Reference:** [Shell scripts](shell-scripts.md), [monitoring contract](monitoring.md), [compatibility](compatibility.md), [validation matrix](validation/matrix.md).
- **Support and reporting:** [Troubleshooting](troubleshooting.md), [anonymous SOS reports](sos-report.md), [security](security.md).
- **Maintainer workflow:** [Maintainer workflow](maintainer-workflow.md), [release process](release/release-process.md), [release integrity policy](release/integrity-and-provenance.md).

## Current release status

`v1.3.1` is the latest published release for the documented component tuple, but exact-tag/package-artifact validation is pending. `v1.3.0` remains the latest validated-compatible release and its published operator-bundle artifact passed the lifecycle validation matrix for the documented scope.

See [production readiness](production-readiness.md) for the current release-readiness state.

## What to read next

- New operator: continue with [Getting started](getting-started.md).
- Planning a real deployment: read [Support matrix](support-matrix.md), then [Production deployment guide](production-deployment.md).
- Contributor or maintainer: read [`CONTRIBUTING.md`](../CONTRIBUTING.md), then [Maintainer workflow](maintainer-workflow.md).
- Reviewing release evidence: read [Compatibility](compatibility.md), then [Validation matrix](validation/matrix.md).
