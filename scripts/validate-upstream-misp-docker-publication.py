#!/usr/bin/env python3
"""Validate and install an upstream-watcher publication bundle."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
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
    if candidate.get("schema") != 3:
        fail("candidate lock has an unsupported schema version")
    if candidate.get("repo") != watcher.DEFAULT_REPO or candidate.get("ref") != watcher.DEFAULT_REF:
        fail("candidate lock does not identify the fixed official upstream")
    commit = candidate.get("upstream_commit")
    if not isinstance(commit, str) or not watcher.COMMIT_PATTERN.fullmatch(commit):
        fail("candidate lock has an invalid upstream commit")
    if commit != expected_commit:
        fail("candidate lock commit does not match collector output")
    for key in EXPECTED_KEYS - {"schema", "repo", "ref", "upstream_commit", "checked_at_utc"}:
        if not isinstance(candidate.get(key), dict):
            fail(f"candidate lock field is not an object: {key}")
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
