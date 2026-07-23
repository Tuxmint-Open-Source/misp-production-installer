import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "lifecycle" / "sos-report.sh"
MODULE_PATH = ROOT / "scripts" / "generate_sos_report.py"
SPEC = importlib.util.spec_from_file_location("generate_sos_report", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SOS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOS)


class StructuredSosReportTests(unittest.TestCase):
    def run_report(self, install_dir, output, *args, env=None):
        return subprocess.run(
            [str(SCRIPT), "--install-dir", str(install_dir), "--output", str(output), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=20,
            env=env,
        )

    def test_no_docker_report_contains_only_allowlisted_facts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install_dir = root / "sensitive-deployment-name"
            install_dir.mkdir()
            (install_dir / ".env").write_text(
                "CORE_TAG=v2.5.44\n"
                "MODULES_TAG=registry.private.invalid/team/image:secret\n"
                "GUARD_TAG=v1.2\n"
                "ADMIN_EMAIL=private-user@private.invalid\n"
                "MYSQL_PASSWORD=fixture-secret-value\n"
                "BASE_URL=https://private.invalid\n"
            )
            (install_dir / ".installer-state.json").write_text(
                '{"base_url":"https://private.invalid","password":"fixture-secret-value"}\n'
            )
            (install_dir / "backups" / "private-backup-name").mkdir(parents=True)
            output = root / "report.md"
            result = self.run_report(
                install_dir, output, "--no-docker", "--workflow", "fresh-install",
                "--explain-redaction",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = output.read_text()
            self.assertIn("Report format: generated-sos-v2", report)
            self.assertIn("Affected workflow: fresh-install", report)
            self.assertIn("Default install directory used: no", report)
            self.assertIn("CORE_TAG: v2.5.44", report)
            self.assertIn("MODULES_TAG: redacted-or-invalid", report)
            self.assertIn("Docker checks enabled: no", report)
            self.assertIn("Overall health: not-checked", report)
            self.assertIn("Backup presence, names, paths, counts", report)
            self.assertIn("does not depend on regex redaction", report)
            for forbidden in (
                str(install_dir), "sensitive-deployment-name", "private.invalid",
                "private-user", "fixture-secret-value", "private-backup-name",
                "registry.private.invalid",
            ):
                self.assertNotIn(forbidden, report)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_fake_docker_output_is_never_copied(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install_dir = root / "install"
            install_dir.mkdir()
            fake_bin = root / "bin"
            fake_bin.mkdir()
            docker = fake_bin / "docker"
            docker.write_text("#!/bin/sh\nprintf '%s\\n' 'https://private.invalid fixture-secret-value'\n")
            docker.chmod(0o755)
            output = root / "report.md"
            env = {**os.environ, "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}
            result = self.run_report(
                install_dir, output, "--no-health-commands", "--workflow", "status", env=env
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = output.read_text()
            self.assertIn("Docker client version: unavailable", report)
            self.assertIn("Docker Compose version: unavailable", report)
            self.assertNotIn("private.invalid", report)
            self.assertNotIn("fixture-secret-value", report)

    def test_health_normalization_drops_free_form_and_unknown_fields(self):
        payload = {
            "status": "critical",
            "private_url": "https://private.invalid",
            "checks": [
                {"id": "compose-services", "status": "critical", "summary": "fixture-secret-value"},
                {"id": "attacker-controlled", "status": "ok", "summary": "private-host.invalid"},
            ],
        }
        normalized = SOS.normalize_health(payload)
        self.assertEqual(normalized["overall"], "critical")
        self.assertEqual(normalized["checks"]["compose-services"], "critical")
        self.assertNotIn("attacker-controlled", normalized["checks"])
        serialized = repr(normalized)
        self.assertNotIn("fixture-secret-value", serialized)
        self.assertNotIn("private.invalid", serialized)

    def test_invalid_workflow_is_rejected_without_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root / "report.md"
            result = self.run_report(
                root, output, "--no-docker", "--workflow", "private-host.invalid"
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_output_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target"
            target.write_text("do-not-overwrite")
            output = root / "report.md"
            output.symlink_to(target)
            result = self.run_report(root, output, "--no-docker")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), "do-not-overwrite")

    def test_output_parent_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real_parent = root / "real-parent"
            real_parent.mkdir()
            linked_parent = root / "linked-parent"
            linked_parent.symlink_to(real_parent, target_is_directory=True)
            output = linked_parent / "report.md"
            result = self.run_report(root, output, "--no-docker")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((real_parent / "report.md").exists())

    def test_existing_regular_output_is_replaced_with_mode_0600(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root / "report.md"
            output.write_text("old-content")
            output.chmod(0o644)
            result = self.run_report(root, output, "--no-docker")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("generated-sos-v2", output.read_text())
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_duplicate_or_oversized_public_tags_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env_file = root / ".env"
            env_file.write_text("CORE_TAG=v2.5.44\nCORE_TAG=private-value\n")
            tags = SOS.read_public_tags(env_file)
            self.assertEqual(tags["CORE_TAG"], "redacted-or-invalid")
            env_file.write_text("X" * (1024 * 1024 + 1))
            tags = SOS.read_public_tags(env_file)
            self.assertTrue(all(value == "unknown" for value in tags.values()))

    def test_component_tag_secret_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env_file = root / ".env"
            env_file.write_text("CORE_TAG=opaqueSecretValue123\n")
            self.assertEqual(SOS.read_public_tags(env_file)["CORE_TAG"], "redacted-or-invalid")
            target = root / "target"
            target.write_text("CORE_TAG=v2.5.44\n")
            env_file.unlink()
            env_file.symlink_to(target)
            self.assertTrue(all(value == "unknown" for value in SOS.read_public_tags(env_file).values()))
            self.assertEqual(SOS.file_mode(env_file), "not-regular")

    def test_all_subprocess_probes_share_one_monotonic_deadline(self):
        clock = [100.0]
        observed_timeouts = []

        def fake_run(args, **kwargs):
            timeout = kwargs["timeout"]
            observed_timeouts.append(timeout)
            delay = 0.75
            if timeout < delay:
                clock[0] += timeout
                raise subprocess.TimeoutExpired(args, timeout)
            clock[0] += delay
            stdout = "a" * 40 if args[0] == "git" else "1.2.3\n"
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

        args = SimpleNamespace(
            install_dir=Path("/tmp/not-a-misp-install"),
            timeout=2,
            no_docker=False,
            no_health_commands=False,
            workflow="unknown",
            explain_redaction=False,
        )
        with mock.patch.object(SOS.time, "monotonic", side_effect=lambda: clock[0]), mock.patch.object(
            SOS.subprocess, "run", side_effect=fake_run
        ):
            report = SOS.render_report(args)

        self.assertLessEqual(clock[0] - 100.0, 2.0)
        self.assertEqual(len(observed_timeouts), 3)
        self.assertGreater(observed_timeouts[0], observed_timeouts[1])
        self.assertGreater(observed_timeouts[1], observed_timeouts[2])
        self.assertIn("Docker client version: 1.2.3", report)
        self.assertIn("Docker Compose version: unavailable", report)
        self.assertIn("Overall health: unknown", report)

    def test_healthcheck_receives_only_the_remaining_deadline(self):
        observed = {}

        def fake_health(args, **kwargs):
            observed["command"] = args
            observed["timeout"] = kwargs["timeout"]
            payload = '{"status":"ok","checks":[]}'
            return subprocess.CompletedProcess(args, 0, stdout=payload, stderr="")

        with mock.patch.object(SOS.time, "monotonic", return_value=0.25):
            health = SOS.collect_health(Path("/tmp/not-a-misp-install"), True, 4.9, fake_health)

        command = observed["command"]
        self.assertEqual(command[command.index("--timeout") + 1], "4")
        selected_checks = command[command.index("--checks") + 1].split(",")
        self.assertEqual(
            selected_checks,
            ["compose-config", "compose-services", "misp-heartbeat", "schema-ready"],
        )
        self.assertNotIn("login", selected_checks)
        self.assertAlmostEqual(observed["timeout"], 4.65)
        self.assertEqual(health["overall"], "ok")

    def test_non_positive_global_timeout_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root / "report.md"
            result = self.run_report(root, output, "--no-docker", "--timeout", "0")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("timeout must be a positive integer", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
