#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Restore a MISP Docker deployment from a backup created by backup.sh.

Usage:
  ./installer/restore.sh --backup-dir PATH [options]

What this script restores:
  - generated deployment configuration from misp-config.tar.gz
  - MISP host-mounted data directories from misp-host-data.tar.gz
  - MariaDB database contents from misp.sql

Options:
  --backup-dir PATH    Backup directory containing misp.sql, misp-host-data.tar.gz,
                       misp-config.tar.gz, and SHA256SUMS (required)
  --install-dir PATH   Deployment directory to restore (default: /opt/misp-docker)
  --upstream-repo URL  Upstream git repository override when backup state is absent
  --upstream-ref REF   Upstream ref override when backup state is absent
  --yes                Enable destructive restore mode. You will still be prompted.
  --force              Skip the interactive confirmation prompt. Use only for
                       automation after testing on a disposable host.
  -h, --help           Show this help
  --version            Show manager version

Safety:
  Restore is destructive for the selected install directory and its Compose
  project. It removes existing containers/volumes for that deployment before
  importing the backup database.
EOF
}

INSTALL_DIR="/opt/misp-docker"
BACKUP_DIR=""
UPSTREAM_REPO="https://github.com/MISP/misp-docker.git"
UPSTREAM_REF="master"
UPSTREAM_REPO_EXPLICIT="false"
UPSTREAM_REF_EXPLICIT="false"
YES="false"
FORCE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-dir) BACKUP_DIR="$2"; shift 2;;
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --upstream-repo) UPSTREAM_REPO="$2"; UPSTREAM_REPO_EXPLICIT="true"; shift 2;;
    --upstream-ref) UPSTREAM_REF="$2"; UPSTREAM_REF_EXPLICIT="true"; shift 2;;
    --yes) YES="true"; shift;;
    --force) FORCE="true"; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

[[ -n "$BACKUP_DIR" ]] || fatal "--backup-dir is required"
BACKUP_DIR="$(python3 - "$BACKUP_DIR" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"
INSTALL_DIR="$(python3 - "$INSTALL_DIR" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"

case "$INSTALL_DIR" in
  /|/opt|/srv|/home|/var|/usr|/tmp) fatal "Refusing unsafe --install-dir: $INSTALL_DIR";;
esac
[[ "$INSTALL_DIR" == */* ]] || fatal "Refusing unsafe --install-dir: $INSTALL_DIR"

BACKUP_SOURCE_DIR="$BACKUP_DIR"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
python3 "$PROJECT_ROOT/scripts/validate-backup.py" "$BACKUP_SOURCE_DIR" "$tmp/backup"
BACKUP_DIR="$tmp/backup"
tar --no-same-owner --no-same-permissions -C "$tmp" -xzf "$BACKUP_DIR/misp-config.tar.gz"

state_file="$tmp/.installer-state.json"
if [[ -f "$state_file" ]]; then
  mapfile -t state_vals < <(python3 - "$state_file" <<'PY'
import json, sys
p=sys.argv[1]
data=json.load(open(p))
print(data.get('upstream_repo') or '')
print(data.get('upstream_ref') or '')
print(data.get('exposure') or '')
print(data.get('base_url') or '')
PY
)
  archived_repo="${state_vals[0]:-}"
  archived_ref="${state_vals[1]:-}"
  archived_exposure="${state_vals[2]:-}"
  archived_base_url="${state_vals[3]:-}"
  if [[ "$UPSTREAM_REPO_EXPLICIT" != true && -n "$archived_repo" ]]; then
    [[ "$archived_repo" == "https://github.com/MISP/misp-docker.git" ]] || fatal "Backup uses a non-default upstream repository; pass the reviewed repository explicitly with --upstream-repo."
    UPSTREAM_REPO="$archived_repo"
  fi
  if [[ "$UPSTREAM_REF_EXPLICIT" != true && -n "$archived_ref" ]]; then
    UPSTREAM_REF="$archived_ref"
  fi
else
  archived_exposure=""
  archived_base_url=""
  warn "Backup has no .installer-state.json; lifecycle state will be regenerated from the restored configuration and selected upstream source."
fi
validate_upstream_source "$UPSTREAM_REPO" "$UPSTREAM_REF"

warn "Restore will replace deployment resources for: $INSTALL_DIR"
warn "Backup source: $BACKUP_SOURCE_DIR"
warn "Upstream source: $UPSTREAM_REPO @ $UPSTREAM_REF"
[[ "$YES" == true ]] || fatal "Dry-run only. Re-run with --yes after reviewing the restore target."

if [[ "$FORCE" != true ]]; then
  [[ -t 0 ]] || fatal "Interactive confirmation requires a terminal. Use --force only for automation after reviewing the restore target."
  printf '\n%s\n' "Are you sure you want to restore this MISP backup?"
  printf 'Install directory: %s\n' "$INSTALL_DIR"
  printf 'Backup directory:  %s\n' "$BACKUP_SOURCE_DIR"
  printf 'Type RESTORE to continue: '
  read -r confirmation
  [[ "$confirmation" == "RESTORE" ]] || fatal "Restore aborted by user."
fi

if [[ -e "$INSTALL_DIR" && ! -d "$INSTALL_DIR/.git" ]]; then
  fatal "$INSTALL_DIR exists but is not a git checkout; refusing to overwrite. Use reset-installation.sh first if this is intentional."
fi
if [[ -d "$INSTALL_DIR/.git" ]]; then
  python3 - "$INSTALL_DIR" <<'PY'
import json
import sys
from pathlib import Path
install = Path(sys.argv[1]).resolve()
state_path = install / '.installer-state.json'
try:
    state = json.loads(state_path.read_text())
except (OSError, ValueError) as exc:
    raise SystemExit(f'existing restore target lacks valid lifecycle-manager state: {exc}')
if state.get('installer') != 'misp-docker-lifecycle-manager':
    raise SystemExit('existing restore target has an unexpected installer identity')
recorded = state.get('install_dir')
if not isinstance(recorded, str) or Path(recorded).resolve() != install:
    raise SystemExit('existing restore target state does not match the requested install directory')
PY
  existing_origin="$(git -C "$INSTALL_DIR" remote get-url origin)"
  validate_upstream_source "$existing_origin" "$UPSTREAM_REF"
  [[ "$existing_origin" == "$UPSTREAM_REPO" ]] || fatal "Existing restore target origin does not match the selected upstream repository."
fi

if [[ -f "$INSTALL_DIR/.env" && ( -f "$INSTALL_DIR/docker-compose.yml" || -f "$INSTALL_DIR/compose.yml" ) ]]; then
  log "Stopping/removing existing deployment resources for restore."
  compose_cmd "$INSTALL_DIR" down --volumes --remove-orphans
fi

"$SCRIPT_DIR/fetch-upstream.sh" --upstream-repo "$UPSTREAM_REPO" --upstream-ref "$UPSTREAM_REF" --install-dir "$INSTALL_DIR"

log "Restoring generated deployment configuration."
tar --no-same-owner --no-same-permissions -C "$INSTALL_DIR" -xzf "$BACKUP_DIR/misp-config.tar.gz"
chmod 600 "$INSTALL_DIR/.env"

python3 - "$INSTALL_DIR/.env" "$archived_exposure" "$archived_base_url" <<'PY' > "$tmp/restored-state-values"
import sys
from pathlib import Path
env_path, exposure, base_url = sys.argv[1:]
env = {}
for line in Path(env_path).read_text(errors='strict').splitlines():
    stripped = line.strip()
    if stripped and not stripped.startswith('#') and '=' in stripped:
        key, value = stripped.split('=', 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
if not base_url:
    base_url = env.get('BASE_URL', '')
if not exposure:
    https_port = env.get('CORE_HTTPS_PORT', '')
    exposure = 'reverse-proxy' if https_port.startswith('127.0.0.1:') else 'direct-qa'
if exposure not in {'reverse-proxy', 'direct-qa'} or not base_url:
    raise SystemExit('restored configuration lacks valid exposure/base URL metadata')
if any(ord(ch) < 32 or ord(ch) == 127 for value in (exposure, base_url) for ch in value):
    raise SystemExit('restored exposure/base URL metadata contains control characters')
print(exposure)
print(base_url)
PY
mapfile -t restored_state_vals < "$tmp/restored-state-values"
restored_exposure="${restored_state_vals[0]:-}"
restored_base_url="${restored_state_vals[1]:-}"
validate_public_base_url "$restored_base_url" "$restored_exposure"
resolved_upstream_commit="$(git -C "$INSTALL_DIR" rev-parse HEAD)"
write_state "$INSTALL_DIR/.installer-state.json" "$UPSTREAM_REPO" "$resolved_upstream_commit" "$INSTALL_DIR" "$restored_exposure" "$restored_base_url"

log "Restoring host-mounted data directories."
sudo tar -C "$INSTALL_DIR" -xzf "$BACKUP_DIR/misp-host-data.tar.gz"

"$SCRIPT_DIR/validate.sh" --install-dir "$INSTALL_DIR"

log "Starting database service for restore."
compose_cmd "$INSTALL_DIR" up -d db redis
for attempt in {1..60}; do
  if compose_cmd "$INSTALL_DIR" exec -T db sh -lc '
    cfg="$(mktemp)"; trap '\''rm -f "$cfg"'\'' EXIT
    printf "[client]\nuser=%s\npassword=%s\n" "$MYSQL_USER" "$MYSQL_PASSWORD" > "$cfg"
    mariadb-admin --defaults-extra-file="$cfg" ping >/dev/null 2>&1
  '; then
    break
  fi
  if [[ "$attempt" == 60 ]]; then
    fatal "Database did not become ready for restore import"
  fi
  sleep 5
done

log "Importing database dump."
compose_cmd "$INSTALL_DIR" exec -T db sh -lc '
  cfg="$(mktemp)"; trap '\''rm -f "$cfg"'\'' EXIT
  printf "[client]\nuser=%s\npassword=%s\n" "$MYSQL_USER" "$MYSQL_PASSWORD" > "$cfg"
  mariadb --defaults-extra-file="$cfg" "$MYSQL_DATABASE"
' < "$BACKUP_DIR/misp.sql"

log "Starting restored stack."
compose_cmd "$INSTALL_DIR" up -d
wait_for_misp_core "$INSTALL_DIR" 600
run_misp_db_updates "$INSTALL_DIR"
check_misp_schema_ready "$INSTALL_DIR"
wait_for_misp_live_marker "$INSTALL_DIR" 900
"$SCRIPT_DIR/doctor.sh" --install-dir "$INSTALL_DIR"

log "Restore completed for $INSTALL_DIR"
