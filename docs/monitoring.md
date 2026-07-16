# Monitoring

MISP Docker Lifecycle Manager manages more than first install. Operators also need a stable way to ask: "is this managed deployment healthy enough for production monitoring?"

This page defines the monitoring contract for the lifecycle-manager healthcheck interface. The command is designed for modern monitoring systems while keeping output stable, bounded, and safe to copy into dashboards or tickets.

## Scope

The monitoring interface is for a single-server Docker Compose deployment managed by this project.

It should help monitoring systems detect whether the lifecycle-managed deployment is operational without exposing secrets or raw diagnostic data.

It is not intended to replace:

- deep troubleshooting with [`doctor.sh`](shell-scripts.md#post-install-and-update-verification);
- public-safe support diagnostics with [`sos-report.sh`](sos-report.md);
- MISP application-level business monitoring;
- external reverse-proxy, TLS, DNS, mail-delivery, or SIEM monitoring.

## Command

The monitoring command is:

```bash
sudo ./installer/healthcheck.sh --install-dir /opt/misp-docker
```

Options:

```text
--install-dir PATH
--format text|json|nagios|checkmk|prometheus
--checks CHECKS
--timeout SECONDS
--strict-tls
--no-login
--version
--help
```

## Status contract

The healthcheck command uses monitoring-plugin compatible exit codes:

| Exit code | Status | Meaning |
| ---: | --- | --- |
| `0` | OK | Required deployment checks are healthy. |
| `1` | WARNING | The deployment is usable but an operator should investigate a degraded or optional condition. |
| `2` | CRITICAL | A required service or readiness check failed. |
| `3` | UNKNOWN | The healthcheck could not determine health because of local execution, permission, Docker, or configuration problems. |

Examples:

| Condition | Expected status |
| --- | --- |
| Compose config validates, expected services are running, MISP heartbeat works, schema is ready | OK |
| Backup freshness threshold exceeded, optional login check skipped, or version drift detected | WARNING |
| Compose config invalid, MISP core stopped, heartbeat fails, schema not ready after timeout | CRITICAL |
| Install directory missing, Docker unavailable, permission denied, unreadable state | UNKNOWN |

The command should finish within the configured timeout and avoid unbounded network waits.

## Check IDs

The command supports a small, stable set of check identifiers:

| Check ID | Purpose | Default |
| --- | --- | --- |
| `compose-config` | Validate generated Docker Compose config. | enabled |
| `compose-services` | Confirm expected Compose services are present and running. | enabled |
| `misp-heartbeat` | Query the container-local MISP heartbeat endpoint. | enabled |
| `schema-ready` | Confirm schema readiness required by login-dependent workflows. | enabled |
| `login` | Perform CSRF-aware login check without printing the password. | optional |
| `backup-freshness` | Reserved warning check for future backup freshness thresholds. | optional |
| `version-drift` | Reserved warning check for future local/upstream component drift reporting. | optional |

Login should not be mandatory for the fastest default probe. It is useful as a deeper check, but it reads credentials and performs a real web login flow, so operators should enable it deliberately.

## Output formats

### Human text

The default text output should be concise and safe for terminals:

```text
OK - MISP core healthy, schema ready, 5/5 services running | services_running=5 services_expected=5
```

### Nagios/Icinga style

Nagios-compatible output should keep the first line stable:

```text
OK - MISP lifecycle health OK | services_running=5 services_expected=5 checks_ok=4 checks_warning=0 checks_critical=0
```

### JSON

JSON output should use a stable schema name so scripts can reject incompatible changes:

```json
{
  "schema": "misp-docker-lifecycle-manager-health-v1",
  "status": "ok",
  "exit_code": 0,
  "summary": "MISP core healthy and schema ready",
  "checks": [
    {
      "id": "compose-config",
      "status": "ok",
      "summary": "Compose config validates"
    },
    {
      "id": "misp-heartbeat",
      "status": "ok",
      "summary": "Heartbeat endpoint responded"
    }
  ],
  "metrics": {
    "services_running": 5,
    "services_expected": 5
  }
}
```

JSON output must not include generated secrets, raw `.env` values, backup names, private paths, raw URLs containing sensitive data, raw logs, MISP event data, MISP user data, MISP organisation data, or API output.

### Checkmk local check

Checkmk local-check output should be one line per service check:

```text
0 "misp_lifecycle_health" services_running=5;5;4 MISP core healthy and schema ready
```

### Prometheus text format

Prometheus text output can be useful for simple scraping or textfile collectors, but it must avoid high-cardinality labels.

Example:

```text
# HELP misp_lifecycle_health_status Overall MISP lifecycle manager health status, 1 ok, 0 not ok.
# TYPE misp_lifecycle_health_status gauge
misp_lifecycle_health_status 1
# HELP misp_lifecycle_services_running Number of expected Compose services currently running.
# TYPE misp_lifecycle_services_running gauge
misp_lifecycle_services_running 5
```

Do not expose hostnames, email addresses, install paths, backup names, URLs, or organisation names as metric labels.

## Zabbix example

A Zabbix agent can call the healthcheck through a `UserParameter`:

```text
UserParameter=misp.lifecycle.health,sudo /path/to/misp-docker-lifecycle-manager/installer/healthcheck.sh --install-dir /opt/misp-docker --format json --timeout 20
```

Recommended approach:

1. Use one item for the overall status or exit code.
2. Add dependent items for selected JSON fields if needed.
3. Keep triggers based on `status` or `exit_code`, not free-form text.
4. Restrict sudoers to the exact healthcheck command if sudo is required.

## Checkmk example

A Checkmk local check can call the Checkmk format:

```bash
#!/usr/bin/env bash
sudo /path/to/misp-docker-lifecycle-manager/installer/healthcheck.sh \
  --install-dir /opt/misp-docker \
  --format checkmk \
  --timeout 20
```

The output should be a single local-check line such as:

```text
0 "misp_lifecycle_health" services_running=5;5;4 MISP core healthy and schema ready
```

## Nagios/Icinga example

Nagios/Icinga-compatible usage should rely on the process exit code:

```bash
sudo /path/to/misp-docker-lifecycle-manager/installer/healthcheck.sh \
  --install-dir /opt/misp-docker \
  --format nagios \
  --timeout 20
```

The first output line should contain the status, summary, and optional performance data.

## systemd or cron example

For lightweight local monitoring, run the command on a timer and alert on non-zero exit codes:

```bash
sudo ./installer/healthcheck.sh --install-dir /opt/misp-docker --format text --timeout 20
```

Use the JSON format if another local tool ingests the result.

## Security and privacy

Monitoring output is often copied into tickets, dashboards, alerts, chat systems, and incident timelines. Treat it as public-adjacent output.

The healthcheck command must not print:

- passwords, API keys, session cookies, CSRF tokens, private keys, or generated secrets;
- raw `.env` contents;
- raw `.installer-state.json` contents;
- backup names, backup paths, checksums, database dumps, or generated config archives;
- raw logs;
- MISP event, attribute, user, organisation, feed, or API data;
- private hostnames, IP addresses, or deployment topology unless a future option explicitly documents that trade-off.

Prefer summaries and counts over raw values.

## Performance guidance

Monitoring checks should be bounded and cheap:

- default timeout should be short enough for frequent monitoring;
- avoid repeated full login checks unless explicitly enabled;
- avoid backup scans that walk large trees by default;
- avoid commands that restart, update, pull, migrate, or otherwise mutate the deployment;
- treat destructive or state-changing workflows as out of scope for monitoring.

## Troubleshooting monitoring results

| Status | First action |
| --- | --- |
| WARNING | Read the check summary, then run `doctor.sh` if the warning is not expected. |
| CRITICAL | Run `doctor.sh`, then inspect service status and logs using the troubleshooting guide. |
| UNKNOWN | Check permissions, Docker availability, the install directory, and whether the command is being run with the intended user/sudo policy. |

Useful follow-up commands:

```bash
sudo ./installer/doctor.sh --install-dir /opt/misp-docker
sudo ./installer/status.sh --install-dir /opt/misp-docker
sudo ./installer/login-check.sh --install-dir /opt/misp-docker --machine-readable
```

## What to read next

- [Documentation](README.md)
- [Shell scripts reference](shell-scripts.md)
- [Operator guide](operator-guide.md)
- [Troubleshooting](troubleshooting.md)
- [Anonymous SOS reports](sos-report.md)
- [Production readiness](production-readiness.md)
