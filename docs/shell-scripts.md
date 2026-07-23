# Shell scripts reference

The `lifecycle/` directory contains Bash helpers for operating an official `MISP/misp-docker` deployment.

This page is the command reference. For the recommended human path, start with the [documentation map](README.md), then use [Getting started](getting-started.md) or the [Operator guide](operator-guide.md).

Most operators should use the main commands below. Internal helpers and thin Docker Compose wrappers exist so the main commands can stay small and reviewable; they are not a second supported user journey.

The legacy `installer/` path remains as compatibility wrappers that forward to `lifecycle/`. New examples use `lifecycle/`.

## Main commands

These operator-facing scripts support both `--help` and `--version`:

| Script | Purpose | Common use |
| --- | --- | --- |
| `prepare-host-rocky.sh` | Prepare a Rocky Linux host with Docker Engine and the Docker Compose plugin. | Fresh host setup. |
| `install.sh` | Install an official MISP Docker checkout with generated config and lifecycle defaults. | First install. |
| `update.sh` | Back up, update upstream/component tags, restart, run DB updates, and verify. | Safe component/update path. |
| `backup.sh` | Create database, host-data, generated-config, and checksum backup artifacts. | Pre-maintenance and scheduled backups. |
| `restore.sh` | Restore generated config, host data, and database from a `backup.sh` backup. | Disaster recovery and rollback drills. |
| `doctor.sh` | Check required config, Compose config, heartbeat, schema readiness, and service status. | Post-install/update verification. |
| `status.sh` | Show Docker Compose service status and MISP heartbeat. | Day-2 status checks. |
| `admin-credentials.sh` | Show the configured initial admin account; hide password unless explicitly requested. | Safe credential lookup. |
| `login-check.sh` | Perform a CSRF-aware Web UI login check without printing the password. | Readiness and login validation. |
| `sos-report.sh` | Generate a public-safe anonymous SOS report for bug reports. | Reproducible support diagnostics without raw logs/secrets. |
| `healthcheck.sh` | Run bounded monitoring-friendly health checks with stable exit codes and output formats. | Zabbix, Checkmk, Nagios/Icinga, Prometheus-style text output, and automation. |
| `get-current-misp-versions.sh` | Show upstream MISP Docker component versions and optionally compare local `.env`. | Version/compatibility review. |
| `reset-installation.sh` | Dry-run or remove a managed deployment scope. | Failed install cleanup or deliberate removal. |

## Internal/helper scripts

These scripts are used by the main commands or are thin Docker Compose wrappers. They may not have standalone `--help`/`--version` output and should normally be called only when the operator guide or troubleshooting docs tell you to do so. In particular, wrapper scripts such as `up.sh`, `down.sh`, `pull.sh`, and `logs.sh` expect a prepared install directory instead of acting like self-contained CLI entry points.

| Script | Role |
| --- | --- |
| `lib.sh` | Shared Bash functions. Source only; do not run directly. |
| `fetch-upstream.sh` | Helper for fetching official `MISP/misp-docker`. |
| `generate-env.sh` | Helper for generating deployment `.env`. |
| `render-compose.sh` | Helper for rendering `docker-compose.override.yml`. |
| `bootstrap-tls.sh` | Helper for bootstrap self-signed TLS material. |
| `validate.sh` | Helper for validating generated config/Compose state. |
| `up.sh`, `down.sh`, `pull.sh`, `logs.sh` | Thin Docker Compose wrappers for a prepared install directory. |

## Shared conventions

Most main commands accept:

```bash
--install-dir /opt/misp-docker
--help
--version
```

`--install-dir` points to the official `MISP/misp-docker` checkout managed by this project. Examples use `/opt/misp-docker`; adjust only if you intentionally manage a different deployment scope.

## First install

```bash
sudo ./lifecycle/install.sh \
  --install-dir /opt/misp-docker \
  --upstream-ref master \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --admin-org ExampleOrg \
  --timezone Europe/Zurich \
  --exposure reverse-proxy
```

`install.sh` performs the full deployment workflow:

1. optionally prepares a Rocky Linux host for Docker;
2. clones or updates the official `MISP/misp-docker` upstream checkout;
3. generates a secret-bearing `.env` from upstream `template.env`;
4. renders `docker-compose.override.yml` for the selected exposure mode;
5. optionally creates bootstrap self-signed TLS material;
6. validates Compose config;
7. starts containers;
8. runs MISP DB updates;
9. checks schema readiness;
10. waits for the upstream interactive-login readiness marker;
11. runs `doctor.sh`.

Use `--prepare-host` if you also want `install.sh` to run host preparation on Rocky Linux. Host preparation rejects unsupported OS families and architectures before package changes; run `prepare-host-rocky.sh --allow-unsupported-host` separately only for expert testing outside the support matrix.

`--base-url`, `--admin-email`, and `--admin-org` are required. Generated environment values are validated before `.env` is written.

## Exposure modes

| Mode | Bind behavior | Intended use |
| --- | --- | --- |
| `reverse-proxy` | Local ports such as `127.0.0.1:8080` and `127.0.0.1:8443`. | Default production-oriented shape behind an external reverse proxy. |
| `direct-qa` | Host ports `0.0.0.0:80` and `0.0.0.0:443`. | Disposable validation and controlled QA only. |

Do not use `direct-qa` as the long-term public exposure model.

## Backup artifacts

`backup.sh` creates a fresh unpredictable backup directory under the selected backup root. It briefly quiesces only application services that were already running, validates the finished backup, and restarts those services before success. Prefer `--backup-root /var/backups/misp` or another protected path outside the deployment directory.

The directory contains:

| Artifact | Meaning | Sensitivity |
| --- | --- | --- |
| `misp.sql` | MariaDB database dump. | Sensitive MISP data. |
| `misp-host-data.tar.gz` | Host-mounted MISP data directories. | Sensitive operational data. |
| `misp-config.tar.gz` | Generated deployment configuration such as `.env`, Compose override, and manager state. | Sensitive secrets/configuration. |
| `SHA256SUMS` | Checksum manifest for integrity verification. | Public by itself, but keep with backup set. |

Treat backups as confidential. Do not paste backup contents, `.env`, database dumps, or full raw logs into public issues.

## Restore and rollback

Restore requires an explicit backup directory:

```bash
sudo ./lifecycle/restore.sh \
  --backup-dir /path/to/misp-backup-RANDOM_SUFFIX \
  --install-dir /opt/misp-docker
```

By default, restore is conservative:

- `--backup-dir` is required;
- `SHA256SUMS` is verified;
- the install directory is safety-checked;
- destructive mode requires `--yes`;
- interactive confirmation requires typing `RESTORE`;
- `--force` should be used only for tested automation on disposable or clearly scoped hosts.

For restore-based rollback drills, keep the pre-update backup outside the deployment directory:

```bash
sudo ./lifecycle/update.sh \
  --install-dir /opt/misp-docker \
  --backup-root /var/backups/misp
```

See [Backup, restore, and rollback](backup-restore-and-rollback.md) for the full recovery procedure.

## Destructive commands

### `reset-installation.sh`

Dry-run first:

```bash
sudo ./lifecycle/reset-installation.sh --install-dir /opt/misp-docker
```

Destructive reset:

```bash
sudo ./lifecycle/reset-installation.sh --install-dir /opt/misp-docker --yes
```

The script asks for confirmation and requires typing `DELETE` unless `--force` is used. It removes only the selected deployment scope and Docker Compose resources. Docker Engine itself is not removed.

### `restore.sh`

Restore is destructive for the selected install directory and Compose project because it replaces deployment state from backup. Use `--force` only after testing the exact command shape and target scope.

## Login and credentials

Check login readiness without printing the password:

```bash
sudo ./lifecycle/login-check.sh --install-dir /opt/misp-docker
```

Machine-readable diagnostics for automation:

```bash
sudo ./lifecycle/login-check.sh --install-dir /opt/misp-docker --machine-readable
```

Show configured admin account without printing the password:

```bash
sudo ./lifecycle/admin-credentials.sh --install-dir /opt/misp-docker
```

Print the initial password only on a trusted terminal:

```bash
sudo ./lifecycle/admin-credentials.sh --install-dir /opt/misp-docker --show-password
```

## Monitoring contract

Use the monitoring healthcheck for bounded probes with stable exit codes and machine-readable output:

```bash
sudo ./lifecycle/healthcheck.sh --install-dir /opt/misp-docker --format json --timeout 20
```

See [Monitoring](monitoring.md) for formats, exit codes, JSON schema, and integration examples.

## Version checks

Show upstream-declared component versions:

```bash
./lifecycle/get-current-misp-versions.sh
```

Compare local `.env` metadata and runtime image pins:

```bash
./lifecycle/get-current-misp-versions.sh --install-dir /opt/misp-docker
```

## Anonymous SOS reports

Generate a public-safe bug-report summary without raw logs, `.env` contents, backups, database dumps, or generated configuration:

```bash
sudo ./lifecycle/sos-report.sh --install-dir /opt/misp-docker --output ./misp-sos-report.md
```

By default, the report runs the bounded non-login healthcheck and retains only allowlisted status enums and counts. It never copies raw helper, Docker, Compose, application, or system command output. Use `--no-health-commands` to skip the structured health probe, or `--no-docker` to avoid Docker/Compose/version checks entirely:

```bash
./lifecycle/sos-report.sh --no-docker --output ./misp-sos-report.md
```

The report may also include backup presence/count metadata, but never backup names, backup paths, backup contents, database dumps, generated configuration archives, or checksums.

Review the generated file before posting it publicly. Use [`docs/sos-report.md`](sos-report.md) for the reporting workflow and redaction guidance.

## Safety notes

- `.env` contains secrets and must not be committed.
- `.installer-state.json` is deployment metadata and should not be committed.
- `backup.sh` may require `sudo` because some upstream bind mounts are root-owned.
- `update.sh` always calls `backup.sh` before changing upstream code.
- MISP DB updates are run with the official Cake command as `www-data`.
- Public issues and validation summaries must omit private hostnames, IPs, credentials, raw logs, and topology.

## What to read next

- Return to the [documentation map](README.md) and choose the user/operator path.
- Follow the normal lifecycle in [Operator guide](operator-guide.md).
- Use [Getting started](getting-started.md) for a first install.
- Use [Troubleshooting](troubleshooting.md) when a command fails.
