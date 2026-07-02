#!/usr/bin/env bash
set -euo pipefail
log() { printf '\033[1;34m[INFO]\033[0m %s\n' "$*" >&2; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*" >&2; }
fatal() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || fatal "Required command not found: $1"; }
random_b64() { openssl rand -base64 "$1" | tr -d '\n'; }
random_hex() { openssl rand -hex "$1" | tr -d '\n'; }
new_uuid() { if command -v uuidgen >/dev/null 2>&1; then uuidgen; else python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
fi; }
compose_cmd() {
  local install_dir="$1"; shift
  local files=(-f docker-compose.yml)
  [[ -f "$install_dir/docker-compose.override.yml" ]] && files+=(-f docker-compose.override.yml)
  (cd "$install_dir" && docker compose --env-file .env "${files[@]}" "$@")
}
wait_for_misp_core() {
  local install_dir="$1" timeout="${2:-600}" elapsed=0 interval=5
  log "Waiting for MISP core HTTPS heartbeat (timeout ${timeout}s)"
  until compose_cmd "$install_dir" exec -T misp-core curl -ks https://localhost/users/heartbeat >/dev/null 2>&1; do
    if (( elapsed >= timeout )); then
      fatal "MISP core did not become ready within ${timeout}s"
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done
}
run_misp_db_updates() {
  local install_dir="$1"
  log "Running MISP database updates"
  compose_cmd "$install_dir" exec -T -u www-data misp-core sh -lc 'cd /var/www/MISP/app && ./Console/cake Admin runUpdates'
}
check_misp_schema_ready() {
  local install_dir="$1"
  log "Checking MISP schema readiness"
  compose_cmd "$install_dir" exec -T db sh -lc 'mariadb -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -NBe "SHOW TABLES LIKE '\''bookmarks'\'';" | grep -qx bookmarks'
}
write_state() {
  local state_file="$1" upstream_repo="$2" upstream_ref="$3" install_dir="$4" exposure="$5" base_url="$6"
  python3 - "$state_file" "$upstream_repo" "$upstream_ref" "$install_dir" "$exposure" "$base_url" <<'PY'
import json, sys, datetime
p, repo, ref, install_dir, exposure, base_url = sys.argv[1:]
data={'upstream_repo': repo, 'upstream_ref': ref, 'install_dir': install_dir, 'exposure': exposure, 'base_url': base_url, 'updated_at_utc': datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z', 'installer': 'misp-production-installer'}
open(p, 'w').write(json.dumps(data, indent=2)+'\n')
PY
}
