# Production deployment guide

This guide describes the supported production deployment workflow for `misp-docker-lifecycle-manager` within the documented `v1.0.0` scope.

`v1.0.0` is the first stable release line for the documented single-server Docker lifecycle-manager scope and is validated compatible with the documented MISP Docker component set.

## Supported production shape

The validated production deployment shape is:

- one Linux server
- Docker Engine and Docker Compose plugin
- official `MISP/misp-docker` checkout managed in an install directory such as `/opt/misp-docker`
- generated `.env` and `docker-compose.override.yml`
- external reverse proxy terminating public HTTPS
- manager repository used for lifecycle operations, but not required at runtime by MISP itself

## Prerequisites

Before installation, prepare:

- a supported host OS from [`support-matrix.md`](support-matrix.md)
- root or sudo access
- working DNS for the intended public MISP URL
- firewall rules allowing the chosen external access path
- enough disk for Docker images, database growth, attachments, logs, and backups
- an email address for the initial MISP administrator
- a backup location and retention plan

## Recommended exposure model

For production-like use, prefer reverse-proxy mode:

```bash
sudo ./installer/install.sh \
  --install-dir /opt/misp-docker \
  --upstream-ref master \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --admin-org ExampleOrg \
  --timezone Europe/Zurich \
  --exposure reverse-proxy
```

The reverse proxy should forward to the local HTTPS endpoint documented by the installer output and overlay docs.

Direct-QA mode is useful for validation and controlled QA. It is not the recommended long-term public exposure model.

## Host preparation

Run host preparation on a supported fresh host:

```bash
sudo ./installer/prepare-host-rocky.sh
```

By default, host preparation does not add the current user to the Docker group. This is intentional because Docker group membership is root-equivalent on the host.

## Post-install verification

After installation, run:

```bash
sudo ./installer/doctor.sh --install-dir /opt/misp-docker
sudo ./installer/login-check.sh --install-dir /opt/misp-docker
sudo ./installer/admin-credentials.sh --install-dir /opt/misp-docker
```

`admin-credentials.sh` hides the generated password by default. Use password-revealing options only on a trusted terminal.

## Updates

Use the update helper from a known manager release:

```bash
sudo ./installer/update.sh --install-dir /opt/misp-docker
```

The update workflow creates a backup before changing the running stack, synchronizes official component tags, pulls images, restarts services, runs MISP database updates, waits for readiness, and runs `doctor.sh`.

For explicit component versions:

```bash
sudo ./installer/update.sh \
  --install-dir /opt/misp-docker \
  --core-tag v2.5.43 \
  --modules-tag v3.0.8 \
  --guard-tag v1.2
```

Use only official upstream component tags.

## Backups

Create a backup before planned maintenance and on a regular schedule:

```bash
sudo ./installer/backup.sh --install-dir /opt/misp-docker
```

Backups are sensitive. Treat database dumps and host-data archives as confidential because they can contain operational data, MISP event data, user data, and generated secrets.

See [`backup-restore-and-rollback.md`](backup-restore-and-rollback.md) for the validated restore workflow and restore-based rollback procedure.

## No-lock-in operation

The generated deployment remains a normal official `MISP/misp-docker` checkout. If this installer repository is removed after installation, operators can still inspect and manage the generated deployment with normal Docker Compose commands from the install directory.

No-lock-in behavior was included in `v1.0.0` release-tag validation and remains a required scenario for future releases that affect lifecycle behavior.

## Future validation

The `v1.0.0` tag passed restore, browser-login, and restore-based rollback validation. Future upstream component sets or expanded deployment scopes require separate validation before compatibility is claimed.

## What to read next

- Return to the [documentation map](README.md).
- Use [Getting started](getting-started.md) for the first install path.
- Use [Operator guide](operator-guide.md) for day-2 lifecycle flow.
- Review recovery in [Backup, restore, and rollback](backup-restore-and-rollback.md).
