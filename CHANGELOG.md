# Changelog

This project follows [Semantic Versioning](https://semver.org/) for the installer code.

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

[0.1.0]: https://github.com/Tuxmint-Open-Source/misp-production-installer/releases/tag/v0.1.0
