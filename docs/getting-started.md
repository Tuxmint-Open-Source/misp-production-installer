# Getting started

This guide gives you a first successful path through MISP Docker Lifecycle Manager.

It is intentionally shorter than the full [operator guide](operator-guide.md). Use it to understand the flow, then read the production and recovery docs before relying on a deployment.

> [!CAUTION]
> The project is still marked **not production ready** until final `v1.0.0` is tagged and validated separately. Use the current release candidate for testing and review, not for unattended production use.

## Before you begin

Read the [support matrix](support-matrix.md) first if you are unsure whether this project fits your environment.

This guide assumes:

- one Linux host dedicated to a single-server Docker deployment;
- Docker and Docker Compose are available or can be installed by the host-preparation helper;
- you will run lifecycle commands with `sudo`;
- your public URL is a real hostname such as `https://misp.example.com`;
- you understand that generated secrets and runtime `.env` files must not be committed.

## 1. Clone the manager

```bash
git clone https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager.git
cd misp-docker-lifecycle-manager
```

For release-candidate testing, use the release tag you want to evaluate:

```bash
git checkout v1.0.0-rc.2
```

## 2. Prepare a Rocky Linux host

```bash
sudo ./installer/prepare-host-rocky.sh
```

By default, this does **not** add your user to the Docker group. Docker group membership is root-equivalent on the host. Use `sudo` unless you intentionally accept that trade-off.

If your host is already prepared, you can skip this step.

## 3. Install MISP behind a reverse proxy

The default deployment mode expects a reverse proxy in front of MISP.

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

In `reverse-proxy` mode, the generated MISP deployment listens locally and expects your reverse proxy to publish the external HTTPS hostname.

Typical local targets:

```text
http://127.0.0.1:8080
https://127.0.0.1:8443
```

For production planning details, read [Production deployment guide](production-deployment.md).

## 4. Verify the deployment

Run the doctor check:

```bash
sudo ./installer/doctor.sh --install-dir /opt/misp-docker
```

Run the login check:

```bash
sudo ./installer/login-check.sh --install-dir /opt/misp-docker
```

Show the generated admin account without printing the password:

```bash
sudo ./installer/admin-credentials.sh --install-dir /opt/misp-docker
```

Show the password only when you are on a trusted console:

```bash
sudo ./installer/admin-credentials.sh \
  --install-dir /opt/misp-docker \
  --show-password
```

## 5. Check component versions

Check the upstream-declared MISP component tags:

```bash
./installer/get-current-misp-versions.sh
```

Compare a local deployment against upstream:

```bash
./installer/get-current-misp-versions.sh --install-dir /opt/misp-docker
```

Compatibility is tracked as a pair: manager release/ref plus official MISP Docker component tags. See [Compatibility](compatibility.md).

## 6. Take a backup before changing things

```bash
sudo ./installer/backup.sh --install-dir /opt/misp-docker
```

Backups include database dump, host data, generated deployment configuration, and checksums. Read [Backup, restore, and rollback](backup-restore-and-rollback.md) before depending on backups operationally.

## 7. Know where to go next

- Follow the full lifecycle story: [Operator guide](operator-guide.md).
- Plan a real deployment: [Production deployment guide](production-deployment.md).
- Update safely: [Upgrade path](upgrade-path.md).
- Recover from mistakes: [Backup, restore, and rollback](backup-restore-and-rollback.md).
- Debug failures: [Troubleshooting](troubleshooting.md).
