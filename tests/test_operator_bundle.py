import hashlib
import importlib.util
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build-operator-bundle.py"
FILE_LIST = ROOT / "operator-bundle-files.txt"

SPEC = importlib.util.spec_from_file_location("operator_bundle_builder", BUILDER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load operator bundle builder")
BUILDER_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER_MODULE)


class OperatorBundleTests(unittest.TestCase):
    def test_release_tag_requires_canonical_semver(self):
        accepted = {
            "v0.0.0",
            "v1.2.3",
            "v1.2.3-rc.1",
            "v1.2.3-alpha.beta",
            "v1.2.3+build.7",
            "v1.2.3-rc.1+build.7",
        }
        rejected = {
            "1.2.3",
            "v01.2.3",
            "v1.02.3",
            "v1.2.03",
            "v1.2.3-01",
            "v1.2",
            "v1.2.3-",
            "v1.2.3+",
            "v1.2.3_rc1",
        }
        for tag in accepted:
            self.assertIsNotNone(BUILDER_MODULE.TAG_RE.fullmatch(tag), tag)
        for tag in rejected:
            self.assertIsNone(BUILDER_MODULE.TAG_RE.fullmatch(tag), tag)

    def manifest_paths(self):
        return [
            line.strip()
            for line in FILE_LIST.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]

    def build(self, destination):
        subprocess.run(
            [
                "python3",
                str(BUILDER),
                "--source-ref",
                "HEAD",
                "--allow-non-tag",
                "--output-dir",
                str(destination),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return next(destination.glob("*.tar.gz"))

    def test_release_mode_requires_semver_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                ["python3", str(BUILDER), "--source-ref", "HEAD", "--output-dir", tmp],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("require an immutable vX.Y.Z tag", proc.stderr)

    def test_bundle_is_deterministic_allowlisted_and_checksums_match(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            archive_a = self.build(Path(first))
            archive_b = self.build(Path(second))
            self.assertEqual(archive_a.read_bytes(), archive_b.read_bytes())
            checksum = Path(str(archive_a) + ".sha256").read_text().split()[0]
            self.assertEqual(checksum, hashlib.sha256(archive_a.read_bytes()).hexdigest())

            with tarfile.open(archive_a, "r:gz") as bundle:
                members = bundle.getmembers()
                root = members[0].name.split("/", 1)[0]
                relative = {member.name.removeprefix(root + "/") for member in members}
                expected = set(self.manifest_paths()) | {"OPERATOR-BUNDLE-MANIFEST.json"}
                self.assertEqual(relative, expected)
                manifest_member = bundle.extractfile(f"{root}/OPERATOR-BUNDLE-MANIFEST.json")
                if manifest_member is None:
                    self.fail("operator bundle manifest is missing")
                manifest = json.load(manifest_member)
                self.assertEqual({item["path"] for item in manifest["files"]}, set(self.manifest_paths()))
                for member in members:
                    self.assertEqual(member.mtime, 0)
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)

    def test_manifest_contains_runtime_closure_and_excludes_contributor_material(self):
        paths = set(self.manifest_paths())
        self.assertEqual(
            {f"installer/{path.name}" for path in (ROOT / "installer").glob("*.sh")},
            {path for path in paths if path.startswith("installer/")},
        )
        self.assertIn("scripts/generate_sos_report.py", paths)
        self.assertIn("scripts/validate-backup.py", paths)
        forbidden_roots = {".github", "tests", ".upstream"}
        self.assertFalse(any(Path(path).parts[0] in forbidden_roots for path in paths))
        self.assertFalse(any("validation" in Path(path).parts for path in paths))
        self.assertNotIn("scripts/check-upstream-misp-docker.py", paths)


if __name__ == "__main__":
    unittest.main()
