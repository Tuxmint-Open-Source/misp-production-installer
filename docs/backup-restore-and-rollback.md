# Backup, restore, and rollback

This document describes the backup, restore, and rollback contract for `misp-docker-lifecycle-manager`.

The restore workflow is intentionally restore-based rather than automatic rollback magic: operators keep a verified backup, recover from that backup with `restore.sh`, then verify the restored deployment.

## Backup creation

Create a backup with:

```bash
sudo ./installer/backup.sh --install-dir /opt/misp-docker
```

A backup includes:

- `misp.sql` — MariaDB database dump
- `misp-host-data.tar.gz` — MISP host-mounted data directories
- `misp-config.tar.gz` — generated deployment configuration such as `.env`, Compose override, and installer state
- `SHA256SUMS` — checksum manifest

Backups are sensitive. `misp-config.tar.gz` contains generated deployment secrets, and `misp.sql` can contain sensitive MISP data.

## Backup verification

Verify checksums from inside the backup directory:

```bash
cd /path/to/misp-backup-YYYYMMDDTHHMMSSZ
sha256sum -c SHA256SUMS
```

Also verify that backup files are stored with restrictive permissions and copied to the intended retention location.

Do not paste backup contents, `.env`, database dumps, or full raw logs into public issues.

## Restore procedure

Restore from a backup created by `backup.sh`:

```bash
sudo ./installer/restore.sh \
  --backup-dir /path/to/misp-backup-YYYYMMDDTHHMMSSZ \
  --install-dir /opt/misp-docker
```

By default, restore is conservative:

- `--backup-dir` is required
- `SHA256SUMS` is verified before restore
- the install directory is safety-checked
- destructive mode requires `--yes`
- interactive confirmation requires typing `RESTORE`
- use `--force` only for tested automation on disposable or clearly scoped hosts

Example non-interactive automation form after reviewing the target:

```bash
sudo ./installer/restore.sh \
  --backup-dir /path/to/misp-backup-YYYYMMDDTHHMMSSZ \
  --install-dir /opt/misp-docker \
  --yes \
  --force
```

`restore.sh` restores:

1. generated deployment configuration from `misp-config.tar.gz`
2. host-mounted data from `misp-host-data.tar.gz`
3. database contents from `misp.sql`

Then it starts the stack, waits for readiness, runs database updates/schema checks, and runs `doctor.sh`.

After restore, run:

```bash
sudo ./installer/doctor.sh --install-dir /opt/misp-docker
sudo ./installer/login-check.sh --install-dir /opt/misp-docker
```

## Restore validation evidence

Exact-tag validation for `v1.0.0-rc.3` passed after `restore.sh` was added. The restore drill exercised:

1. fresh install
2. creation of meaningful host-mounted state
3. `backup.sh` with generated config, host data, database dump, and checksums
4. destructive reset of the deployment scope
5. `restore.sh` from the backup
6. restored state verification
7. `doctor.sh`
8. `login-check.sh`

Public production-readiness claims for final releases still require exact release-tag validation.

## Restore-based rollback after failed update

`update.sh` creates a backup before applying changes. For rollback drills and production recovery planning, store the pre-update backup outside the deployment directory:

```bash
sudo ./installer/update.sh \
  --install-dir /opt/misp-docker \
  --backup-root /var/backups/misp
```

If an update fails after the pre-update backup is created:

1. stop repeated retries
2. preserve logs privately for diagnosis
3. identify the pre-update backup under the external backup root
4. verify `SHA256SUMS`
5. restore with `restore.sh`
6. run `doctor.sh`
7. run `login-check.sh`

A restore-based rollback drill passed for `v1.0.0-rc.3` by intentionally triggering an update failure after backup creation, then recovering with `restore.sh` from the pre-update backup.

## Reset behavior

Reset is intentionally conservative:

- dry-run by default
- explicit destructive confirmation required
- install directory safety checks required
- deployment-scoped Compose resources only
- Docker Engine remains installed

Example dry run:

```bash
sudo ./installer/reset-installation.sh --install-dir /opt/misp-docker
```

Use destructive reset only after reading the command output and confirming it targets the intended deployment.

## Failure evidence handling

If backup, restore, update, or rollback fails:

- keep raw logs private
- do not paste credentials, `.env`, database dumps, or full logs into public issues
- summarize command shapes, versions, expected result, and failure class
- redact secrets before sharing any snippets

## v1.0.0 gate

`v1.0.0-rc.3` includes exact-tag restore and rollback validation. The final `v1.0.0` tag must repeat restore and rollback validation before final `v1.0.0` is marked validated compatible.

## What to read next

- Return to the [documentation map](README.md).
- Follow the end-to-end lifecycle in [Operator guide](operator-guide.md).
- Review update behavior in [Upgrade path](upgrade-path.md).
- Review sensitive artifact handling in [Security](security.md).
