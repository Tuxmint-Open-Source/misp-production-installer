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

validate_public_base_url() {
  local base_url="$1" exposure="$2"
  python3 - "$base_url" "$exposure" <<'PY'
import ipaddress
import sys
from urllib.parse import urlparse

base_url, exposure = sys.argv[1:]
parsed = urlparse(base_url)
if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
    raise SystemExit('BASE_URL must be an http(s) URL with a hostname')

host = parsed.hostname.lower().rstrip('.')
if exposure == 'direct-qa':
    if host in {'localhost', 'localhost.localdomain'}:
        raise SystemExit('direct-qa BASE_URL must be reachable by users; localhost would redirect browsers back to their own machine')
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip and ip.is_loopback:
        raise SystemExit('direct-qa BASE_URL must not use a loopback IP address')
PY
}

compose_interpolation_defaults() {
  # Upstream misp-docker references many optional variables in docker-compose.yml.
  # Docker Compose prints a warning for each unset variable before defaulting it
  # to an empty string. For operator-facing scripts this is noisy, so we set only
  # variables that are referenced by Compose but absent from the generated .env.
  # This keeps .env concise while making status/doctor/update output readable.
  local install_dir="$1"; shift
  python3 - "$install_dir" "$@" <<'PY'
from pathlib import Path
import re
import sys

install_dir = Path(sys.argv[1])
compose_files = [install_dir / p for p in sys.argv[2:]]
env_file = install_dir / '.env'

env_keys = set()
if env_file.exists():
    for line in env_file.read_text(errors='ignore').splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            env_keys.add(stripped.split('=', 1)[0])

vars_seen = set()
braced_pattern = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)')
plain_pattern = re.compile(r'(?<!\$)\$([A-Za-z_][A-Za-z0-9_]*)')
for compose_file in compose_files:
    if not compose_file.exists():
        continue
    text = compose_file.read_text(errors='ignore')
    vars_seen.update(braced_pattern.findall(text))
    vars_seen.update(plain_pattern.findall(text))

for name in sorted(vars_seen - env_keys):
    print(name)
PY
}

compose_cmd() {
  # Always call Docker Compose from the upstream checkout directory and always
  # include the generated .env and optional override file. This prevents subtle
  # differences between manual commands and installer commands.
  local install_dir="$1"; shift
  local compose_files=(docker-compose.yml)
  [[ -f "$install_dir/docker-compose.override.yml" ]] && compose_files+=(docker-compose.override.yml)
  local file_args=()
  for compose_file in "${compose_files[@]}"; do
    file_args+=(-f "$compose_file")
  done

  local env_args=()
  local var_name
  while IFS= read -r var_name; do
    [[ -z "$var_name" ]] && continue
    if [[ -z "${!var_name+x}" ]]; then
      env_args+=("$var_name=")
    fi
  done < <(compose_interpolation_defaults "$install_dir" "${compose_files[@]}")

  (cd "$install_dir" && env "${env_args[@]}" docker compose --env-file .env "${file_args[@]}" "$@")
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
  # The heartbeat can become healthy before the upstream entrypoint has finished
  # first-start database/user setup. In that window CakePHP may report missing DB
  # connections even though the stack later becomes usable. Keep waiting long
  # enough for slow first starts, but avoid printing the same stack trace on every
  # retry.
  local install_dir="$1" attempts="${2:-90}" delay="${3:-10}" attempt output
  log "Running MISP database updates"
  for ((attempt=1; attempt<=attempts; attempt++)); do
    if output="$(compose_cmd "$install_dir" exec -T -u www-data misp-core sh -lc 'cd /var/www/MISP/app && ./Console/cake Admin runUpdates' 2>&1)"; then
      [[ -n "$output" ]] && printf '%s\n' "$output"
      return 0
    fi
    if (( attempt == attempts )); then
      [[ -n "$output" ]] && printf '%s\n' "$output" >&2
      fatal "MISP database updates failed after ${attempts} attempts"
    fi
    if [[ "$output" == *'MysqlObserverExtended'* || "$output" == *'could not be created'* ]]; then
      warn "MISP database connection is not ready yet; first-start initialization may still be running (attempt ${attempt}/${attempts}); retrying in ${delay}s"
    else
      warn "MISP database update attempt ${attempt}/${attempts} failed; retrying in ${delay}s"
    fi
    sleep "$delay"
  done
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
