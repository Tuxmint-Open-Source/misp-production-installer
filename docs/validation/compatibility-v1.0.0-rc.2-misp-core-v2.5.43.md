# Compatibility validation: manager v1.0.0-rc.2 with MISP core v2.5.43

This document records public-safe exact-tag validation for the `misp-docker-lifecycle-manager` `v1.0.0-rc.2` release candidate with the official MISP Docker component set listed below.

## Summary

| Field | Value |
| --- | --- |
| Manager release/ref | `v1.0.0-rc.2` release candidate tag |
| Manager commit | `4cf1268` |
| MISP core | `v2.5.43` |
| MISP modules | `v3.0.8` |
| MISP guard | `v1.2` |
| Validation date | 2026-07-13 |
| Overall result | ✅ Validated compatible |

## Scenarios validated

| Scenario | Result | Public-safe evidence |
| --- | --- | --- |
| Direct fresh install | ✅ Passed | Install completed in direct QA mode; `doctor.sh`, `login-check.sh`, and safe credential-helper output checks passed. |
| Reverse-proxy fresh install with Caddy | ✅ Passed | Install completed in reverse-proxy mode; Caddy fixture started; `doctor.sh` and proxied `login-check.sh` passed. |
| Update path | ✅ Passed | Baseline component-tag install completed; `update.sh --image-track version-tags` completed; post-update doctor and login checks passed. |
| Lifecycle backup/reset/no-lock-in smoke | ✅ Passed | Backup completed; reset dry-run completed; generated upstream checkout remained usable with manual Docker Compose configuration; login check still passed. |
| Failure guardrails | ✅ Passed | Invalid direct-QA loopback `BASE_URL` was rejected and no deployment `.env` was created. |
| Restore drill | ✅ Passed | Backup included database, host data, generated config, and checksums; destructive reset removed deployment state; `restore.sh`, doctor, and login checks passed after restore. |
| Browser login | ✅ Passed | Playwright Chromium reached the MISP login page over HTTPS and completed an authenticated login without printing the password. |
| Restore-based rollback after failed update | ✅ Passed | A simulated failed update created a pre-update backup; checksum verification passed; `restore.sh`, doctor, and login checks passed after rollback recovery. |

## Interpretation

This result means the `v1.0.0-rc.2` manager release candidate was validated compatible with the listed official MISP Docker component set in the tested single-server Docker scenarios.

It does **not** mean every environment, reverse proxy, operating system, or future upstream MISP Docker component set is automatically validated. New manager releases and new official MISP Docker component sets should be validated as explicit compatibility pairs.

## Limitations

- Validation was performed in private reproducible VM slots; private infrastructure identifiers and raw logs are intentionally omitted.
- Caddy is the tested reverse-proxy fixture for this compatibility entry.
- High-availability, Kubernetes, multi-node, and non-Docker deployments are outside this manager's current support scope.
- The final `v1.0.0` release must still be tagged and validated separately before final production-ready claims are made.
