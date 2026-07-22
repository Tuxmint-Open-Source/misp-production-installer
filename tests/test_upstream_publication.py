import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHER_SCRIPT = ROOT / "scripts" / "check-upstream-misp-docker.py"
VALIDATOR_SCRIPT = ROOT / "scripts" / "validate-upstream-misp-docker-publication.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WATCH = load_module("upstream_watch_for_publication_tests", WATCHER_SCRIPT)
PUBLISH = load_module("upstream_publication", VALIDATOR_SCRIPT)


class UpstreamPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.artifact = self.root / "publication"
        self.artifact.mkdir()
        self.baseline_path = self.root / "baseline.json"
        self.destination_lock = self.root / "destination" / "misp-docker.lock.json"
        self.destination_report = self.root / "destination" / "misp-docker-upstream-review.md"
        self.destination_lock.parent.mkdir()
        self.destination_lock.write_text("old lock\n")
        self.destination_report.write_text("old report\n")

        self.baseline = json.loads((ROOT / ".upstream" / "misp-docker.lock.json").read_text())
        self.baseline_path.write_text(json.dumps(self.baseline))
        self.candidate = copy.deepcopy(self.baseline)
        self.candidate["component_tags"]["CORE_TAG"] = "v9.9.9"
        self.expected_commit = self.candidate["upstream_commit"]
        self.write_bundle()

    def tearDown(self):
        self.temporary.cleanup()

    def write_bundle(self, candidate=None, report=None):
        candidate = copy.deepcopy(candidate if candidate is not None else self.candidate)
        changes = WATCH.diff_state(self.baseline, candidate)
        if report is None:
            report = WATCH.render_report(self.baseline, candidate, changes)
        (self.artifact / PUBLISH.CANDIDATE_LOCK).write_text(
            json.dumps(candidate, indent=2, sort_keys=True) + "\n"
        )
        (self.artifact / PUBLISH.CANDIDATE_REPORT).write_text(report)

    def validate(self):
        return PUBLISH.validate_and_install(
            self.artifact,
            self.expected_commit,
            baseline_path=self.baseline_path,
            destination_lock=self.destination_lock,
            destination_report=self.destination_report,
        )

    def assert_destinations_unchanged(self):
        self.assertEqual(self.destination_lock.read_text(), "old lock\n")
        self.assertEqual(self.destination_report.read_text(), "old report\n")

    def test_valid_generated_pair_is_installed_to_only_allowlisted_destinations(self):
        changes = self.validate()
        self.assertTrue(changes)
        self.assertEqual(json.loads(self.destination_lock.read_text()), self.candidate)
        self.assertEqual(
            self.destination_report.read_text(),
            (self.artifact / PUBLISH.CANDIDATE_REPORT).read_text(),
        )
        self.assertEqual(
            {path.name for path in self.destination_lock.parent.iterdir()},
            {self.destination_lock.name, self.destination_report.name},
        )

    def test_commit_mismatch_is_rejected_without_writes(self):
        self.expected_commit = "f" * 40
        with self.assertRaisesRegex(ValueError, "collector output"):
            self.validate()
        self.assert_destinations_unchanged()

    def test_tampered_report_is_rejected_without_writes(self):
        (self.artifact / PUBLISH.CANDIDATE_REPORT).write_text("tampered\n")
        with self.assertRaisesRegex(ValueError, "recomputed public report"):
            self.validate()
        self.assert_destinations_unchanged()

    def test_no_drift_is_rejected_without_writes(self):
        self.write_bundle(candidate=self.baseline, report="unused\n")
        with self.assertRaisesRegex(ValueError, "lifecycle-sensitive drift"):
            self.validate()
        self.assert_destinations_unchanged()

    def test_malformed_or_unofficial_candidate_is_rejected_without_writes(self):
        invalid_candidates = []
        wrong_schema = copy.deepcopy(self.candidate)
        wrong_schema["schema"] = 99
        invalid_candidates.append(wrong_schema)
        unofficial = copy.deepcopy(self.candidate)
        unofficial["repo"] = "https://example.invalid/untrusted.git"
        invalid_candidates.append(unofficial)
        bad_ref = copy.deepcopy(self.candidate)
        bad_ref["ref"] = "unreviewed"
        invalid_candidates.append(bad_ref)
        bad_commit = copy.deepcopy(self.candidate)
        bad_commit["upstream_commit"] = "main"
        invalid_candidates.append(bad_commit)
        extra_key = copy.deepcopy(self.candidate)
        extra_key["unexpected"] = True
        invalid_candidates.append(extra_key)

        for candidate in invalid_candidates:
            with self.subTest(candidate=candidate.get("repo"), schema=candidate.get("schema")):
                self.write_bundle(candidate=candidate, report="unused\n")
                with self.assertRaises(ValueError):
                    self.validate()
                self.assert_destinations_unchanged()

        (self.artifact / PUBLISH.CANDIDATE_LOCK).write_text("not json\n")
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            self.validate()
        self.assert_destinations_unchanged()

    def test_missing_extra_and_symlink_entries_are_rejected(self):
        report_path = self.artifact / PUBLISH.CANDIDATE_REPORT
        report_data = report_path.read_text()
        report_path.unlink()
        with self.assertRaisesRegex(ValueError, "exactly the two"):
            self.validate()
        self.assert_destinations_unchanged()

        report_path.write_text(report_data)
        (self.artifact / "extra.txt").write_text("extra")
        with self.assertRaisesRegex(ValueError, "exactly the two"):
            self.validate()
        self.assert_destinations_unchanged()

        (self.artifact / "extra.txt").unlink()
        report_path.unlink()
        symlink_target = self.root / "outside-report.md"
        symlink_target.write_text(report_data)
        os.symlink(symlink_target, report_path)
        with self.assertRaisesRegex(ValueError, "regular file"):
            self.validate()
        self.assert_destinations_unchanged()

    def test_oversized_entry_is_rejected(self):
        report_path = self.artifact / PUBLISH.CANDIDATE_REPORT
        report_path.write_bytes(b"x" * (PUBLISH.MAX_REPORT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "size limit"):
            self.validate()
        self.assert_destinations_unchanged()


if __name__ == "__main__":
    unittest.main()
