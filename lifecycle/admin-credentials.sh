#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Show the configured initial MISP administrator account.

Usage:
  ./lifecycle/admin-credentials.sh [options]

Options:
  --install-dir PATH   Deployment directory (default: /opt/misp-docker)
  --show-password      Print the configured ADMIN_PASSWORD value
  -h, --help           Show this help
  --version            Show manager version

By default the password is not printed. Use --show-password only on a trusted
terminal, because the value is sensitive.
EOF
}

INSTALL_DIR="/opt/misp-docker"
SHOW_PASSWORD="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --show-password) SHOW_PASSWORD="true"; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

ENV_FILE="$INSTALL_DIR/.env"
[[ -f "$ENV_FILE" ]] || fatal "$ENV_FILE missing"

python3 - "$ENV_FILE" "$SHOW_PASSWORD" <<'PY'
from pathlib import Path
import sys

env_file = Path(sys.argv[1])
show_password = sys.argv[2] == 'true'
values = {}
for line in env_file.read_text(errors='ignore').splitlines():
    stripped = line.strip()
    if stripped and not stripped.startswith('#') and '=' in stripped:
        key, value = stripped.split('=', 1)
        values[key] = value

email = values.get('ADMIN_EMAIL', '')
password = values.get('ADMIN_PASSWORD', '')
base_url = values.get('BASE_URL', '')

if not email:
    raise SystemExit('ADMIN_EMAIL is missing in .env')
if not password:
    raise SystemExit('ADMIN_PASSWORD is missing in .env')

print(f'BASE_URL={base_url or "(not set)"}')
print(f'ADMIN_EMAIL={email}')
if show_password:
    print(f'ADMIN_PASSWORD={password}')
else:
    print('ADMIN_PASSWORD=(hidden; rerun with --show-password to print it)')
PY
