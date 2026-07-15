# Production readiness roadmap

This project is on a deliberate path toward a first production-ready major release.

The current release candidate, `v1.0.0-rc.3`, has passed exact-tag validation after user-facing SOS report and maintainer workflow additions. The repository keeps the **not production ready** warning until the final `v1.0.0` tag is prepared, published, and validated separately.

## Current status

| Area | Status |
| --- | --- |
| Latest manager release candidate | `v1.0.0-rc.3` |
| Latest validated MISP component set | core `v2.5.43`, modules `v3.0.8`, guard `v1.2` |
| Compatibility status | ✅ `v1.0.0-rc.3` validated compatible; final `v1.0.0` still pending |
| Public compatibility docs | ✅ available in [`compatibility.md`](compatibility.md) and [`validation/matrix.md`](validation/matrix.md) |
| Production-ready status | not yet |

## What must be true before `v1.0.0`

The following public docs define the intended production contract:

- [`support-matrix.md`](support-matrix.md)
- [`production-deployment.md`](production-deployment.md)
- [`security.md`](security.md)
- [`backup-restore-and-rollback.md`](backup-restore-and-rollback.md)

`v1.0.0` should mean the supported operator workflow is stable, documented, and backed by exact release-tag validation.

Before removing the public production warning, the project should have:

| Requirement | Status | Notes |
| --- | --- | --- |
| Exact release-tag compatibility validation | ✅ passed for `v1.0.0-rc.3` | Must be repeated for final `v1.0.0`. |
| Public compatibility matrix | ✅ | Tracks manager release/ref × official MISP Docker component set. |
| Public support matrix | drafted | Defines intended `v1.0.0` support scope and explicit non-goals. |
| Production deployment guide | drafted | Describes intended single-server Docker deployment workflow and remaining gates. |
| Security model and hardening statement | drafted | Documents installer security posture, non-goals, and evidence policy. |
| Backup restore documentation | ✅ documented | `restore.sh` restores generated config, host data, and database dumps from `backup.sh` output. |
| Real restore validation | ✅ validated for `v1.0.0-rc.2` | Restore drill passed: fresh install -> backup -> reset -> restore -> doctor/login. |
| Rollback/failure recovery docs | ✅ restore-based | A failed-update recovery drill passed using an external pre-update backup and `restore.sh`. |
| Current-release browser login validation | ✅ validated for `v1.0.0-rc.2` | Playwright Chromium login validation passed against the configured HTTPS URL. |
| Public production-readiness validation report | ✅ for `v1.0.0-rc.3` | Public-safe exact-tag validation report is available under `docs/validation/`. |

## Required validation before `v1.0.0`

The final `v1.0.0` tag should pass at least these scenarios:

- direct fresh install
- reverse-proxy fresh install
- install/update path with explicit official MISP component tags
- backup creation
- restore from backup into a clean deployment scope
- reset dry-run safety
- rollback or documented failure-recovery path
- browser-facing login flow
- failure-mode guardrails
- no-lock-in/manual Docker Compose usability
- compatibility with the latest reviewed official MISP Docker component set

## Release path

The recommended release path is:

1. Complete the documentation and validation gaps above.
2. Use `v1.0.0-rc.3` as the current validated release candidate.
3. Fix any release-candidate findings from operator testing.
4. Publish `v1.0.0` only after the final release tag passes the full validation set.
5. Mark `v1.0.0` **validated compatible** only after exact-tag validation passes.

## What this does not claim yet

Until `v1.0.0` is published and validated, this project does not claim:

- broad operating-system support beyond documented validation
- high-availability or multi-node deployment support
- Kubernetes support
- support for custom MISP images or forks
- complete disaster-recovery assurance for a final `v1.0.0` release tag before that exact tag is validated
- compatibility with future upstream MISP component sets before validation completes

## Evidence policy

Public production-readiness evidence should include:

- release/ref
- official MISP Docker component versions
- validation date
- scenario list
- pass/fail result
- limitations

Public evidence must not include private hostnames, private IP addresses, VM IDs, topology, raw logs, credentials, or private repository paths.

## What to read next

- Return to the [documentation map](README.md).
- Review the public support scope in [Support matrix](support-matrix.md).
- Review compatibility evidence in [Compatibility](compatibility.md).
- Review exact validation coverage in [Validation matrix](validation/matrix.md).
