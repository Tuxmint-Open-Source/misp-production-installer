#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Show Docker Compose service status and the MISP heartbeat.

Usage:
  ./installer/status.sh [options]

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

compose_cmd "$INSTALL_DIR" ps
printf '\nHeartbeat via container-local HTTPS:\n'
compose_cmd "$INSTALL_DIR" exec -T misp-core curl -ks https://localhost/users/heartbeat || true
printf '\n'
