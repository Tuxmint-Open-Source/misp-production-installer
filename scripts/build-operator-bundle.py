#!/usr/bin/env python3
"""Build a deterministic, allowlisted operator bundle from a Git ref."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "operator-bundle-files.txt"
NUMERIC_IDENTIFIER = r"(?:0|[1-9][0-9]*)"
PRERELEASE_IDENTIFIER = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
TAG_RE = re.compile(
    rf"v({NUMERIC_IDENTIFIER}\."
    rf"{NUMERIC_IDENTIFIER}\."
    rf"{NUMERIC_IDENTIFIER}"
    rf"(?:-{PRERELEASE_IDENTIFIER}(?:\.{PRERELEASE_IDENTIFIER})*)?"
    rf"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)\Z"
)


def git_text(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True)


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def source_files(commit: str) -> list[str]:
    entries = [
        line.strip()
        for line in git_text("show", f"{commit}:{MANIFEST_PATH}").splitlines()
    ]
    entries = [line for line in entries if line and not line.startswith("#")]
    if entries != sorted(set(entries)):
        raise ValueError("operator bundle file list must be unique and sorted")
    for entry in entries:
        path = PurePosixPath(entry)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe bundle path: {entry}")
    return entries


def resolve_source(ref: str, allow_non_tag: bool) -> tuple[str, str]:
    commit = git_text("rev-parse", f"{ref}^{{commit}}").strip()
    tag_match = TAG_RE.fullmatch(ref)
    if not allow_non_tag:
        if not tag_match:
            raise ValueError("release bundles require an immutable vX.Y.Z tag")
        tag_commit = git_text("rev-parse", f"refs/tags/{ref}^{{commit}}").strip()
        if tag_commit != commit:
            raise ValueError("tag does not resolve to the selected source commit")
    version = git_text("show", f"{commit}:VERSION").strip()
    if tag_match and version != tag_match.group(1):
        raise ValueError(f"tag {ref} does not match VERSION {version}")
    return commit, version


def blob(commit: str, path: str) -> bytes:
    try:
        return git_bytes("show", f"{commit}:{path}")
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"missing allowlisted runtime file at source ref: {path}") from exc


def build(ref: str, output_dir: Path, allow_non_tag: bool = False) -> tuple[Path, Path]:
    commit, version = resolve_source(ref, allow_non_tag)
    paths = source_files(commit)
    payloads = {path: blob(commit, path) for path in paths}
    manifest = {
        "schema_version": 1,
        "product": "misp-docker-lifecycle-manager",
        "version": version,
        "source_ref": ref,
        "source_commit": commit,
        "files": [
            {"path": path, "sha256": hashlib.sha256(payloads[path]).hexdigest()}
            for path in paths
        ],
    }
    payloads["OPERATOR-BUNDLE-MANIFEST.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()

    root_name = f"misp-docker-lifecycle-manager-v{version}"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{root_name}.tar.gz"
    raw_tar = io.BytesIO()
    with tarfile.open(fileobj=raw_tar, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(payloads):
            data = payloads[path]
            info = tarfile.TarInfo(f"{root_name}/{path}")
            info.size = len(data)
            info.mode = 0o755 if path.endswith((".sh", ".py")) else 0o644
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            tar.addfile(info, io.BytesIO(data))
    with archive.open("wb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
            compressed.write(raw_tar.getvalue())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_name(archive.name + ".sha256")
    checksum.write_text(f"{digest}  {archive.name}\n")
    return archive, checksum


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-non-tag",
        action="store_true",
        help="test/development only; release publication must not use this option",
    )
    args = parser.parse_args()
    archive, checksum = build(args.source_ref, args.output_dir, args.allow_non_tag)
    print(archive)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
