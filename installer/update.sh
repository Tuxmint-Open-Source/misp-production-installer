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
  4. Re-renders the local Compose override.
  5. Pulls images, restarts containers, runs MISP DB updates, and runs doctor.

Options:
  --install-dir PATH   Existing deployment directory (default: /opt/misp-docker)
  --upstream-ref REF   Optional upstream MISP/misp-docker tag, branch, or commit
  -h, --help           Show this help
  --version            Show installer version

Versioning note:
  --upstream-ref controls the MISP/misp-docker version. The installer itself is
  versioned separately with VERSION, CHANGELOG.md, and Git tags.
EOF
}

INSTALL_DIR="/opt/misp-docker"
UPSTREAM_REF=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --upstream-ref) UPSTREAM_REF="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

[[ -d "$INSTALL_DIR/.git" ]] || fatal "$INSTALL_DIR is not an upstream git checkout"
old_ref="$(git -C "$INSTALL_DIR" rev-parse --short HEAD)"

# Always back up first. MISP updates may include database migrations.
"$SCRIPT_DIR/backup.sh" --install-dir "$INSTALL_DIR"
git -C "$INSTALL_DIR" fetch --tags origin

if [[ -n "$UPSTREAM_REF" ]]; then
  git -C "$INSTALL_DIR" checkout "$UPSTREAM_REF"
else
  git -C "$INSTALL_DIR" pull --ff-only
fi

"$SCRIPT_DIR/render-compose.sh" --install-dir "$INSTALL_DIR"
"$SCRIPT_DIR/validate.sh" --install-dir "$INSTALL_DIR"
compose_cmd "$INSTALL_DIR" pull
compose_cmd "$INSTALL_DIR" up -d
wait_for_misp_core "$INSTALL_DIR" 600
run_misp_db_updates "$INSTALL_DIR"
check_misp_schema_ready "$INSTALL_DIR"
"$SCRIPT_DIR/doctor.sh" --install-dir "$INSTALL_DIR"

new_ref="$(git -C "$INSTALL_DIR" rev-parse --short HEAD)"
log "Updated upstream $old_ref -> $new_ref"
