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

sync_misp_image_tags() {
  # Official misp-docker does not use Git repository tags as the runtime image
  # version. Its template.env declares component versions (CORE_TAG,
  # MODULES_TAG, GUARD_TAG), and the published container images are tagged with
  # those values. For production we make the running image tags explicit instead
  # of relying on docker-compose.yml's default `latest` fallback.
  local install_dir="$1" image_track="${2:-version-tags}" core_tag="${3:-}" modules_tag="${4:-}" guard_tag="${5:-}"
  [[ -f "$install_dir/template.env" ]] || fatal "Official upstream template.env missing in $install_dir"
  [[ -f "$install_dir/.env" ]] || fatal "$install_dir/.env missing"
  [[ "$image_track" =~ ^(version-tags|latest|keep)$ ]] || fatal "image track must be version-tags, latest, or keep"
  python3 - "$install_dir/template.env" "$install_dir/.env" "$image_track" "$core_tag" "$modules_tag" "$guard_tag" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
env_path = Path(sys.argv[2])
image_track = sys.argv[3]
overrides = {
    'CORE_TAG': sys.argv[4],
    'MODULES_TAG': sys.argv[5],
    'GUARD_TAG': sys.argv[6],
}

def parse_active(path):
    values = {}
    for line in path.read_text(errors='ignore').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        values[key.strip()] = value.strip()
    return values

template = parse_active(template_path)
for key, value in overrides.items():
    if value:
        template[key] = value
required = ['CORE_TAG', 'MODULES_TAG', 'GUARD_TAG']
missing = [key for key in required if not template.get(key)]
if missing:
    raise SystemExit('Missing upstream template values: ' + ', '.join(missing))

updates = {
    'CORE_TAG': template['CORE_TAG'],
    'MODULES_TAG': template['MODULES_TAG'],
    'GUARD_TAG': template['GUARD_TAG'],
}
if image_track == 'version-tags':
    updates.update({
        'CORE_RUNNING_TAG': template['CORE_TAG'],
        'MODULES_RUNNING_TAG': template['MODULES_TAG'],
        'GUARD_RUNNING_TAG': template['GUARD_TAG'],
    })
elif image_track == 'latest':
    updates.update({
        'CORE_RUNNING_TAG': 'latest',
        'MODULES_RUNNING_TAG': 'latest',
        'GUARD_RUNNING_TAG': 'latest',
    })
else:
    # keep: refresh component version metadata, but do not change image pins.
    pass

seen = set()
out = []
for line in env_path.read_text(errors='ignore').splitlines():
    if line and not line.startswith('#') and '=' in line:
        key = line.split('=', 1)[0]
        if key in updates:
            line = f'{key}={updates[key]}'
            seen.add(key)
    out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f'{key}={value}')
env_path.write_text('\n'.join(out) + '\n')
for key in ['CORE_TAG', 'MODULES_TAG', 'GUARD_TAG', 'CORE_RUNNING_TAG', 'MODULES_RUNNING_TAG', 'GUARD_RUNNING_TAG']:
    if key in updates:
        print(f'{key}={updates[key]}')
PY
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
