#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
UPSTREAM_REPO="https://github.com/MISP/misp-docker.git"; UPSTREAM_REF="master"; INSTALL_DIR="/opt/misp-docker"
while [[ $# -gt 0 ]]; do case "$1" in --upstream-repo) UPSTREAM_REPO="$2"; shift 2;; --upstream-ref) UPSTREAM_REF="$2"; shift 2;; --install-dir) INSTALL_DIR="$2"; shift 2;; *) fatal "Unknown argument: $1";; esac; done
require_cmd git
validate_upstream_source "$UPSTREAM_REPO" "$UPSTREAM_REF"
mkdir -p "$(dirname "$INSTALL_DIR")"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  existing_origin="$(git -C "$INSTALL_DIR" remote get-url origin)"
  validate_upstream_source "$existing_origin" "$UPSTREAM_REF"
  [[ "$existing_origin" == "$UPSTREAM_REPO" ]] || fatal "Existing checkout origin does not match the selected upstream repository."
  log "Using existing upstream checkout: $INSTALL_DIR"; git -C "$INSTALL_DIR" fetch --tags origin
else
  [[ -e "$INSTALL_DIR" ]] && fatal "$INSTALL_DIR exists but is not a git checkout"
  log "Cloning official upstream $UPSTREAM_REPO to $INSTALL_DIR"; git clone -- "$UPSTREAM_REPO" "$INSTALL_DIR"
fi
log "Checking out upstream ref: $UPSTREAM_REF"; git -C "$INSTALL_DIR" checkout "$UPSTREAM_REF"
log "Upstream HEAD: $(git -C "$INSTALL_DIR" rev-parse --short HEAD)"
