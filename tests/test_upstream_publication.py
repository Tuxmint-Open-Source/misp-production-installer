import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_valid_collector_missing_input_records_are_accepted(self):
        candidate = copy.deepcopy(self.candidate)
        first_file = next(iter(candidate["watched_files"].values()))
        first_file.update({"exists": False, "sha256": ""})
        first_tree = next(iter(candidate["watched_trees"]))
        candidate["watched_trees"][first_tree] = {".": {"exists": False, "sha256": ""}}
        self.write_bundle(candidate=candidate)
        self.assertTrue(self.validate())

    def test_actual_collector_empty_checkout_shape_is_accepted(self):
        def empty_clone(_repo, _ref, target):
            target.mkdir()
            return self.expected_commit

        with (
            mock.patch.object(WATCH, "clone_upstream", side_effect=empty_clone),
            mock.patch.object(
                WATCH,
                "collect_official_component_releases",
                return_value=copy.deepcopy(self.baseline["official_component_releases"]),
            ),
        ):
            candidate = WATCH.collect_state(WATCH.DEFAULT_REPO, WATCH.DEFAULT_REF)
        self.assertEqual(candidate["component_tags"], {key: "" for key in WATCH.COMPONENT_KEYS})
        self.assertEqual(candidate["template_env_keys"], {"active_keys": [], "commented_keys": []})
        self.write_bundle(candidate=candidate)
        self.assertTrue(self.validate())

    def test_actual_collector_build_only_service_and_empty_running_tag_are_accepted(self):
        compose = """services:
  app:
    image: example/app:v1
  builder:
    build: .
"""
        candidate = copy.deepcopy(self.candidate)
        candidate["compose"] = WATCH.parse_compose_facts(compose)
        candidate["running_tag_defaults_in_template_env"]["CORE_RUNNING_TAG"] = ""
        self.write_bundle(candidate=candidate)
        self.assertTrue(self.validate())

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

    def test_malformed_nested_schema_is_rejected_without_writes(self):
        mutations = []

        def mutate(name, function):
            candidate = copy.deepcopy(self.candidate)
            function(candidate)
            mutations.append((name, candidate))

        mutate("timestamp object", lambda value: value.__setitem__("checked_at_utc", {}))
        mutate("floating schema", lambda value: value.__setitem__("schema", 3.0))
        mutate("invalid timestamp", lambda value: value.__setitem__("checked_at_utc", "2026-02-30T00:00:00Z"))
        mutate("missing component key", lambda value: value["component_tags"].pop("GUARD_TAG"))
        mutate("invalid component tag", lambda value: value["component_tags"].__setitem__("CORE_TAG", "latest"))
        mutate(
            "prerelease component tag",
            lambda value: value["component_tags"].__setitem__("CORE_TAG", "v2.5.45-rc.1"),
        )
        mutate(
            "boolean release ID",
            lambda value: value["official_component_releases"]["CORE_TAG"].__setitem__("release_id", True),
        )
        mutate(
            "unofficial release repository",
            lambda value: value["official_component_releases"]["CORE_TAG"].__setitem__("repo", "Other/MISP"),
        )
        mutate(
            "extra release key",
            lambda value: value["official_component_releases"]["CORE_TAG"].__setitem__("extra", "x"),
        )
        mutate("wrong template list type", lambda value: value["template_env_keys"].__setitem__("active_keys", {}))
        mutate("compose services boolean", lambda value: value["compose"]["services"].append(True))
        mutate("unsorted compose services", lambda value: value["compose"]["services"].reverse())
        mutate(
            "collector-impossible service name",
            lambda value: (
                value["compose"]["services"].append("foo/bar"),
                value["compose"]["images"].__setitem__("foo/bar", "example:v1"),
                value["compose"]["service_block_hashes"].__setitem__("foo/bar", "0" * 64),
                value["compose"]["services"].sort(),
            ),
        )
        mutate(
            "newline image",
            lambda value: value["compose"]["images"].__setitem__("db", "valid-image\ninjected"),
        )
        mutate(
            "uppercase service hash",
            lambda value: value["compose"]["service_block_hashes"].__setitem__(
                "db", value["compose"]["service_block_hashes"]["db"].upper()
            ),
        )
        mutate(
            "unknown interpolation operator",
            lambda value: value["compose"]["interpolation_contract"].__setitem__("BASE_URL", ["shell"]),
        )
        mutate("arbitrary watched files", lambda value: value.__setitem__("watched_files", {"../escape": {}}))
        mutate(
            "extra safe watched file",
            lambda value: value["watched_files"].__setitem__(
                "safe-looking.txt", {"exists": False, "sha256": ""}
            ),
        )
        mutate(
            "integer file existence",
            lambda value: next(iter(value["watched_files"].values())).__setitem__("exists", 1),
        )
        mutate(
            "missing file with digest",
            lambda value: next(iter(value["watched_files"].values())).__setitem__("exists", False),
        )
        mutate(
            "unsafe watched tree path",
            lambda value: value["watched_trees"].__setitem__("/absolute", {}),
        )
        mutate(
            "extra safe watched tree",
            lambda value: value["watched_trees"].__setitem__("safe/tree", {}),
        )
        mutate(
            "true missing-tree sentinel",
            lambda value: next(iter(value["watched_trees"].values())).__setitem__(
                ".", {"exists": True, "sha256": "0" * 64}
            ),
        )
        mutate(
            "mixed missing-tree sentinel",
            lambda value: next(iter(value["watched_trees"].values())).__setitem__(
                ".", {"exists": False, "sha256": ""}
            ),
        )
        mutate(
            "non-dot missing tree child",
            lambda value: next(iter(value["watched_trees"].values())).__setitem__(
                "invented.json", {"exists": False, "sha256": ""}
            ),
        )
        mutate(
            "malformed README digest",
            lambda value: value["readme_operator_section_sha256"].__setitem__("Production", "not-a-digest"),
        )
        mutate(
            "extra README heading",
            lambda value: value["readme_operator_section_sha256"].__setitem__("Extra", "0" * 64),
        )

        for name, candidate in mutations:
            with self.subTest(name=name):
                self.write_bundle(candidate=candidate)
                with self.assertRaises(ValueError):
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
