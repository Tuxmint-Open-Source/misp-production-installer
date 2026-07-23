import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-backup.py"


def add_bytes(archive: tarfile.TarFile, name: str, data: bytes = b"data\n", mode: int = 0o600) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(data)
    member.mode = mode
    archive.addfile(member, io.BytesIO(data))


def rewrite_checksums(backup: Path) -> None:
    lines = []
    for name in ["misp.sql", "misp-host-data.tar.gz", "misp-config.tar.gz"]:
        digest = hashlib.sha256((backup / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (backup / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def make_backup(
    root: Path,
    *,
    extra_config: str | None = None,
    unsafe_host_link: bool = False,
    state_overrides: dict[str, object] | None = None,
    env_text: bytes = b"BASE_URL=https://misp.example.com\n",
) -> Path:
    backup = root / "backup"
    backup.mkdir()
    state: dict[str, object] = {"installer": "misp-docker-lifecycle-manager"}
    state.update(state_overrides or {})
    (backup / "misp.sql").write_text("-- test dump\n")
    with tarfile.open(backup / "misp-config.tar.gz", "w:gz") as archive:
        add_bytes(archive, ".env", env_text)
        add_bytes(archive, "docker-compose.override.yml", b"services: {}\n")
        add_bytes(archive, ".installer-state.json", json.dumps(state).encode())
        if extra_config:
            add_bytes(archive, extra_config, b"unexpected\n", 0o755)
    with tarfile.open(backup / "misp-host-data.tar.gz", "w:gz") as archive:
        add_bytes(archive, "configs/config.php")
        if unsafe_host_link:
            member = tarfile.TarInfo("configs/escape")
            member.type = tarfile.SYMTYPE
            member.linkname = "../../outside"
            archive.addfile(member)
    rewrite_checksums(backup)
    return backup


class BackupValidationTests(unittest.TestCase):
    def run_validator(self, backup: Path, staging: Path | None = None):
        command = ["python3", str(VALIDATOR), str(backup)]
        if staging is not None:
            command.append(str(staging))
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_accepts_manager_backup_shape(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.run_validator(make_backup(Path(td)))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("backup validation OK", result.stdout)

    def test_stages_private_regular_copies_before_validation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            backup = make_backup(root)
            staging = root / "staging"
            result = self.run_validator(backup, staging)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({path.name for path in staging.iterdir()}, {
                "misp.sql", "misp-host-data.tar.gz", "misp-config.tar.gz", "SHA256SUMS",
            })
            for path in staging.iterdir():
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_accepts_legacy_absolute_manifest_paths_without_following_them(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td))
            lines = backup.joinpath("SHA256SUMS").read_text().splitlines()
            backup.joinpath("SHA256SUMS").write_text("\n".join(
                line.split("  ", 1)[0] + "  /old/location/" + line.split("  ", 1)[1]
                for line in lines
            ) + "\n")
            result = self.run_validator(backup)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_relative_manifest_paths(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td))
            lines = backup.joinpath("SHA256SUMS").read_text().splitlines()
            first_digest = lines[0].split("  ", 1)[0]
            lines[0] = first_digest + "  ../" + lines[0].split("  ", 1)[1]
            backup.joinpath("SHA256SUMS").write_text("\n".join(lines) + "\n")
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsafe relative SHA256SUMS path", result.stderr)

    def test_rejects_unexpected_config_archive_member(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.run_validator(make_backup(Path(td), extra_config=".git/hooks/post-checkout"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unexpected configuration archive member", result.stderr)

    def test_rejects_host_symlink_that_escapes_archive_root(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.run_validator(make_backup(Path(td), unsafe_host_link=True))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsafe link target", result.stderr)

    def test_rejects_setuid_host_member(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td))
            with tarfile.open(backup / "misp-host-data.tar.gz", "w:gz") as archive:
                add_bytes(archive, "configs/unsafe", mode=0o4755)
            rewrite_checksums(backup)
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("setuid/setgid mode", result.stderr)

    def test_rejects_credential_bearing_repository_from_backup_state(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td), state_overrides={
                "upstream_repo": "https://user:credential@example.invalid/repo.git",
                "upstream_ref": "master",
            })
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsafe upstream repository", result.stderr)
            self.assertNotIn("credential@example", result.stderr)

    def test_rejects_malformed_repository_without_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td), state_overrides={
                "upstream_repo": "https://[invalid/repo.git",
                "upstream_ref": "master",
            })
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsafe upstream repository", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_symlinked_backup_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            backup = make_backup(root)
            target = root / "external.sql"
            target.write_text("-- replacement\n")
            (backup / "misp.sql").unlink()
            (backup / "misp.sql").symlink_to(target)
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("regular non-symlink file", result.stderr)

    def test_rejects_option_like_repository_from_backup_state(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td), state_overrides={
                "upstream_repo": "--upload-pack=unsafe-command",
                "upstream_ref": "master",
            })
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsafe upstream repository", result.stderr)

    def test_rejects_non_string_upstream_source_in_backup_state(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td), state_overrides={"upstream_repo": ["unexpected"]})
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source and deployment fields must be strings", result.stderr)

    def test_rejects_falsey_non_string_upstream_source_in_backup_state(self):
        for value in (0, [], {}):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as td:
                backup = make_backup(Path(td), state_overrides={"upstream_repo": value})
                result = self.run_validator(backup)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("source and deployment fields must be strings", result.stderr)

    def test_rejects_malformed_base_url_before_restore(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(
                Path(td),
                env_text=b"BASE_URL=https://misp.example.com/?unsafe=true\n",
            )
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("BASE_URL must not contain a query or fragment", result.stderr)

    def test_rejects_state_and_environment_base_url_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td), state_overrides={
                "exposure": "reverse-proxy",
                "base_url": "https://other.example.com",
            })
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not match .installer-state.json", result.stderr)

    def test_rejects_invalid_resolved_commit_in_backup_state(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td), state_overrides={"upstream_commit": "master"})
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid upstream commit", result.stderr)

    def test_rejects_oversized_configuration_member(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(
                Path(td),
                env_text=b"BASE_URL=https://misp.example.com\n" + b"X" * (1024 * 1024),
            )
            result = self.run_validator(backup)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("configuration archive member is too large", result.stderr)

    def test_fetch_upstream_rejects_option_like_repository_before_git(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = root / "must-not-exist"
            result = subprocess.run([
                str(ROOT / "lifecycle" / "fetch-upstream.sh"),
                "--upstream-repo", f"--upload-pack=touch {marker}",
                "--upstream-ref", "master",
                "--install-dir", str(root / "checkout"),
            ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertIn("unsafe option/control characters", result.stderr)

    def test_fetch_upstream_rejects_existing_origin_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            checkout = root / "checkout"
            (checkout / ".git").mkdir(parents=True)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            operations = root / "git-operations"
            git = fake_bin / "git"
            git.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' \"$*\" >> {operations}\n"
                "case \"$*\" in *'remote get-url origin'*) printf '%s\\n' 'https://example.invalid/other.git';; esac\n"
            )
            git.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            result = subprocess.run([
                str(ROOT / "lifecycle" / "fetch-upstream.sh"),
                "--upstream-repo", "https://github.com/MISP/misp-docker.git",
                "--upstream-ref", "master",
                "--install-dir", str(checkout),
            ], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("origin does not match", result.stderr)
            self.assertNotIn("fetch --tags origin", operations.read_text())

    def test_restore_rejects_non_git_target_before_docker_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            backup = make_backup(root)
            target = root / "existing-target"
            target.mkdir()
            (target / ".env").write_text("TEST=1\n")
            (target / "docker-compose.yml").write_text("services: {}\n")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            marker = root / "docker-was-called"
            docker = fake_bin / "docker"
            docker.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n")
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            result = subprocess.run([
                str(ROOT / "lifecycle" / "restore.sh"),
                "--backup-dir", str(backup),
                "--install-dir", str(target),
                "--yes", "--force",
            ], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertTrue(target.exists())
            self.assertIn("not a git checkout", result.stderr)

    def test_rejects_authenticated_upstream_url(self):
        result = subprocess.run([
            "bash", "-c",
            "source lifecycle/lib.sh; validate_upstream_source 'https://user:credential@example.invalid/repo.git' master",
        ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not contain credentials", result.stderr)
        self.assertNotIn("credential@example", result.stderr)

    def test_backup_rejects_symlinked_root_before_compose(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install = root / "install"
            install.mkdir()
            (install / ".env").write_text("TEST=1\n")
            destination = root / "destination"
            destination.mkdir()
            linked = root / "linked-root"
            linked.symlink_to(destination, target_is_directory=True)
            result = subprocess.run([
                str(ROOT / "lifecycle" / "backup.sh"),
                "--install-dir", str(install),
                "--backup-root", str(linked),
            ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-symlink directory", result.stderr)
            self.assertEqual(list(destination.iterdir()), [])

    def test_backup_rejects_world_writable_root_before_compose(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install = root / "install"
            install.mkdir()
            (install / ".env").write_text("TEST=1\n")
            backup_root = root / "backup-root"
            backup_root.mkdir()
            backup_root.chmod(0o777)
            result = subprocess.run([
                str(ROOT / "lifecycle" / "backup.sh"),
                "--install-dir", str(install),
                "--backup-root", str(backup_root),
            ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must not be group- or world-writable", result.stderr)
            self.assertEqual(list(backup_root.iterdir()), [])

    def test_restore_requires_explicit_non_default_repository(self):
        with tempfile.TemporaryDirectory() as td:
            backup = make_backup(Path(td), state_overrides={
                "upstream_repo": "https://example.invalid/repo.git",
                "upstream_ref": "master",
            })
            target = Path(td) / "new-target"
            result = subprocess.run([
                str(ROOT / "lifecycle" / "restore.sh"),
                "--backup-dir", str(backup),
                "--install-dir", str(target),
                "--yes", "--force",
            ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pass the reviewed repository explicitly", result.stderr)

    def test_restore_rejects_unmarked_git_target_before_docker_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            backup = make_backup(root)
            target = root / "existing-target"
            (target / ".git").mkdir(parents=True)
            (target / ".env").write_text("TEST=1\n")
            (target / "docker-compose.yml").write_text("services: {}\n")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            marker = root / "docker-was-called"
            docker = fake_bin / "docker"
            docker.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n")
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            result = subprocess.run([
                str(ROOT / "lifecycle" / "restore.sh"),
                "--backup-dir", str(backup),
                "--install-dir", str(target),
                "--yes", "--force",
            ], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertIn("lacks valid lifecycle-manager state", result.stderr)

    def test_restore_stops_when_compose_cleanup_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "existing-target"
            backup = make_backup(root, state_overrides={
                "install_dir": str(target),
                "upstream_repo": "https://github.com/MISP/misp-docker.git",
                "upstream_ref": "master",
            })
            subprocess.run(["git", "init", "-q", str(target)], check=True)
            subprocess.run(["git", "-C", str(target), "remote", "add", "origin", "https://github.com/MISP/misp-docker.git"], check=True)
            (target / ".env").write_text("TEST=1\n")
            (target / "docker-compose.yml").write_text("services: {}\n")
            (target / ".installer-state.json").write_text(json.dumps({
                "installer": "misp-docker-lifecycle-manager",
                "install_dir": str(target),
            }))
            fake_bin = root / "bin"
            fake_bin.mkdir()
            marker = root / "docker-was-called"
            docker = fake_bin / "docker"
            docker.write_text(f"#!/bin/sh\ntouch {marker}\nexit 9\n")
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            result = subprocess.run([
                str(ROOT / "lifecycle" / "restore.sh"),
                "--backup-dir", str(backup),
                "--install-dir", str(target),
                "--yes", "--force",
            ], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(marker.exists())
            self.assertFalse((target / "configs").exists())

    def test_state_writer_uses_mode_600(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / ".installer-state.json"
            subprocess.run([
                "bash", "-c",
                "source lifecycle/lib.sh; write_state \"$1\" repo master 0123456789abcdef0123456789abcdef01234567 /opt/misp-docker reverse-proxy https://misp.example.com",
                "_", str(state),
            ], cwd=ROOT, check=True)
            self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o600)
            data = json.loads(state.read_text())
            self.assertEqual(data["upstream_ref"], "master")
            self.assertEqual(data["upstream_commit"], "0123456789abcdef0123456789abcdef01234567")


if __name__ == "__main__":
    unittest.main()
