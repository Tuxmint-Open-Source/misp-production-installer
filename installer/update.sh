#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
INSTALL_DIR="/opt/misp-docker"; UPSTREAM_REF=""
while [[ $# -gt 0 ]]; do case "$1" in --install-dir) INSTALL_DIR="$2"; shift 2;; --upstream-ref) UPSTREAM_REF="$2"; shift 2;; *) fatal "Unknown argument: $1";; esac; done
[[ -d "$INSTALL_DIR/.git" ]] || fatal "$INSTALL_DIR is not an upstream git checkout"; old_ref="$(git -C "$INSTALL_DIR" rev-parse --short HEAD)"
"$SCRIPT_DIR/backup.sh" --install-dir "$INSTALL_DIR"; git -C "$INSTALL_DIR" fetch --tags origin
if [[ -n "$UPSTREAM_REF" ]]; then git -C "$INSTALL_DIR" checkout "$UPSTREAM_REF"; else git -C "$INSTALL_DIR" pull --ff-only; fi
"$SCRIPT_DIR/render-compose.sh" --install-dir "$INSTALL_DIR"
"$SCRIPT_DIR/validate.sh" --install-dir "$INSTALL_DIR"
compose_cmd "$INSTALL_DIR" pull
compose_cmd "$INSTALL_DIR" up -d
wait_for_misp_core "$INSTALL_DIR" 600
run_misp_db_updates "$INSTALL_DIR"
check_misp_schema_ready "$INSTALL_DIR"
"$SCRIPT_DIR/doctor.sh" --install-dir "$INSTALL_DIR"
new_ref="$(git -C "$INSTALL_DIR" rev-parse --short HEAD)"; log "Updated upstream $old_ref -> $new_ref"
