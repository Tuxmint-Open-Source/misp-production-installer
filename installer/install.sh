#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
UPSTREAM_REPO="https://github.com/MISP/misp-docker.git"; UPSTREAM_REF="master"; INSTALL_DIR="/opt/misp-docker"; BASE_URL="https://misp.example.com"; ADMIN_EMAIL="admin@example.com"; ADMIN_ORG="ExampleOrg"; TIMEZONE="Europe/Zurich"; EXPOSURE="reverse-proxy"; PREPARE_HOST="false"; BOOTSTRAP_TLS="false"; START="true"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream-repo) UPSTREAM_REPO="$2"; shift 2;; --upstream-ref) UPSTREAM_REF="$2"; shift 2;; --install-dir) INSTALL_DIR="$2"; shift 2;; --base-url) BASE_URL="$2"; shift 2;; --admin-email) ADMIN_EMAIL="$2"; shift 2;; --admin-org) ADMIN_ORG="$2"; shift 2;; --timezone) TIMEZONE="$2"; shift 2;; --exposure) EXPOSURE="$2"; shift 2;; --prepare-host) PREPARE_HOST="true"; shift;; --bootstrap-tls) BOOTSTRAP_TLS="true"; shift;; --no-start) START="false"; shift;; *) fatal "Unknown argument: $1";;
  esac
done
[[ "$EXPOSURE" =~ ^(reverse-proxy|direct-qa)$ ]] || fatal "--exposure must be reverse-proxy or direct-qa"
[[ "$PREPARE_HOST" == true ]] && "$SCRIPT_DIR/prepare-host-rocky.sh"
"$SCRIPT_DIR/fetch-upstream.sh" --upstream-repo "$UPSTREAM_REPO" --upstream-ref "$UPSTREAM_REF" --install-dir "$INSTALL_DIR"
"$SCRIPT_DIR/generate-env.sh" --install-dir "$INSTALL_DIR" --base-url "$BASE_URL" --admin-email "$ADMIN_EMAIL" --admin-org "$ADMIN_ORG" --timezone "$TIMEZONE" --exposure "$EXPOSURE"
"$SCRIPT_DIR/render-compose.sh" --install-dir "$INSTALL_DIR" --exposure "$EXPOSURE"
if [[ "$BOOTSTRAP_TLS" == true ]]; then fqdn="$(python3 - <<PY
from urllib.parse import urlparse
print(urlparse('$BASE_URL').hostname or 'misp.example.com')
PY
)"; "$SCRIPT_DIR/bootstrap-tls.sh" --install-dir "$INSTALL_DIR" --fqdn "$fqdn"; fi
"$SCRIPT_DIR/validate.sh" --install-dir "$INSTALL_DIR"
if [[ "$START" == true ]]; then
  compose_cmd "$INSTALL_DIR" pull
  compose_cmd "$INSTALL_DIR" up -d
  wait_for_misp_core "$INSTALL_DIR" 600
  run_misp_db_updates "$INSTALL_DIR"
  check_misp_schema_ready "$INSTALL_DIR"
  "$SCRIPT_DIR/doctor.sh" --install-dir "$INSTALL_DIR" || warn "Doctor reported a problem; inspect logs with installer/logs.sh"
fi
write_state "$INSTALL_DIR/.installer-state.json" "$UPSTREAM_REPO" "$UPSTREAM_REF" "$INSTALL_DIR" "$EXPOSURE" "$BASE_URL"
cat <<EOF

Installation complete.
MISP URL: $BASE_URL
Admin email: $ADMIN_EMAIL
Admin password: stored in $INSTALL_DIR/.env
Install dir: $INSTALL_DIR
Exposure mode: $EXPOSURE
EOF
