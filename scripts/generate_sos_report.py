#!/usr/bin/env python3
"""Generate a bounded, allowlisted public SOS report."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import secrets
import stat
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTALL_DIR = Path("/opt/misp-docker")
REPORT_SCHEMA = "generated-sos-v2"
WORKFLOWS = {
    "unknown", "fresh-install", "install", "update", "backup", "restore",
    "rollback", "reset", "doctor", "status", "login-check", "monitoring",
    "documentation", "other",
}
EXPECTED_HEALTH_IDS = {
    "preflight", "compose-config", "compose-services", "misp-heartbeat", "schema-ready"
}
STATUS_VALUES = {"ok", "warning", "critical", "unknown", "not-checked"}
TAG_KEYS = (
    "CORE_TAG", "MODULES_TAG", "GUARD_TAG",
    "CORE_RUNNING_TAG", "MODULES_RUNNING_TAG", "GUARD_RUNNING_TAG",
)
TAG_RE = re.compile(r"(?:latest|v?[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9.-]+)?)\Z")
VERSION_RE = re.compile(r"v?[0-9]+(?:\.[0-9]+){0,3}(?:[-+][A-Za-z0-9.-]+)?\Z")
MODE_RE = re.compile(r"[0-7]{3,4}\Z")
SAFE_OS_IDS = {
    "alpine", "arch", "centos", "debian", "fedora", "opensuse", "rhel",
    "rocky", "ubuntu", "unknown",
}
ARCH_MAP = {
    "x86_64": "x86_64", "amd64": "x86_64", "aarch64": "arm64",
    "arm64": "arm64", "armv7l": "armv7", "ppc64le": "ppc64le",
    "s390x": "s390x",
}


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def strict_token(value: str, pattern: re.Pattern[str], fallback: str = "unknown") -> str:
    value = value.strip()
    return value if pattern.fullmatch(value) else fallback


def file_mode(path: Path) -> str:
    try:
        metadata = path.lstat()
    except OSError:
        return "missing"
    if not stat.S_ISREG(metadata.st_mode):
        return "not-regular"
    mode = f"{metadata.st_mode & 0o777:03o}"
    return mode if MODE_RE.fullmatch(mode) else "unknown"


def read_public_tags(env_file: Path) -> dict[str, str]:
    values = {key: "unknown" for key in TAG_KEYS}
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(env_file, flags)
    except OSError:
        return values
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 1024 * 1024:
            return values
        handle = os.fdopen(fd, "r", errors="replace")
        fd = -1
        with handle:
            lines = handle.read(1024 * 1024 + 1).splitlines()
    except OSError:
        return values
    finally:
        if fd >= 0:
            os.close(fd)
    seen: set[str] = set()
    duplicates: set[str] = set()
    for line in lines:
        key, sep, raw = line.partition("=")
        if not sep or key not in values:
            continue
        if key in seen:
            duplicates.add(key)
            continue
        seen.add(key)
        values[key] = strict_token(raw, TAG_RE, "redacted-or-invalid")
    for key in duplicates:
        values[key] = "redacted-or-invalid"
    return values


def os_facts() -> tuple[str, str, str, str]:
    os_id = "unknown"
    os_major = "unknown"
    try:
        release = platform.freedesktop_os_release()
        candidate = release.get("ID", "").lower()
        os_id = candidate if candidate in SAFE_OS_IDS else "other"
        major = release.get("VERSION_ID", "").split(".", 1)[0]
        os_major = major if major.isdigit() and len(major) <= 3 else "unknown"
    except OSError:
        pass
    kernel_match = re.match(r"([0-9]+\.[0-9]+)", platform.release())
    kernel_series = kernel_match.group(1) if kernel_match else "unknown"
    architecture = ARCH_MAP.get(platform.machine().lower(), "other")
    return os_id, os_major, kernel_series, architecture


def remaining_budget(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def run_version(args: list[str], deadline: float) -> str:
    remaining = remaining_budget(deadline)
    if remaining <= 0:
        return "unavailable"
    try:
        result = subprocess.run(
            args, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=remaining, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    if result.returncode != 0 or len(result.stdout) > 256:
        return "unavailable"
    return strict_token(result.stdout, VERSION_RE, "unavailable")


def normalize_health(payload: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "overall": "unknown",
        "checks": {check_id: "not-checked" for check_id in sorted(EXPECTED_HEALTH_IDS)},
        "counts": {status: 0 for status in ("ok", "warning", "critical", "unknown")},
    }
    if not isinstance(payload, dict):
        return result
    overall = payload.get("status")
    if overall in STATUS_VALUES - {"not-checked"}:
        result["overall"] = overall
    checks = payload.get("checks")
    if not isinstance(checks, list) or len(checks) > 16:
        return result
    for item in checks:
        if not isinstance(item, dict):
            continue
        check_id = item.get("id")
        status = item.get("status")
        if check_id in EXPECTED_HEALTH_IDS and status in STATUS_VALUES - {"not-checked"}:
            result["checks"][check_id] = status
    for status in result["counts"]:
        result["counts"][status] = sum(1 for value in result["checks"].values() if value == status)
    return result


def collect_health(
    install_dir: Path,
    enabled: bool,
    deadline: float,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    if not enabled:
        return {
            "overall": "not-checked",
            "checks": {check_id: "not-checked" for check_id in sorted(EXPECTED_HEALTH_IDS)},
            "counts": {status: 0 for status in ("ok", "warning", "critical", "unknown")},
        }
    remaining = remaining_budget(deadline)
    health_timeout = int(remaining)
    if health_timeout <= 0:
        return normalize_health(None)
    if runner is None:
        runner = subprocess.run
    command = [
        str(ROOT / "installer" / "healthcheck.sh"), "--install-dir", str(install_dir),
        "--format", "json", "--checks",
        "compose-config,compose-services,misp-heartbeat,schema-ready", "--timeout", str(health_timeout),
    ]
    try:
        completed = runner(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=remaining, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return normalize_health(None)
    if len(completed.stdout) > 65536:
        return normalize_health(None)
    try:
        return normalize_health(json.loads(completed.stdout))
    except (json.JSONDecodeError, TypeError):
        return normalize_health(None)


def manager_facts(deadline: float) -> tuple[str, str]:
    try:
        version = strict_token((ROOT / "VERSION").read_text().strip(), VERSION_RE)
    except OSError:
        version = "unknown"
    commit = "unknown"
    remaining = remaining_budget(deadline)
    if remaining <= 0:
        return version, commit
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=remaining, check=False,
        )
        candidate = result.stdout.strip()
        if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", candidate):
            commit = candidate[:12]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return version, commit


def render_report(args: argparse.Namespace) -> str:
    deadline = time.monotonic() + args.timeout
    install_dir = args.install_dir
    manager_version, manager_commit = manager_facts(deadline)
    os_id, os_major, kernel_series, architecture = os_facts()
    tags = read_public_tags(install_dir / ".env")
    docker_enabled = not args.no_docker
    health_enabled = docker_enabled and not args.no_health_commands
    if docker_enabled:
        docker_version = run_version(["docker", "version", "--format", "{{.Client.Version}}"], deadline)
        compose_version = run_version(["docker", "compose", "version", "--short"], deadline)
    else:
        docker_version = compose_version = "not-checked"
    health = collect_health(install_dir, health_enabled, deadline)
    lines = [
        "# MISP Docker Lifecycle Manager SOS Report",
        "",
        "## Safety notice",
        "Generated locally from allowlisted structured facts only. Review before sharing publicly. No raw command output is included.",
        "",
        "## Summary",
        f"- Manager version: {manager_version}",
        f"- Manager commit: {manager_commit}",
        f"- Report format: {REPORT_SCHEMA}",
        f"- Affected workflow: {args.workflow}",
        "",
        "## Environment",
        f"- OS family: {os_id}",
        f"- OS major version: {os_major}",
        f"- Kernel series: {kernel_series}",
        f"- Architecture: {architecture}",
        f"- Docker client version: {docker_version}",
        f"- Docker Compose version: {compose_version}",
        "",
        "## Installation shape",
        f"- Default install directory used: {yes_no(install_dir == DEFAULT_INSTALL_DIR)}",
        f"- Install directory present: {yes_no(install_dir.is_dir())}",
        f"- docker-compose.yml present: {yes_no((install_dir / 'docker-compose.yml').is_file())}",
        f"- docker-compose.override.yml present: {yes_no((install_dir / 'docker-compose.override.yml').is_file())}",
        f"- .env present: {yes_no((install_dir / '.env').is_file())}",
        f"- .env permissions: {file_mode(install_dir / '.env')}",
        f"- .installer-state.json present: {yes_no((install_dir / '.installer-state.json').is_file())}",
        f"- .installer-state.json permissions: {file_mode(install_dir / '.installer-state.json')}",
        "",
        "## Public component tags",
    ]
    lines.extend(f"- {key}: {tags[key]}" for key in TAG_KEYS)
    lines.extend([
        "",
        "## Bounded health summary",
        f"- Docker checks enabled: {yes_no(docker_enabled)}",
        f"- Structured health check enabled: {yes_no(health_enabled)}",
        f"- Overall health: {health['overall']}",
    ])
    lines.extend(f"- {check_id}: {health['checks'][check_id]}" for check_id in sorted(EXPECTED_HEALTH_IDS))
    lines.extend([
        f"- Checks OK: {health['counts']['ok']}",
        f"- Checks warning: {health['counts']['warning']}",
        f"- Checks critical: {health['counts']['critical']}",
        f"- Checks unknown: {health['counts']['unknown']}",
        "",
        "## Deliberately not collected",
        "- Raw helper, Docker, Compose, application, or system command output",
        "- URLs, hostnames, IP addresses, email addresses, organization names, or topology",
        "- `.env` or `.installer-state.json` contents other than strictly validated public component tags",
        "- Backup presence, names, paths, counts, contents, checksums, or timestamps",
        "- Logs, database data, generated configuration, browser output, or MISP business data",
        "",
        "## Reproduction prompt",
        "Before posting, add expected behavior, actual behavior, a sanitized command shape, and whether the issue reproduces on a fresh install.",
        "",
        "## Safety confirmation",
        "Review every line before posting. If the issue cannot be explained safely in public, use SECURITY.md and private vulnerability reporting.",
    ])
    if args.explain_redaction:
        lines.extend([
            "",
            "## Privacy model",
            "This v2 report emits only bounded allowlisted values. It does not depend on regex redaction to make arbitrary command output public-safe.",
        ])
    return "\n".join(lines) + "\n"


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(path.parent, directory_flags)
    except OSError as exc:
        raise SystemExit("output parent must be a real accessible directory") from exc
    temporary_name = f".misp-sos-{os.getpid()}-{secrets.token_hex(8)}"
    try:
        try:
            existing = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise SystemExit("output path must be a regular file and not a symlink")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            fd = -1
            os.replace(
                temporary_name, path.name,
                src_dir_fd=directory_fd, dst_dir_fd=directory_fd,
            )
            os.chmod(path.name, 0o600, dir_fd=directory_fd, follow_symlinks=False)
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
    finally:
        os.close(directory_fd)


def positive_timeout(value: str) -> int:
    try:
        timeout = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a positive integer") from exc
    if timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive integer")
    return timeout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--install-dir", type=Path, default=DEFAULT_INSTALL_DIR)
    parser.add_argument("--output", type=Path, default=Path("./misp-sos-report.md"))
    parser.add_argument("--format", choices=("markdown",), default="markdown")
    parser.add_argument("--workflow", choices=sorted(WORKFLOWS), default="unknown")
    parser.add_argument("--no-docker", action="store_true")
    parser.add_argument("--no-health-commands", action="store_true")
    parser.add_argument("--explain-redaction", action="store_true")
    parser.add_argument("--timeout", type=positive_timeout, default=20, help="Global deadline in seconds for all SOS probes (default: 20)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_report(args.output, render_report(args))
    print(f"SOS report written to {args.output}")
    print("Review the report before posting it publicly. Use SECURITY.md for sensitive issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
