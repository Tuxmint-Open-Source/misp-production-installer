# Shell scripts

The `installer/` directory contains small operator scripts. They are intentionally plain Bash so they can run on a minimal Rocky Linux host.

All main scripts support:

```bash
--help
--version
```

## First install

```bash
./installer/install.sh \
  --install-dir /opt/misp-docker \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --admin-org ExampleOrg \
  --exposure reverse-proxy \
  --bootstrap-tls
```

`install.sh` performs the full deployment workflow:

1. Fetch official `MISP/misp-docker`.
2. Generate `.env` with secrets and production defaults.
3. Render `docker-compose.override.yml`.
4. Optionally create bootstrap TLS material.
5. Validate Compose config.
6. Pull and start containers.
7. Wait for MISP core readiness.
8. Run MISP DB updates.
9. Verify schema readiness.
10. Run `doctor.sh`.

Use `--prepare-host` if you also want the script to install Docker on Rocky Linux.

## Day-2 scripts

| Script | Purpose |
| --- | --- |
| `prepare-host-rocky.sh` | Install Docker Engine and Compose plugin on Rocky Linux. |
| `validate.sh` | Validate `.env` and Docker Compose config. |
| `doctor.sh` | Run health/readiness checks after install or update. |
| `status.sh` | Show Compose service status and heartbeat. |
| `backup.sh` | Create DB dump, host-data archive, and checksums. |
| `reset-installation.sh` | Remove a failed install: containers, networks, named volumes, and generated files; Docker itself stays installed. |
| `update.sh` | Backup first, update official upstream, restart, run DB updates, then doctor. |
| `logs.sh` | Follow or print Docker Compose logs. |
| `up.sh` / `down.sh` / `pull.sh` | Thin wrappers around Docker Compose for routine operations. |

## Reset a failed install

If a first install fails halfway, for example because the partition ran full, use the reset script before trying again.

First inspect the dry-run:

```bash
./installer/reset-installation.sh --install-dir /opt/misp-docker
```

Then run the destructive reset. The script asks for interactive confirmation and requires typing `DELETE`:

```bash
./installer/reset-installation.sh --install-dir /opt/misp-docker --yes
```

Docker Engine is not removed. The reset targets only the selected MISP install directory and Docker Compose resources for that deployment.

## Exposure modes

### `reverse-proxy`

Default mode. MISP binds to localhost:

```text
127.0.0.1:8080
127.0.0.1:8443
```

Put Caddy, Nginx, Traefik, HAProxy, or another reverse proxy in front of it.

### `direct-qa`

Lab-only mode. MISP binds directly to:

```text
0.0.0.0:80
0.0.0.0:443
```

Use this for disposable QA environments, not internet-facing production.

## Safety notes

- `.env` contains secrets and must not be committed.
- `backup.sh` may require `sudo` because some upstream bind mounts are root-owned.
- `update.sh` always calls `backup.sh` before changing upstream code.
- MISP DB updates are run with the official Cake command as `www-data`.
