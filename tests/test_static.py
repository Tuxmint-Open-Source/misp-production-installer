from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class StaticRepoTests(unittest.TestCase):
    def test_no_runtime_env_committed(self):
        self.assertFalse((ROOT / '.env').exists())
        self.assertFalse((ROOT / '.installer-state.json').exists())

    def test_scripts_are_bash_strict(self):
        for p in (ROOT / 'installer').glob('*.sh'):
            text = p.read_text()
            self.assertTrue(text.startswith('#!/usr/bin/env bash'), p)
            self.assertIn('set -euo pipefail', text, p)

    def test_main_scripts_have_help_and_version(self):
        for name in ['install.sh', 'update.sh', 'backup.sh', 'doctor.sh', 'status.sh', 'admin-credentials.sh', 'login-check.sh', 'get-current-misp-versions.sh', 'reset-installation.sh']:
            script = ROOT / 'installer' / name
            help_text = subprocess.check_output([str(script), '--help'], text=True, cwd=ROOT)
            self.assertIn('Usage:', help_text, name)
            version_text = subprocess.check_output([str(script), '--version'], text=True, cwd=ROOT).strip()
            self.assertRegex(version_text, r'^misp-production-installer \d+\.\d+\.\d+')

    def test_version_files_are_consistent(self):
        version = (ROOT / 'VERSION').read_text().strip()
        self.assertRegex(version, r'^\d+\.\d+\.\d+$')
        self.assertIn(f'Current installer version: `{version}`', (ROOT / 'README.md').read_text())
        self.assertIn(f'## [{version}]', (ROOT / 'CHANGELOG.md').read_text())

    def test_redis_password_url_safe_generation(self):
        text = (ROOT / 'installer' / 'generate-env.sh').read_text()
        self.assertIn('REDIS_PASSWORD_VALUE="$(random_hex 32)"', text)
        self.assertIn('session.save_path', text)

    def test_no_private_lab_markers(self):
        markers = [
            '192' + '.168.',
            '.loc' + '.internal',
            'TOKEN_' + 'SECRET',
            'PRIVATE_' + 'KEY',
            'BEGIN ' + 'OPENSSH ' + 'PRIVATE KEY',
        ]
        for p in ROOT.rglob('*'):
            if '.git' in p.parts or '__pycache__' in p.parts or p.suffix == '.pyc' or not p.is_file():
                continue
            text = p.read_text(errors='ignore')
            for marker in markers:
                self.assertNotIn(marker, text, f'{marker} leaked in {p}')

    def test_install_runs_db_updates_before_doctor(self):
        text = (ROOT / 'installer' / 'install.sh').read_text()
        self.assertLess(text.index('wait_for_misp_core'), text.index('run_misp_db_updates'))
        self.assertLess(text.index('run_misp_db_updates'), text.index('doctor.sh'))
        lib = (ROOT / 'installer' / 'lib.sh').read_text()
        self.assertIn('./Console/cake Admin runUpdates', lib)
        self.assertIn("SHOW TABLES LIKE", lib)

    def test_compose_wrapper_suppresses_optional_variable_noise(self):
        lib = (ROOT / 'installer' / 'lib.sh').read_text()
        self.assertIn('braced_pattern', lib)
        self.assertIn('plain_pattern', lib)
        self.assertIn('vars_seen - env_keys', lib)
        self.assertIn('env_args+=("$var_name=")', lib)
        self.assertIn('env "${env_args[@]}" docker compose', lib)

    def test_misp_image_tags_are_deterministic_by_default(self):
        lib = (ROOT / 'installer' / 'lib.sh').read_text()
        update = (ROOT / 'installer' / 'update.sh').read_text()
        generate = (ROOT / 'installer' / 'generate-env.sh').read_text()
        versions = (ROOT / 'installer' / 'get-current-misp-versions.sh').read_text()
        self.assertIn('sync_misp_image_tags()', lib)
        self.assertIn('CORE_RUNNING_TAG', lib)
        self.assertIn('MODULES_RUNNING_TAG', lib)
        self.assertIn('GUARD_RUNNING_TAG', lib)
        self.assertIn('IMAGE_TRACK="version-tags"', update)
        self.assertIn('sync_misp_image_tags "$INSTALL_DIR" "$IMAGE_TRACK"', update)
        self.assertIn('sync_misp_image_tags "$INSTALL_DIR" version-tags', generate)
        self.assertIn('component upstream_tag local_component_tag local_running_tag', versions)

    def test_admin_credentials_helper_is_safe_by_default(self):
        text = (ROOT / 'installer' / 'admin-credentials.sh').read_text()
        self.assertIn('--show-password', text)
        self.assertIn('ADMIN_PASSWORD=(hidden', text)
        self.assertIn('Use --show-password only on a trusted', text)

    def test_login_check_does_not_print_password(self):
        text = (ROOT / 'installer' / 'login-check.sh').read_text()
        self.assertIn('HTTPCookieProcessor', text)
        self.assertIn('csrf_marker', text)
        self.assertIn('invalid_credentials_marker', text)
        self.assertIn('It never prints the password', text)
        self.assertIn('users/logout', text)
        self.assertIn('logout_attempted', text)

    def test_reset_installation_has_safety_guards(self):
        text = (ROOT / 'installer' / 'reset-installation.sh').read_text()
        self.assertIn('Dry-run only', text)
        self.assertIn('Are you sure you want to delete everything', text)
        self.assertIn('Type DELETE to continue', text)
        self.assertIn('down --volumes --remove-orphans', text)
        self.assertIn('Refusing unsafe --install-dir', text)
        self.assertIn('Docker Engine itself is not removed', text)

    def test_upstream_monitoring_artifacts_exist(self):
        self.assertTrue((ROOT / 'scripts' / 'check-upstream-misp-docker.py').exists())
        self.assertTrue((ROOT / '.github' / 'workflows' / 'upstream-misp-docker-watch.yml').exists())
        self.assertTrue((ROOT / '.upstream' / 'misp-docker.lock.json').exists())
        monitor = (ROOT / 'scripts' / 'check-upstream-misp-docker.py').read_text()
        self.assertIn('template.env', monitor)
        self.assertIn('docker-compose.yml', monitor)
        self.assertIn('CORE_TAG', monitor)
        self.assertIn('MODULES_TAG', monitor)
        self.assertIn('GUARD_TAG', monitor)

if __name__ == '__main__':
    unittest.main()
