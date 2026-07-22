# Compatibility validation: v1.2.0 with MISP core v2.5.44

## Summary

| Field | Value |
| --- | --- |
| Manager release/ref | `v1.2.0` |
| Manager commit | `b4972950ba80dd02b9bcebec30543b46b27443ea` |
| Manager version | `1.2.0` |
| MISP core tag | `v2.5.44` |
| MISP modules tag | `v3.0.9` |
| MISP guard tag | `v1.2` |
| Validation date | 2026-07-22 |
| Overall result | ✅ Validated compatible |
| Total duration | 2849 seconds |

This validates the immutable `v1.2.0` release tag and the published `v1.2.0` operator-bundle artifact against the listed official MISP Docker component set.

## Scenario coverage

| Scenario | Result | Public-safe evidence |
| --- | --- | --- |
| Direct-QA fresh install | ✅ Passed | Install completed in direct-QA mode; `doctor.sh` completed; login check passed without printing the password; default credential display did not reveal the password. |
| Browser login validation | ✅ Passed | A fresh direct-QA install was exercised with Playwright Chromium over HTTPS; the browser reached the login page, authenticated with configured admin credentials without printing the password, and reached an authenticated MISP page. |
| Reverse-proxy fresh install | ✅ Passed | Install completed in reverse-proxy mode with the documented proxy fixture; `doctor.sh` completed; verified-TLS login produced positive authenticated-session evidence; invalid credentials did not create authenticated-session evidence; explicit insecure mode remained opt-in only. |
| Install/update path | ✅ Passed | An explicit component-tag baseline install completed; `update.sh` completed with version-tag image tracking; `doctor.sh` and `login-check.sh` passed after update. |
| Restore-based rollback | ✅ Passed | A pre-update backup was created before an intentionally failed update; checksum verification passed; `restore.sh` recovered the deployment; the restored deployment passed doctor and login checks. |
| Backup, reset dry-run, and no-lock-in smoke | ✅ Passed | Backup completed; reset dry-run completed without destructive flags; the generated upstream checkout remained usable with normal Docker Compose configuration; login still passed after the lifecycle smoke. |
| Restore drill into clean deployment scope | ✅ Passed | Backup artifacts were created; destructive reset removed deployment state before restore; `restore.sh` completed from the backup directory; the restored deployment passed doctor and login checks. |
| Failure-mode guardrail smoke | ✅ Passed | An invalid direct-QA base URL was rejected before rendering deployment state. |
| Monitoring healthcheck contract and controlled failure/recovery | ✅ Passed | JSON, Nagios, Checkmk, and Prometheus output contracts passed the independent validator; healthy and missing deployments mapped to OK and UNKNOWN respectively; a controlled `misp-core` stop mapped to CRITICAL; restart and readiness checks recovered to OK. |
| Structured SOS privacy | ✅ Passed | Generated SOS output used the structured report format with mode `0600`; credentials, deployment URL/email values, private paths, backup metadata, raw helper output, and command-summary sections were absent. |

## Scope and limitations

- This evidence applies to the exact manager release/ref and official component tuple listed above.
- It does not claim compatibility with future MISP core, modules, or guard tags before those tuples are validated.
- It covers the documented single-server Docker lifecycle-manager scope.
- It is not high-availability, multi-node, or Kubernetes validation.
- Monitoring output was contract-tested and exercised against a managed deployment, but native ingestion by Zabbix, Checkmk, Nagios/Icinga, and Prometheus systems remains community validation work.
- Raw logs, private infrastructure identifiers, deployment-specific URLs, credentials, and topology are intentionally omitted from this public report.

## Release asset note

The `v1.2.0` GitHub Release includes a checksummed operator-bundle archive for the same immutable tag. The bundle artifact was downloaded and checksum-verified before validation. This compatibility result therefore covers both the source-checkout lifecycle path and the published operator-bundle artifact for the documented scope.

## What to read next

- [Compatibility overview](../compatibility.md)
- [Validation matrix](matrix.md)
- [Production readiness](../production-readiness.md)
- [Operator bundle](../operator-bundle.md)
