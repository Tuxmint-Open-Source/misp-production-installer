import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_bash(script: str, *args: str, env: dict[str, str] | None = None):
    return subprocess.run(
        ["bash", "-c", script, "_", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def init_upstream(path: Path) -> None:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "master", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    (path / "template.env").write_text(
        "CORE_TAG=v2.5.44\nMODULES_TAG=v3.0.9\nGUARD_TAG=v1.2\n"
    )
    (path / "docker-compose.yml").write_text("services:\n  misp-core:\n    image: example.invalid/misp:fixture\n")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "fixture"], check=True)


class LifecycleSafetyTests(unittest.TestCase):
    def test_generate_env_rejects_control_characters_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            install = Path(td)
            (install / "template.env").write_text(
                "CORE_TAG=v2.5.44\nMODULES_TAG=v3.0.9\nGUARD_TAG=v1.2\n"
            )
            result = subprocess.run(
                [
                    str(ROOT / "lifecycle" / "generate-env.sh"),
                    "--install-dir", str(install),
                    "--base-url", "https://misp.example.com",
                    "--admin-email", "admin@example.com",
                    "--admin-org", "SafeOrg\nCOMPOSE_PROJECT_NAME=unexpected",
                    "--timezone", "UTC",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((install / ".env").exists())

    def test_base_url_rejects_userinfo_query_and_fragment(self):
        for url in (
            "https://user@misp.example.com",
            "https://misp.example.com/path?mode=unsafe",
            "https://misp.example.com/path#fragment",
            "https://[2001:db8::1",
        ):
            with self.subTest(url=url):
                result = run_bash(
                    'source lifecycle/lib.sh; validate_public_base_url "$1" reverse-proxy',
                    url,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)

    def test_existing_checkout_advances_to_fetched_branch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            remote = root / "upstream"
            init_upstream(remote)
            install = root / "install"
            command = ROOT / "lifecycle" / "fetch-upstream.sh"
            first = subprocess.run(
                [str(command), "--upstream-repo", str(remote), "--upstream-ref", "master", "--install-dir", str(install)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            old_commit = subprocess.check_output(["git", "-C", str(install), "rev-parse", "HEAD"], text=True).strip()
            (remote / "template.env").write_text(
                "CORE_TAG=v2.5.45\nMODULES_TAG=v3.0.9\nGUARD_TAG=v1.2\n"
            )
            subprocess.run(["git", "-C", str(remote), "commit", "-qam", "advance"], check=True)
            expected = subprocess.check_output(["git", "-C", str(remote), "rev-parse", "HEAD"], text=True).strip()
            second = subprocess.run(
                [str(command), "--upstream-repo", str(remote), "--upstream-ref", "master", "--install-dir", str(install)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            actual = subprocess.check_output(["git", "-C", str(install), "rev-parse", "HEAD"], text=True).strip()
            self.assertNotEqual(actual, old_commit)
            self.assertEqual(actual, expected)

    def test_restore_root_cleanup_unlinks_destination_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install = root / "install"
            outside = root / "outside"
            install.mkdir()
            outside.mkdir()
            (outside / "keep").write_text("outside\n")
            (install / "configs").symlink_to(outside, target_is_directory=True)
            result = run_bash(
                'source lifecycle/lib.sh; prepare_restore_host_roots "$1"',
                str(install),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((install / "configs").exists())
            self.assertEqual((outside / "keep").read_text(), "outside\n")

    def test_heartbeat_rejects_http_error_even_when_curl_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install = root / "install"
            fake_bin = root / "bin"
            install.mkdir()
            fake_bin.mkdir()
            (install / ".env").write_text("TEST=1\n")
            (install / "docker-compose.yml").write_text("services: {}\n")
            docker = fake_bin / "docker"
            docker.write_text("#!/bin/sh\nprintf '{\"message\":\"error\"}\\n500\\n'\n")
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            result = run_bash(
                'source lifecycle/lib.sh; check_misp_heartbeat "$1"',
                str(install),
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_no_start_does_not_claim_login_readiness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            upstream = root / "upstream"
            install = root / "install"
            fake_bin = root / "bin"
            init_upstream(upstream)
            fake_bin.mkdir()
            docker = fake_bin / "docker"
            docker.write_text("#!/bin/sh\nexit 0\n")
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            result = subprocess.run(
                [
                    str(ROOT / "lifecycle" / "install.sh"),
                    "--upstream-repo", str(upstream),
                    "--upstream-ref", "master",
                    "--install-dir", str(install),
                    "--base-url", "https://misp.example.com",
                    "--admin-email", "admin@example.com",
                    "--admin-org", "Example Org",
                    "--timezone", "UTC",
                    "--no-start",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Interactive login: ready", result.stdout)
            self.assertIn("Stack start: skipped", result.stdout)
            state = json.loads((install / ".installer-state.json").read_text())
            self.assertRegex(state["upstream_commit"], r"^[0-9a-f]{40}$")
            self.assertEqual(state["upstream_ref"], "master")

    def test_operation_lock_rejects_concurrent_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            install = str(Path(td) / "install")
            first = subprocess.Popen(
                [
                    "bash", "-c",
                    'source lifecycle/lib.sh; acquire_operation_lock "$1"; echo locked; sleep 10',
                    "_", install,
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertEqual(first.stdout.readline().strip(), "locked")
                alias = str(Path(td) / "unused" / ".." / "install")
                second = run_bash(
                    'source lifecycle/lib.sh; acquire_operation_lock "$1"',
                    alias,
                )
                self.assertNotEqual(second.returncode, 0)
                self.assertIn("Another lifecycle operation", second.stderr)
            finally:
                first.terminate()
                first.communicate(timeout=5)

    def test_backup_quiesces_and_restarts_running_application_services(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install = root / "install"
            backup_root = root / "backups"
            fake_bin = root / "bin"
            install.mkdir()
            backup_root.mkdir(mode=0o700)
            fake_bin.mkdir()
            (install / ".env").write_text("BASE_URL=https://misp.example.com\n")
            (install / ".env").chmod(0o600)
            (install / "docker-compose.yml").write_text("services: {}\n")
            (install / "docker-compose.override.yml").write_text("services: {}\n")
            for name in ("configs", "logs", "files", "ssl", "gnupg", "custom", "guard"):
                (install / name).mkdir()
            (install / "configs" / "config.php").write_text("fixture\n")
            log = root / "docker.log"
            docker = fake_bin / "docker"
            docker.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >> \"$DOCKER_LOG\"\n"
                "case \"$*\" in\n"
                "  *\" ps --status running --services\") printf 'misp-core\\ndb\\nredis\\n';;\n"
                "  *\" exec -T db \"*) printf '%s\\n' '-- fixture dump';;\n"
                "esac\n"
            )
            docker.chmod(0o755)
            sudo = fake_bin / "sudo"
            sudo.write_text("#!/bin/sh\nexec \"$@\"\n")
            sudo.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            env["DOCKER_LOG"] = str(log)
            result = subprocess.run(
                [
                    str(ROOT / "lifecycle" / "backup.sh"),
                    "--install-dir", str(install),
                    "--backup-root", str(backup_root),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = log.read_text().splitlines()
            stop_index = next(i for i, call in enumerate(calls) if " stop misp-core" in call)
            dump_index = next(i for i, call in enumerate(calls) if " exec -T db " in call)
            restart_index = next(i for i, call in enumerate(calls) if " up -d misp-core" in call)
            self.assertLess(stop_index, dump_index)
            self.assertLess(dump_index, restart_index)
            backups = [path for path in backup_root.iterdir() if path.is_dir()]
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "SHA256SUMS").is_file())

    def test_host_preparation_rejects_unsupported_host_before_package_changes(self):
        os_release = {}
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_release[key] = value.strip('"')
        architecture = subprocess.check_output(["uname", "-m"], text=True).strip()
        if os_release.get("ID") in {"rocky", "almalinux", "rhel", "centos"} and architecture == "x86_64":
            self.skipTest("test requires an unsupported host")
        result = subprocess.run(
            [str(ROOT / "lifecycle" / "prepare-host-rocky.sh")],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("supports Rocky-compatible Linux on x86_64", result.stderr)

    def test_restore_clears_managed_roots_before_privileged_extraction(self):
        text = (ROOT / "lifecycle" / "restore.sh").read_text()
        cleanup = text.index('prepare_restore_host_roots "$INSTALL_DIR"')
        extraction = text.index('sudo tar -C "$INSTALL_DIR" -xzf "$BACKUP_DIR/misp-host-data.tar.gz"')
        self.assertLess(cleanup, extraction)

    def test_action_version_annotations_match_pinned_shas(self):
        workflow = (ROOT / ".github" / "workflows" / "operator-bundle-release-assets.yml").read_text()
        self.assertIn(
            "# actions/upload-artifact@v6\n        uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f",
            workflow,
        )
        self.assertIn(
            "# actions/download-artifact@v7\n        uses: actions/download-artifact@37930b1c2abaa49bbe596cd826c3c89aef350131",
            workflow,
        )

    def test_reset_rejects_target_replaced_during_lock_acquisition(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install = root / "install"
            install.mkdir()
            (install / ".installer-state.json").write_text(
                json.dumps({"installer": "misp-docker-lifecycle-manager"})
            )
            fake_bin = root / "bin"
            fake_bin.mkdir()
            flock = fake_bin / "flock"
            flock.write_text(
                "#!/bin/sh\n"
                "rm -rf -- \"$RESET_TARGET\"\n"
                "mkdir -p -- \"$RESET_TARGET\"\n"
                "printf replaced > \"$RESET_TARGET/replacement-marker\"\n"
            )
            flock.chmod(0o755)
            docker_marker = root / "docker-called"
            docker = fake_bin / "docker"
            docker.write_text(f"#!/bin/sh\ntouch {docker_marker}\n")
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            env["RESET_TARGET"] = str(install)
            result = subprocess.run(
                [
                    str(ROOT / "lifecycle" / "reset-installation.sh"),
                    "--install-dir", str(install), "--yes", "--force",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Reset target changed after review", result.stderr)
            self.assertTrue((install / "replacement-marker").exists())
            self.assertFalse(docker_marker.exists())

    def test_mutating_entry_points_acquire_operation_lock(self):
        scripts = (
            "backup.sh", "bootstrap-tls.sh", "down.sh", "fetch-upstream.sh",
            "generate-env.sh", "install.sh", "pull.sh", "render-compose.sh",
            "reset-installation.sh", "restore.sh", "up.sh", "update.sh",
        )
        for name in scripts:
            with self.subTest(script=name):
                text = (ROOT / "lifecycle" / name).read_text()
                self.assertIn("acquire_operation_lock", text)
        for name in ("up.sh", "down.sh", "pull.sh"):
            with self.subTest(forwarding=name):
                self.assertIn('"$@"', (ROOT / "lifecycle" / name).read_text())

    def test_install_propagates_doctor_failure(self):
        text = (ROOT / "lifecycle" / "install.sh").read_text()
        doctor_call = '"$SCRIPT_DIR/doctor.sh" --install-dir "$INSTALL_DIR"'
        self.assertIn(doctor_call, text)
        self.assertNotIn(doctor_call + ' ||', text)

    def test_update_handles_an_unchanged_core_without_stale_logs(self):
        text = (ROOT / "lifecycle" / "update.sh").read_text()
        self.assertIn('previous_core_id=', text)
        self.assertIn('current_core_id=', text)
        self.assertIn('"$previous_core_id" == "$current_core_id"', text)
        self.assertIn('wait_for_misp_live_marker "$INSTALL_DIR" 900 "$operation_started_at"', text)


if __name__ == "__main__":
    unittest.main()
