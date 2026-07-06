#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Show official MISP Docker component versions from upstream template.env.

Usage:
  ./installer/get-current-misp-versions.sh [options]

Options:
  --upstream-repo URL   MISP/misp-docker repo URL (default: https://github.com/MISP/misp-docker.git)
  --upstream-ref REF    Upstream branch, commit, or ref to inspect (default: master)
  --install-dir PATH    Optional existing install dir; compare local .env when provided
  -h, --help            Show this help
  --version             Show installer version

This command does not change the installation. It only reports the component
versions declared by official upstream template.env and, when --install-dir is
provided, the currently configured local image tags.
EOF
}

UPSTREAM_REPO="https://github.com/MISP/misp-docker.git"
UPSTREAM_REF="master"
INSTALL_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream-repo) UPSTREAM_REPO="$2"; shift 2;;
    --upstream-ref) UPSTREAM_REF="$2"; shift 2;;
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

require_cmd git
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

git clone --depth 1 --filter=blob:none --no-checkout "$UPSTREAM_REPO" "$TMPDIR/upstream" >/dev/null 2>&1 || fatal "Failed to clone $UPSTREAM_REPO"
git -C "$TMPDIR/upstream" fetch --depth 1 origin "$UPSTREAM_REF" >/dev/null 2>&1 || true
git -C "$TMPDIR/upstream" checkout --quiet "$UPSTREAM_REF" 2>/dev/null || git -C "$TMPDIR/upstream" checkout --quiet FETCH_HEAD
[[ -f "$TMPDIR/upstream/template.env" ]] || fatal "template.env not found at upstream ref $UPSTREAM_REF"

python3 - "$TMPDIR/upstream/template.env" "${INSTALL_DIR:-}" <<'PY'
from pathlib import Path
import sys

def parse_active(path):
    values = {}
    if not path or not Path(path).exists():
        return values
    for line in Path(path).read_text(errors='ignore').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        values[key.strip()] = value.strip()
    return values

upstream_template = Path(sys.argv[1])
install_dir = sys.argv[2]
upstream = parse_active(upstream_template)
local = parse_active(Path(install_dir) / '.env') if install_dir else {}

rows = [
    ('core', 'CORE_TAG', 'CORE_RUNNING_TAG'),
    ('modules', 'MODULES_TAG', 'MODULES_RUNNING_TAG'),
    ('guard', 'GUARD_TAG', 'GUARD_RUNNING_TAG'),
]
print('component upstream_tag local_component_tag local_running_tag')
for component, component_key, running_key in rows:
    print(
        component,
        upstream.get(component_key, '(missing)'),
        local.get(component_key, '(not checked)' if not local else '(missing)'),
        local.get(running_key, '(not checked)' if not local else '(unset -> latest)'),
    )
PY
