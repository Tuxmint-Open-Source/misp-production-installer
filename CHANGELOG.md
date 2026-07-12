# Changelog

This project follows [Semantic Versioning](https://semver.org/) for the installer code.

## [Unreleased]

### Changed

- Mark `v1.0.0-rc.1` as validated compatible after exact-tag validation passes.

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

- Add public compatibility tracking for installer release/ref and official MISP Docker component sets, including README summary and detailed compatibility reports.

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

- Initial public MISP production installer/overlay repository.
- Rocky Linux Docker host preparation script.
- Installer workflow for official `MISP/misp-docker` upstream checkouts.
- Generated `.env` handling with URL-safe Redis session password generation.
- Reverse-proxy and direct-QA exposure modes.
- Bootstrap TLS certificate helper.
- Backup, update, status, logs, start, stop, pull, validate, and doctor scripts.
- MISP schema readiness handling via `Admin runUpdates` and `bookmarks` table check.
- Public documentation for architecture, upgrade path, troubleshooting, shell scripts, and versioning.

[Unreleased]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v1.0.0-rc.1...HEAD
[1.0.0-rc.1]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v0.3.3...v1.0.0-rc.1
[0.3.3]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Tuxmint-Open-Source/misp-production-installer/releases/tag/v0.1.0
