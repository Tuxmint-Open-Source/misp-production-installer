#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Generate a bounded, allowlisted anonymous SOS report for public bug reports.

Usage:
  ./lifecycle/sos-report.sh [options]

Options:
  --install-dir PATH      Deployment directory (default: /opt/misp-docker)
  --output PATH           Write report to PATH (default: ./misp-sos-report.md)
  --format markdown       Output format; only markdown is currently supported
  --workflow NAME         Affected workflow from the documented fixed vocabulary
  --no-docker             Do not query Docker, Compose, or deployment health
  --no-health-commands    Do not run the bounded structured health check
  --explain-redaction     Explain the v2 allowlist privacy model in the report
  --timeout SECONDS       Global deadline for all SOS probes (default: 20)
  -h, --help              Show this help
  --version               Show manager version

Allowed workflow values:
  unknown, fresh-install, install, update, backup, restore, rollback, reset,
  doctor, status, login-check, monitoring, documentation, other

The v2 report emits only bounded structured facts. It never includes raw command
output, URLs, hostnames, IPs, email addresses, topology, logs, backup metadata,
.env/state contents beyond validated public component tags, or MISP business data.

Review the generated file before posting it publicly. If the issue cannot be
explained safely in public, use SECURITY.md and private vulnerability reporting.
EOF
}

for argument in "$@"; do
  case "$argument" in
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
  esac
done

exec python3 "$PROJECT_ROOT/scripts/generate_sos_report.py" "$@"
