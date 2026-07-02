#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
INSTALL_DIR="/opt/misp-docker"
while [[ $# -gt 0 ]]; do case "$1" in --install-dir) INSTALL_DIR="$2"; shift 2;; --) shift; break;; *) break;; esac; done
compose_cmd "$INSTALL_DIR" pull
