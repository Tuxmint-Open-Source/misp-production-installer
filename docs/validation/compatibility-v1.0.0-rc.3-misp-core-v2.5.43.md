# Compatibility validation: v1.0.0-rc.3 with MISP core v2.5.43

## Summary

| Field | Value |
| --- | --- |
| Manager release/ref | `v1.0.0-rc.3` |
| Manager commit | `25ee1a9f82dd4fa16504b8ce9490c4f186cc4438` |
| MISP core | `v2.5.43` |
| MISP modules | `v3.0.8` |
| MISP guard | `v1.2` |
| Validation date | 2026-07-15 |
| Run ID | `2026-07-15-compat-v1.0.0-rc.3-misp-core-v2.5.43` |
| Overall result | ✅ Validated compatible |
| Total duration | 2312 seconds |

`v1.0.0-rc.3` is validated compatible with the listed official MISP Docker component set for the scenarios below.

This report is public-safe. It intentionally excludes private hostnames, private IP addresses, credentials, generated secrets, raw logs, internal topology, VM identifiers, backup contents, database dumps, screenshots, and private infrastructure details.

## Scenarios exercised

| Scenario | Result | Duration |
| --- | --- | ---: |
| Direct-QA fresh install | ✅ passed | 233s |
| Reverse-proxy fresh install with Caddy | ✅ passed | 268s |
| Install baseline tags and run update path | ✅ passed | 375s |
| Backup, reset dry-run, and no-lock-in smoke | ✅ passed | 251s |
| Failure-mode guardrails smoke | ✅ passed | 0s |
| Restore drill from backup into clean deployment scope | ✅ passed | 323s |
| Browser login validation for current manager ref | ✅ passed | 286s |
| Restore-based rollback after failed update | ✅ passed | 372s |

## What passed

The validation covered:

- clean direct-QA install with doctor and login checks;
- reverse-proxy install shape with a Caddy fixture;
- install/update workflow using explicit official component tags;
- backup creation, reset dry-run safety, and no-lock-in Docker Compose usability;
- failure guardrails for invalid direct-QA base URL input;
- restore from a backup into a clean deployment scope;
- browser login using Playwright Chromium against the configured HTTPS URL;
- restore-based rollback after a simulated failed update.

## Limitations

This validation does not claim:

- compatibility with future official MISP Docker component sets;
- compatibility with custom MISP images, forks, or locally modified upstream checkouts;
- high-availability, multi-node, or Kubernetes support;
- broad operating-system coverage beyond the documented validation environment;
- production-ready status for final `v1.0.0` before that exact final tag is published and validated separately.

## Compatibility decision

The pair below is marked **validated compatible**:

```text
misp-docker-lifecycle-manager v1.0.0-rc.3 × MISP core v2.5.43 / modules v3.0.8 / guard v1.2
```

The final `v1.0.0` release must still be tagged and validated separately before final production-ready claims are made.

## What to read next

- Return to the [validation matrix](matrix.md).
- Review release/component status in [Compatibility](../compatibility.md).
- Review production-readiness state in [Production readiness](../production-readiness.md).
