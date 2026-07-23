#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
INSTALL_DIR="/opt/misp-docker"; FQDN="misp.example.com"
while [[ $# -gt 0 ]]; do case "$1" in --install-dir) INSTALL_DIR="$2"; shift 2;; --fqdn) FQDN="$2"; shift 2;; *) fatal "Unknown argument: $1";; esac; done
acquire_operation_lock "$INSTALL_DIR"
require_cmd openssl; mkdir -p "$INSTALL_DIR/ssl"
python3 - "$FQDN" <<'PY'
import re
import sys

fqdn = sys.argv[1]
if not fqdn or len(fqdn) > 253:
    raise SystemExit('FQDN must be non-empty and no longer than 253 characters')
if not re.fullmatch(r'[A-Za-z0-9.-]+', fqdn):
    raise SystemExit('FQDN contains unsupported characters')
if any(not label or len(label) > 63 or label.startswith('-') or label.endswith('-') for label in fqdn.rstrip('.').split('.')):
    raise SystemExit('FQDN contains an invalid DNS label')
PY
[[ -e "$INSTALL_DIR/ssl/key.pem" || -e "$INSTALL_DIR/ssl/cert.pem" ]] && fatal "TLS files already exist in $INSTALL_DIR/ssl. Replace manually if desired."
OPENSSL_LOG="$(mktemp)"
if ! openssl req -x509 -newkey rsa:4096 -sha256 -days 30 -nodes \
  -keyout "$INSTALL_DIR/ssl/key.pem" \
  -out "$INSTALL_DIR/ssl/cert.pem" \
  -subj "/CN=$FQDN" \
  -addext "subjectAltName=DNS:$FQDN" >/dev/null 2>"$OPENSSL_LOG"; then
  sed 's/^/[openssl] /' "$OPENSSL_LOG" >&2
  rm -f "$OPENSSL_LOG"
  fatal "Failed to create bootstrap TLS certificate"
fi
rm -f "$OPENSSL_LOG"
chmod 600 "$INSTALL_DIR/ssl/key.pem"; log "Created temporary self-signed TLS certificate for $FQDN. Replace for production."
