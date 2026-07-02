#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
INSTALL_DIR="/opt/misp-docker"
while [[ $# -gt 0 ]]; do case "$1" in --install-dir) INSTALL_DIR="$2"; shift 2;; *) fatal "Unknown argument: $1";; esac; done
compose_cmd "$INSTALL_DIR" ps
printf '\nHeartbeat via container-local HTTPS:\n'
compose_cmd "$INSTALL_DIR" exec -T misp-core curl -ks https://localhost/users/heartbeat || true
printf '\n'
