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
  --version            Show installer version

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
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_ROOT/misp-backup-$stamp"
mkdir -p "$out"
chmod 700 "$out"

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
sha256sum "$out"/* > "$out/SHA256SUMS"
chmod 600 "$out/misp.sql" "$out/misp-host-data.tar.gz" "$out/misp-config.tar.gz" "$out/SHA256SUMS"
log "Backup written to $out"
