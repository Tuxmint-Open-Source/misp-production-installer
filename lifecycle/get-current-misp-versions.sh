#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Show official MISP Docker component versions from upstream template.env.

Usage:
  ./lifecycle/get-current-misp-versions.sh [options]

Options:
  --upstream-repo URL   MISP/misp-docker repo URL (default: https://github.com/MISP/misp-docker.git)
  --upstream-ref REF    Upstream branch, commit, or ref to inspect (default: master)
  --install-dir PATH    Optional existing install dir; compare local .env when provided
  -h, --help            Show this help
  --version             Show manager version

This command does not change the installation. Without --install-dir it shows
upstream component versions only. With --install-dir it also compares local .env
component metadata and runtime image pins.
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
validate_upstream_source "$UPSTREAM_REPO" "$UPSTREAM_REF"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

git clone --depth 1 --filter=blob:none --no-checkout -- "$UPSTREAM_REPO" "$TMPDIR/upstream" >/dev/null 2>&1 || fatal "Failed to clone $UPSTREAM_REPO"
git -C "$TMPDIR/upstream" fetch --depth 1 origin "$UPSTREAM_REF" >/dev/null 2>&1 || fatal "Failed to resolve requested upstream ref"
git -C "$TMPDIR/upstream" checkout --quiet --detach FETCH_HEAD
[[ -f "$TMPDIR/upstream/template.env" ]] || fatal "template.env not found at upstream ref $UPSTREAM_REF"
UPSTREAM_COMMIT="$(git -C "$TMPDIR/upstream" rev-parse --short HEAD)"

python3 - "$TMPDIR/upstream/template.env" "${INSTALL_DIR:-}" "$UPSTREAM_REF" "$UPSTREAM_COMMIT" <<'PY'
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
upstream_ref = sys.argv[3]
upstream_commit = sys.argv[4]
upstream = parse_active(upstream_template)
local_env = Path(install_dir) / '.env' if install_dir else None
local = parse_active(local_env) if local_env else {}
local_checked = bool(install_dir)
local_exists = bool(local_env and local_env.exists())

rows = [
    ('Core', 'CORE_TAG', 'CORE_RUNNING_TAG'),
    ('Modules', 'MODULES_TAG', 'MODULES_RUNNING_TAG'),
    ('Guard', 'GUARD_TAG', 'GUARD_RUNNING_TAG'),
]

print('MISP Docker component versions')
print('==============================')
print(f'Upstream ref:    {upstream_ref}')
print(f'Upstream commit: {upstream_commit}')
if local_checked:
    print(f'Install dir:     {install_dir}')
    if not local_exists:
        print('Local .env:      missing')
else:
    print('Install dir:     not provided; local columns are omitted')
print()

if local_checked:
    print(f'{"Component":<10} {"Upstream":<14} {"Local metadata":<16} {"Runtime image":<16}')
    print(f'{"-"*10} {"-"*14} {"-"*16} {"-"*16}')
    for component, component_key, running_key in rows:
        upstream_value = upstream.get(component_key, 'missing')
        local_component = local.get(component_key, 'missing') if local_exists else 'missing'
        local_running = local.get(running_key, 'unset -> latest') if local_exists else 'missing'
        print(f'{component:<10} {upstream_value:<14} {local_component:<16} {local_running:<16}')
else:
    print(f'{"Component":<10} {"Upstream tag":<14}')
    print(f'{"-"*10} {"-"*14}')
    for component, component_key, _running_key in rows:
        print(f'{component:<10} {upstream.get(component_key, "missing"):<14}')
PY
