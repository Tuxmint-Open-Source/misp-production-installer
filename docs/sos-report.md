# Anonymous SOS reports

An SOS report is a public-safe diagnostic summary that helps maintainers understand and reproduce a bug without asking you to publish private deployment details.

Use it when you want to report a normal bug such as an install, update, backup, restore, rollback, doctor, status, or login-check problem.

Do **not** use a public SOS report for suspected security vulnerabilities. Use [`SECURITY.md`](../SECURITY.md) instead.

## Current status

The project includes `installer/sos-report.sh`, which generates a bounded Markdown report from allowlisted structured facts. It never copies raw helper, Docker, Compose, application, or system command output into the report. You should still review every line before sharing it.

## Before posting publicly

GitHub issues are public. Review every line before posting.

Never include:

- passwords, tokens, API keys, private keys, generated secrets, or `.env` contents;
- full `.installer-state.json` contents;
- private hostnames, internal domains, private IPs, VM IDs, topology, or access paths;
- raw logs that may contain deployment-specific details;
- raw Docker Compose config;
- database dumps, backup archives, backup contents, or generated configuration archives;
- MISP event data, attributes, feeds, organizations, users, API output, or browser screenshots containing private details.

Use placeholders such as:

```text
misp.example.com
admin@example.com
/opt/misp-docker
[REDACTED]
```

If you cannot explain the issue without sensitive detail, do not open a public issue. Use the private security-reporting path in [`SECURITY.md`](../SECURITY.md).

## What maintainers need

A useful public bug report answers these questions:

1. Which manager version or commit did you use?
2. Which workflow failed?
3. What command shape did you run, with sensitive values replaced?
4. What did you expect?
5. What happened instead?
6. What public-safe environment was involved?
7. Can the issue be reproduced on a fresh install?

## Generate a report

```bash
sudo ./installer/sos-report.sh --install-dir /opt/misp-docker --output ./misp-sos-report.md
less ./misp-sos-report.md
```

Use `--no-docker` if you want to avoid Docker/Compose checks:

```bash
./installer/sos-report.sh --no-docker --output ./misp-sos-report.md
```

Use `--no-health-commands` if version detection is acceptable but you do not want the report to run the bounded structured `healthcheck.sh` probe:

```bash
sudo ./installer/sos-report.sh --install-dir /opt/misp-docker --no-health-commands --output ./misp-sos-report.md
```

The generated v2 report contains only fixed enums, booleans, numeric counts, validated public component tags, restricted version fields, file-presence/mode facts, and allowlisted health statuses. It does not include raw command summaries or backup metadata. The health probe does not include the credential-bearing login check.

All Git, Docker, Compose, and health probes share one monotonic end-to-end deadline. The default is 20 seconds; set a different positive global budget with `--timeout SECONDS`. A probe that exhausts the remaining budget is reported as unavailable or unknown, and later probes are skipped rather than receiving fresh timeout windows.

The report is written atomically with mode `0600`; symlink output targets are refused. Review it manually before posting.

## Manual SOS report template

Copy this template into a GitHub bug issue and fill in only public-safe values.

```text
# MISP Docker Lifecycle Manager SOS Report

## Safety confirmation
I reviewed this report before posting and removed secrets, credentials, private hostnames/IPs, internal topology, raw logs, database dumps, backup contents, generated configuration, and deployment-specific data.

## Summary
- Manager version/ref: v1.1.0 or commit SHA
- Report format: manual-sos-v1
- Affected workflow: install | update | backup | restore | rollback | reset | doctor | status | login-check | documentation | other
- Reproducible on a fresh install: yes | no | unknown

## Environment
- OS family/version: Rocky Linux 9 | Debian 12 | Ubuntu 24.04 | other
- Architecture: x86_64 | arm64 | other
- Docker version: redacted-safe version string
- Docker Compose version: redacted-safe version string
- Exposure mode: direct | reverse-proxy | unknown

## Installation shape
- Install directory used: /opt/misp-docker or [REDACTED_PATH]
- Expected generated files exist: yes | no | unknown
- Sensitive file permissions checked: yes | no | unknown
- Upstream ref/component tags: public tags only, no private registry values

## Expected behavior
Describe what should have happened.

## Actual behavior
Describe what happened instead. Do not paste raw logs. Include only short sanitized error lines if needed.

## Sanitized command shape
Example:

sudo ./installer/install.sh \
  --install-dir /opt/misp-docker \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --admin-org ExampleOrg \
  --exposure reverse-proxy

## Public-safe output summary
- Command exit status: 0 | non-zero | unknown
- Doctor summary: passed | failed | not run | unknown
- Login-check summary: passed | failed | not run | unknown
- Containers expected/running/healthy/unhealthy: summary only, no raw logs
- Backup/restore state: summary only, no archive contents

## Redaction summary
- Hostnames/IPs redacted: yes | no | not applicable
- Emails redacted: yes | no | not applicable
- Secrets redacted: yes | no | not applicable
- Paths redacted: yes | no | not applicable
```

## Safe command examples

These commands usually produce useful public-safe version/status facts when you copy only the sanitized summary, not raw logs:

```bash
./installer/install.sh --version
./installer/doctor.sh --help
./installer/login-check.sh --help
./installer/get-current-misp-versions.sh --help
```

For an installed deployment, summarize the result of these commands instead of pasting full raw output if it contains deployment-specific values:

```bash
sudo ./installer/doctor.sh --install-dir /opt/misp-docker
sudo ./installer/login-check.sh --install-dir /opt/misp-docker --machine-readable
sudo ./installer/status.sh --install-dir /opt/misp-docker
```

If output includes real URLs, hostnames, IPs, paths, usernames, tokens, or internal details, replace them with placeholders before posting.

## Redaction guidance

| Sensitive input | Public replacement |
| --- | --- |
| private or public IP address | `[REDACTED_IP]` |
| real hostname or FQDN | `[REDACTED_HOST]` |
| URL with real host | `https://[REDACTED_HOST]` |
| email address | `[REDACTED_EMAIL]` |
| token/password-like value | `[REDACTED_SECRET]` |
| real home path or deployment-specific path | `[REDACTED_PATH]` |
| organization/user/event data from MISP | `[REDACTED_MISP_DATA]` |

Prefer over-redaction. Maintainers can ask follow-up questions if a safe detail is missing.

## Public issue or private security report?

Use a public bug issue when:

- the report can be fully sanitized;
- no vulnerability is suspected;
- no secret, private topology, private host, or raw sensitive output is needed;
- the issue is about normal behavior, docs, compatibility, or operator workflow.

Use private security reporting when:

- the bug exposes secrets or generated credentials;
- reset, restore, update, or rollback might affect the wrong target;
- command arguments may allow injection or unsafe shell behavior;
- logs or output reveal deployment-sensitive details;
- you are unsure whether public disclosure is safe.

## Maintainer triage checklist

When maintainers receive an SOS report, check:

1. Is it public-safe, or should it be moved to private security handling?
2. Which manager release/ref and workflow are affected?
3. Is the deployment model supported by the [support matrix](support-matrix.md)?
4. Is the affected release/component pair listed in [compatibility](compatibility.md)?
5. Are the reproduction steps specific enough to test with sanitized values?
6. Does the issue require a docs fix, code fix, validation follow-up, or security advisory?

Maintainers may use the [`needs-sos-report`](maintainer-workflow.md#sos-report-triage) label when a public bug needs an anonymous SOS report before it can be reproduced or classified.

## What to read next

- Open a normal bug: use the GitHub bug template.
- Unsure whether details are sensitive: read [`SECURITY.md`](../SECURITY.md).
- Contributing a fix: read [`CONTRIBUTING.md`](../CONTRIBUTING.md).
- Troubleshooting locally first: read [troubleshooting](troubleshooting.md).
