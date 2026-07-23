# Compatibility validation: v1.3.0 with MISP core v2.5.44

This public-safe report records exact-tag and packaged-artifact validation for `misp-docker-lifecycle-manager` `v1.3.0` with the official MISP Docker component set listed below.

| Field | Value |
| --- | --- |
| Manager release/ref | `v1.3.0` |
| Manager commit | `4af5ce532c24963505a6fb6cdc01e5302e051cea` |
| MISP core tag | `v2.5.44` |
| MISP modules tag | `v3.0.9` |
| MISP guard tag | `v1.2` |
| Validation date | 2026-07-23 |
| Overall result | ✅ Validated compatible |
| Total duration | 3025 seconds |

## Scope

The validation covered the immutable `v1.3.0` release tag and the published `v1.3.0` operator-bundle artifact from the same GitHub Release. The bundle artifact was downloaded and checksum-verified before validation.

This result covers both the source-checkout lifecycle path and the published operator-bundle artifact for the documented single-server Docker scope. It also covers the canonical `./lifecycle/*.sh` command path and retained `./installer/*.sh` compatibility wrappers.

## Scenario results

| Scenario | Result | Evidence summary |
| --- | --- | --- |
| Direct-QA fresh install | ✅ Passed | Install, doctor, login check, default credential display, and `installer/` wrapper smoke passed. |
| Browser login validation | ✅ Passed | Chromium reached the login page and authenticated without exposing the generated password. |
| Reverse-proxy fresh install | ✅ Passed | Reverse-proxy deployment, verified-TLS login, invalid-credential rejection, explicit insecure mode, and healthcheck login integration passed. |
| Upgrade path | ✅ Passed | Explicit baseline component-tag install updated to the target component tuple with doctor and login checks passing afterward. |
| Restore-based rollback | ✅ Passed | A failed update created a pre-update backup; restore recovered the deployment and post-restore doctor/login checks passed. |
| Backup, reset dry-run, and no-lock-in smoke | ✅ Passed | Backup completed, reset dry-run remained non-destructive, manual Compose configuration worked from the generated upstream checkout, and login still passed. |
| Restore drill | ✅ Passed | Backup artifacts and checksums were present, destructive reset removed deployment state, restore completed, and doctor/login passed afterward. |
| Failure-mode guardrails | ✅ Passed | Direct-QA loopback URL was rejected before creating deployment state. |
| Monitoring healthcheck | ✅ Passed | JSON, Nagios, Checkmk, and Prometheus output contracts passed; healthy, missing deployment, controlled outage, and recovery states mapped to expected statuses. |
| Structured SOS privacy | ✅ Passed | Generated SOS report stayed bounded, used restrictive permissions, and omitted deployment credentials, private paths, backup metadata, and raw helper output. |

## Notes and limitations

- The result applies to the listed manager release/ref and official MISP Docker component tuple only.
- Future manager releases, upstream component sets, deployment topologies, or custom images require separate validation before compatibility is claimed.
- Native ingestion by running Zabbix, Checkmk, Nagios/Icinga, and Prometheus systems remains separate community testing work. This validation covers producer-side output contracts and status mapping.
- Raw logs and private infrastructure identifiers are intentionally excluded from this public report.
