import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEALTHCHECK = ROOT / "lifecycle" / "healthcheck.sh"


FAKE_DOCKER = r'''#!/usr/bin/env bash
set -euo pipefail
mode="${FAKE_DOCKER_MODE:-healthy}"
args="$*"
if [[ "$1" == "version" ]]; then
  printf '26.0.0\n'
  exit 0
fi
if [[ "$args" == *" config --services"* ]]; then
  printf 'db\nredis\nmisp-core\nmisp-modules\n'
  exit 0
fi
if [[ "$args" == *" ps --all --format json"* ]]; then
  printf '%s\n' '{"Service":"db","State":"running"}'
  printf '%s\n' '{"Service":"redis","State":"running"}'
  printf '%s\n' '{"Service":"misp-core","State":"running"}'
  if [[ "$mode" != "missing-service" ]]; then
    printf '%s\n' '{"Service":"misp-modules","State":"running"}'
  fi
  exit 0
fi
if [[ "$args" == *" config"* ]]; then
  [[ "$mode" != "slow" ]] || sleep 0.7
  exit 0
fi
if [[ "$args" == *"users/heartbeat"* ]]; then
  [[ "$mode" != "slow" ]] || sleep 0.7
  case "$mode" in
    heartbeat-http-error) exit 22 ;;
    heartbeat-redirect) printf '{"message":"redirect body"}\n302\n'; exit 0 ;;
    heartbeat-html) printf '<html>login</html>\n200\n'; exit 0 ;;
    heartbeat-wrong-json) printf '"You must construct additional pylons."\n200\n'; exit 0 ;;
    heartbeat-extra-fields) printf '{"message":"ok","debug":"not allowed"}\n200\n'; exit 0 ;;
    *) printf '{"message":"You must construct additional pylons."}\n200\n'; exit 0 ;;
  esac
fi
exit 1
'''


class HealthcheckCorrectnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.install_dir = self.root / "deployment"
        self.bin_dir = self.root / "bin"
        self.install_dir.mkdir()
        self.bin_dir.mkdir()
        (self.install_dir / ".env").write_text("PLACEHOLDER=1\n")
        (self.install_dir / "docker-compose.yml").write_text("services: {}\n")
        docker = self.bin_dir / "docker"
        docker.write_text(FAKE_DOCKER)
        docker.chmod(0o755)

    def run_healthcheck(self, checks, mode="healthy", timeout=3):
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"
        env["FAKE_DOCKER_MODE"] = mode
        proc = subprocess.run(
            [
                str(HEALTHCHECK), "--install-dir", str(self.install_dir),
                "--format", "json", "--checks", checks,
                "--timeout", str(timeout),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            env=env,
            timeout=timeout + 2,
            check=False,
        )
        return proc, json.loads(proc.stdout)

    def test_missing_expected_service_is_critical(self):
        proc, data = self.run_healthcheck("compose-services", "missing-service")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        check = next(item for item in data["checks"] if item["id"] == "compose-services")
        self.assertEqual(check["status"], "critical")
        self.assertIn("1 missing", check["summary"])
        self.assertEqual(data["metrics"]["services_expected"], 4)
        self.assertEqual(data["metrics"]["services_running"], 3)

    def test_all_expected_services_running_is_ok(self):
        proc, data = self.run_healthcheck("compose-services")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        check = next(item for item in data["checks"] if item["id"] == "compose-services")
        self.assertEqual(check["status"], "ok")
        self.assertEqual(data["metrics"]["services_expected"], 4)
        self.assertEqual(data["metrics"]["services_running"], 4)

    def test_heartbeat_requires_successful_http_and_json_string_contract(self):
        healthy_proc, healthy = self.run_healthcheck("misp-heartbeat")
        self.assertEqual(healthy_proc.returncode, 0, healthy_proc.stderr)
        self.assertEqual(healthy["status"], "ok")

        for mode in (
            "heartbeat-http-error", "heartbeat-redirect", "heartbeat-html",
            "heartbeat-wrong-json", "heartbeat-extra-fields",
        ):
            with self.subTest(mode=mode):
                proc, data = self.run_healthcheck("misp-heartbeat", mode)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                check = next(item for item in data["checks"] if item["id"] == "misp-heartbeat")
                self.assertEqual(check["status"], "critical")

    def test_timeout_is_one_global_deadline(self):
        started = time.monotonic()
        proc, data = self.run_healthcheck("compose-config,misp-heartbeat", "slow", timeout=1)
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 3, proc.stderr)
        self.assertEqual(data["status"], "unknown")
        self.assertLess(elapsed, 1.7, f"healthcheck exceeded global deadline: {elapsed:.3f}s")
        heartbeat = next(item for item in data["checks"] if item["id"] == "misp-heartbeat")
        self.assertIn("timed out", heartbeat["summary"])


if __name__ == "__main__":
    unittest.main()
