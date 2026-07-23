# Operator guide

This guide is the red line through the repository. It explains the normal lifecycle of a MISP deployment managed by MISP Docker Lifecycle Manager and points to detailed docs when you need them.

## 1. Understand the model

MISP Docker Lifecycle Manager does not replace MISP and does not fork `MISP/misp-docker`.

It manages a normal official MISP Docker checkout by adding:

- generated `.env` values and secrets;
- generated Compose overrides;
- install, update, backup, restore, status, doctor, login-check, and reset helpers;
- compatibility and validation documentation;
- operator guidance around safe lifecycle actions.

The deployment remains no-lock-in: if the manager repository is removed after installation, the install directory remains a normal official `MISP/misp-docker` checkout that can be operated manually with Docker Compose.

Read more: [Architecture](architecture.md), [Support matrix](support-matrix.md).

## 2. Decide whether this fits your use case

The intended scope is a single-server Docker deployment managed by a human operator.

Good fit:

- one host;
- official MISP Docker components;
- Docker Compose lifecycle;
- reverse proxy in front of MISP;
- backup-first updates;
- restore-based recovery.

Not the current scope:

- Kubernetes;
- high availability;
- multi-node orchestration;
- custom MISP image builds;
- replacing the official MISP Docker project.

Read more: [Support matrix](support-matrix.md).

## 3. Prepare the host

For Rocky Linux hosts, use:

```bash
sudo ./lifecycle/prepare-host-rocky.sh
```

The helper is intentionally conservative about Docker group membership because Docker group access is effectively root-equivalent. Use `sudo` unless you intentionally accept that trade-off. It rejects hosts outside the supported Rocky-compatible Linux and x86_64 matrix before package changes; `--allow-unsupported-host` is an expert testing override only.

Read more: [Getting started](getting-started.md), [Security](security.md).

## 4. Install the deployment

The normal production-oriented path is reverse-proxy mode:

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

The manager clones official upstream MISP Docker into the install directory, generates local configuration, pins component image tags, starts the stack, waits for readiness, runs database updates, and verifies the result. The base URL, administrator email, and organization are required and validated before the install directory is changed. With `--no-start`, the manager prepares and validates configuration but reports that startup and runtime checks were skipped.

Read more: [Getting started](getting-started.md), [Production deployment guide](production-deployment.md).

## 5. Verify readiness before using the UI

After install or update, verify the deployment before handing it to users:

```bash
sudo ./lifecycle/doctor.sh --install-dir /opt/misp-docker
sudo ./lifecycle/login-check.sh --install-dir /opt/misp-docker
sudo ./lifecycle/admin-credentials.sh --install-dir /opt/misp-docker
```

The login check is designed not to print the password. The credential helper hides the password unless `--show-password` is explicitly requested.

Read more: [Troubleshooting](troubleshooting.md), [Security](security.md).

## 6. Operate day to day

Useful checks:

```bash
sudo ./lifecycle/status.sh --install-dir /opt/misp-docker
./lifecycle/get-current-misp-versions.sh --install-dir /opt/misp-docker
```

The status and version checks help you understand what is running locally and what official upstream currently declares. For integration with Zabbix, Checkmk, Nagios/Icinga, Prometheus-style text output, or automation, use the monitoring contract.

Read more: [Monitoring](monitoring.md), [Upgrade path](upgrade-path.md), [Compatibility](compatibility.md).

## 7. Update safely

The update helper is backup-first:

```bash
sudo ./lifecycle/update.sh --install-dir /opt/misp-docker
```

For rollback drills, keep the pre-update backup outside the deployment directory:

```bash
sudo ./lifecycle/update.sh \
  --install-dir /opt/misp-docker \
  --backup-root /var/backups/misp
```

After update, verify again with `doctor.sh` and `login-check.sh`.

Read more: [Upgrade path](upgrade-path.md), [Backup, restore, and rollback](backup-restore-and-rollback.md).

## 8. Back up before risky changes

```bash
sudo ./lifecycle/backup.sh \
  --install-dir /opt/misp-docker \
  --backup-root /var/backups/misp
```

Use a protected backup root outside the deployment directory so reset and failed-update recovery cannot remove the backup with the deployment. The backup helper briefly stops only running application services, captures the database and host data consistently, validates checksums and archive structure, then restarts those services.

Backups include:

- database dump;
- host data;
- generated deployment configuration;
- checksums.

Store backups somewhere protected. They may contain sensitive operational data and secrets.

Read more: [Backup, restore, and rollback](backup-restore-and-rollback.md), [Security](security.md).

## 9. Restore and recover

Restore from a backup directory:

```bash
sudo ./lifecycle/restore.sh \
  --backup-dir /path/to/misp-backup-RANDOM_SUFFIX \
  --install-dir /opt/misp-docker \
  --yes
```

Restore is intentionally explicit because it can overwrite deployment state. It verifies checksums, restores generated config and host data, imports the database, starts the stack, waits for readiness, and runs verification.

The same restore workflow is used for restore-based rollback after a failed update.

Read more: [Backup, restore, and rollback](backup-restore-and-rollback.md).

## 10. Reset or remove a managed deployment

Start with a dry run:

```bash
sudo ./lifecycle/reset-installation.sh --install-dir /opt/misp-docker
```

Destructive reset requires explicit confirmation and checks for lifecycle-manager markers. Docker Engine itself is not removed.

Read more: [Shell scripts reference](shell-scripts.md), [Security](security.md).

## 11. Check validation evidence

Compatibility is not claimed generically. It is tracked as:

```text
manager release/ref × official MISP Docker component set = status
```

Read the compatibility docs before assuming a release has been validated for a given MISP component set.

Read more: [Compatibility](compatibility.md), [Validation matrix](validation/matrix.md), [Production readiness](production-readiness.md).

## 12. Troubleshoot with a path

If something fails, start with:

```bash
sudo ./lifecycle/doctor.sh --install-dir /opt/misp-docker
sudo ./lifecycle/login-check.sh --install-dir /opt/misp-docker
sudo ./lifecycle/status.sh --install-dir /opt/misp-docker
```

Then follow [Troubleshooting](troubleshooting.md). Common categories are invalid URLs, reverse-proxy mismatch, not-yet-ready login, component tag problems, Docker/host issues, and credential handling mistakes.

## What to read next

- First install: [Getting started](getting-started.md).
- Real deployment planning: [Production deployment guide](production-deployment.md).
- Recovery planning: [Backup, restore, and rollback](backup-restore-and-rollback.md).
- Exact command options: [Shell scripts reference](shell-scripts.md).
