#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Create a filesystem + database backup for a MISP Docker deployment.

Usage:
  ./installer/backup.sh [options]

What this script backs up:
  - MariaDB dump written to misp.sql
  - MISP host-mounted data directories archived as misp-host-data.tar.gz
  - generated deployment configuration archived as misp-config.tar.gz
  - SHA256SUMS for integrity verification

Options:
  --install-dir PATH   Deployment directory (default: /opt/misp-docker)
  --backup-root PATH   Backup output directory (default: INSTALL_DIR/backups)
  -h, --help           Show this help
  --version            Show manager version

Note:
  Some upstream bind mounts are owned by root inside containers. The script uses
  sudo for the host-data archive and then gives the archive back to the operator.
EOF
}

INSTALL_DIR="/opt/misp-docker"
BACKUP_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --backup-root) BACKUP_ROOT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

[[ -f "$INSTALL_DIR/.env" ]] || fatal "$INSTALL_DIR/.env missing"
BACKUP_ROOT="${BACKUP_ROOT:-$INSTALL_DIR/backups}"
umask 077
mkdir -p "$BACKUP_ROOT"
python3 - "$BACKUP_ROOT" "$(id -u)" "${SUDO_UID:-}" <<'PY'
import os
import stat
import sys
from pathlib import Path
root = Path(sys.argv[1])
info = root.lstat()
allowed_owners = {int(value) for value in sys.argv[2:] if value}
if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
    raise SystemExit('backup root must be a non-symlink directory')
if info.st_uid not in allowed_owners:
    raise SystemExit('backup root is not owned by the invoking operator or root process')
if info.st_mode & 0o022:
    raise SystemExit('backup root must not be group- or world-writable')
PY
out="$(mktemp -d --tmpdir="$BACKUP_ROOT" 'misp-backup-XXXXXXXX')"
chmod 700 "$out"
complete=false
trap 'if [[ "$complete" != true ]]; then rm -rf -- "$out"; fi' EXIT

# Database backup: single-transaction keeps the dump consistent without a long
# global lock for typical InnoDB tables.
compose_cmd "$INSTALL_DIR" exec -T db sh -lc '
  umask 077
  cfg="$(mktemp)"
  trap '\''rm -f "$cfg"'\'' EXIT
  printf "[client]\nuser=%s\npassword=%s\n" "$MYSQL_USER" "$MYSQL_PASSWORD" > "$cfg"
  mariadb-dump --defaults-extra-file="$cfg" --single-transaction --quick "$MYSQL_DATABASE"
' > "$out/misp.sql"

# Host-data backup: these directories contain MISP files, generated configs,
# logs, TLS material, GnuPG state, and optional customizations.
(cd "$INSTALL_DIR" && { sudo tar --xattrs --selinux -czf "$out/misp-host-data.tar.gz" configs logs files ssl gnupg custom guard 2>/dev/null || sudo tar -czf "$out/misp-host-data.tar.gz" configs logs files ssl gnupg custom guard; })
sudo chown "$(id -u):$(id -g)" "$out/misp-host-data.tar.gz"

# Generated deployment configuration: keep this separate from host data so a
# restore can reproduce the exact runtime settings and secrets used by the DB.
# This archive is sensitive because it contains .env.
(cd "$INSTALL_DIR" && tar -czf "$out/misp-config.tar.gz" .env docker-compose.override.yml .installer-state.json 2>/dev/null || tar -czf "$out/misp-config.tar.gz" .env docker-compose.override.yml)
(cd "$out" && sha256sum misp.sql misp-host-data.tar.gz misp-config.tar.gz > SHA256SUMS)
chmod 600 "$out/misp.sql" "$out/misp-host-data.tar.gz" "$out/misp-config.tar.gz" "$out/SHA256SUMS"
complete=true
trap - EXIT
log "Backup written to $out"
