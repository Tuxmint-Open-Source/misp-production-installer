#!/usr/bin/env python3
"""Validate lifecycle-manager backup integrity and archive shape before restore."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import posixpath
import re
import stat
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import NoReturn
from urllib.parse import urlparse

ARTIFACTS = {
    "misp.sql",
    "misp-host-data.tar.gz",
    "misp-config.tar.gz",
}
BACKUP_FILES = ARTIFACTS | {"SHA256SUMS"}
CONFIG_MEMBERS = {
    ".env",
    "docker-compose.override.yml",
    ".installer-state.json",
}
REQUIRED_CONFIG_MEMBERS = {
    ".env",
    "docker-compose.override.yml",
}
HOST_ROOTS = {
    "configs",
    "logs",
    "files",
    "ssl",
    "gnupg",
    "custom",
    "guard",
}
CHECKSUM_RE = re.compile(r"^([0-9a-fA-F]{64}) [ *]([^\r\n]+)$")
MAX_CONFIG_MEMBER_SIZE = 1024 * 1024


class ValidationError(ValueError):
    pass


def fail(message: str) -> NoReturn:
    print(f"backup validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_regular_file(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise ValidationError(f"missing required file: {path.name}") from exc
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise ValidationError(f"{path.name} must be a regular non-symlink file")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stage_backup(source: Path, destination: Path) -> None:
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    for name in sorted(BACKUP_FILES):
        source_fd = os.open(source / name, os.O_RDONLY | nofollow)
        try:
            source_info = os.fstat(source_fd)
            if not stat.S_ISREG(source_info.st_mode):
                raise ValidationError(f"{name} must be a regular non-symlink file")
            destination_fd = os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                while True:
                    block = os.read(source_fd, 1024 * 1024)
                    if not block:
                        break
                    view = memoryview(block)
                    while view:
                        written = os.write(destination_fd, view)
                        view = view[written:]
                os.fsync(destination_fd)
            finally:
                os.close(destination_fd)
        finally:
            os.close(source_fd)


def validate_checksums(backup: Path) -> None:
    manifest = backup / "SHA256SUMS"
    require_regular_file(manifest)
    entries: dict[str, str] = {}
    for line_number, line in enumerate(manifest.read_text(errors="strict").splitlines(), 1):
        match = CHECKSUM_RE.fullmatch(line)
        if not match:
            raise ValidationError(f"invalid SHA256SUMS line {line_number}")
        digest, recorded_name = match.groups()
        # Older manager backups wrote absolute artifact paths. Resolve only the
        # final fixed artifact name and always hash the file in BACKUP_DIR; never
        # follow a path from the manifest.
        recorded_path = PurePosixPath(recorded_name)
        name = recorded_path.name
        if recorded_name != name and not recorded_path.is_absolute():
            raise ValidationError(f"unsafe relative SHA256SUMS path on line {line_number}")
        if name not in ARTIFACTS:
            raise ValidationError(f"unexpected SHA256SUMS entry: {name}")
        if name in entries:
            raise ValidationError(f"duplicate SHA256SUMS entry: {name}")
        entries[name] = digest.lower()
    if set(entries) != ARTIFACTS:
        missing = ", ".join(sorted(ARTIFACTS - set(entries)))
        raise ValidationError(f"SHA256SUMS is missing required entries: {missing}")
    for name in sorted(ARTIFACTS):
        path = backup / name
        require_regular_file(path)
        if sha256(path) != entries[name]:
            raise ValidationError(f"checksum mismatch: {name}")


def normalize_member_name(raw: str) -> str:
    if not raw or "\\" in raw or raw.startswith("/"):
        raise ValidationError(f"unsafe archive member path: {raw!r}")
    normalized = posixpath.normpath(raw)
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        raise ValidationError(f"unsafe archive member path: {raw!r}")
    return normalized.removeprefix("./")


def validate_link(member: tarfile.TarInfo, normalized_name: str) -> None:
    target = member.linkname
    if not target or "\\" in target or target.startswith("/"):
        raise ValidationError(f"unsafe link target in archive member: {normalized_name}")
    if member.issym():
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(normalized_name), target))
    else:
        resolved = posixpath.normpath(target)
    if resolved in {"", ".", ".."} or resolved.startswith("../"):
        raise ValidationError(f"unsafe link target in archive member: {normalized_name}")
    if PurePosixPath(resolved).parts[0] not in HOST_ROOTS:
        raise ValidationError(f"unsafe link target in archive member: {normalized_name}")


def validate_public_base_url(base_url: str, exposure: str) -> None:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in base_url):
        raise ValidationError("BASE_URL must not contain control characters")
    if any(ch.isspace() or ch in "#$\\\"'" for ch in base_url):
        raise ValidationError("BASE_URL contains dotenv-unsafe characters")
    try:
        parsed = urlparse(base_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValidationError("BASE_URL contains a malformed host or port") from exc
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise ValidationError("BASE_URL must be an http(s) URL with a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValidationError("BASE_URL must not contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValidationError("BASE_URL must not contain a query or fragment")
    if port is not None and not 1 <= port <= 65535:
        raise ValidationError("BASE_URL contains an invalid port")
    host = hostname.lower().rstrip(".")
    try:
        parsed_ip = ipaddress.ip_address(host)
    except ValueError:
        parsed_ip = None
        labels = host.split(".")
        if any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        ):
            raise ValidationError("BASE_URL hostname contains an invalid DNS label")
    if exposure == "direct-qa" and (
        host in {"localhost", "localhost.localdomain"}
        or (parsed_ip is not None and parsed_ip.is_loopback)
    ):
        raise ValidationError("direct-qa BASE_URL must not use a loopback host")


def validate_config_archive(path: Path) -> None:
    seen: set[str] = set()
    env_tar_member: tarfile.TarInfo | None = None
    state_tar_member: tarfile.TarInfo | None = None
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            name = normalize_member_name(member.name)
            if name in seen:
                raise ValidationError(f"duplicate configuration archive member: {name}")
            seen.add(name)
            if name not in CONFIG_MEMBERS:
                raise ValidationError(f"unexpected configuration archive member: {name}")
            if not member.isfile():
                raise ValidationError(f"configuration archive member must be a regular file: {name}")
            if member.size > MAX_CONFIG_MEMBER_SIZE:
                raise ValidationError(f"configuration archive member is too large: {name}")
            if name == ".env":
                env_tar_member = member
            elif name == ".installer-state.json":
                state_tar_member = member
        missing = REQUIRED_CONFIG_MEMBERS - seen
        if missing:
            raise ValidationError(
                "configuration archive is missing required members: " + ", ".join(sorted(missing))
            )
        if env_tar_member is None:
            raise ValidationError("could not locate .env")
        env_member = archive.extractfile(env_tar_member)
        if env_member is None:
            raise ValidationError("could not read .env")
        try:
            env_text = env_member.read().decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValidationError(".env is not valid UTF-8") from exc
        env: dict[str, str] = {}
        for line in env_text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, value = stripped.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
        state: dict[str, object] = {}
        if state_tar_member is not None:
            state_member = archive.extractfile(state_tar_member)
            if state_member is None:
                raise ValidationError("could not read .installer-state.json")
            try:
                state = json.load(state_member)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValidationError(".installer-state.json is not valid JSON") from exc
            if not isinstance(state, dict) or state.get("installer") != "misp-docker-lifecycle-manager":
                raise ValidationError(".installer-state.json has an unexpected installer identity")
            raw_repo = state.get("upstream_repo", "")
            raw_ref = state.get("upstream_ref", "")
            raw_commit = state.get("upstream_commit", "")
            raw_exposure = state.get("exposure", "")
            raw_base_url = state.get("base_url", "")
            if not all(
                isinstance(value, str)
                for value in (raw_repo, raw_ref, raw_commit, raw_exposure, raw_base_url)
            ):
                raise ValidationError(".installer-state.json source and deployment fields must be strings")
            if raw_commit and not re.fullmatch(r"[0-9a-f]{40}", raw_commit):
                raise ValidationError(".installer-state.json contains an invalid upstream commit")
            if raw_exposure and raw_exposure not in {"reverse-proxy", "direct-qa"}:
                raise ValidationError(".installer-state.json contains an unsupported exposure mode")
            if any(any(ord(ch) < 32 or ord(ch) == 127 for ch in value) for value in (raw_exposure, raw_base_url)):
                raise ValidationError(".installer-state.json deployment fields contain control characters")
            repo = raw_repo
            ref = raw_ref
            if repo:
                try:
                    parsed = urlparse(repo)
                    has_credentials = parsed.username is not None or parsed.password is not None
                except ValueError as exc:
                    raise ValidationError(
                        ".installer-state.json contains an unsafe upstream repository"
                    ) from exc
                if (
                    repo.startswith("-")
                    or any(ord(ch) < 32 or ord(ch) == 127 for ch in repo)
                    or (parsed.scheme and parsed.scheme not in {"https", "ssh", "git"})
                    or has_credentials
                    or parsed.query
                    or parsed.fragment
                ):
                    raise ValidationError(".installer-state.json contains an unsafe upstream repository")
            if ref and (
                ref.startswith("-")
                or len(ref) > 255
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in ref)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/@{}+~-]*", ref)
            ):
                raise ValidationError(".installer-state.json contains an unsafe upstream ref")

        env_base_url = env.get("BASE_URL", "")
        state_base_url = state.get("base_url", "")
        state_exposure = state.get("exposure", "")
        exposure = state_exposure or (
            "reverse-proxy" if env.get("CORE_HTTPS_PORT", "").startswith("127.0.0.1:") else "direct-qa"
        )
        if not isinstance(state_base_url, str) or not isinstance(state_exposure, str):
            raise ValidationError(".installer-state.json deployment fields must be strings")
        if not env_base_url:
            raise ValidationError(".env lacks BASE_URL")
        validate_public_base_url(env_base_url, exposure)
        if state_base_url:
            validate_public_base_url(state_base_url, exposure)
            if state_base_url != env_base_url:
                raise ValidationError(".env BASE_URL does not match .installer-state.json")


def validate_host_archive(path: Path) -> None:
    seen: set[str] = set()
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            name = normalize_member_name(member.name)
            if name in seen:
                raise ValidationError(f"duplicate host-data archive member: {name}")
            seen.add(name)
            if PurePosixPath(name).parts[0] not in HOST_ROOTS:
                raise ValidationError(f"unexpected host-data archive member: {name}")
            if member.mode & 0o6000:
                raise ValidationError(f"setuid/setgid mode is not allowed in host-data archive: {name}")
            if member.isdev() or member.isfifo():
                raise ValidationError(f"special file is not allowed in host-data archive: {name}")
            if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValidationError(f"unsupported host-data archive member type: {name}")
            if member.issym() or member.islnk():
                validate_link(member, name)


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("usage: validate-backup.py BACKUP_DIR [STAGING_DIR]", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).expanduser().resolve()
    if not source.is_dir():
        fail("backup directory is missing")
    backup = source
    try:
        if len(sys.argv) == 3:
            backup = Path(sys.argv[2]).expanduser().resolve()
            stage_backup(source, backup)
        validate_checksums(backup)
        validate_config_archive(backup / "misp-config.tar.gz")
        validate_host_archive(backup / "misp-host-data.tar.gz")
    except (ValidationError, OSError, UnicodeError, tarfile.TarError) as exc:
        fail(str(exc))
    print("backup validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
