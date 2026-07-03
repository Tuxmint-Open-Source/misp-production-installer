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
        for name in ['install.sh', 'update.sh', 'backup.sh', 'doctor.sh', 'status.sh']:
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
            'PROXMOX_' + 'TOKEN_SECRET',
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

if __name__ == '__main__':
    unittest.main()
