#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Run health checks for a MISP Docker deployment.

Usage:
  ./lifecycle/doctor.sh [options]

What this script checks:
  - Required .env values and Docker Compose config
  - BASE_URL DNS lookup from the host
  - Container-local MISP heartbeat
  - Schema readiness required by first interactive login
  - Docker Compose service status

Options:
  --install-dir PATH   Deployment directory (default: /opt/misp-docker)
  -h, --help           Show this help
  --version            Show manager version
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
HOST="$(url_hostname "$BASE_URL")"
log "BASE_URL=$BASE_URL"
if [[ -n "$HOST" ]] && getent hosts "$HOST" >/dev/null; then
  log "DNS lookup OK for $HOST"
else
  warn "DNS lookup failed for $HOST"
fi

wait_for_misp_core "$INSTALL_DIR" 600
"$SCRIPT_DIR/healthcheck.sh" --install-dir "$INSTALL_DIR" --format text --timeout 60
log "Doctor checks completed."
