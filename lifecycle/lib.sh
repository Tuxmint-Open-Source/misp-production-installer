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

acquire_operation_lock() {
  local install_dir="$1" canonical parent lock_id lock_file old_umask
  local -a lock_values=()
  if [[ -n "${LIFECYCLE_LOCK_FD:-}" && -e "/proc/$$/fd/$LIFECYCLE_LOCK_FD" ]]; then
    return 0
  fi
  require_cmd flock
  mapfile -t lock_values < <(python3 - "$install_dir" <<'PY'
import hashlib
from pathlib import Path
import sys
canonical = str(Path(sys.argv[1]).expanduser().resolve())
print(canonical)
print(Path(canonical).parent)
print(hashlib.sha256(canonical.encode()).hexdigest()[:24])
PY
)
  canonical="${lock_values[0]}"
  parent="${lock_values[1]}"
  lock_id="${lock_values[2]}"
  mkdir -p "$parent"
  lock_file="$parent/.misp-lifecycle-$lock_id.lock"
  [[ ! -L "$lock_file" ]] || fatal "Refusing symlinked lifecycle lock: $lock_file"
  old_umask="$(umask)"
  umask 077
  exec {LIFECYCLE_LOCK_FD}>>"$lock_file"
  umask "$old_umask"
  export LIFECYCLE_LOCK_FD
  flock -n "$LIFECYCLE_LOCK_FD" || fatal "Another lifecycle operation is already active for $canonical"
}

retry_cmd() {
  local attempts="$1" delay="$2"; shift 2
  local attempt
  for ((attempt=1; attempt<=attempts; attempt++)); do
    if "$@"; then
      return 0
    fi
    if (( attempt == attempts )); then
      fatal "Command failed after ${attempts} attempts: $*"
    fi
    warn "Command failed (attempt ${attempt}/${attempts}); retrying in ${delay}s: $*"
    sleep "$delay"
  done
}

installer_version() {
  if [[ -f "$VERSION_FILE" ]]; then
    tr -d '\n' < "$VERSION_FILE"
  else
    printf '0.0.0-dev'
  fi
}

PRODUCT_ID="misp-docker-lifecycle-manager"

print_version() {
  printf '%s %s\n' "$PRODUCT_ID" "$(installer_version)"
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
import re
import sys
from urllib.parse import urlparse

base_url, exposure = sys.argv[1:]
if any(ord(ch) < 32 or ord(ch) == 127 for ch in base_url):
    raise SystemExit('BASE_URL must not contain control characters')
if any(ch.isspace() or ch in '#$\\"\'' for ch in base_url):
    raise SystemExit('BASE_URL contains characters that are unsafe in dotenv')
try:
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    port = parsed.port
except ValueError:
    raise SystemExit('BASE_URL contains a malformed host or port')
if parsed.scheme not in {'http', 'https'} or not hostname:
    raise SystemExit('BASE_URL must be an http(s) URL with a hostname')
if parsed.username is not None or parsed.password is not None:
    raise SystemExit('BASE_URL must not contain embedded credentials')
if parsed.query or parsed.fragment:
    raise SystemExit('BASE_URL must not contain query parameters or fragments')

if port is not None and not 1 <= port <= 65535:
    raise SystemExit('BASE_URL contains an invalid port')
host = hostname.lower().rstrip('.')
try:
    parsed_ip = ipaddress.ip_address(host)
except ValueError:
    parsed_ip = None
    labels = host.split('.')
    if any(
        not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
        for label in labels
    ):
        raise SystemExit('BASE_URL hostname contains an invalid DNS label')
if exposure == 'direct-qa':
    if host in {'localhost', 'localhost.localdomain'}:
        raise SystemExit('direct-qa BASE_URL must be reachable by users; localhost would redirect browsers back to their own machine')
    ip = parsed_ip
    if ip and ip.is_loopback:
        raise SystemExit('direct-qa BASE_URL must not use a loopback IP address')
PY
}

url_hostname() {
  local base_url="$1" fallback="${2:-}"
  python3 - "$base_url" "$fallback" <<'PY'
import sys
from urllib.parse import urlparse

base_url, fallback = sys.argv[1:]
print(urlparse(base_url).hostname or fallback)
PY
}

validate_env_inputs() {
  python3 - "$@" <<'PY'
import re
import sys
from pathlib import Path

email, organization, timezone, core_tag, modules_tag, guard_tag = sys.argv[1:]
values = {
    'admin email': email,
    'admin organization': organization,
    'timezone': timezone,
    'core tag': core_tag,
    'modules tag': modules_tag,
    'guard tag': guard_tag,
}
for label, value in values.items():
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise SystemExit(f'{label} must not contain control characters')
dotenv_unsafe = set('#$\\"\'')
if (
    len(email) > 254
    or not re.fullmatch(r'[^\s@=]+@[^\s@=]+', email)
    or any(ch in dotenv_unsafe for ch in email)
):
    raise SystemExit('admin email must be a dotenv-safe single-line email address')
if (
    not organization
    or len(organization) > 255
    or organization != organization.strip()
    or any(ch in dotenv_unsafe for ch in organization)
):
    raise SystemExit('admin organization must be 1-255 dotenv-safe characters without surrounding whitespace')
if (
    len(timezone) > 128
    or not re.fullmatch(r'[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)*', timezone)
    or any(part in {'.', '..'} for part in timezone.split('/'))
):
    raise SystemExit('timezone contains unsupported characters')
zone = Path('/usr/share/zoneinfo') / timezone
if Path('/usr/share/zoneinfo').is_dir() and not zone.is_file():
    raise SystemExit('timezone is not present in the system zoneinfo database')
tag_pattern = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}')
for label, value in [('core tag', core_tag), ('modules tag', modules_tag), ('guard tag', guard_tag)]:
    if value and not tag_pattern.fullmatch(value):
        raise SystemExit(f'{label} contains unsupported characters')
PY
}

validate_upstream_source() {
  local upstream_repo="$1" upstream_ref="$2"
  python3 - "$upstream_repo" "$upstream_ref" <<'PY'
import re
import sys
from urllib.parse import urlparse
repo, ref = sys.argv[1:]
if not repo or repo.startswith('-') or any(ord(ch) < 32 or ord(ch) == 127 for ch in repo):
    raise SystemExit('upstream repository contains unsafe option/control characters')
parsed = urlparse(repo)
if parsed.scheme:
    if parsed.scheme not in {'https', 'ssh', 'git'}:
        raise SystemExit('upstream repository uses an unsupported URL scheme')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SystemExit('upstream repository URL must not contain credentials, query parameters, or fragments')
if not ref or ref.startswith('-') or len(ref) > 255 or any(ord(ch) < 32 or ord(ch) == 127 for ch in ref):
    raise SystemExit('upstream ref contains unsafe option/control characters')
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/@{}+~-]*', ref):
    raise SystemExit('upstream ref contains unsupported characters')
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
import re
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
tag_pattern = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}')
invalid = [key for key in required if not tag_pattern.fullmatch(template[key])]
if invalid:
    raise SystemExit('Invalid upstream template values: ' + ', '.join(invalid))

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

check_misp_heartbeat() {
  local install_dir="$1" output body status
  output="$(compose_cmd "$install_dir" exec -T misp-core curl -ksS --fail --max-time 30 --write-out $'\n%{http_code}' https://localhost/users/heartbeat)" || return 1
  body="${output%$'\n'*}"
  status="${output##*$'\n'}"
  [[ "$status" == 200 ]] || return 1
  python3 - "$body" <<'PY'
import json
import sys

try:
    payload = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit(1)
message = payload.get('message') if isinstance(payload, dict) and set(payload) == {'message'} else None
raise SystemExit(0 if isinstance(message, str) and 0 < len(message) <= 512 else 1)
PY
}

wait_for_misp_core() {
  # MISP's public BASE_URL can point through DNS/reverse proxies. Readiness here
  # intentionally uses container-local HTTPS so DNS and proxy outages do not
  # make container health ambiguous.
  local install_dir="$1" timeout="${2:-600}" elapsed=0 interval=5
  log "Waiting for MISP core HTTPS heartbeat (timeout ${timeout}s)"
  until check_misp_heartbeat "$install_dir" >/dev/null 2>&1; do
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
  compose_cmd "$install_dir" exec -T db sh -lc '
    umask 077
    cfg="$(mktemp)"
    trap '\''rm -f "$cfg"'\'' EXIT
    printf "[client]\nuser=%s\npassword=%s\n" "$MYSQL_USER" "$MYSQL_PASSWORD" > "$cfg"
    mariadb --defaults-extra-file="$cfg" "$MYSQL_DATABASE" -NBe "SHOW TABLES LIKE '\''bookmarks'\'';" | grep -qx bookmarks
  '
}

prepare_restore_host_roots() {
  local install_dir="$1" root
  for root in configs logs files ssl gnupg custom guard; do
    rm -rf -- "$install_dir/$root"
  done
}

wait_for_misp_live_marker() {
  # The heartbeat and database schema can become ready before the upstream MISP
  # entrypoint has completed all first-start application/admin initialization.
  # Upstream emits this line when it considers interactive user login available.
  local install_dir="$1" timeout="${2:-900}" since="${3:-}" elapsed=0 interval=10
  local marker="MISP is now live. Users can now log in."
  local log_args=(logs --no-color --tail=2000)
  [[ -n "$since" ]] && log_args+=(--since "$since")
  log_args+=(misp-core)
  log "Waiting for MISP interactive login readiness marker (timeout ${timeout}s)"
  until compose_cmd "$install_dir" "${log_args[@]}" 2>/dev/null | grep -Fq "$marker"; do
    if (( elapsed >= timeout )); then
      fatal "MISP did not report interactive login readiness within ${timeout}s. Inspect logs with lifecycle/logs.sh."
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
    if (( elapsed % 60 == 0 )); then
      warn "Still waiting for MISP to finish first-start initialization (${elapsed}/${timeout}s)"
    fi
  done
  log "MISP reports interactive login is ready."
}

write_state() {
  # Store non-secret deployment metadata for operators and future update runs.
  local state_file="$1" upstream_repo="$2" upstream_ref="$3" upstream_commit="$4" install_dir="$5" exposure="$6" base_url="$7"
  python3 - "$state_file" "$upstream_repo" "$upstream_ref" "$upstream_commit" "$install_dir" "$exposure" "$base_url" "$(installer_version)" <<'PY'
import datetime, json, os, re, sys, tempfile
from pathlib import Path
p, repo, ref, commit, install_dir, exposure, base_url, installer_version = sys.argv[1:]
if not re.fullmatch(r'[0-9a-f]{40}', commit):
    raise SystemExit('upstream commit must be a full lowercase Git commit ID')
data={
    'upstream_repo': repo,
    'upstream_ref': ref,
    'upstream_commit': commit,
    'install_dir': install_dir,
    'exposure': exposure,
    'base_url': base_url,
    'installer': 'misp-docker-lifecycle-manager',
    'installer_version': installer_version,
    'updated_at_utc': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
}
target = Path(p)
fd, temporary = tempfile.mkstemp(prefix='.installer-state.', dir=target.parent)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    os.chmod(target, 0o600)
except BaseException:
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
    raise
PY
}
