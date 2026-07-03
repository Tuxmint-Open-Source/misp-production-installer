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
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_ROOT/misp-backup-$stamp"
mkdir -p "$out"

# Database backup: single-transaction keeps the dump consistent without a long
# global lock for typical InnoDB tables.
compose_cmd "$INSTALL_DIR" exec -T db sh -c 'exec mariadb-dump --single-transaction --quick -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' > "$out/misp.sql"

# Host-data backup: these directories contain MISP files, generated configs,
# logs, TLS material, GnuPG state, and optional customizations.
(cd "$INSTALL_DIR" && { sudo tar --xattrs --selinux -czf "$out/misp-host-data.tar.gz" configs logs files ssl gnupg custom guard 2>/dev/null || sudo tar -czf "$out/misp-host-data.tar.gz" configs logs files ssl gnupg custom guard; })
sudo chown "$(id -u):$(id -g)" "$out/misp-host-data.tar.gz"
sha256sum "$out"/* > "$out/SHA256SUMS"
log "Backup written to $out"
