#!/usr/bin/env bash
set -euo pipefail

# Shared helpers for all installer scripts.
# Keep this file small and dependency-free: every script sources it before doing work.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$PROJECT_ROOT/VERSION"

log() { printf '\033[1;34m[INFO]\033[0m %s\n' "$*" >&2; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*" >&2; }
fatal() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || fatal "Required command not found: $1"; }

installer_version() {
  if [[ -f "$VERSION_FILE" ]]; then
    tr -d '\n' < "$VERSION_FILE"
  else
    printf '0.0.0-dev'
  fi
}

print_version() {
  printf 'misp-production-installer %s\n' "$(installer_version)"
}

random_b64() { openssl rand -base64 "$1" | tr -d '\n'; }
random_hex() { openssl rand -hex "$1" | tr -d '\n'; }
new_uuid() { if command -v uuidgen >/dev/null 2>&1; then uuidgen; else python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
fi; }

compose_cmd() {
  # Always call Docker Compose from the upstream checkout directory and always
  # include the generated .env and optional override file. This prevents subtle
  # differences between manual commands and installer commands.
  local install_dir="$1"; shift
  local files=(-f docker-compose.yml)
  [[ -f "$install_dir/docker-compose.override.yml" ]] && files+=(-f docker-compose.override.yml)
  (cd "$install_dir" && docker compose --env-file .env "${files[@]}" "$@")
}

wait_for_misp_core() {
  # MISP's public BASE_URL can point through DNS/reverse proxies. Readiness here
  # intentionally uses container-local HTTPS so DNS and proxy outages do not
  # make container health ambiguous.
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
  # The heartbeat may become healthy before all MISP DB migrations are applied.
  # Run the official Cake command as the web user before declaring success.
  local install_dir="$1"
  log "Running MISP database updates"
  compose_cmd "$install_dir" exec -T -u www-data misp-core sh -lc 'cd /var/www/MISP/app && ./Console/cake Admin runUpdates'
}

check_misp_schema_ready() {
  # The bookmarks table is used immediately after interactive login. Checking it
  # catches the observed first-login /users/routeafterlogin MissingTableException.
  local install_dir="$1"
  log "Checking MISP schema readiness"
  compose_cmd "$install_dir" exec -T db sh -lc 'mariadb -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -NBe "SHOW TABLES LIKE '\''bookmarks'\'';" | grep -qx bookmarks'
}

write_state() {
  # Store non-secret deployment metadata for operators and future update runs.
  local state_file="$1" upstream_repo="$2" upstream_ref="$3" install_dir="$4" exposure="$5" base_url="$6"
  python3 - "$state_file" "$upstream_repo" "$upstream_ref" "$install_dir" "$exposure" "$base_url" "$(installer_version)" <<'PY'
import json, sys, datetime
p, repo, ref, install_dir, exposure, base_url, installer_version = sys.argv[1:]
data={
    'upstream_repo': repo,
    'upstream_ref': ref,
    'install_dir': install_dir,
    'exposure': exposure,
    'base_url': base_url,
    'installer': 'misp-production-installer',
    'installer_version': installer_version,
    'updated_at_utc': datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z',
}
open(p, 'w').write(json.dumps(data, indent=2)+'\n')
PY
}
