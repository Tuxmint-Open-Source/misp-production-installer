import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-upstream-misp-docker.py"
SPEC = importlib.util.spec_from_file_location("upstream_watch", SCRIPT)
assert SPEC and SPEC.loader
WATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCH)


class UpstreamWatcherTests(unittest.TestCase):
    def make_state(self):
        return {
            "schema": 2,
            "repo": "https://github.com/MISP/misp-docker.git",
            "ref": "master",
            "upstream_commit": "a" * 40,
            "checked_at_utc": "2026-07-17T00:00:00Z",
            "watched_files": {
                rel: {"exists": True, "sha256": "same"}
                for rel in WATCH.WATCHED_FILES
            },
            "watched_trees": {
                "core/files/etc/misp-docker": {
                    "critical.envars.json": {"exists": True, "sha256": "same"}
                }
            },
            "component_tags": {
                "CORE_TAG": "v1",
                "MODULES_TAG": "v2",
                "GUARD_TAG": "v3",
            },
            "running_tag_defaults_in_template_env": {
                "CORE_RUNNING_TAG": "(commented or unset)",
                "MODULES_RUNNING_TAG": "(commented or unset)",
                "GUARD_RUNNING_TAG": "(commented or unset)",
            },
            "template_env_keys": {
                "active_keys": ["CORE_TAG"],
                "commented_keys": ["CORE_RUNNING_TAG"],
            },
            "compose": {
                "services": ["db", "misp-core"],
                "images": {"misp-core": "example/core:${CORE_RUNNING_TAG:-latest}"},
                "service_block_hashes": {"db": "db-hash", "misp-core": "core-hash"},
                "interpolation_keys": ["CORE_RUNNING_TAG"],
                "interpolation_contract": {"CORE_RUNNING_TAG": [":-"]},
            },
            "readme_operator_section_sha256": {
                heading: "same" for heading in WATCH.README_SECTIONS
            },
        }

    def test_commit_only_movement_is_not_drift(self):
        old = self.make_state()
        new = copy.deepcopy(old)
        new["upstream_commit"] = "b" * 40
        self.assertEqual(WATCH.diff_state(old, new), [])

    def test_component_tag_change_is_class_a(self):
        old = self.make_state()
        new = copy.deepcopy(old)
        new["component_tags"]["CORE_TAG"] = "v2"
        changes = WATCH.diff_state(old, new)
        self.assertIn("A", {change["class"] for change in changes})
        self.assertTrue(any("component tag" in change["detail"].lower() for change in changes))

    def test_compose_service_change_is_class_b(self):
        old = self.make_state()
        new = copy.deepcopy(old)
        new["watched_files"]["docker-compose.yml"]["sha256"] = "changed"
        new["compose"]["service_block_hashes"]["misp-core"] = "changed"
        changes = WATCH.diff_state(old, new)
        self.assertIn("B", {change["class"] for change in changes})
        self.assertTrue(any("`misp-core`" in change["detail"] for change in changes))

    def test_template_and_operator_guidance_changes_are_class_c(self):
        old = self.make_state()
        new = copy.deepcopy(old)
        new["template_env_keys"]["active_keys"].append("NEW_REQUIRED_INPUT")
        new["readme_operator_section_sha256"]["Database Management"] = "changed"
        changes = WATCH.diff_state(old, new)
        self.assertIn("C", {change["class"] for change in changes})
        self.assertTrue(any("Database Management" in change["detail"] for change in changes))

    def test_compose_parser_tracks_service_blocks_and_variables(self):
        text = """services:
  db:
    image: mariadb:10
  misp-core:
    image: ghcr.io/misp/core:${CORE_RUNNING_TAG:-latest}
    ports:
      - ${CORE_HTTPS_PORT:-443}:443
volumes:
  data:
"""
        facts = WATCH.parse_compose_facts(text)
        self.assertEqual(facts["services"], ["db", "misp-core"])
        self.assertEqual(facts["interpolation_keys"], ["CORE_HTTPS_PORT", "CORE_RUNNING_TAG"])
        self.assertEqual(facts["interpolation_contract"], {
            "CORE_HTTPS_PORT": [":-"],
            "CORE_RUNNING_TAG": [":-"],
        })
        self.assertEqual(set(facts["service_block_hashes"]), {"db", "misp-core"})

    def test_interpolation_requiredness_change_is_class_b_without_values(self):
        old = self.make_state()
        new = copy.deepcopy(old)
        new["compose"]["interpolation_contract"]["CORE_RUNNING_TAG"] = [":?"]
        changes = WATCH.diff_state(old, new)
        self.assertTrue(any(
            change["class"] == "B" and "operator contract" in change["detail"]
            for change in changes
        ))
        self.assertNotIn("latest", str(new["compose"]["interpolation_contract"]))

    def test_configuration_tree_addition_is_class_b(self):
        old = self.make_state()
        new = copy.deepcopy(old)
        new["watched_trees"]["core/files/etc/misp-docker"]["new.envars.json"] = {
            "exists": True,
            "sha256": "new",
        }
        changes = WATCH.diff_state(old, new)
        self.assertTrue(any(
            change["class"] == "B" and "new.envars.json" in change["detail"]
            for change in changes
        ))

    def test_env_inventory_never_records_values(self):
        inventory = WATCH.parse_env_key_inventory("ACTIVE=public\n# SECRET_NAME=do-not-record\n")
        self.assertEqual(inventory, {
            "active_keys": ["ACTIVE"],
            "commented_keys": ["SECRET_NAME"],
        })
        self.assertNotIn("do-not-record", str(inventory))

    def test_report_preserves_compatibility_boundary(self):
        old = self.make_state()
        new = copy.deepcopy(old)
        new["component_tags"]["CORE_TAG"] = "v2"
        report = WATCH.render_report(old, new, WATCH.diff_state(old, new))
        self.assertIn("prompt, not compatibility proof", report)
        self.assertIn("review required / not validated", report)
        self.assertIn("Lifecycle-manager context", report)
        self.assertIn("validated compatible", report)
        self.assertIn("Compose services added", report)
        self.assertNotIn("certified", report.lower())


if __name__ == "__main__":
    unittest.main()
