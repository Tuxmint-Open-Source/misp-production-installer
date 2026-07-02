#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
INSTALL_DIR="/opt/misp-docker"
while [[ $# -gt 0 ]]; do case "$1" in --install-dir) INSTALL_DIR="$2"; shift 2;; *) fatal "Unknown argument: $1";; esac; done
"$SCRIPT_DIR/validate.sh" --install-dir "$INSTALL_DIR"
BASE_URL="$(python3 - "$INSTALL_DIR/.env" <<'PY'
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text().splitlines():
    if line.startswith('BASE_URL='): print(line.split('=',1)[1])
PY
)"
HOST="$(python3 - <<PY
from urllib.parse import urlparse
print(urlparse('$BASE_URL').hostname or '')
PY
)"
log "BASE_URL=$BASE_URL"; [[ -n "$HOST" ]] && getent hosts "$HOST" || warn "DNS lookup failed for $HOST"
wait_for_misp_core "$INSTALL_DIR" 600
check_misp_schema_ready "$INSTALL_DIR"
compose_cmd "$INSTALL_DIR" ps
compose_cmd "$INSTALL_DIR" exec -T misp-core curl -ks https://localhost/users/heartbeat >/tmp/misp-heartbeat.json
log "Heartbeat OK: $(tr '\n' ' ' </tmp/misp-heartbeat.json)"; log "Doctor checks completed."
