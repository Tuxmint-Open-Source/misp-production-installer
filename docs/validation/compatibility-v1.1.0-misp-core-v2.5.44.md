# Compatibility validation: v1.1.0 with MISP core v2.5.44

## Summary

| Field | Value |
| --- | --- |
| Manager release/ref | `v1.1.0` |
| Manager commit | `a0172cc1708803ce80f8542ec467515b1c44f5fb` |
| Manager version | `1.1.0` |
| MISP core tag | `v2.5.44` |
| MISP modules tag | `v3.0.9` |
| MISP guard tag | `v1.2` |
| Validation date | 2026-07-21 |
| Overall result | ✅ Validated compatible |

This validates the immutable `v1.1.0` release tag against the listed official MISP Docker component set.

## Scenario coverage

| Scenario | Result | Evidence source |
| --- | --- | --- |
| Direct-QA fresh install | ✅ Passed | corrected TLS-mode rerun |
| Browser login | ✅ Passed | full run |
| Reverse-proxy fresh install | ✅ Passed | full run |
| Install/update path | ✅ Passed | corrected TLS-mode rerun |
| Restore-based rollback | ✅ Passed | corrected TLS-mode rerun |
| Backup/reset/no-lock-in lifecycle smoke | ✅ Passed | lifecycle rerun |
| Restore drill into a clean deployment scope | ✅ Passed | final restore rerun |
| Failure-mode guardrails | ✅ Passed | full run |
| Monitoring health/failure/recovery contracts | ✅ Passed | full run |
| Structured SOS privacy | ✅ Passed | full run |

## Rerun classification

The first full run established five passing scenarios but used strict TLS for direct-QA login checks against an intentional bootstrap certificate. A corrected targeted rerun passed direct install, update, and rollback. The remaining scenarios encountered transient pre-install network-readiness failures. Lifecycle then passed in a targeted rerun, and restore passed in the final rerun after the validation readiness check was corrected.

These failures were validation-harness or validation-infrastructure defects, not manager product failures. Failed runs remain retained privately; compatibility is based only on passing evidence for every scenario at the same immutable manager tag and component tuple.

## Evidence summary

Validation confirmed that:

- direct and reverse-proxy installs completed and passed health and login checks;
- browser login reached an authenticated MISP page;
- explicit baseline component tags updated successfully with version-tag tracking;
- a simulated failed update recovered through the external pre-update backup;
- backup, reset dry-run, and no-lock-in Compose operation passed;
- destructive reset followed by restore recovered configuration, host data, database state, health, and login;
- invalid direct-QA input failed before deployment state was written;
- monitoring formats passed healthy, missing-deployment, controlled-critical, and recovery checks;
- structured SOS output remained bounded and excluded credential-bearing login checks and private deployment data.

## Limitations

This report covers only the exact manager tag and component set listed above. It does not imply compatibility with future component tags, custom images, forks, Kubernetes, high-availability deployments, or broader operating-system coverage.

Public evidence is intentionally summarized. Raw logs, private infrastructure identifiers, credentials, topology, and deployment-specific details are omitted.

## What to read next

- [Compatibility matrix](../compatibility.md)
- [Validation matrix](matrix.md)
- [Production readiness](../production-readiness.md)
- [Backup, restore, and rollback](../backup-restore-and-rollback.md)
