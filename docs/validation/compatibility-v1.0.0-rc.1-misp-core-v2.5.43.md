# Compatibility validation: installer v1.0.0-rc.1 with MISP core v2.5.43

This document records public-safe exact-tag validation for the `misp-production-installer` `v1.0.0-rc.1` release candidate with the reviewed official MISP Docker component set.

Private infrastructure identifiers, raw logs, credentials, and topology are intentionally omitted.

## Summary

| Field | Value |
| --- | --- |
| Installer ref | `v1.0.0-rc.1` release candidate tag |
| Installer commit | `c4592fc` |
| MISP core | `v2.5.43` |
| MISP modules | `v3.0.8` |
| MISP guard | `v1.2` |
| Validation date | 2026-07-12 |
| Overall result | ✅ Validated compatible |

## Scenario results

| Scenario | Result | Public-safe evidence |
| --- | --- | --- |
| Direct fresh install | ✅ passed | Install completed in direct-QA mode; `doctor.sh` completed; `login-check.sh` passed without printing the password; credentials helper default output did not print the password. |
| Reverse-proxy fresh install | ✅ passed | Install completed in reverse-proxy mode; Caddy fixture started; `doctor.sh` completed; `login-check.sh` passed via the proxied URL. |
| Update path | ✅ passed | Baseline component-tag install completed; `update.sh` completed with `version-tags` image tracking; `doctor.sh` and `login-check.sh` passed after update. |
| Lifecycle smoke | ✅ passed | Backup completed; reset dry-run completed without destructive flags; generated upstream checkout remained usable with manual Docker Compose config; login check still passed. |
| Failure guardrails | ✅ passed | Direct-QA loopback `BASE_URL` was rejected; the failure message identified the invalid direct-QA/base URL condition; no deployment `.env` was created. |
| Restore drill | ✅ passed | Backup contained database, host data, generated config, and checksum artifacts; destructive reset removed deployment state; `restore.sh` restored into a clean deployment scope; `doctor.sh` and `login-check.sh` passed after restore. |
| Browser login | ✅ passed | Playwright Chromium reached the HTTPS login page, submitted configured admin credentials without printing the password, and reached an authenticated MISP page. |
| Restore-based rollback | ✅ passed | A simulated failed update created an external pre-update backup before failing on an invalid component tag; checksum verification passed; `restore.sh` recovered from that backup; `doctor.sh` and `login-check.sh` passed after recovery. |

## Validation scope

This validation covers the installer release candidate and official MISP Docker component set listed above.

It does not claim:

- support for custom MISP images or forks
- support for every Linux distribution
- high-availability, clustered, or Kubernetes deployments
- compatibility with future MISP component sets before separate validation

## Status

`v1.0.0-rc.1` is validated compatible with the listed component set.

The final `v1.0.0` release must still be tagged and validated separately before the project removes the production warning or marks final `v1.0.0` as validated compatible.
