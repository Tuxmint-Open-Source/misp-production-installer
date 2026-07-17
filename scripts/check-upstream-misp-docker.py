#!/usr/bin/env python3
"""Check official MISP/misp-docker upstream drift.

The watcher records public upstream facts that the lifecycle manager depends on.
It deliberately ignores commit-only movement: a new upstream commit opens a review
only when a lifecycle-sensitive file or extracted fact changed.

The generated report is a review prompt, never compatibility proof.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "https://github.com/MISP/misp-docker.git"
DEFAULT_REF = "master"
LOCK_PATH = ROOT / ".upstream" / "misp-docker.lock.json"
REPORT_PATH = ROOT / ".upstream" / "reports" / "misp-docker-upstream-review.md"

# Full hashes are appropriate for runtime/configuration inputs: even a small change
# can affect install, update, restore, readiness, or generated configuration.
WATCHED_FILE_CLASSES = {
    "template.env": "C",
    "docker-compose.yml": "B",
    "core/files/entrypoint.sh": "B",
    "core/files/entrypoint_nginx.sh": "B",
    "core/files/configure_misp.sh": "B",
    "core/files/utilities.sh": "B",
}
WATCHED_TREE_CLASSES = {
    # These public JSON files define critical, minimum, optional, proxy, storage,
    # and initialization environment handling. Track the directory so newly added
    # definitions are visible without updating this script first.
    "core/files/etc/misp-docker": "B",
    "core/files/etc/supervisor": "B",
    "core/files/etc/nginx": "B",
    "guard/files": "B",
}
WATCHED_FILES = list(WATCHED_FILE_CLASSES)
COMPONENT_KEYS = ["CORE_TAG", "MODULES_TAG", "GUARD_TAG"]
RUNNING_KEYS = ["CORE_RUNNING_TAG", "MODULES_RUNNING_TAG", "GUARD_RUNNING_TAG"]
README_SECTIONS = [
    "Getting Started",
    "Configuration",
    "MISP-Guard (optional)",
    "Authentication",
    "Production",
    "SELinux",
    "Installing custom root CA certificates",
    "Database Management",
    "Troubleshooting",
    "Versioning",
]


def run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.STDOUT)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def normalized_sha(text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    return sha256_text(normalized)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_active_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def parse_env_key_inventory(text: str) -> dict[str, list[str]]:
    active: set[str] = set()
    commented: set[str] = set()
    for line in text.splitlines():
        active_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=", line)
        if active_match:
            active.add(active_match.group(1))
            continue
        commented_match = re.match(r"^\s*#\s*([A-Za-z_][A-Za-z0-9_]*)=", line)
        if commented_match:
            commented.add(commented_match.group(1))
    return {
        "active_keys": sorted(active),
        "commented_keys": sorted(commented),
    }


def compose_service_blocks(text: str) -> dict[str, str]:
    lines = text.splitlines()
    blocks: dict[str, list[str]] = {}
    in_services = False
    current: str | None = None
    for line in lines:
        if re.match(r"^services:\s*$", line):
            in_services = True
            current = None
            continue
        if in_services and re.match(r"^[A-Za-z0-9_.-]+:\s*$", line):
            break
        if not in_services:
            continue
        match = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
        if match:
            service = match.group(1)
            current = service
            blocks[service] = [line]
            continue
        if current is not None:
            blocks[current].append(line)
    return {name: "\n".join(block) for name, block in blocks.items()}


def parse_interpolation_contract(text: str) -> dict[str, list[str]]:
    contract: dict[str, set[str]] = {}
    for expression in re.findall(r"\$\{([^}]+)\}", text):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(:?[-?+])?", expression)
        if not match:
            continue
        key = match.group(1)
        operator = match.group(2) or "plain"
        contract.setdefault(key, set()).add(operator)
    return {key: sorted(operators) for key, operators in sorted(contract.items())}


def parse_compose_facts(text: str) -> dict[str, object]:
    blocks = compose_service_blocks(text)
    images: dict[str, str] = {}
    service_block_hashes: dict[str, str] = {}
    for service, block in blocks.items():
        service_block_hashes[service] = normalized_sha(block)
        image_match = re.search(r"^    image:\s*(.+?)\s*$", block, re.MULTILINE)
        if image_match:
            images[service] = image_match.group(1).strip().strip('"')
    interpolation_contract = parse_interpolation_contract(text)
    return {
        "services": sorted(blocks),
        "images": images,
        "service_block_hashes": service_block_hashes,
        "interpolation_keys": sorted(interpolation_contract),
        "interpolation_contract": interpolation_contract,
    }


def extract_markdown_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start: int | None = None
    level = 0
    pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    for idx, line in enumerate(lines):
        match = pattern.match(line)
        if match and match.group(2).strip().lower() == heading.lower():
            start = idx
            level = len(match.group(1))
            break
    if start is None:
        return ""
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        match = pattern.match(lines[idx])
        if match and len(match.group(1)) <= level:
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def readme_section_hashes(text: str) -> dict[str, str]:
    return {heading: normalized_sha(extract_markdown_section(text, heading)) for heading in README_SECTIONS}


def collect_tree_hashes(root: Path, rel: str) -> dict[str, dict[str, str | bool]]:
    directory = root / rel
    if not directory.is_dir():
        return {".": {"exists": False, "sha256": ""}}
    result: dict[str, dict[str, str | bool]] = {}
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        child = path.relative_to(directory).as_posix()
        result[child] = {"exists": True, "sha256": sha256_text(read_text(path))}
    return result


def clone_upstream(repo: str, ref: str, target: Path) -> str:
    run(["git", "clone", "--filter=blob:none", "--no-checkout", repo, str(target)])
    try:
        run(["git", "fetch", "--depth", "1", "origin", ref], cwd=target)
    except subprocess.CalledProcessError:
        pass
    try:
        run(["git", "checkout", "--quiet", ref], cwd=target)
    except subprocess.CalledProcessError:
        run(["git", "checkout", "--quiet", "FETCH_HEAD"], cwd=target)
    return run(["git", "rev-parse", "HEAD"], cwd=target).strip()


def collect_state(repo: str, ref: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="misp-docker-upstream-") as tmp:
        upstream = Path(tmp) / "misp-docker"
        commit = clone_upstream(repo, ref, upstream)

        file_hashes: dict[str, dict[str, str | bool]] = {}
        file_text: dict[str, str] = {}
        for rel in WATCHED_FILES:
            path = upstream / rel
            if path.exists():
                text = read_text(path)
                file_text[rel] = text
                file_hashes[rel] = {"exists": True, "sha256": sha256_text(text)}
            else:
                file_hashes[rel] = {"exists": False, "sha256": ""}

        readme_path = upstream / "README.md"
        readme_text = read_text(readme_path) if readme_path.exists() else ""
        template_text = file_text.get("template.env", "")
        template_values = parse_active_env(template_text)
        watched_trees = {
            rel: collect_tree_hashes(upstream, rel) for rel in WATCHED_TREE_CLASSES
        }

        return {
            "schema": 2,
            "repo": repo,
            "ref": ref,
            "upstream_commit": commit,
            "checked_at_utc": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "watched_files": file_hashes,
            "watched_trees": watched_trees,
            "component_tags": {key: template_values.get(key, "") for key in COMPONENT_KEYS},
            "running_tag_defaults_in_template_env": {
                key: template_values.get(key, "(commented or unset)") for key in RUNNING_KEYS
            },
            "template_env_keys": parse_env_key_inventory(template_text),
            "compose": parse_compose_facts(file_text.get("docker-compose.yml", "")),
            "readme_operator_section_sha256": readme_section_hashes(readme_text),
        }


def load_lock(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def as_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def changed_mapping_keys(old: object, new: object) -> list[str]:
    old_map = as_mapping(old)
    new_map = as_mapping(new)
    return sorted(key for key in set(old_map) | set(new_map) if old_map.get(key) != new_map.get(key))


def list_delta(old: object, new: object) -> tuple[list[str], list[str]]:
    old_set = set(old if isinstance(old, list) else [])
    new_set = set(new if isinstance(new, list) else [])
    return sorted(new_set - old_set), sorted(old_set - new_set)


def diff_state(old: dict[str, object] | None, new: dict[str, object]) -> list[dict[str, str]]:
    if old is None:
        return [{"class": "A+B+C", "detail": "No previous upstream baseline existed."}]

    changes: list[dict[str, str]] = []

    if old.get("component_tags") != new.get("component_tags"):
        changes.append({"class": "A", "detail": "Official component tag defaults changed."})
    if old.get("running_tag_defaults_in_template_env") != new.get("running_tag_defaults_in_template_env"):
        changes.append({"class": "A", "detail": "Runtime image tag defaults changed."})

    old_files = as_mapping(old.get("watched_files"))
    new_files = as_mapping(new.get("watched_files"))
    for rel in WATCHED_FILES:
        if old_files.get(rel) != new_files.get(rel):
            changes.append({"class": WATCHED_FILE_CLASSES[rel], "detail": f"Watched file changed: `{rel}`"})

    old_trees = as_mapping(old.get("watched_trees"))
    new_trees = as_mapping(new.get("watched_trees"))
    for rel, change_class in WATCHED_TREE_CLASSES.items():
        old_tree = as_mapping(old_trees.get(rel))
        new_tree = as_mapping(new_trees.get(rel))
        changed_children = changed_mapping_keys(old_tree, new_tree)
        if changed_children:
            children = ", ".join(f"`{rel}/{child}`" for child in changed_children)
            changes.append({"class": change_class, "detail": f"Watched configuration tree changed: {children}"})

    old_compose = as_mapping(old.get("compose"))
    new_compose = as_mapping(new.get("compose"))
    changed_services = changed_mapping_keys(old_compose.get("service_block_hashes"), new_compose.get("service_block_hashes"))
    if changed_services:
        changes.append({"class": "B", "detail": "Compose service definitions changed: " + ", ".join(f"`{s}`" for s in changed_services)})
    if old_compose.get("interpolation_keys") != new_compose.get("interpolation_keys"):
        changes.append({"class": "B", "detail": "Compose interpolation-key inventory changed."})
    if old_compose.get("interpolation_contract") != new_compose.get("interpolation_contract"):
        changes.append({"class": "B", "detail": "Compose interpolation required/default operator contract changed."})

    if old.get("template_env_keys") != new.get("template_env_keys"):
        changes.append({"class": "C", "detail": "`template.env` active/commented key inventory changed."})

    changed_sections = changed_mapping_keys(
        old.get("readme_operator_section_sha256"), new.get("readme_operator_section_sha256")
    )
    if changed_sections:
        changes.append({"class": "C", "detail": "Operator guidance changed: " + ", ".join(f"`{s}`" for s in changed_sections)})

    # Upstream commit movement alone is informational and intentionally not drift.
    return changes


def markdown_code(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    return text.replace("`", "'").replace("|", "¦")


def manager_context() -> dict[str, str]:
    version_path = ROOT / "VERSION"
    version = read_text(version_path).strip() if version_path.exists() else "unknown"
    try:
        commit = run(["git", "rev-parse", "HEAD"], cwd=ROOT).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = "unknown"
    return {"version": version, "commit": commit}


def component_table(old: dict[str, object] | None, new: dict[str, object]) -> str:
    old_tags = as_mapping(old.get("component_tags")) if old else {}
    new_tags = as_mapping(new.get("component_tags"))
    rows = ["| Component | Previous | Current |", "|---|---:|---:|"]
    for key in COMPONENT_KEYS:
        rows.append(
            f"| `{markdown_code(key)}` | `{markdown_code(old_tags.get(key, '(none)'))}` | "
            f"`{markdown_code(new_tags.get(key, ''))}` |"
        )
    return "\n".join(rows)


def compare_url(old: dict[str, object] | None, new: dict[str, object]) -> str:
    repo = str(new["repo"])
    if repo.endswith(".git"):
        repo = repo[:-4]
    if repo.startswith("https://github.com/") and old and old.get("upstream_commit"):
        return f"{repo}/compare/{old['upstream_commit']}...{new['upstream_commit']}"
    if repo.startswith("https://github.com/"):
        return f"{repo}/commit/{new['upstream_commit']}"
    return ""


def render_delta(label: str, old: object, new: object) -> str:
    added, removed = list_delta(old, new)
    added_text = ", ".join(f"`{item}`" for item in added) or "none"
    removed_text = ", ".join(f"`{item}`" for item in removed) or "none"
    return f"- {label} added: {added_text}\n- {label} removed: {removed_text}"


def render_report(old: dict[str, object] | None, new: dict[str, object], changes: list[dict[str, str]]) -> str:
    old_compose = as_mapping(old.get("compose")) if old else {}
    new_compose = as_mapping(new.get("compose"))
    old_env = as_mapping(old.get("template_env_keys")) if old else {}
    new_env = as_mapping(new.get("template_env_keys"))
    classes = sorted({change["class"] for change in changes})
    changes_text = "\n".join(f"- **Class {item['class']}** — {item['detail']}" for item in changes)
    manager = manager_context()

    return f"""# Upstream MISP Docker review

## Summary

The scheduled upstream monitor detected lifecycle-sensitive changes in official `MISP/misp-docker` inputs. Upstream commit movement without a watched-file or extracted-fact change does not create a review.

Detected classes: **{'+'.join(classes) if classes else 'none'}**

Validation status: **review required / not validated**

## Lifecycle-manager context

- `VERSION` value: `{manager['version']}`
- Source commit at detection time: `{manager['commit']}`

## Upstream

- Repository: `{markdown_code(new['repo'])}`
- Ref: `{markdown_code(new['ref'])}`
- Previous reviewed commit: `{markdown_code(old.get('upstream_commit') if old else '(none)')}`
- Current commit: `{markdown_code(new['upstream_commit'])}`
- Compare: {compare_url(old, new)}

## Detected changes

{changes_text or '- No relevant upstream drift detected.'}

## Component tags

{component_table(old, new)}

## Structured deltas

{render_delta('Compose services', old_compose.get('services'), new_compose.get('services'))}
{render_delta('Compose interpolation keys', old_compose.get('interpolation_keys'), new_compose.get('interpolation_keys'))}
{render_delta('Active template.env keys', old_env.get('active_keys'), new_env.get('active_keys'))}
{render_delta('Commented template.env keys', old_env.get('commented_keys'), new_env.get('commented_keys'))}

## Classification

- **A:** component or runtime image tag defaults changed.
- **B:** Compose structure or runtime/configuration behavior changed, including service blocks, ports, volumes, dependencies, profiles, healthchecks, entrypoint/configuration scripts, or critical/minimum environment definitions.
- **C:** template environment inventory or selected operator guidance changed.

## Review checklist

- [ ] Inspect the upstream compare link; hashes and extracted facts summarize drift but do not replace review.
- [ ] Check upstream component tag changes and release notes.
- [ ] Check Compose service names, image expressions, ports, volumes, dependencies, profiles, healthchecks, and interpolation variables.
- [ ] Check new, removed, or changed required/default variables in `template.env` and the critical/minimum environment definitions.
- [ ] Check entrypoint, configuration, migration, startup, and readiness behavior.
- [ ] Check install, production, backup/restore, troubleshooting, and versioning guidance.
- [ ] Decide whether manager code, docs, or validation changes are needed.
- [ ] Run repository validation before merge.
- [ ] Run compatibility validation for the affected manager release/ref and official MISP component set when runtime or component behavior is affected.
- [ ] Update compatibility docs only after the documented compatibility scenarios pass.

## Compatibility note

This upstream-review report is a drift-detection prompt, not compatibility proof by itself. A listed manager release/ref and component set becomes **validated compatible** only after the documented compatibility scenarios pass and public compatibility evidence is updated.

## Validation command

```bash
python3 scripts/check-upstream-misp-docker.py --check
```
"""


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def set_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--lock", default=str(LOCK_PATH))
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--write", action="store_true", help="write updated lock/report files")
    parser.add_argument("--check", action="store_true", help="fail if lifecycle-sensitive upstream drift is detected")
    args = parser.parse_args()

    lock_path = Path(args.lock)
    report_path = Path(args.report)
    if args.write and args.repo != DEFAULT_REPO:
        try:
            report_path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            pass
        else:
            parser.error("refusing to write a non-official repository into a public in-repo report path")
    old = load_lock(lock_path)
    new = collect_state(args.repo, args.ref)
    changes = diff_state(old, new)
    drift = bool(changes)

    print(f"upstream_commit={new['upstream_commit']}")
    print(f"drift={'true' if drift else 'false'}")
    if old and old.get("upstream_commit") != new.get("upstream_commit") and not drift:
        print("- Upstream commit changed, but no lifecycle-sensitive watched input changed.")
    for change in changes:
        print(f"- Class {change['class']}: {change['detail']}")

    set_github_output("drift", "true" if drift else "false")
    set_github_output("upstream_commit", str(new["upstream_commit"]))

    if args.write:
        write_json(lock_path, new)
        if drift:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_report(old, new, changes), encoding="utf-8")
        elif report_path.exists():
            report_path.unlink()

    if args.check and drift:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
