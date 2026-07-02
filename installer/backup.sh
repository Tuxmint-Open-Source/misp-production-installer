#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
INSTALL_DIR="/opt/misp-docker"; BACKUP_ROOT=""
while [[ $# -gt 0 ]]; do case "$1" in --install-dir) INSTALL_DIR="$2"; shift 2;; --backup-root) BACKUP_ROOT="$2"; shift 2;; *) fatal "Unknown argument: $1";; esac; done
[[ -f "$INSTALL_DIR/.env" ]] || fatal "$INSTALL_DIR/.env missing"; BACKUP_ROOT="${BACKUP_ROOT:-$INSTALL_DIR/backups}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"; out="$BACKUP_ROOT/misp-backup-$stamp"; mkdir -p "$out"
compose_cmd "$INSTALL_DIR" exec -T db sh -c 'exec mariadb-dump --single-transaction --quick -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' > "$out/misp.sql"
(cd "$INSTALL_DIR" && { sudo tar --xattrs --selinux -czf "$out/misp-host-data.tar.gz" configs logs files ssl gnupg custom guard 2>/dev/null || sudo tar -czf "$out/misp-host-data.tar.gz" configs logs files ssl gnupg custom guard; })
sudo chown "$(id -u):$(id -g)" "$out/misp-host-data.tar.gz"; sha256sum "$out"/* > "$out/SHA256SUMS"; log "Backup written to $out"
