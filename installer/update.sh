#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Update an existing MISP Docker deployment managed by this installer.

Usage:
  ./installer/update.sh [options]

What this script does:
  1. Creates a backup before changing anything.
  2. Fetches official MISP/misp-docker updates.
  3. Checks out the requested upstream ref or fast-forwards the current branch.
  4. Synchronizes MISP component image tags from upstream template.env.
  5. Re-renders the local Compose override.
  6. Pulls images, restarts containers, runs MISP DB updates, and runs doctor.

Options:
  --install-dir PATH   Existing deployment directory (default: /opt/misp-docker)
  --upstream-ref REF   Optional upstream MISP/misp-docker branch or commit
  --core-tag TAG       Explicit misp-core image/component tag override
  --modules-tag TAG    Explicit misp-modules image/component tag override
  --guard-tag TAG      Explicit misp-guard image/component tag override
  --image-track MODE   Image tracking mode: version-tags, latest, or keep
                       default: version-tags
  --backup-root PATH   Backup output directory passed to backup.sh
  -h, --help           Show this help
  --version            Show manager version

Versioning note:
  --upstream-ref controls the official MISP/misp-docker checkout. Runtime images
  are controlled by CORE_RUNNING_TAG, MODULES_RUNNING_TAG, and GUARD_RUNNING_TAG.
  By default this script pins them to the official component tags declared in the
  checked-out upstream template.env. The installer itself is versioned separately.
EOF
}

INSTALL_DIR="/opt/misp-docker"
UPSTREAM_REF=""
CORE_TAG_OVERRIDE=""
MODULES_TAG_OVERRIDE=""
GUARD_TAG_OVERRIDE=""
IMAGE_TRACK="version-tags"
BACKUP_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --upstream-ref) UPSTREAM_REF="$2"; shift 2;;
    --core-tag) CORE_TAG_OVERRIDE="$2"; shift 2;;
    --modules-tag) MODULES_TAG_OVERRIDE="$2"; shift 2;;
    --guard-tag) GUARD_TAG_OVERRIDE="$2"; shift 2;;
    --image-track) IMAGE_TRACK="$2"; shift 2;;
    --backup-root) BACKUP_ROOT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

[[ "$IMAGE_TRACK" =~ ^(version-tags|latest|keep)$ ]] || fatal "--image-track must be version-tags, latest, or keep"
[[ -z "$UPSTREAM_REF" ]] || validate_upstream_source "https://github.com/MISP/misp-docker.git" "$UPSTREAM_REF"
[[ -d "$INSTALL_DIR/.git" ]] || fatal "$INSTALL_DIR is not an upstream git checkout"
state_file="$INSTALL_DIR/.installer-state.json"
[[ -f "$state_file" ]] || fatal "$state_file missing; refusing to update an unmarked checkout"
state_values_file="$(mktemp)"
trap 'rm -f "$state_values_file"' EXIT
python3 - "$state_file" "$INSTALL_DIR" <<'PY' > "$state_values_file"
import json
import sys
from pathlib import Path
state = json.loads(Path(sys.argv[1]).read_text())
if state.get('installer') != 'misp-docker-lifecycle-manager':
    raise SystemExit('unexpected installer identity in state file')
recorded_install = state.get('install_dir')
repo = state.get('upstream_repo')
exposure = state.get('exposure')
base_url = state.get('base_url')
if not all(isinstance(value, str) for value in (recorded_install, repo, exposure, base_url)):
    raise SystemExit('state source/deployment fields must be strings')
if Path(recorded_install).resolve() != Path(sys.argv[2]).resolve():
    raise SystemExit('state install directory does not match update target')
if not repo or exposure not in {'reverse-proxy', 'direct-qa'} or not base_url:
    raise SystemExit('state file lacks valid repository/exposure/base URL metadata')
if any(ord(ch) < 32 or ord(ch) == 127 for value in (repo, exposure, base_url) for ch in value):
    raise SystemExit('state source/deployment fields contain control characters')
print(repo)
print(exposure)
print(base_url)
PY
mapfile -t state_vals < "$state_values_file"
state_repo="${state_vals[0]:-}"
state_exposure="${state_vals[1]:-}"
state_base_url="${state_vals[2]:-}"
validate_upstream_source "$state_repo" "${UPSTREAM_REF:-HEAD}"
validate_public_base_url "$state_base_url" "$state_exposure"
origin_url="$(git -C "$INSTALL_DIR" remote get-url origin)"
validate_upstream_source "$origin_url" "${UPSTREAM_REF:-HEAD}"
[[ "$origin_url" == "$state_repo" ]] || fatal "Git origin does not match lifecycle-manager state; refusing update."
old_ref="$(git -C "$INSTALL_DIR" rev-parse --short HEAD)"

# Always back up first. MISP updates may include database migrations.
backup_args=(--install-dir "$INSTALL_DIR")
[[ -n "$BACKUP_ROOT" ]] && backup_args+=(--backup-root "$BACKUP_ROOT")
"$SCRIPT_DIR/backup.sh" "${backup_args[@]}"
git -C "$INSTALL_DIR" fetch --tags origin

if [[ -n "$UPSTREAM_REF" ]]; then
  git -C "$INSTALL_DIR" checkout "$UPSTREAM_REF"
else
  git -C "$INSTALL_DIR" pull --ff-only
fi

log "Synchronizing MISP image tags (track: $IMAGE_TRACK)"
sync_misp_image_tags "$INSTALL_DIR" "$IMAGE_TRACK" "$CORE_TAG_OVERRIDE" "$MODULES_TAG_OVERRIDE" "$GUARD_TAG_OVERRIDE"
"$SCRIPT_DIR/render-compose.sh" --install-dir "$INSTALL_DIR"
"$SCRIPT_DIR/validate.sh" --install-dir "$INSTALL_DIR"
compose_cmd "$INSTALL_DIR" pull
compose_cmd "$INSTALL_DIR" up -d
wait_for_misp_core "$INSTALL_DIR" 600
run_misp_db_updates "$INSTALL_DIR"
check_misp_schema_ready "$INSTALL_DIR"
wait_for_misp_live_marker "$INSTALL_DIR" 900
"$SCRIPT_DIR/doctor.sh" --install-dir "$INSTALL_DIR"

new_commit="$(git -C "$INSTALL_DIR" rev-parse HEAD)"
write_state "$state_file" "$origin_url" "$new_commit" "$INSTALL_DIR" "$state_exposure" "$state_base_url"
new_ref="$(git -C "$INSTALL_DIR" rev-parse --short HEAD)"
log "Updated upstream $old_ref -> $new_ref"
log "Interactive login: ready (MISP live marker observed)."
