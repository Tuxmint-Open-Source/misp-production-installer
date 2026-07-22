#!/usr/bin/env python3
"""Validate and install an upstream-watcher publication bundle."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
WATCHER_PATH = ROOT / "scripts" / "check-upstream-misp-docker.py"
DEST_LOCK = ROOT / ".upstream" / "misp-docker.lock.json"
DEST_REPORT = ROOT / ".upstream" / "reports" / "misp-docker-upstream-review.md"
CANDIDATE_LOCK = "misp-docker.lock.json"
CANDIDATE_REPORT = "misp-docker-upstream-review.md"
MAX_LOCK_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 512 * 1024
EXPECTED_KEYS = {
    "schema",
    "repo",
    "ref",
    "upstream_commit",
    "checked_at_utc",
    "watched_files",
    "watched_trees",
    "component_tags",
    "official_component_releases",
    "running_tag_defaults_in_template_env",
    "template_env_keys",
    "compose",
    "readme_operator_section_sha256",
}
COMPONENT_KEYS = {"CORE_TAG", "MODULES_TAG", "GUARD_TAG"}
COMPOSE_KEYS = {
    "images", "interpolation_contract", "interpolation_keys", "service_block_hashes", "services"
}
RELEASE_KEYS = {"published_at", "release_id", "repo", "tag", "url"}
RELEASE_REPOS = {
    "CORE_TAG": "MISP/MISP",
    "MODULES_TAG": "MISP/misp-modules",
    "GUARD_TAG": "MISP/misp-guard",
}
RUNNING_TAG_KEYS = {"CORE_RUNNING_TAG", "MODULES_RUNNING_TAG", "GUARD_RUNNING_TAG"}
TEMPLATE_ENV_KEYS = {"active_keys", "commented_keys"}
FILE_RECORD_KEYS = {"exists", "sha256"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
TAG_PATTERN = re.compile(r"v[0-9]+(?:\.[0-9]+){1,3}")
SERVICE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_.-]+")
ENV_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
INTERPOLATION_OPERATORS = {"plain", ":-", "-", ":?", "?", ":+", "+"}


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def load_watcher():
    spec = importlib.util.spec_from_file_location("upstream_watch_publication", WATCHER_PATH)
    if not spec or not spec.loader:
        fail("could not load upstream watcher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_regular_file(path: Path, maximum: int) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError:
        fail(f"publication bundle is missing {path.name}")
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        fail(f"publication bundle entry is not a regular file: {path.name}")
    if info.st_size > maximum:
        fail(f"publication bundle entry exceeds size limit: {path.name}")
    data = path.read_bytes()
    if len(data) != info.st_size:
        fail(f"publication bundle entry changed while reading: {path.name}")
    return data


def require_exact_keys(value: object, keys: set[str], field: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"candidate lock field has an unexpected shape: {field}")
    if not all(isinstance(key, str) for key in value):
        fail(f"candidate lock field has a non-string key: {field}")
    return value


def require_string(value: object, field: str, maximum: int = 4096) -> str:
    if (
        not isinstance(value, str) or not value or len(value) > maximum
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        fail(f"candidate lock field is not a bounded string: {field}")
    return value


def require_string_list(value: object, field: str, pattern=None) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(f"candidate lock field is not a string list: {field}")
    if len(value) != len(set(value)):
        fail(f"candidate lock field contains duplicate list members: {field}")
    for item in value:
        require_string(item, field, 200)
        if pattern is not None and not pattern.fullmatch(item):
            fail(f"candidate lock field contains an invalid list member: {field}")
    return value


def require_timestamp(value: object, field: str) -> str:
    timestamp = require_string(value, field, 32)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp):
        fail(f"candidate lock field is not an RFC3339 UTC timestamp: {field}")
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(f"candidate lock field is not a valid UTC timestamp: {field}") from exc
    return timestamp


def require_sha256(value: object, field: str) -> str:
    digest = require_string(value, field, 64)
    if not SHA256_PATTERN.fullmatch(digest):
        fail(f"candidate lock field is not a lowercase SHA-256 digest: {field}")
    return digest


def require_safe_path(value: object, field: str, allow_dot: bool = False) -> str:
    path = require_string(value, field, 512)
    if allow_dot and path == ".":
        return path
    pure = PurePosixPath(path)
    if (
        pure.is_absolute() or "\\" in path or path.startswith("./") or path.endswith("/")
        or any(part in {"", ".", ".."} for part in pure.parts) or str(pure) != path
    ):
        fail(f"candidate lock field is not a safe relative path: {field}")
    return path


def validate_file_record(value: object, field: str) -> None:
    record = require_exact_keys(value, FILE_RECORD_KEYS, field)
    if type(record["exists"]) is not bool:
        fail(f"candidate lock file existence flag is not boolean: {field}")
    if record["exists"]:
        require_sha256(record["sha256"], f"{field}.sha256")
    elif record["sha256"] != "":
        fail(f"candidate lock missing-file digest is not empty: {field}")


def validate_string_map(value: object, field: str, value_validator=require_string) -> dict[str, object]:
    if not isinstance(value, dict):
        fail(f"candidate lock field is not an object: {field}")
    for key, item in value.items():
        require_string(key, f"{field} key", 200)
        value_validator(item, f"{field}.{key}")
    return value


def validate_nested_schema(candidate: dict[str, object], watcher) -> None:
    require_timestamp(candidate["checked_at_utc"], "checked_at_utc")

    component_tags = require_exact_keys(candidate["component_tags"], COMPONENT_KEYS, "component_tags")
    for key, value in component_tags.items():
        if value == "":
            continue
        tag = require_string(value, f"component_tags.{key}", 100)
        if not TAG_PATTERN.fullmatch(tag):
            fail(f"candidate lock component tag is invalid: {key}")

    releases = require_exact_keys(
        candidate["official_component_releases"], COMPONENT_KEYS, "official_component_releases"
    )
    for component, value in releases.items():
        record = require_exact_keys(value, RELEASE_KEYS, f"official_component_releases.{component}")
        require_timestamp(record["published_at"], f"official_component_releases.{component}.published_at")
        if type(record["release_id"]) is not int or record["release_id"] <= 0:
            fail(f"candidate lock release ID is not a positive integer: {component}")
        if record["repo"] != RELEASE_REPOS[component]:
            fail(f"candidate lock release repository is not official: {component}")
        tag = require_string(record["tag"], f"official_component_releases.{component}.tag", 100)
        if not TAG_PATTERN.fullmatch(tag):
            fail(f"candidate lock release tag is invalid: {component}")
        expected_url = f"https://github.com/{record['repo']}/releases/tag/{tag}"
        if record["url"] != expected_url:
            fail(f"candidate lock release URL is not canonical: {component}")

    running = require_exact_keys(
        candidate["running_tag_defaults_in_template_env"], RUNNING_TAG_KEYS,
        "running_tag_defaults_in_template_env",
    )
    for key, value in running.items():
        if value != "":
            require_string(value, f"running_tag_defaults_in_template_env.{key}", 200)

    template_keys = require_exact_keys(candidate["template_env_keys"], TEMPLATE_ENV_KEYS, "template_env_keys")
    active_keys = require_string_list(
        template_keys["active_keys"], "template_env_keys.active_keys", ENV_KEY_PATTERN
    )
    commented_keys = require_string_list(
        template_keys["commented_keys"], "template_env_keys.commented_keys", ENV_KEY_PATTERN
    )
    if active_keys != sorted(active_keys) or commented_keys != sorted(commented_keys):
        fail("candidate lock template environment inventories are not sorted")

    compose = require_exact_keys(candidate["compose"], COMPOSE_KEYS, "compose")
    images = validate_string_map(compose["images"], "compose.images")
    hashes = validate_string_map(compose["service_block_hashes"], "compose.service_block_hashes", require_sha256)
    services = require_string_list(compose["services"], "compose.services", SERVICE_NAME_PATTERN)
    if services != sorted(services):
        fail("candidate lock compose services are not sorted")
    if not set(images) <= set(services) or set(hashes) != set(services):
        fail("candidate lock compose service inventories do not match")
    interpolation_keys = require_string_list(
        compose["interpolation_keys"], "compose.interpolation_keys", ENV_KEY_PATTERN
    )
    if interpolation_keys != sorted(interpolation_keys):
        fail("candidate lock interpolation keys are not sorted")
    contract = validate_string_map(
        compose["interpolation_contract"], "compose.interpolation_contract",
        lambda value, field: require_string_list(value, field),
    )
    if set(contract) != set(interpolation_keys):
        fail("candidate lock interpolation inventories do not match")
    for key, operators in contract.items():
        if (
            not isinstance(operators, list) or not operators or operators != sorted(operators)
            or not set(operators) <= INTERPOLATION_OPERATORS
        ):
            fail(f"candidate lock interpolation operator is invalid: {key}")

    watched_files = require_exact_keys(
        candidate["watched_files"], set(watcher.WATCHED_FILES), "watched_files"
    )
    for path, record in watched_files.items():
        require_safe_path(path, "watched_files path")
        validate_file_record(record, f"watched_files.{path}")

    watched_trees = require_exact_keys(
        candidate["watched_trees"], set(watcher.WATCHED_TREE_CLASSES), "watched_trees"
    )
    for root, records in watched_trees.items():
        require_safe_path(root, "watched_trees root")
        if not isinstance(records, dict):
            fail(f"candidate lock watched tree is not an object: {root}")
        if "." in records:
            if set(records) != {"."}:
                fail(f"candidate lock missing-tree sentinel is not exclusive: {root}")
            if records["."] != {"exists": False, "sha256": ""}:
                fail(f"candidate lock missing-tree sentinel is invalid: {root}")
        for relative, record in records.items():
            require_safe_path(relative, f"watched_trees.{root} path", allow_dot=True)
            validate_file_record(record, f"watched_trees.{root}.{relative}")

    readme_hashes = require_exact_keys(
        candidate["readme_operator_section_sha256"], set(watcher.README_SECTIONS),
        "readme_operator_section_sha256",
    )
    for heading, digest in readme_hashes.items():
        require_sha256(digest, f"readme_operator_section_sha256.{heading}")


def validate_directory(artifact_dir: Path) -> tuple[bytes, bytes]:
    if artifact_dir.is_symlink() or not artifact_dir.is_dir():
        fail("publication bundle path is not a directory")
    entries = {entry.name for entry in artifact_dir.iterdir()}
    expected = {CANDIDATE_LOCK, CANDIDATE_REPORT}
    if entries != expected:
        fail("publication bundle must contain exactly the two allowlisted files")
    return (
        read_regular_file(artifact_dir / CANDIDATE_LOCK, MAX_LOCK_BYTES),
        read_regular_file(artifact_dir / CANDIDATE_REPORT, MAX_REPORT_BYTES),
    )


def validate_candidate(candidate: object, expected_commit: str, watcher) -> dict[str, object]:
    if not isinstance(candidate, dict) or set(candidate) != EXPECTED_KEYS:
        fail("candidate lock has an unexpected schema shape")
    if type(candidate.get("schema")) is not int or candidate.get("schema") != 3:
        fail("candidate lock has an unsupported schema version")
    if candidate.get("repo") != watcher.DEFAULT_REPO or candidate.get("ref") != watcher.DEFAULT_REF:
        fail("candidate lock does not identify the fixed official upstream")
    commit = candidate.get("upstream_commit")
    if not isinstance(commit, str) or not watcher.COMMIT_PATTERN.fullmatch(commit):
        fail("candidate lock has an invalid upstream commit")
    if commit != expected_commit:
        fail("candidate lock commit does not match collector output")
    validate_nested_schema(candidate, watcher)
    return candidate


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def validate_and_install(
    artifact_dir: Path,
    expected_commit: str,
    baseline_path: Path = DEST_LOCK,
    destination_lock: Path = DEST_LOCK,
    destination_report: Path = DEST_REPORT,
) -> list[dict[str, str]]:
    watcher = load_watcher()
    if not watcher.COMMIT_PATTERN.fullmatch(expected_commit):
        fail("collector output is not a full lowercase commit hash")
    lock_bytes, report_bytes = validate_directory(artifact_dir)
    try:
        candidate_raw = json.loads(lock_bytes.decode("utf-8"))
        report_text = report_bytes.decode("utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("publication bundle is not valid UTF-8 JSON/text") from exc
    candidate = validate_candidate(candidate_raw, expected_commit, watcher)
    baseline = watcher.load_lock(baseline_path)
    if not isinstance(baseline, dict):
        fail("committed upstream baseline is missing or invalid")
    changes = watcher.diff_state(baseline, candidate)
    if not changes:
        fail("candidate does not contain lifecycle-sensitive drift")
    expected_report = watcher.render_report(baseline, candidate, changes)
    if report_text != expected_report:
        fail("candidate report does not match recomputed public report")

    # Every validation has passed. Only the two fixed destination paths are written.
    atomic_write(destination_lock, lock_bytes)
    atomic_write(destination_report, report_bytes)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    try:
        changes = validate_and_install(args.artifact_dir, args.expected_commit)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"publication bundle rejected: {exc}", file=sys.stderr)
        return 2
    print(f"validated_changes={len(changes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
