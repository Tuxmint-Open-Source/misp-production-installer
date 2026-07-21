#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Run bounded, monitoring-friendly health checks for a managed MISP Docker deployment.

Usage:
  ./installer/healthcheck.sh [options]

Options:
  --install-dir PATH      Deployment directory (default: /opt/misp-docker)
  --format FORMAT         Output format: text, json, nagios, checkmk, prometheus (default: text)
  --checks LIST           Comma-separated checks to run (default: compose-config,compose-services,misp-heartbeat,schema-ready)
  --timeout SECONDS       Global deadline for the complete health command (default: 20)
  --strict-tls            Verify TLS certificates for login checks (default)
  --insecure              Explicitly allow insecure transport for login checks
  --no-login              Remove login from the selected checks
  -h, --help              Show this help
  --version               Show manager version

Check IDs:
  compose-config          Validate generated Docker Compose config
  compose-services        Count expected/running Compose services
  misp-heartbeat          Query the container-local MISP heartbeat endpoint
  schema-ready            Confirm schema readiness required by login-dependent workflows
  login                   Optional CSRF-aware Web UI login check without printing the password
  backup-freshness        Reserved for future backup freshness thresholds
  version-drift           Reserved for future local/upstream component drift checks

Exit codes:
  0 OK                    Required deployment checks are healthy
  1 WARNING               Deployment is usable but an operator should investigate
  2 CRITICAL              Required service/readiness check failed
  3 UNKNOWN               Health could not be determined due local execution/config problems

Formats:
  text                    Human-friendly one-line status plus check summaries
  json                    Stable JSON schema: misp-docker-lifecycle-manager-health-v1
  nagios                  Nagios/Icinga plugin-style first line with perfdata
  checkmk                 Checkmk local-check line
  prometheus              Prometheus text exposition with low-cardinality metrics

Monitoring output is public-adjacent. It never prints generated secrets, raw .env
values, backup names/paths, raw logs, MISP data, or deployment topology.
EOF
}

INSTALL_DIR="/opt/misp-docker"
FORMAT="text"
CHECKS="compose-config,compose-services,misp-heartbeat,schema-ready"
TIMEOUT_SECONDS="20"
INSECURE="false"
STRICT_TLS_SEEN="false"
INSECURE_SEEN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --format) FORMAT="$2"; shift 2;;
    --checks) CHECKS="$2"; shift 2;;
    --timeout) TIMEOUT_SECONDS="$2"; shift 2;;
    --strict-tls) INSECURE="false"; STRICT_TLS_SEEN="true"; shift;;
    --insecure) INSECURE="true"; INSECURE_SEEN="true"; shift;;
    --no-login) CHECKS=",$CHECKS,"; CHECKS="${CHECKS//,login,/,}"; CHECKS="${CHECKS#,}"; CHECKS="${CHECKS%,}"; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done
[[ "$STRICT_TLS_SEEN" != true || "$INSECURE_SEEN" != true ]] || fatal "--strict-tls and --insecure cannot be used together"

[[ "$FORMAT" =~ ^(text|json|nagios|checkmk|prometheus)$ ]] || fatal "format must be text, json, nagios, checkmk, or prometheus"
[[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || fatal "timeout must be a positive integer"
(( TIMEOUT_SECONDS > 0 )) || fatal "timeout must be greater than zero"

python3 - "$INSTALL_DIR" "$FORMAT" "$CHECKS" "$TIMEOUT_SECONDS" "$INSECURE" "$SCRIPT_DIR" <<'PY'
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import urllib.request
import ssl
import time
from pathlib import Path
from typing import Any

install_dir = Path(sys.argv[1])
output_format = sys.argv[2]
checks_arg = sys.argv[3]
timeout = int(sys.argv[4])
insecure = sys.argv[5] == 'true'
script_dir = Path(sys.argv[6])

STATUS_RANK = {'ok': 0, 'warning': 1, 'critical': 2, 'unknown': 3}
EXIT_CODE = {'ok': 0, 'warning': 1, 'critical': 2, 'unknown': 3}
STATUS_LABEL = {'ok': 'OK', 'warning': 'WARNING', 'critical': 'CRITICAL', 'unknown': 'UNKNOWN'}
VALID_CHECKS = {
    'compose-config', 'compose-services', 'misp-heartbeat', 'schema-ready',
    'login', 'backup-freshness', 'version-drift'
}
RESERVED_CHECKS = {'backup-freshness', 'version-drift'}
deadline = time.monotonic() + timeout

selected = [item.strip() for item in checks_arg.split(',') if item.strip()]
if not selected:
    selected = ['compose-config', 'compose-services', 'misp-heartbeat', 'schema-ready']
unknown = [item for item in selected if item not in VALID_CHECKS]
if unknown:
    print(f"UNKNOWN - unsupported check id(s): {', '.join(unknown)}")
    sys.exit(3)

checks: list[dict[str, Any]] = []
metrics: dict[str, int | float] = {
    'checks_ok': 0,
    'checks_warning': 0,
    'checks_critical': 0,
    'checks_unknown': 0,
}

def add_check(check_id: str, status: str, summary: str, metric_updates: dict[str, int | float] | None = None) -> None:
    checks.append({'id': check_id, 'status': status, 'summary': summary})
    metrics[f'checks_{status}'] = int(metrics.get(f'checks_{status}', 0)) + 1
    if metric_updates:
        metrics.update(metric_updates)

def run_cmd(args: list[str], cwd: Path | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired(args, timeout)
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=remaining,
        check=False,
    )

def compose_args(*args: str) -> list[str]:
    files = ['-f', 'docker-compose.yml']
    if (install_dir / 'docker-compose.override.yml').exists():
        files += ['-f', 'docker-compose.override.yml']
    return ['docker', 'compose', '--env-file', '.env', *files, *args]

def preflight() -> bool:
    if not install_dir.exists():
        add_check('preflight', 'unknown', 'install directory is missing')
        return False
    if not (install_dir / '.env').exists():
        add_check('preflight', 'unknown', '.env is missing in install directory')
        return False
    if not (install_dir / 'docker-compose.yml').exists():
        add_check('preflight', 'unknown', 'docker-compose.yml is missing in install directory')
        return False
    docker = run_cmd(['docker', 'version', '--format', '{{.Server.Version}}'])
    if docker.returncode != 0:
        add_check('preflight', 'unknown', 'Docker is unavailable or permission denied')
        return False
    add_check('preflight', 'ok', 'required local files and Docker are available')
    return True

def check_compose_config() -> None:
    result = run_cmd(compose_args('config'), cwd=install_dir)
    if result.returncode == 0:
        add_check('compose-config', 'ok', 'Compose config validates')
    else:
        add_check('compose-config', 'critical', 'Compose config validation failed')

def check_compose_services() -> None:
    expected_result = run_cmd(compose_args('config', '--services'), cwd=install_dir)
    if expected_result.returncode != 0:
        add_check('compose-services', 'critical', 'Expected Docker Compose service discovery failed')
        return
    expected_names = {line.strip() for line in expected_result.stdout.splitlines() if line.strip()}
    if not expected_names:
        add_check('compose-services', 'critical', 'No expected Compose services were configured', {'services_running': 0, 'services_expected': 0})
        return
    result = run_cmd(compose_args('ps', '--all', '--format', 'json'), cwd=install_dir)
    if result.returncode != 0:
        add_check('compose-services', 'critical', 'Docker Compose service status failed')
        return
    services = []
    text = result.stdout.strip()
    if text:
        try:
            # Docker Compose commonly emits one JSON object per line here.
            services = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError:
            try:
                parsed = json.loads(text)
                services = parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                add_check('compose-services', 'unknown', 'Docker Compose returned unparseable service status')
                return
    seen = {str(s.get('Service') or s.get('Name') or '') for s in services}
    running_names = set()
    for service in services:
        name = str(service.get('Service') or service.get('Name') or '')
        state = str(service.get('State') or service.get('Status') or '').lower()
        if name in expected_names and 'running' in state:
            running_names.add(name)
    missing = expected_names - seen
    running = len(running_names)
    expected = len(expected_names)
    metrics_update = {'services_running': running, 'services_expected': expected}
    if not missing and running_names == expected_names:
        add_check('compose-services', 'ok', f'{running}/{expected} expected services running', metrics_update)
    else:
        add_check('compose-services', 'critical', f'{running}/{expected} expected services running; {len(missing)} missing', metrics_update)

def check_misp_heartbeat() -> None:
    remaining = max(1, int(deadline - time.monotonic()))
    result = run_cmd(compose_args(
        'exec', '-T', 'misp-core', 'curl', '-ksS', '--fail', '--max-time', str(remaining),
        '--write-out', '\n%{http_code}',
        'https://localhost/users/heartbeat'
    ), cwd=install_dir)
    if result.returncode != 0:
        add_check('misp-heartbeat', 'critical', 'MISP heartbeat endpoint returned an HTTP or transport failure')
        return
    body, separator, status_code = result.stdout.rstrip('\r\n').rpartition('\n')
    if not separator or status_code.strip() != '200':
        add_check('misp-heartbeat', 'critical', 'MISP heartbeat endpoint returned an unexpected HTTP status')
        return
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        add_check('misp-heartbeat', 'critical', 'MISP heartbeat response did not match the JSON contract')
        return
    if isinstance(payload, str) and 0 < len(payload) <= 512:
        add_check('misp-heartbeat', 'ok', 'MISP heartbeat returned the expected JSON response contract')
    else:
        add_check('misp-heartbeat', 'critical', 'MISP heartbeat response did not match the JSON contract')

def check_schema_ready() -> None:
    code = """
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text(errors='ignore')
required = ['MYSQL_PASSWORD', 'MYSQL_ROOT_PASSWORD', 'ADMIN_EMAIL', 'ADMIN_PASSWORD']
missing = [key for key in required if f'{key}=' not in text]
raise SystemExit(1 if missing else 0)
""".strip()
    result = run_cmd(['python3', '-c', code, str(install_dir / '.env')])
    if result.returncode != 0:
        add_check('schema-ready', 'unknown', 'required local configuration for schema/login checks is incomplete')
        return
    # Use the existing manager helper for the real schema readiness boundary.
    helper = f"source {shlex.quote(str(script_dir / 'lib.sh'))}; check_misp_schema_ready {shlex.quote(str(install_dir))}"
    result = run_cmd(['bash', '-lc', helper])
    if result.returncode == 0:
        add_check('schema-ready', 'ok', 'MISP schema readiness check passed')
    else:
        add_check('schema-ready', 'critical', 'MISP schema readiness check failed')

def check_login() -> None:
    args = [str(script_dir / 'login-check.sh'), '--install-dir', str(install_dir), '--machine-readable']
    if insecure:
        args.append('--insecure')
    result = run_cmd(args)
    values = {}
    for line in result.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
    status = values.get('status')
    reason = values.get('reason', 'unknown')
    transport = values.get('transport_security', 'unknown')
    if status == 'passed' and result.returncode == 0:
        suffix = ' (explicit insecure transport)' if transport == 'insecure-explicit' else ''
        add_check('login', 'ok', f'CSRF-aware Web UI login check passed{suffix}')
    elif status == 'failed':
        add_check('login', 'critical', f'CSRF-aware Web UI login check failed: {reason} ({transport})')
    elif result.returncode != 0:
        add_check('login', 'unknown', 'login-check command failed without recognized machine-readable output')
    else:
        add_check('login', 'unknown', 'login-check returned unrecognized machine-readable output')

def check_reserved(check_id: str) -> None:
    add_check(check_id, 'warning', f'{check_id} check is documented but not implemented yet')

runners = {
    'compose-config': check_compose_config,
    'compose-services': check_compose_services,
    'misp-heartbeat': check_misp_heartbeat,
    'schema-ready': check_schema_ready,
    'login': check_login,
}

if preflight():
    for check_id in selected:
        if check_id in RESERVED_CHECKS:
            check_reserved(check_id)
        else:
            try:
                runners[check_id]()
            except subprocess.TimeoutExpired:
                add_check(check_id, 'unknown', f'{check_id} timed out after {timeout}s')
            except Exception as exc:
                add_check(check_id, 'unknown', f'{check_id} could not complete: {exc.__class__.__name__}')

rank = max((STATUS_RANK[c['status']] for c in checks), default=3)
overall = next(status for status, value in STATUS_RANK.items() if value == rank)
exit_code = EXIT_CODE[overall]
if overall == 'ok':
    summary = 'MISP lifecycle health OK'
elif overall == 'warning':
    summary = 'MISP lifecycle health has warnings'
elif overall == 'critical':
    summary = 'MISP lifecycle health is critical'
else:
    summary = 'MISP lifecycle health is unknown'

result = {
    'schema': 'misp-docker-lifecycle-manager-health-v1',
    'status': overall,
    'exit_code': exit_code,
    'summary': summary,
    'checks': checks,
    'metrics': metrics,
}

def perfdata() -> str:
    keys = ['services_running', 'services_expected', 'checks_ok', 'checks_warning', 'checks_critical', 'checks_unknown']
    return ' '.join(f'{key}={metrics.get(key, 0)}' for key in keys)

if output_format == 'json':
    print(json.dumps(result, sort_keys=True))
elif output_format == 'nagios':
    print(f"{STATUS_LABEL[overall]} - {summary} | {perfdata()}")
elif output_format == 'checkmk':
    print(f"{exit_code} \"misp_lifecycle_health\" {perfdata()} {summary}")
elif output_format == 'prometheus':
    healthy = 1 if overall == 'ok' else 0
    print('# HELP misp_lifecycle_health_status Overall MISP lifecycle manager health status, 1 ok, 0 not ok.')
    print('# TYPE misp_lifecycle_health_status gauge')
    print(f'misp_lifecycle_health_status {healthy}')
    for key in ['services_running', 'services_expected', 'checks_ok', 'checks_warning', 'checks_critical', 'checks_unknown']:
        print(f'# TYPE misp_lifecycle_{key} gauge')
        print(f'misp_lifecycle_{key} {metrics.get(key, 0)}')
else:
    print(f"{STATUS_LABEL[overall]} - {summary} | {perfdata()}")
    for check in checks:
        print(f"{STATUS_LABEL[check['status']]} {check['id']}: {check['summary']}")

sys.exit(exit_code)
PY
