#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Install a production-oriented MISP Docker deployment.

Usage:
  ./installer/install.sh [options]

What this script does:
  1. Optionally prepares a Rocky Linux host for Docker.
  2. Clones or updates the official MISP/misp-docker upstream checkout.
  3. Generates a secret-bearing .env from upstream template.env.
  4. Renders docker-compose.override.yml for the selected exposure mode.
  5. Optionally creates a bootstrap self-signed TLS certificate.
  6. Validates Compose config, starts containers, runs MISP DB updates,
     checks schema readiness, and runs doctor.

Options:
  --install-dir PATH      Deployment directory for official misp-docker checkout
                          (default: /opt/misp-docker)
  --upstream-repo URL     Upstream git repository (default: official MISP/misp-docker)
  --upstream-ref REF      Upstream branch, tag, or commit (default: master)
  --core-tag TAG          Explicit misp-core image/component tag override
  --modules-tag TAG       Explicit misp-modules image/component tag override
  --guard-tag TAG         Explicit misp-guard image/component tag override
  --base-url URL          Public MISP URL, e.g. https://misp.example.com
  --admin-email EMAIL     Initial MISP admin email
  --admin-org NAME        Initial MISP organization name
  --timezone TZ           Container timezone (default: Europe/Zurich)
  --exposure MODE         reverse-proxy or direct-qa (default: reverse-proxy)
  --prepare-host          Install Docker packages on Rocky Linux first
  --bootstrap-tls         Generate a bootstrap self-signed certificate
  --no-start              Generate files only; do not pull/start containers
  -h, --help              Show this help
  --version               Show installer version

Exposure modes:
  reverse-proxy  Binds MISP to localhost ports 8080/8443 for an external proxy.
  direct-qa      Binds MISP directly to host ports 80/443 for lab testing only.
EOF
}

UPSTREAM_REPO="https://github.com/MISP/misp-docker.git"
UPSTREAM_REF="master"
CORE_TAG_OVERRIDE=""
MODULES_TAG_OVERRIDE=""
GUARD_TAG_OVERRIDE=""
INSTALL_DIR="/opt/misp-docker"
BASE_URL="https://misp.example.com"
ADMIN_EMAIL="admin@example.com"
ADMIN_ORG="ExampleOrg"
TIMEZONE="Europe/Zurich"
EXPOSURE="reverse-proxy"
PREPARE_HOST="false"
BOOTSTRAP_TLS="false"
START="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream-repo) UPSTREAM_REPO="$2"; shift 2;;
    --upstream-ref) UPSTREAM_REF="$2"; shift 2;;
    --core-tag) CORE_TAG_OVERRIDE="$2"; shift 2;;
    --modules-tag) MODULES_TAG_OVERRIDE="$2"; shift 2;;
    --guard-tag) GUARD_TAG_OVERRIDE="$2"; shift 2;;
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --base-url) BASE_URL="$2"; shift 2;;
    --admin-email) ADMIN_EMAIL="$2"; shift 2;;
    --admin-org) ADMIN_ORG="$2"; shift 2;;
    --timezone) TIMEZONE="$2"; shift 2;;
    --exposure) EXPOSURE="$2"; shift 2;;
    --prepare-host) PREPARE_HOST="true"; shift;;
    --bootstrap-tls) BOOTSTRAP_TLS="true"; shift;;
    --no-start) START="false"; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

[[ "$EXPOSURE" =~ ^(reverse-proxy|direct-qa)$ ]] || fatal "--exposure must be reverse-proxy or direct-qa"

# Host preparation is optional so operators can manage Docker themselves.
[[ "$PREPARE_HOST" == true ]] && "$SCRIPT_DIR/prepare-host-rocky.sh"

# Keep upstream clean: fetch official files, then add generated config beside them.
"$SCRIPT_DIR/fetch-upstream.sh" --upstream-repo "$UPSTREAM_REPO" --upstream-ref "$UPSTREAM_REF" --install-dir "$INSTALL_DIR"
"$SCRIPT_DIR/generate-env.sh" --install-dir "$INSTALL_DIR" --base-url "$BASE_URL" --admin-email "$ADMIN_EMAIL" --admin-org "$ADMIN_ORG" --timezone "$TIMEZONE" --exposure "$EXPOSURE" --core-tag "$CORE_TAG_OVERRIDE" --modules-tag "$MODULES_TAG_OVERRIDE" --guard-tag "$GUARD_TAG_OVERRIDE"
"$SCRIPT_DIR/render-compose.sh" --install-dir "$INSTALL_DIR" --exposure "$EXPOSURE"

if [[ "$BOOTSTRAP_TLS" == true ]]; then
  fqdn="$(python3 - <<PY
from urllib.parse import urlparse
print(urlparse('$BASE_URL').hostname or 'misp.example.com')
PY
)"
  "$SCRIPT_DIR/bootstrap-tls.sh" --install-dir "$INSTALL_DIR" --fqdn "$fqdn"
fi

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
Installer version: $(installer_version)
EOF
