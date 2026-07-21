#!/usr/bin/env python3
"""Validate healthcheck output contracts without requiring a monitoring server."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

STATUSES = {"ok": 0, "warning": 1, "critical": 2, "unknown": 3}
LABELS = {"ok": "OK", "warning": "WARNING", "critical": "CRITICAL", "unknown": "UNKNOWN"}
FORMATS = ("json", "nagios", "checkmk", "prometheus")
SCHEMA = "misp-docker-lifecycle-manager-health-v1"
SENSITIVE_KEY = re.compile(r"(?:PASSWORD|SECRET|TOKEN|API_KEY|ADMIN_KEY|ENCRYPTION_KEY|SALT|EMAIL|BASE_URL)", re.I)
PROM_METRIC = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*(?:\{[^}]*\})?\s+[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate healthcheck machine formats and privacy without Zabbix, Checkmk, Nagios/Icinga, or Prometheus servers."
    )
    parser.add_argument("--healthcheck", type=Path, default=Path("installer/healthcheck.sh"))
    parser.add_argument("--install-dir", type=Path, required=True)
    parser.add_argument("--expect-status", choices=tuple(STATUSES), required=True)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--include-login", action="store_true")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Explicitly allow unverified TLS for an included login check (disposable/bootstrap environments only)",
    )
    parser.add_argument("--sudo", action="store_true", help="Run healthcheck via sudo (use only with an exact trusted command path)")
    return parser.parse_args()


def load_sensitive_values(install_dir: Path) -> set[str]:
    """Load values only for output-leak detection; never return or print them."""
    values: set[str] = {str(install_dir.resolve())}
    env_file = install_dir / ".env"
    if not env_file.is_file():
        return values
    for raw in env_file.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if SENSITIVE_KEY.search(key) and len(value) >= 8:
            values.add(value)
            if key == "BASE_URL":
                host = urlparse(value).hostname
                if host and len(host) >= 4:
                    values.add(host)
    return values


def assert_public_safe(text: str, sensitive_values: set[str], context: str) -> None:
    forbidden_literals = (
        "ADMIN_PASSWORD=",
        "MYSQL_PASSWORD=",
        "MYSQL_ROOT_PASSWORD=",
        "REDIS_PASSWORD=",
        "ADMIN_KEY=",
        "ENCRYPTION_KEY=",
        "BEGIN " + "OPENSSH " + "PRIVATE KEY",
        '"base_url"',
    )
    for marker in forbidden_literals:
        if marker in text:
            raise ValueError(f"{context}: output contains forbidden sensitive marker")
    for value in sensitive_values:
        if value and value in text:
            raise ValueError(f"{context}: output contains a deployment-sensitive value")


def healthcheck_command(args: argparse.Namespace, output_format: str) -> list[str]:
    command = [str(args.healthcheck.resolve()), "--install-dir", str(args.install_dir), "--format", output_format, "--timeout", str(args.timeout)]
    if args.include_login:
        command += ["--checks", "compose-config,compose-services,misp-heartbeat,schema-ready,login"]
    if args.insecure:
        if not args.include_login:
            raise ValueError("--insecure requires --include-login")
        command.append("--insecure")
    if args.sudo:
        command.insert(0, "sudo")
    return command


def run_format(args: argparse.Namespace, output_format: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            healthcheck_command(args, output_format),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(args.timeout * 8, 30),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{output_format}: validator-level timeout expired") from exc


def validate_json(proc: subprocess.CompletedProcess[str], expected: str) -> dict:
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"json: invalid JSON: {exc.msg}") from exc
    required = {"schema", "status", "exit_code", "summary", "checks", "metrics"}
    if set(data) != required:
        raise ValueError(f"json: top-level fields must be exactly {sorted(required)}")
    if data["schema"] != SCHEMA:
        raise ValueError("json: unexpected schema identifier")
    if data["status"] != expected or data["exit_code"] != STATUSES[expected]:
        raise ValueError("json: status/exit_code does not match expected state")
    if proc.returncode != data["exit_code"]:
        raise ValueError("json: process exit code does not match JSON exit_code")
    if not isinstance(data["summary"], str) or not data["summary"]:
        raise ValueError("json: summary must be a non-empty string")
    if not isinstance(data["checks"], list) or not data["checks"]:
        raise ValueError("json: checks must be a non-empty array")
    seen: set[str] = set()
    for check in data["checks"]:
        if set(check) != {"id", "status", "summary"}:
            raise ValueError("json: each check must contain exactly id/status/summary")
        if not re.fullmatch(r"[a-z0-9-]+", check["id"]):
            raise ValueError("json: check id is not stable-token shaped")
        if check["id"] in seen:
            raise ValueError("json: duplicate check id")
        seen.add(check["id"])
        if check["status"] not in STATUSES:
            raise ValueError("json: unsupported check status")
        if not isinstance(check["summary"], str) or not check["summary"]:
            raise ValueError("json: check summary must be non-empty")
    if not isinstance(data["metrics"], dict) or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in data["metrics"].values()):
        raise ValueError("json: metrics must contain numeric values")
    return data


def require_single_line(proc: subprocess.CompletedProcess[str], output_format: str) -> str:
    lines = proc.stdout.rstrip("\n").splitlines()
    if len(lines) != 1:
        raise ValueError(f"{output_format}: expected exactly one output line")
    return lines[0]


def validate_nagios(proc: subprocess.CompletedProcess[str], expected: str) -> None:
    line = require_single_line(proc, "nagios")
    if proc.returncode != STATUSES[expected]:
        raise ValueError("nagios: incorrect process exit code")
    if not line.startswith(f"{LABELS[expected]} - ") or " | " not in line:
        raise ValueError("nagios: invalid status/summary/perfdata line")
    perfdata = line.split(" | ", 1)[1]
    if not re.fullmatch(r"(?:[a-z_]+=[0-9]+)(?: [a-z_]+=[0-9]+)*", perfdata):
        raise ValueError("nagios: invalid performance data shape")


def validate_checkmk(proc: subprocess.CompletedProcess[str], expected: str) -> None:
    line = require_single_line(proc, "checkmk")
    if proc.returncode != STATUSES[expected]:
        raise ValueError("checkmk: incorrect process exit code")
    pattern = rf'^{STATUSES[expected]} "misp_lifecycle_health" (?:[a-z_]+=[0-9]+)(?: [a-z_]+=[0-9]+)* .+$'
    if not re.fullmatch(pattern, line):
        raise ValueError("checkmk: invalid local-check line")


def validate_prometheus(proc: subprocess.CompletedProcess[str], expected: str) -> None:
    if proc.returncode != STATUSES[expected]:
        raise ValueError("prometheus: incorrect process exit code")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if "# TYPE misp_lifecycle_health_status gauge" not in lines:
        raise ValueError("prometheus: missing health-status TYPE declaration")
    expected_value = "1" if expected == "ok" else "0"
    if f"misp_lifecycle_health_status {expected_value}" not in lines:
        raise ValueError("prometheus: incorrect health-status metric")
    metric_lines = [line for line in lines if not line.startswith("#")]
    if not metric_lines or any(not PROM_METRIC.fullmatch(line) for line in metric_lines):
        raise ValueError("prometheus: invalid metric line")
    if any("{" in line for line in metric_lines):
        raise ValueError("prometheus: labels are intentionally unsupported to prevent cardinality/privacy leaks")
    promtool = shutil.which("promtool")
    if promtool:
        checked = subprocess.run([promtool, "check", "metrics"], input=proc.stdout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if checked.returncode != 0:
            raise ValueError("prometheus: promtool rejected exposition")


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        raise SystemExit("--timeout must be greater than zero")
    if not args.healthcheck.is_file():
        raise SystemExit("healthcheck command not found")

    sensitive_values = load_sensitive_values(args.install_dir)
    results = {output_format: run_format(args, output_format) for output_format in FORMATS}
    for output_format, proc in results.items():
        assert_public_safe(proc.stdout + proc.stderr, sensitive_values, output_format)

    data = validate_json(results["json"], args.expect_status)
    validate_nagios(results["nagios"], args.expect_status)
    validate_checkmk(results["checkmk"], args.expect_status)
    validate_prometheus(results["prometheus"], args.expect_status)

    check_ids = ",".join(check["id"] for check in data["checks"])
    print(f"healthcheck output validation passed: status={args.expect_status} formats={','.join(FORMATS)} checks={check_ids}")
    if shutil.which("promtool"):
        print("prometheus validation: internal parser and promtool passed")
    else:
        print("prometheus validation: internal parser passed; promtool not available")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"healthcheck output validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
