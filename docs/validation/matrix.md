# Validation matrix

This matrix summarizes public-safe real-world validation coverage by release.

It is not a guarantee that every environment or component combination works. It records the scenarios that were actually exercised and passed.

| Release | Fresh VM | Host prep | Fresh older/specific install | Update to latest | DB migrations | External redirect | CLI login check | Browser login | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v0.3.1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Rocky Linux 10.2, single-server Docker, published release artifact |

## Legend

- **Fresh VM**: validation started from a newly recreated VM, not only a reset application directory.
- **Host prep**: `prepare-host-rocky.sh` installed Docker and Docker Compose.
- **Fresh older/specific install**: install used explicit older MISP component tags.
- **Update to latest**: update moved from the older component set to current upstream-declared component tags.
- **DB migrations**: MISP database updates ran and completed during install/update.
- **External redirect**: browser-facing URL stayed on the configured non-loopback base URL.
- **CLI login check**: `login-check.sh` succeeded without printing the password.
- **Browser login**: a Playwright-controlled Chromium browser reached the authenticated MISP UI.

## Detailed reports

- [`real-world-v0.3.1.md`](real-world-v0.3.1.md)
