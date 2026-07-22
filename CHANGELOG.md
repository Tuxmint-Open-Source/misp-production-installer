# Changelog

This project follows [Semantic Versioning](https://semver.org/) for the installer code.

## [Unreleased]

### Added

- Add an always-running, read-only repository gate for unit/static tests, Bash syntax, Python compilation, tracked-YAML parsing, and complete-tree whitespace checks on every pull request and push to `main`.
- Add deterministic, allowlisted operator-bundle generation with embedded file digests, a companion archive checksum, runtime-closure and exclusion tests, and offline install/rollback guidance.

### Changed

- Mark immutable `v1.1.0` as validated compatible with MISP core `v2.5.44`, modules `v3.0.9`, and guard `v1.2` after the complete exact-tag matrix passed.
- Add explicit `latest_published` and `latest_validated` release channels without mutable Git aliases.
- Separate read-only upstream collection/testing from narrowly scoped review-PR publication, with a validated short-lived artifact boundary between the jobs.
- Keep the primary README focused on current stable release evidence while retaining pre-`v1.0.0` history in the detailed compatibility and changelog records.
- Reject collector-impossible missing child records inside watched-tree publication data.
- Replace transitive ShellCheck acquisition with an explicit official release, pinned platform artifact, and verified SHA-256 digest before execution.

## [1.1.0] - 2026-07-21

### Added

- Document the monitoring healthcheck contract, including exit codes, JSON schema, and Zabbix/Checkmk/Nagios integration examples.
- Add `installer/healthcheck.sh` with text, JSON, Nagios/Icinga, Checkmk, and Prometheus-style output formats.
- Add a monitoring-output validator, an explicit integration-evidence matrix, and a community call for real Zabbix, Checkmk, Nagios/Icinga, and Prometheus testing.
- Record successful real-deployment monitoring validation across healthy, UNKNOWN, controlled-CRITICAL, and recovery states while preserving the untested-platform limitation.
- Replace free-form SOS command output and backup metadata with a bounded `generated-sos-v2` allowlist of enums, booleans, counts, validated public tags, restricted versions, and non-login health statuses; write reports atomically and refuse symlink targets.
- Align primary README, readiness, deployment, support, security, and versioning docs with the `v1.1.0` release while keeping exact-tag compatibility explicitly pending until validation passes.
- Clarify stable security support, community support expectations, issue examples, contribution discovery, and public evidence navigation after the post-v1 trust review.
- Expand upstream MISP Docker drift coverage to Compose service blocks and variables, template key inventory, initialization/configuration/readiness/process inputs, and selected operator guidance while suppressing commit-only noise and bounding concurrent workflow runs.
- Monitor official MISP core, modules, and guard releases directly so maintainers are prompted before or after official MISP Docker adopts a new component tag.

### Changed

- Make monitoring fail closed for missing expected Compose services and malformed/non-200 heartbeat responses, enforce `--timeout` as one global command deadline rather than a fresh timeout per probe, and require an explicit validator opt-out before login checks use unverified TLS in disposable bootstrap environments.
- Mark `v1.0.0` as validated compatible with MISP core `v2.5.44` and modules `v3.0.9` after upstream drift validation.
- Validate backup manifests and archive member/link allowlists before destructive restore, reject credential-bearing or option-like upstream sources, require matching managed-target identity, stop on cleanup failure, create unpredictable backup sets under trusted roots, refresh update state to the resolved upstream commit, and write installer state atomically with mode `0600`.
- Verify TLS for credential-bearing login checks by default, reject plain HTTP unless explicitly requested as insecure, constrain redirects to the selected origin, and require a positive authenticated-session marker before reporting success.
- Bound all SOS Git, Docker, Compose, and health probes under one monotonic global deadline instead of independent subprocess timeout windows.

## [1.0.0] - 2026-07-15

### Changed

- Prepare the first stable release line from the validated `v1.0.0-rc.3` baseline.
- Replace the README production warning with first-stable-release wording.
- Mark final `v1.0.0` as validated compatible after exact-tag validation passes.

## [1.0.0-rc.3] - 2026-07-15

### Added

- Add a documentation landing page, getting-started guide, and operator guide to give human readers a clear path through the repository.
- Add cross-links and "What to read next" sections to major docs so readers can continue through the operator journey without returning to search manually.
- Refresh the shell-script reference against actual command help output, including main commands, helper scripts, destructive workflows, backup artifacts, credential handling, and safety notes.
- Add community health files and GitHub templates for code of conduct, contributing, pull requests, bugs, feature requests, and documentation improvements.
- Add a repository-level security policy for private vulnerability reporting, supported versions, disclosure expectations, and public redaction rules.
- Add low-noise dependency and code-scanning automation for GitHub Actions, Python CodeQL analysis, and ShellCheck.
- Add a maintainer workflow guide for labels, PR review, repository settings, automation rollout, branch-protection timing, and release discipline.
- Add anonymous SOS report documentation and update the bug-report template so users can provide reproducible public-safe diagnostics without leaking deployment details.
- Add `installer/sos-report.sh` and a redaction helper for generated public-safe SOS bug reports.
- Add concise redacted health-command and backup-shape summaries to generated SOS reports.
- Document maintainer triage for anonymous SOS reports, including when to request `needs-sos-report` and when to move reports to private security handling.
- Update the pinned CodeQL workflow from CodeQL Action v3 to v4 to avoid GitHub Actions Node.js 20 and CodeQL v3 deprecation warnings.
- Document the maintainer response workflow for scheduled official MISP Docker upstream drift review PRs.

### Changed

- Mark `v1.0.0-rc.2` as validated compatible after exact-tag validation passes.

## [1.0.0-rc.2] - 2026-07-13

### Changed

- Mark `v1.0.0-rc.1` as validated compatible after exact-tag validation passes.
- Rebrand the project from MISP Production Installer to MISP Docker Lifecycle Manager after the GitHub repository rename.
- Update public repository links, README positioning, script version output, generated metadata, and compatibility wording for the new project name.
- Treat the new product identity as authoritative for new release candidates because the project is still pre-`v1.0.0`; historical pre-1.0 metadata markers are not guaranteed compatibility targets.

## [1.0.0-rc.1] - 2026-07-12

### Added

- Add a public production-readiness roadmap describing the remaining documentation and validation gates before `v1.0.0`.
- Add public `v1.0.0` operator-readiness docs for support scope, production deployment, security model, and backup/restore/rollback expectations.
- Add `restore.sh` for restoring generated deployment config, host data, and database dumps from `backup.sh` output.
- Allow `update.sh --backup-root PATH` so pre-update backups can be stored outside the deployment directory for restore-based rollback drills.

### Changed

- Document the post-tag compatibility validation flow for releases and clarify that release/component pairs are marked **validated compatible** only after exact-tag validation passes.
- Clean up the `v0.3.3` compatibility report wording now that the release tag has passed validation.
- Include generated deployment configuration in backups so restore can reproduce the original runtime settings and secrets.
- Update production-readiness docs now that restore, browser login, and restore-based rollback validation have passed for current `main`.

## [0.3.3] - 2026-07-12

### Added

- Add public compatibility tracking for manager release/ref and official MISP Docker component sets, including README summary and detailed compatibility reports.

### Changed

- Make `login-check.sh` human-readable by default and add `--machine-readable` for stable key/value diagnostics.
- Mention `admin-credentials.sh` in the install success output and troubleshooting docs so operators can safely retrieve generated login details.

### Fixed

- Wait for MISP's upstream interactive-login readiness marker before declaring install/update readiness.

## [0.3.2] - 2026-07-08

### Added

- Add public-safe real-world `v0.3.1` validation documentation and a validation matrix covering fresh VM host preparation, older/specific component install, update-to-latest, database migrations, external redirect checks, CLI login checks, and Playwright browser login.

### Changed

- Pin scheduled upstream-monitor GitHub Actions to commit SHAs and align versioning guidance with the release-PR workflow.
- Make Docker group membership during Rocky host preparation explicit opt-in because Docker group access is root-equivalent.

### Fixed

- Harden installer safety checks around URL parsing, reset target validation, backup artifact permissions, database credential handling, and temporary diagnostic output.

## [0.3.1] - 2026-07-07

### Changed

- Reorganize `README.md` so new users see the supported install/update workflows, version model, post-install checks, non-invasive/no-lock-in project focus, and key `v0.3.0` validation findings before the architecture details.

## [0.3.0] - 2026-07-07

### Added

- Add `AGENTS.md` with public-safe coding-agent guidance for repository workflow, validation, and release conventions.
- Add `QA.md` with repository quality gates, acceptance criteria, and definition of done.
- Add scheduled upstream drift monitoring for public `MISP/misp-docker` inputs that affect installer assumptions.
- Add `installer/get-current-misp-versions.sh` to show official upstream MISP component versions and compare them with a local install.
- Add explicit `--core-tag`, `--modules-tag`, and `--guard-tag` overrides for installing or updating to specific MISP component image versions.

### Changed

- Document and implement deterministic MISP component image tracking for updates. The default update path now pins runtime image tags to the official component tags from upstream `template.env` instead of relying on implicit `latest`.
- Improve `installer/get-current-misp-versions.sh` output with a readable table and clearer local-install status.
- Reduce noisy bootstrap TLS and DNS-check output so installer and doctor logs focus on actionable status.
- Retry Rocky/Docker package-manager operations during host preparation to tolerate transient repository or GPG-key download failures.

### Fixed

- Wait longer for MISP database updates during install/update and report first-start database initialization clearly instead of flooding logs with repeated CakePHP stack traces.
- Reject loopback `BASE_URL` values for direct-QA installs so browser redirects do not point users to their own localhost.
- Generate MySQL passwords with hex characters only to match upstream MISP Docker's alphanumeric password requirement and avoid corrupting generated database configuration.

## [0.2.0] - 2026-07-06

### Added

- Add `installer/reset-installation.sh` for failed or unwanted installs. It performs a dry-run by default, prompts for confirmation in destructive mode, removes MISP Compose containers/networks/named volumes and generated install files, and intentionally leaves Docker Engine installed.
- Add `installer/admin-credentials.sh` to show the configured initial administrator account and optionally print the generated password on a trusted terminal.
- Add `installer/login-check.sh` for a CSRF-aware Web UI login check that does not print the password and attempts logout after a successful check.
- Add troubleshooting guidance for Web UI login failures.

### Changed

- Suppress noisy Docker Compose warnings for unset optional upstream variables by setting them to empty values only for wrapper-managed Compose commands.

## [0.1.0] - 2026-07-03

### Added

- Initial public MISP Docker lifecycle manager repository.
- Rocky Linux Docker host preparation script.
- Installer workflow for official `MISP/misp-docker` upstream checkouts.
- Generated `.env` handling with URL-safe Redis session password generation.
- Reverse-proxy and direct-QA exposure modes.
- Bootstrap TLS certificate helper.
- Backup, update, status, logs, start, stop, pull, validate, and doctor scripts.
- MISP schema readiness handling via `Admin runUpdates` and `bookmarks` table check.
- Public documentation for architecture, upgrade path, troubleshooting, shell scripts, and versioning.

[Unreleased]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v1.0.0-rc.3...v1.0.0
[1.0.0-rc.3]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v1.0.0-rc.2...v1.0.0-rc.3
[1.0.0-rc.2]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v1.0.0-rc.1...v1.0.0-rc.2
[1.0.0-rc.1]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v0.3.3...v1.0.0-rc.1
[0.3.3]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/releases/tag/v0.1.0
