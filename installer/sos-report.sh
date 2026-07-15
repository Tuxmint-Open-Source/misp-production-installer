#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Generate a public-safe anonymous SOS report for bug reports.

Usage:
  ./installer/sos-report.sh [options]

Options:
  --install-dir PATH      Deployment directory (default: /opt/misp-docker)
  --output PATH           Write report to PATH (default: ./misp-sos-report.md)
  --format markdown       Output format; only markdown is currently supported
  --workflow NAME         Affected workflow label to include in the report
  --no-docker             Do not call Docker or Docker Compose
  --no-health-commands    Do not run doctor/status/login-check summaries
  --explain-redaction     Include redaction guidance in the generated report
  -h, --help              Show this help
  --version               Show manager version

The report is designed for public GitHub bug reports. It does not collect raw
logs, .env contents, .installer-state.json contents, database dumps, backup
contents, generated configuration archives, or MISP event/user data.

Review the generated file before posting it publicly. If the issue cannot be
explained safely in public, use SECURITY.md and private vulnerability reporting.
EOF
}

INSTALL_DIR="/opt/misp-docker"
OUTPUT="./misp-sos-report.md"
FORMAT="markdown"
WORKFLOW="unknown"
USE_DOCKER=1
USE_HEALTH_COMMANDS=1
EXPLAIN_REDACTION=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --output) OUTPUT="$2"; shift 2;;
    --format) FORMAT="$2"; shift 2;;
    --workflow) WORKFLOW="$2"; shift 2;;
    --no-docker) USE_DOCKER=0; USE_HEALTH_COMMANDS=0; shift;;
    --no-health-commands) USE_HEALTH_COMMANDS=0; shift;;
    --explain-redaction) EXPLAIN_REDACTION=1; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

[[ "$FORMAT" == "markdown" ]] || fatal "Only --format markdown is currently supported"

redact() {
  python3 "$PROJECT_ROOT/scripts/redact-sos-report.py" "$INSTALL_DIR"
}

sanitize_value() {
  printf '%s' "${1:-unknown}" | redact
}

bool_exists() {
  [[ -e "$1" ]] && printf 'yes' || printf 'no'
}

file_mode_or_missing() {
  if [[ -e "$1" ]]; then
    stat -c '%a' "$1" 2>/dev/null || printf 'unknown'
  else
    printf 'missing'
  fi
}

safe_cmd_one_line() {
  local output status
  set +e
  output="$("$@" 2>&1)"
  status=$?
  set -e
  output="$(printf '%s' "$output" | tr '\n' ' ' | redact)"
  if [[ $status -eq 0 ]]; then
    printf '%s' "${output:-available}"
  else
    printf 'unavailable'
  fi
}

safe_env_value() {
  local key="$1" env_file="$INSTALL_DIR/.env"
  [[ -f "$env_file" ]] || { printf 'unknown'; return; }
  python3 - "$env_file" "$key" <<'PY' | redact
from pathlib import Path
import re
import sys
path = Path(sys.argv[1])
key = sys.argv[2]
value = 'unknown'
for line in path.read_text(errors='ignore').splitlines():
    if line.startswith(key + '='):
        value = line.split('=', 1)[1].strip()
        break
# Component tags are expected to be public image tags. If the value contains
# registry paths, whitespace, shell syntax, or surprising punctuation, redact it.
if value != 'unknown' and not re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}', value):
    value = '[REDACTED]'
print(value)
PY
}

container_summary() {
  if [[ "$USE_DOCKER" -ne 1 ]]; then
    printf 'not checked (--no-docker)'
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    printf 'docker command unavailable'
    return
  fi
  if [[ ! -d "$INSTALL_DIR" || ! -f "$INSTALL_DIR/docker-compose.yml" || ! -f "$INSTALL_DIR/.env" ]]; then
    printf 'not checked (install directory incomplete)'
    return
  fi
  local output status
  set +e
  output="$(compose_cmd "$INSTALL_DIR" ps --format 'table {{.Service}}\t{{.State}}\t{{.Health}}' 2>&1)"
  status=$?
  set -e
  if [[ $status -ne 0 ]]; then
    printf 'docker compose status unavailable'
    return
  fi
  printf '%s' "$output" | redact
}

health_command_summary() {
  local name="$1"; shift
  if [[ "$USE_HEALTH_COMMANDS" -ne 1 ]]; then
    printf '%s: not checked (--no-health-commands or --no-docker)\n' "$name"
    return
  fi
  if [[ ! -d "$INSTALL_DIR" || ! -f "$INSTALL_DIR/docker-compose.yml" || ! -f "$INSTALL_DIR/.env" ]]; then
    printf '%s: not checked (install directory incomplete)\n' "$name"
    return
  fi
  if [[ "$USE_DOCKER" -ne 1 ]]; then
    printf '%s: not checked (--no-docker)\n' "$name"
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    printf '%s: unavailable (docker command missing)\n' "$name"
    return
  fi

  local output status first_lines
  set +e
  output="$("$@" 2>&1)"
  status=$?
  set -e
  first_lines="$(printf '%s\n' "$output" | redact | sed -n '1,12p')"
  if [[ $status -eq 0 ]]; then
    printf '%s: passed\n' "$name"
  else
    printf '%s: failed (exit %s)\n' "$name" "$status"
  fi
  if [[ -n "$first_lines" ]]; then
    printf '%s\n' "$first_lines"
  fi
}

health_summaries() {
  health_command_summary "doctor.sh" "$SCRIPT_DIR/doctor.sh" --install-dir "$INSTALL_DIR"
  printf '\n'
  health_command_summary "status.sh" "$SCRIPT_DIR/status.sh" --install-dir "$INSTALL_DIR"
  printf '\n'
  health_command_summary "login-check.sh" "$SCRIPT_DIR/login-check.sh" --install-dir "$INSTALL_DIR" --machine-readable
}

backup_shape_summary() {
  local backup_root="$INSTALL_DIR/backups"
  if [[ ! -d "$backup_root" ]]; then
    printf 'Backup directory present: no\n'
    return
  fi
  local count
  count="$(find "$backup_root" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
  printf 'Backup directory present: yes\n'
  printf 'Backup set count: %s\n' "${count:-0}"
  if [[ "${count:-0}" != "0" ]]; then
    printf 'Latest backup detected: yes\n'
  fi
}

mkdir -p "$(dirname "$OUTPUT")"
TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

safe_install_dir="/opt/misp-docker"
[[ "$INSTALL_DIR" == "/opt/misp-docker" ]] || safe_install_dir="[REDACTED_PATH]"

os_summary="unknown"
if [[ -f /etc/os-release ]]; then
  os_summary="$(python3 - <<'PY'
from pathlib import Path
values = {}
for line in Path('/etc/os-release').read_text(errors='ignore').splitlines():
    if '=' in line:
        k, v = line.split('=', 1)
        values[k] = v.strip().strip('"')
print(values.get('PRETTY_NAME') or values.get('NAME') or 'unknown')
PY
)"
fi
kernel_summary="$(uname -r 2>/dev/null || printf 'unknown')"
arch_summary="$(uname -m 2>/dev/null || printf 'unknown')"
docker_summary="$(safe_cmd_one_line docker --version)"
compose_summary="$(safe_cmd_one_line docker compose version)"
manager_version="$(print_version)"

git_ref="unknown"
if command -v git >/dev/null 2>&1 && git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_ref="$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
fi

{
  cat <<EOF
# MISP Docker Lifecycle Manager SOS Report

## Safety notice
Generated locally. Review before sharing publicly. Do not post this report if it still contains secrets, credentials, private hostnames/IPs, internal topology, raw logs, database dumps, backup contents, generated configuration, or deployment-specific data.

## Summary
- Manager version/ref: $(sanitize_value "$manager_version")
- Manager git ref: $(sanitize_value "$git_ref")
- Report format: generated-sos-v1
- Affected workflow: $(sanitize_value "$WORKFLOW")

## Environment
- OS: $(sanitize_value "$os_summary")
- Kernel: $(sanitize_value "$kernel_summary")
- Architecture: $(sanitize_value "$arch_summary")
- Docker: $(sanitize_value "$docker_summary")
- Docker Compose: $(sanitize_value "$compose_summary")

## Installation shape
- Install directory used: $safe_install_dir
- Install directory present: $(bool_exists "$INSTALL_DIR")
- docker-compose.yml present: $(bool_exists "$INSTALL_DIR/docker-compose.yml")
- docker-compose.override.yml present: $(bool_exists "$INSTALL_DIR/docker-compose.override.yml")
- .env present: $(bool_exists "$INSTALL_DIR/.env")
- .env permissions: $(file_mode_or_missing "$INSTALL_DIR/.env")
- .installer-state.json present: $(bool_exists "$INSTALL_DIR/.installer-state.json")
- .installer-state.json permissions: $(file_mode_or_missing "$INSTALL_DIR/.installer-state.json")

## Component versions
- CORE_TAG: $(safe_env_value CORE_TAG)
- MODULES_TAG: $(safe_env_value MODULES_TAG)
- GUARD_TAG: $(safe_env_value GUARD_TAG)
- CORE_RUNNING_TAG: $(safe_env_value CORE_RUNNING_TAG)
- MODULES_RUNNING_TAG: $(safe_env_value MODULES_RUNNING_TAG)
- GUARD_RUNNING_TAG: $(safe_env_value GUARD_RUNNING_TAG)

## Health summary
- Docker checks enabled: $([[ "$USE_DOCKER" -eq 1 ]] && printf 'yes' || printf 'no')
- Health command summaries enabled: $([[ "$USE_HEALTH_COMMANDS" -eq 1 ]] && printf 'yes' || printf 'no')
- Compose/container status:

\`\`\`text
$(container_summary)
\`\`\`

## Command summaries
These are concise, redacted summaries. Raw logs are not included.

\`\`\`text
$(health_summaries)
\`\`\`

## Backup shape summary
This section reports backup presence only. It does not include backup names, backup paths, backup contents, database dumps, generated configuration, or checksums.

\`\`\`text
$(backup_shape_summary)
\`\`\`

## Reproduction prompt
Please add these details before posting the report:

1. Expected behavior.
2. Actual behavior.
3. Sanitized command shape.
4. Whether this reproduces on a fresh install.

## Redaction summary
This report redacts URLs, hostnames, IP addresses, email addresses, secret-like key/value pairs, home paths, root paths, and long hex identifiers before writing public-facing command output.
EOF

  if [[ "$EXPLAIN_REDACTION" -eq 1 ]]; then
    cat <<'EOF'

## Redaction guidance
- Replace private or public IP addresses with `[REDACTED_IP]`.
- Replace real hostnames with `[REDACTED_HOST]`.
- Replace email addresses with `[REDACTED_EMAIL]`.
- Replace token/password-like values with `[REDACTED_SECRET]`.
- Replace deployment-specific paths with `[REDACTED_PATH]`.
- Prefer over-redaction. Maintainers can ask for more public-safe details if needed.
EOF
  fi
} > "$TMP_OUTPUT"

# Final safety pass over the whole report before writing it.
redact < "$TMP_OUTPUT" > "$OUTPUT"
chmod 600 "$OUTPUT" 2>/dev/null || true
printf 'SOS report written to %s\n' "$OUTPUT"
printf 'Review the report before posting it publicly. Use SECURITY.md for sensitive issues.\n'
