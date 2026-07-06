# Changelog

This project follows [Semantic Versioning](https://semver.org/) for the installer code.

## [Unreleased]

### Added

- Add `AGENTS.md` with public-safe coding-agent guidance for repository workflow, validation, and release conventions.
- Add `QA.md` with repository quality gates, acceptance criteria, and definition of done.

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

[Unreleased]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Tuxmint-Open-Source/misp-production-installer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Tuxmint-Open-Source/misp-production-installer/releases/tag/v0.1.0
