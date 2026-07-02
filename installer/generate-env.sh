#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
INSTALL_DIR="/opt/misp-docker"; BASE_URL="https://misp.example.com"; ADMIN_EMAIL="admin@example.com"; ADMIN_ORG="ExampleOrg"; TIMEZONE="Europe/Zurich"; EXPOSURE="reverse-proxy"; FORCE="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;; --base-url) BASE_URL="$2"; shift 2;; --admin-email) ADMIN_EMAIL="$2"; shift 2;; --admin-org) ADMIN_ORG="$2"; shift 2;; --timezone) TIMEZONE="$2"; shift 2;; --exposure) EXPOSURE="$2"; shift 2;; --force) FORCE="true"; shift;; *) fatal "Unknown argument: $1";;
  esac
done
[[ -f "$INSTALL_DIR/template.env" ]] || fatal "Official upstream template.env missing in $INSTALL_DIR"
[[ "$EXPOSURE" =~ ^(reverse-proxy|direct-qa)$ ]] || fatal "--exposure must be reverse-proxy or direct-qa"
[[ -e "$INSTALL_DIR/.env" && "$FORCE" != true ]] && fatal "$INSTALL_DIR/.env already exists. Use --force only if intentionally rotating generated secrets."
cp "$INSTALL_DIR/template.env" "$INSTALL_DIR/.env"; chmod 600 "$INSTALL_DIR/.env"
export BASE_URL ADMIN_EMAIL ADMIN_ORG TIMEZONE EXPOSURE
export ADMIN_PASSWORD_VALUE="$(random_b64 36)"
export ADMIN_KEY_VALUE="$(random_hex 20)"
export MYSQL_PASSWORD_VALUE="$(random_b64 32)"
export MYSQL_ROOT_PASSWORD_VALUE="$(random_b64 32)"
# Redis is used by PHP sessions via session.save_path. Use URL-safe hex, not base64.
export REDIS_PASSWORD_VALUE="$(random_hex 32)"
export GPG_PASSPHRASE_VALUE="$(random_b64 32)"
export ENCRYPTION_KEY_VALUE="$(random_b64 32)"
export SALT_VALUE="$(random_hex 32)"
export UUID_VALUE="$(new_uuid)"
export ADMIN_ORG_UUID_VALUE="$(new_uuid)"
if [[ "$EXPOSURE" == direct-qa ]]; then export CORE_HTTP_PORT_VALUE="80" CORE_HTTPS_PORT_VALUE="443"; else export CORE_HTTP_PORT_VALUE="127.0.0.1:8080" CORE_HTTPS_PORT_VALUE="127.0.0.1:8443"; fi
python3 - "$INSTALL_DIR/.env" <<'PY'
from pathlib import Path
import os, sys
p=Path(sys.argv[1])
updates={
 'BASE_URL': os.environ['BASE_URL'], 'TZ': os.environ['TIMEZONE'], 'ADMIN_EMAIL': os.environ['ADMIN_EMAIL'], 'ADMIN_ORG': os.environ['ADMIN_ORG'], 'ADMIN_ORG_UUID': os.environ['ADMIN_ORG_UUID_VALUE'],
 'ADMIN_PASSWORD': os.environ['ADMIN_PASSWORD_VALUE'], 'ADMIN_KEY': os.environ['ADMIN_KEY_VALUE'], 'GPG_PASSPHRASE': os.environ['GPG_PASSPHRASE_VALUE'], 'MISP_EMAIL': os.environ['ADMIN_EMAIL'], 'MISP_CONTACT': os.environ['ADMIN_EMAIL'],
 'ENCRYPTION_KEY': os.environ['ENCRYPTION_KEY_VALUE'], 'SALT': os.environ['SALT_VALUE'], 'UUID': os.environ['UUID_VALUE'], 'MYSQL_HOST': 'db', 'MYSQL_PORT': '3306', 'MYSQL_DATABASE': 'misp', 'MYSQL_USER': 'misp',
 'MYSQL_PASSWORD': os.environ['MYSQL_PASSWORD_VALUE'], 'MYSQL_ROOT_PASSWORD': os.environ['MYSQL_ROOT_PASSWORD_VALUE'], 'REDIS_HOST': 'redis', 'REDIS_PORT': '6379', 'REDIS_PASSWORD': os.environ['REDIS_PASSWORD_VALUE'],
 'ENABLE_REDIS_EMPTY_PASSWORD': 'false', 'DISABLE_PRINTING_PLAINTEXT_CREDENTIALS': 'true', 'DEBUG': '0', 'ENABLE_DB_SETTINGS': 'false', 'ENABLE_BACKGROUND_UPDATES': 'false',
 'CORE_HTTP_PORT': os.environ['CORE_HTTP_PORT_VALUE'], 'CORE_HTTPS_PORT': os.environ['CORE_HTTPS_PORT_VALUE'], 'PHP_SESSION_DEFAULTS': 'php', 'PHP_SESSION_COOKIE_SECURE': 'true', 'PHP_SESSION_COOKIE_SAMESITE': 'Lax', 'PHP_SESSION_COOKIE_DOMAIN': ''}
seen=set(); out=[]
for line in p.read_text().splitlines():
    if line and not line.startswith('#') and '=' in line:
        k=line.split('=',1)[0]
        if k in updates:
            line=f'{k}={updates[k]}'; seen.add(k)
    out.append(line)
for k,v in updates.items():
    if k not in seen: out.append(f'{k}={v}')
p.write_text('\n'.join(out)+'\n')
PY
log "Generated $INSTALL_DIR/.env for $BASE_URL ($EXPOSURE)."; log "Initial admin email: $ADMIN_EMAIL"; warn "Initial admin password is in $INSTALL_DIR/.env. Store securely and rotate after first login."
