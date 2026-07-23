#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
INSTALL_DIR="/opt/misp-docker"
while [[ $# -gt 0 ]]; do case "$1" in --install-dir) INSTALL_DIR="$2"; shift 2;; *) fatal "Unknown argument: $1";; esac; done
[[ -f "$INSTALL_DIR/.env" ]] || fatal "$INSTALL_DIR/.env missing"; [[ -f "$INSTALL_DIR/docker-compose.yml" ]] || fatal "$INSTALL_DIR/docker-compose.yml missing"
python3 - "$INSTALL_DIR/.env" <<'PY'
from pathlib import Path
import sys, re
kv={}
for line in Path(sys.argv[1]).read_text().splitlines():
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); kv[k]=v
required=['BASE_URL','ADMIN_EMAIL','ADMIN_PASSWORD','ADMIN_KEY','MYSQL_PASSWORD','MYSQL_ROOT_PASSWORD','REDIS_PASSWORD','ENCRYPTION_KEY','SALT','UUID']
missing=[k for k in required if not kv.get(k)]
if missing: raise SystemExit('Missing required env values: '+', '.join(missing))
if not re.fullmatch(r'[A-Za-z0-9]{40}', kv['ADMIN_KEY']): raise SystemExit('ADMIN_KEY must be exactly 40 alphanumeric characters')
if not re.fullmatch(r'[0-9a-f]{64}', kv['REDIS_PASSWORD']): raise SystemExit('REDIS_PASSWORD must be URL-safe 64-char hex; Redis sessions/CSRF can break otherwise')
print('env validation OK')
PY
compose_cmd "$INSTALL_DIR" config >/dev/null; log "Compose config OK."
