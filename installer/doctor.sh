#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Run health checks for a MISP Docker deployment.

Usage:
  ./installer/doctor.sh [options]

What this script checks:
  - Required .env values and Docker Compose config
  - BASE_URL DNS lookup from the host
  - Container-local MISP heartbeat
  - Schema readiness required by first interactive login
  - Docker Compose service status

Options:
  --install-dir PATH   Deployment directory (default: /opt/misp-docker)
  -h, --help           Show this help
  --version            Show installer version
EOF
}

INSTALL_DIR="/opt/misp-docker"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

"$SCRIPT_DIR/validate.sh" --install-dir "$INSTALL_DIR"
BASE_URL="$(python3 - "$INSTALL_DIR/.env" <<'PY'
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text().splitlines():
    if line.startswith('BASE_URL='):
        print(line.split('=',1)[1])
PY
)"
HOST="$(python3 - <<PY
from urllib.parse import urlparse
print(urlparse('$BASE_URL').hostname or '')
PY
)"
log "BASE_URL=$BASE_URL"
if [[ -n "$HOST" ]] && getent hosts "$HOST" >/dev/null; then
  log "DNS lookup OK for $HOST"
else
  warn "DNS lookup failed for $HOST"
fi

wait_for_misp_core "$INSTALL_DIR" 600
check_misp_schema_ready "$INSTALL_DIR"
compose_cmd "$INSTALL_DIR" ps
compose_cmd "$INSTALL_DIR" exec -T misp-core curl -ks https://localhost/users/heartbeat >/tmp/misp-heartbeat.json
log "Heartbeat OK: $(tr '\n' ' ' </tmp/misp-heartbeat.json)"
log "Doctor checks completed."
