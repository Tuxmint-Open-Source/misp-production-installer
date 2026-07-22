# Monitoring healthcheck validation — PR #61

Date: 2026-07-17
Result: **passed**

This report records monitoring-system-independent validation of the healthcheck command and output validator added around public PR [#61](https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/pull/61).

## Source under test

- Manager commit: `dbf0b841448ae892be607c90d712800135b4e8f7`
- `VERSION` file at that commit: `1.0.0`
- Official MISP Docker component set:
  - MISP core: `v2.5.44`
  - MISP modules: `v3.0.9`
  - MISP guard: `v1.2`

The commit is a post-`v1.0.0` development commit, not a claim that the original `v1.0.0` release artifact contained the validator.

## Scenario

A fresh direct-QA deployment was created on disposable private validation infrastructure. The scenario then exercised:

| State | Action | Expected result | Outcome |
|---|---|---|---|
| Healthy | Validate the live deployment, including the optional login check | `OK` / exit `0` | Passed |
| Missing deployment | Validate an empty temporary install directory | `UNKNOWN` / exit `3` | Passed |
| Controlled outage | Stop only the `misp-core` service | `CRITICAL` / exit `2` | Passed |
| Recovery | Restart `misp-core`, wait for heartbeat/schema readiness, and validate again | `OK` / exit `0` | Passed |

The controlled service stop occurred only on disposable validation infrastructure and was followed by an explicit recovery check.

## Output contracts exercised

For each applicable state, the independent validator executed and parsed:

- JSON;
- Nagios/Icinga plugin-style output;
- Checkmk local-check output;
- Prometheus text exposition.

It also checked:

- process exit code matches the normalized health status;
- stable JSON schema and required result fields;
- deterministic single-line plugin output;
- numeric, low-cardinality Prometheus metrics;
- absence of known sensitive deployment values and forbidden raw-state markers in emitted output.

Total monitoring scenario duration: **260 seconds**.

## Limitations

This validation did **not** use running Zabbix, Checkmk, Nagios/Icinga, or Prometheus servers. It establishes command behavior, parser compatibility, status transitions, and real-deployment failure detection—not end-to-end certification for those platforms.

`promtool` was not installed in this run, so Prometheus output was checked by the repository validator's built-in exposition parser. The validator will additionally invoke `promtool check metrics` automatically when that utility is available.

Real monitoring-platform configuration, agent execution context, discovery, ingestion, alert routing, dashboards, and upgrades remain community-testing work. See [Monitoring integrations](../monitoring.md#integration-validation-status) for the current evidence matrix and contribution request.

## Evidence handling

Raw execution logs remain local-only. This report intentionally excludes private infrastructure identifiers, deployment URLs, credentials, generated environment files, and raw logs.
