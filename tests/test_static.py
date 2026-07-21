from pathlib import Path
import json
import re
import subprocess
import tempfile
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
        for name in ['install.sh', 'update.sh', 'backup.sh', 'restore.sh', 'doctor.sh', 'status.sh', 'healthcheck.sh', 'admin-credentials.sh', 'login-check.sh', 'sos-report.sh', 'get-current-misp-versions.sh', 'reset-installation.sh']:
            script = ROOT / 'installer' / name
            help_text = subprocess.check_output([str(script), '--help'], text=True, cwd=ROOT)
            self.assertIn('Usage:', help_text, name)
            version_text = subprocess.check_output([str(script), '--version'], text=True, cwd=ROOT).strip()
            self.assertRegex(version_text, r'^misp-docker-lifecycle-manager \d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?')

    def test_version_files_are_consistent(self):
        version = (ROOT / 'VERSION').read_text().strip()
        self.assertRegex(version, r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')
        self.assertIn(f'Current `VERSION` value on `main`: `{version}`', (ROOT / 'README.md').read_text())
        self.assertIn(f'## [{version}]', (ROOT / 'CHANGELOG.md').read_text())

    def test_redis_password_url_safe_generation(self):
        text = (ROOT / 'installer' / 'generate-env.sh').read_text()
        self.assertIn('MYSQL_PASSWORD_VALUE="$(random_hex 32)"', text)
        self.assertIn('MYSQL_ROOT_PASSWORD_VALUE="$(random_hex 32)"', text)
        self.assertIn('alphanumeric-only', text)
        self.assertIn('REDIS_PASSWORD_VALUE="$(random_hex 32)"', text)
        self.assertIn('session.save_path', text)

    def test_direct_qa_rejects_loopback_base_url(self):
        lib = (ROOT / 'installer' / 'lib.sh').read_text()
        install = (ROOT / 'installer' / 'install.sh').read_text()
        generate = (ROOT / 'installer' / 'generate-env.sh').read_text()
        self.assertIn('validate_public_base_url()', lib)
        self.assertIn('localhost would redirect browsers back to their own machine', lib)
        self.assertIn('ip.is_loopback', lib)
        self.assertIn('validate_public_base_url "$BASE_URL" "$EXPOSURE"', install)
        self.assertIn('validate_public_base_url "$BASE_URL" "$EXPOSURE"', generate)

    def test_no_private_lab_markers(self):
        markers = [
            '10' + '.0.',
            '10' + '.1.',
            '172' + '.16.',
            '172' + '.31.',
            '192' + '.168.',
            '.loc' + '.internal',
            '/home/' + 'hermes',
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
        self.assertLess(text.index('run_misp_db_updates'), text.index('wait_for_misp_live_marker'))
        self.assertLess(text.index('wait_for_misp_live_marker'), text.index('doctor.sh'))
        self.assertIn('Credentials helper: sudo ./installer/admin-credentials.sh --install-dir $INSTALL_DIR', text)
        self.assertLess(text.index('Admin password: stored'), text.index('Credentials helper:'))
        update = (ROOT / 'installer' / 'update.sh').read_text()
        self.assertLess(update.index('run_misp_db_updates'), update.index('wait_for_misp_live_marker'))
        self.assertLess(update.index('wait_for_misp_live_marker'), update.index('doctor.sh'))
        lib = (ROOT / 'installer' / 'lib.sh').read_text()
        self.assertIn('./Console/cake Admin runUpdates', lib)
        self.assertIn('MISP database update attempt', lib)
        self.assertIn('attempts="${2:-90}"', lib)
        self.assertIn('first-start initialization may still be running', lib)
        self.assertIn("SHOW TABLES LIKE", lib)
        self.assertIn('wait_for_misp_live_marker()', lib)
        self.assertIn('MISP is now live. Users can now log in.', lib)

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
        self.assertIn('--core-tag', update)
        self.assertIn('--modules-tag', update)
        self.assertIn('--guard-tag', update)
        self.assertIn('--core-tag', (ROOT / 'installer' / 'install.sh').read_text())
        self.assertIn('sync_misp_image_tags "$INSTALL_DIR" version-tags', generate)
        self.assertIn('MISP Docker component versions', versions)
        self.assertIn('Install dir:     not provided; local columns are omitted', versions)

    def test_prepare_host_retries_package_manager_operations(self):
        text = (ROOT / 'installer' / 'prepare-host-rocky.sh').read_text()
        self.assertIn('retry_cmd 3 15', text)
        self.assertIn('download.docker.com', text)
        self.assertIn('docker-ce', text)

    def test_prepare_host_docker_group_is_explicit_opt_in(self):
        text = (ROOT / 'installer' / 'prepare-host-rocky.sh').read_text()
        self.assertIn('ADD_CURRENT_USER_TO_DOCKER_GROUP="false"', text)
        self.assertIn('--add-current-user-to-docker-group', text)
        self.assertIn('Docker group membership is root-equivalent', text)
        self.assertIn('safer by default', text)
        self.assertIn('usermod -aG docker', text)

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
        self.assertIn('--machine-readable', text)
        self.assertIn('--ai-output', text)
        self.assertIn('MISP Web UI login check failed.', text)
        self.assertIn('invalid-credentials-or-not-ready', text)
        self.assertIn('print_machine(result)', text)
        self.assertIn("ssl.create_default_context()", text)
        self.assertIn("--insecure", text)
        self.assertIn("authenticated_session_marker", text)
        self.assertIn("'/users/logout'", text)
        self.assertIn("Login form redirected to a different origin", text)
        self.assertIn("failure_result", text)
        self.assertIn("tls-verification-failed", text)
        self.assertIn("cross-origin-redirect", text)
        self.assertNotIn("ctx = ssl.create_default_context() if strict_tls else", text)
        healthcheck = (ROOT / 'installer' / 'healthcheck.sh').read_text()
        self.assertIn("values = {}", healthcheck)
        self.assertIn("explicit insecure transport", healthcheck)
        self.assertIn("failed without recognized machine-readable output", healthcheck)

    def test_reset_installation_has_safety_guards(self):
        text = (ROOT / 'installer' / 'reset-installation.sh').read_text()
        self.assertIn('Dry-run only', text)
        self.assertIn('Are you sure you want to delete everything', text)
        self.assertIn('Type DELETE to continue', text)
        self.assertIn('down --volumes --remove-orphans', text)
        self.assertIn('Refusing unsafe --install-dir', text)
        self.assertIn('does not contain expected MISP lifecycle manager markers', text)
        self.assertIn('misp-docker-lifecycle-manager', text)
        self.assertIn('Docker Engine itself is not removed', text)

    def test_reset_refuses_unmarked_directory_even_with_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'not-a-misp-install'
            target.mkdir()
            result = subprocess.run(
                [str(ROOT / 'installer' / 'reset-installation.sh'), '--install-dir', str(target), '--yes', '--force'],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(target.exists())
            self.assertIn('expected MISP lifecycle manager markers', result.stderr)

    def test_base_url_is_not_embedded_in_python_source(self):
        install = (ROOT / 'installer' / 'install.sh').read_text()
        doctor = (ROOT / 'installer' / 'doctor.sh').read_text()
        lib = (ROOT / 'installer' / 'lib.sh').read_text()
        self.assertNotIn("urlparse('$BASE_URL')", install)
        self.assertNotIn("urlparse('$BASE_URL')", doctor)
        self.assertIn('url_hostname "$BASE_URL"', install)
        self.assertIn('url_hostname "$BASE_URL"', doctor)
        self.assertIn('python3 - "$base_url" "$fallback" <<\'PY\'', lib)

    def test_malicious_base_url_is_rejected(self):
        payload = "https://example.com').hostname);print('INJECTED');#"
        result = subprocess.run(
            ['bash', '-lc', f'source installer/lib.sh; validate_public_base_url {payload!r} reverse-proxy'],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('INJECTED', result.stdout)

    def test_doctor_does_not_use_predictable_tmp_heartbeat_file(self):
        text = (ROOT / 'installer' / 'doctor.sh').read_text()
        self.assertNotIn('/tmp/misp-heartbeat.json', text)
        self.assertIn('heartbeat_body=', text)

    def test_backup_and_schema_checks_avoid_password_argv(self):
        backup = (ROOT / 'installer' / 'backup.sh').read_text()
        lib = (ROOT / 'installer' / 'lib.sh').read_text()
        for text in [backup, lib]:
            self.assertIn('--defaults-extra-file="$cfg"', text)
            self.assertNotIn('-p"$MYSQL_PASSWORD"', text)
            self.assertNotIn('-p$MYSQL_PASSWORD', text)

    def test_backup_uses_restrictive_permissions(self):
        text = (ROOT / 'installer' / 'backup.sh').read_text()
        self.assertIn('umask 077', text)
        self.assertIn('chmod 700 "$out"', text)
        self.assertIn('misp-config.tar.gz', text)
        self.assertIn('chmod 600 "$out/misp.sql" "$out/misp-host-data.tar.gz" "$out/misp-config.tar.gz"', text)
        self.assertIn('sha256sum misp.sql misp-host-data.tar.gz misp-config.tar.gz > SHA256SUMS', text)

    def test_restore_has_destructive_safety_and_imports_backup(self):
        text = (ROOT / 'installer' / 'restore.sh').read_text()
        self.assertIn('--backup-dir', text)
        self.assertIn('Dry-run only', text)
        self.assertIn('Type RESTORE to continue', text)
        self.assertIn('validate-backup.py', text)
        self.assertIn('tar --no-same-owner --no-same-permissions -C "$INSTALL_DIR" -xzf "$BACKUP_DIR/misp-config.tar.gz"', text)
        self.assertIn('sudo tar -C "$INSTALL_DIR" -xzf "$BACKUP_DIR/misp-host-data.tar.gz"', text)
        self.assertNotIn('sudo tar --no-same-owner', text)
        self.assertIn('write_state "$INSTALL_DIR/.installer-state.json"', text)
        self.assertIn('misp-config.tar.gz', text)
        self.assertIn('misp-host-data.tar.gz', text)
        self.assertIn('misp.sql', text)
        self.assertIn('down --volumes --remove-orphans', text)
        self.assertIn('mariadb --defaults-extra-file="$cfg" "$MYSQL_DATABASE"', text)
        self.assertIn('wait_for_misp_live_marker', text)

    def test_update_allows_external_backup_root_for_restore_based_rollback(self):
        text = (ROOT / 'installer' / 'update.sh').read_text()
        self.assertIn('--backup-root', text)
        self.assertIn('backup_args=(--install-dir "$INSTALL_DIR")', text)
        self.assertIn('backup_args+=(--backup-root "$BACKUP_ROOT")', text)
        self.assertIn('"$SCRIPT_DIR/backup.sh" "${backup_args[@]}"', text)
        self.assertIn('write_state "$state_file"', text)
        self.assertIn('new_commit="$(git -C "$INSTALL_DIR" rev-parse HEAD)"', text)

    def test_temp_checkout_cleanup_trap_expands_tmpdir(self):
        text = (ROOT / 'installer' / 'get-current-misp-versions.sh').read_text()
        self.assertIn("trap 'rm -rf \"$TMPDIR\"' EXIT", text)
        self.assertNotIn("trap 'rm -rf \\\"$TMPDIR\\\"' EXIT", text)

    def test_gitignore_covers_sensitive_backup_artifacts(self):
        text = (ROOT / '.gitignore').read_text()
        for pattern in ['*.sql', '*.sql.gz', 'SHA256SUMS', 'misp-backup-*/']:
            self.assertIn(pattern, text)

    def test_upstream_monitoring_artifacts_exist(self):
        self.assertTrue((ROOT / 'scripts' / 'check-upstream-misp-docker.py').exists())
        self.assertTrue((ROOT / '.github' / 'workflows' / 'upstream-misp-docker-watch.yml').exists())
        self.assertTrue((ROOT / '.upstream' / 'misp-docker.lock.json').exists())
        monitor = (ROOT / 'scripts' / 'check-upstream-misp-docker.py').read_text()
        self.assertIn('template.env', monitor)
        self.assertIn('docker-compose.yml', monitor)
        self.assertIn('core/files/entrypoint.sh', monitor)
        self.assertIn('core/files/entrypoint_nginx.sh', monitor)
        self.assertIn('core/files/utilities.sh', monitor)
        self.assertIn('core/files/etc/misp-docker', monitor)
        self.assertIn('core/files/etc/supervisor', monitor)
        self.assertIn('core/files/etc/nginx', monitor)
        self.assertIn('guard/files', monitor)
        self.assertIn('WATCHED_TREE_CLASSES', monitor)
        self.assertIn('README_SECTIONS', monitor)
        self.assertIn('service_block_hashes', monitor)
        self.assertIn('template_env_keys', monitor)
        self.assertIn('Upstream commit movement alone is informational and intentionally not drift', monitor)
        self.assertIn('CORE_TAG', monitor)
        self.assertIn('MODULES_TAG', monitor)
        self.assertIn('GUARD_TAG', monitor)

    def test_upstream_monitoring_workflow_actions_are_sha_pinned(self):
        text = (ROOT / '.github' / 'workflows' / 'upstream-misp-docker-watch.yml').read_text()
        self.assertIn('uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0', text)
        self.assertIn('uses: peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1', text)
        self.assertNotIn('uses: actions/checkout@v', text)
        self.assertNotIn('uses: peter-evans/create-pull-request@v', text)

    def test_upstream_watch_handles_blocked_pr_creation_and_prompts_compatibility_validation(self):
        workflow = (ROOT / '.github' / 'workflows' / 'upstream-misp-docker-watch.yml').read_text()
        self.assertIn('continue-on-error: true', workflow)
        self.assertIn('timeout-minutes: 10', workflow)
        self.assertIn('group: upstream-misp-docker-review', workflow)
        self.assertIn('python3 -m unittest tests.test_upstream_watcher', workflow)
        self.assertIn('Report manual PR fallback', workflow)
        self.assertIn("steps.create-pr.outputs.pull-request-number == ''", workflow)
        self.assertIn('Upstream drift detected but no pull request number was returned', workflow)
        self.assertIn('exit 1', workflow)
        self.assertIn('pull/new/automation/upstream-misp-docker-review', workflow)
        script = (ROOT / 'scripts' / 'check-upstream-misp-docker.py').read_text()
        maintainer = (ROOT / 'docs' / 'maintainer-workflow.md').read_text()
        self.assertIn('Run compatibility validation for the affected manager release/ref', script)
        self.assertIn('validated compatible', script)
        self.assertIn('A pushed review branch without an open PR still means upstream drift exists', maintainer)

    def test_release_docs_require_exact_tag_compatibility_validation(self):
        release = (ROOT / 'docs' / 'release' / 'release-process.md').read_text()
        versioning = (ROOT / 'docs' / 'versioning.md').read_text()
        qa = (ROOT / 'QA.md').read_text()
        readiness = (ROOT / 'docs' / 'production-readiness.md').read_text()
        support = (ROOT / 'docs' / 'support-matrix.md').read_text()
        deployment = (ROOT / 'docs' / 'production-deployment.md').read_text()
        security = (ROOT / 'docs' / 'security.md').read_text()
        backup_restore = (ROOT / 'docs' / 'backup-restore-and-rollback.md').read_text()
        compat_report = (ROOT / 'docs' / 'validation' / 'compatibility-v0.3.3-misp-core-v2.5.43.md').read_text()

        self.assertIn('Run the compatibility validation harness against the exact tag', release)
        self.assertIn('Mark the release/component pair **validated compatible** only after the exact tag passes', release)
        self.assertIn('validate the immutable Git tag, not just `main` or a release branch', versioning)
        self.assertIn('compatibility claims are based on the immutable release tag', qa)
        self.assertIn('release/component pairs are marked **validated compatible** only after the documented compatibility scenarios pass', qa)
        self.assertIn('Current stable-release status', readiness)
        self.assertIn('Backup, restore, and rollback | ✅ `v1.1.0` exact-tag evidence', readiness)
        self.assertIn('Browser-facing login | ✅ `v1.1.0` exact-tag browser evidence', readiness)
        self.assertIn('No-lock-in Compose operation | ✅ `v1.1.0` exact-tag evidence', readiness)
        self.assertIn('`v1.1.0` release-validation state', readiness)
        self.assertIn('Its immutable tag passed the full release suite', readiness)
        self.assertIn('Native ingestion by running Zabbix, Checkmk, Nagios/Icinga, and Prometheus systems remains unvalidated', readiness)
        self.assertIn('single-server Docker', support)
        self.assertIn('Explicit non-goals', support)
        self.assertIn('Post-install verification', deployment)
        self.assertIn('No-lock-in operation', deployment)
        self.assertIn('documented `v1.1.0` scope', deployment)
        self.assertIn('latest published and latest validated release', deployment)
        self.assertIn('Secret handling', security)
        self.assertIn('Docker privilege model', security)
        self.assertIn('Restore procedure', backup_restore)
        self.assertIn('Restore-based rollback after failed update', backup_restore)
        self.assertIn('misp-config.tar.gz', backup_restore)
        self.assertIn('restore.sh', backup_restore)
        self.assertNotIn('current `main` at PR #22 validation time', (ROOT / 'docs' / 'compatibility.md').read_text())
        self.assertNotIn('current `main` at PR #22 validation time', (ROOT / 'docs' / 'validation' / 'matrix.md').read_text())
        self.assertNotIn('1.0.0-rc.2', (ROOT / '.github' / 'ISSUE_TEMPLATE' / 'bug_report.yml').read_text())
        self.assertNotIn('1.0.0-rc.2', (ROOT / 'docs' / 'sos-report.md').read_text())
        self.assertNotIn('being prepared as `v0.3.3`', compat_report)
        self.assertNotIn('Publish a patch release from the validated `main` line', compat_report)

        current_docs = {
            'README.md': (ROOT / 'README.md').read_text(),
            'docs/README.md': (ROOT / 'docs' / 'README.md').read_text(),
            'docs/production-readiness.md': readiness,
            'docs/production-deployment.md': deployment,
            'docs/security.md': security,
            'docs/support-matrix.md': support,
        }
        stale_current_state_phrases = [
            'first release-candidate test',
            'Current release-candidate status',
            'What must be true before `v1.0.0`',
            'Required validation before `v1.0.0`',
            'Before removing the public production warning',
            'intended first production-ready deployment shape',
            'release-candidate validation set',
            'support scope intended for the first production-ready major release',
        ]
        for path, content in current_docs.items():
            for phrase in stale_current_state_phrases:
                self.assertNotIn(phrase, content, f'{path} still presents the stable release as future work')

    def test_documentation_red_line_entry_points_exist(self):
        docs_readme = (ROOT / 'docs' / 'README.md').read_text()
        getting_started = (ROOT / 'docs' / 'getting-started.md').read_text()
        operator = (ROOT / 'docs' / 'operator-guide.md').read_text()
        readme = (ROOT / 'README.md').read_text()

        for path in [
            'docs/README.md',
            'docs/getting-started.md',
            'docs/operator-guide.md',
            'docs/support-matrix.md',
            'docs/production-deployment.md',
            'docs/backup-restore-and-rollback.md',
            'docs/compatibility.md',
            'docs/troubleshooting.md',
        ]:
            self.assertIn(path, readme)

        self.assertIn('Recommended reading path', docs_readme)
        self.assertIn('Common tasks', docs_readme)
        self.assertIn('getting-started.md', docs_readme)
        self.assertIn('operator-guide.md', docs_readme)
        self.assertIn('support-matrix.md', docs_readme)
        self.assertIn('compatibility.md', docs_readme)

        self.assertIn('first successful path', getting_started)
        version = (ROOT / 'VERSION').read_text().strip()
        self.assertIn(f'git checkout v{version}', getting_started)
        self.assertIn('doctor.sh', getting_started)
        self.assertIn('login-check.sh', getting_started)
        self.assertIn('backup.sh', getting_started)

        self.assertIn('red line through the repository', operator)
        self.assertIn('Understand the model', operator)
        self.assertIn('Decide whether this fits your use case', operator)
        self.assertIn('Update safely', operator)
        self.assertIn('Restore and recover', operator)
        self.assertIn('manager release/ref × official MISP Docker component set = status', operator)

    def test_documentation_cross_links_existing_major_pages(self):
        major_docs = [
            'architecture.md',
            'backup-restore-and-rollback.md',
            'compatibility.md',
            'monitoring.md',
            'production-deployment.md',
            'production-readiness.md',
            'security.md',
            'shell-scripts.md',
            'support-matrix.md',
            'troubleshooting.md',
            'upgrade-path.md',
            'versioning.md',
        ]
        for rel in major_docs:
            text = (ROOT / 'docs' / rel).read_text()
            self.assertIn('README.md', text, rel)
            self.assertRegex(text, r'## What to read next\n', rel)

        matrix = (ROOT / 'docs' / 'validation' / 'matrix.md').read_text()
        self.assertIn('## What to read next', matrix)
        self.assertIn('../README.md', matrix)
        release = (ROOT / 'docs' / 'release' / 'release-process.md').read_text()
        self.assertIn('## What to read next', release)
        self.assertIn('../README.md', release)

    def test_monitoring_contract_is_documented_and_healthcheck_command_matches_it(self):
        monitoring = (ROOT / 'docs' / 'monitoring.md').read_text()
        readme = (ROOT / 'README.md').read_text()
        docs_index = (ROOT / 'docs' / 'README.md').read_text()
        operator = (ROOT / 'docs' / 'operator-guide.md').read_text()
        shell_docs = (ROOT / 'docs' / 'shell-scripts.md').read_text()
        readiness = (ROOT / 'docs' / 'production-readiness.md').read_text()
        changelog = (ROOT / 'CHANGELOG.md').read_text()
        healthcheck = (ROOT / 'installer' / 'healthcheck.sh').read_text()

        self.assertIn('installer/healthcheck.sh', monitoring)
        self.assertIn('--format text|json|nagios|checkmk|prometheus', monitoring)
        for code, status in [('0', 'OK'), ('1', 'WARNING'), ('2', 'CRITICAL'), ('3', 'UNKNOWN')]:
            self.assertIn(f'`{code}` | {status}', monitoring)
        self.assertIn('misp-docker-lifecycle-manager-health-v1', monitoring)
        self.assertIn('Zabbix', monitoring)
        self.assertIn('Checkmk', monitoring)
        self.assertIn('Nagios/Icinga', monitoring)
        self.assertIn('Prometheus text format', monitoring)
        self.assertIn('Do not expose hostnames, email addresses, install paths, backup names, URLs, or organisation names as metric labels.', monitoring)
        self.assertIn('docs/monitoring.md', readme)
        self.assertIn('monitoring.md', docs_index)
        self.assertIn('[Monitoring](monitoring.md)', operator)
        self.assertIn('[Monitoring](monitoring.md)', shell_docs)
        self.assertIn('Monitoring contract', readiness)
        self.assertIn('monitoring healthcheck contract', changelog)
        self.assertIn('STATUS_RANK', healthcheck)
        self.assertIn('misp-docker-lifecycle-manager-health-v1', healthcheck)
        self.assertIn('backup-freshness', healthcheck)
        self.assertIn('version-drift', healthcheck)
        self.assertIn('does not currently have dedicated Zabbix, Checkmk, Nagios/Icinga, or Prometheus server infrastructure', monitoring)
        self.assertIn('Not yet tested by this project', monitoring)
        self.assertIn('Community testing wanted', monitoring)
        self.assertIn('scripts/validate-healthcheck-output.py', monitoring)
        self.assertIn('monitoring-healthcheck-pr61.md', monitoring)
        self.assertIn('monitoring issue #62', readme)
        self.assertIn('Native ingestion by Zabbix, Checkmk, Nagios/Icinga, and Prometheus remains community-testing work', readme)
        self.assertIn('Monitoring integration contributions', (ROOT / 'CONTRIBUTING.md').read_text())
        validation_report = (ROOT / 'docs' / 'validation' / 'monitoring-healthcheck-pr61.md').read_text()
        self.assertIn('Stop only the `misp-core` service', validation_report)
        self.assertIn('did **not** use running Zabbix, Checkmk, Nagios/Icinga, or Prometheus servers', validation_report)
        self.assertIn('post-`v1.0.0` development commit', validation_report)
        self.assertIn('`promtool` was not installed', validation_report)
        self.assertIn('../monitoring.md#integration-validation-status', validation_report)
        self.assertIn('[`CONTRIBUTING.md`](../CONTRIBUTING.md)', docs_index)
        self.assertIn('community testing issue #62', docs_index)

    def test_healthcheck_output_validator_accepts_unknown_contract(self):
        validator = ROOT / 'scripts' / 'validate-healthcheck-output.py'
        self.assertTrue(validator.exists())
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    'python3', str(validator),
                    '--healthcheck', str(ROOT / 'installer' / 'healthcheck.sh'),
                    '--install-dir', tmp,
                    '--expect-status', 'unknown',
                    '--timeout', '1',
                ],
                text=True,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('healthcheck output validation passed', result.stdout)
            self.assertIn('formats=json,nagios,checkmk,prometheus', result.stdout)
            self.assertNotIn(str(Path(tmp).resolve()), result.stdout + result.stderr)

        invalid = subprocess.run(
            [
                'python3', str(validator),
                '--healthcheck', str(ROOT / 'installer' / 'healthcheck.sh'),
                '--install-dir', '/tmp/not-a-misp-install',
                '--expect-status', 'unknown',
                '--insecure',
            ],
            text=True,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(invalid.returncode, 1)
        self.assertIn('--insecure requires --include-login', invalid.stderr)

    def test_healthcheck_outputs_stable_machine_formats_without_deployment(self):
        script = ROOT / 'installer' / 'healthcheck.sh'
        with tempfile.TemporaryDirectory() as tmp:
            json_proc = subprocess.run(
                [str(script), '--install-dir', tmp, '--format', 'json', '--timeout', '1'],
                text=True,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(json_proc.returncode, 3)
            import json
            data = json.loads(json_proc.stdout)
            self.assertEqual(data['schema'], 'misp-docker-lifecycle-manager-health-v1')
            self.assertEqual(data['status'], 'unknown')
            self.assertEqual(data['exit_code'], 3)
            self.assertEqual(data['checks'][0]['id'], 'preflight')
            serialized = json_proc.stdout + json_proc.stderr
            forbidden_markers = [
                'ADMIN_PASSWORD',
                'MYSQL_PASSWORD',
                '.installer-state.json',
                'misp-backup-',
                'BEGIN ' + 'OPENSSH ' + 'PRIVATE KEY',
            ]
            for forbidden in forbidden_markers:
                self.assertNotIn(forbidden, serialized)

            nagios = subprocess.run(
                [str(script), '--install-dir', tmp, '--format', 'nagios', '--timeout', '1'],
                text=True,
                cwd=ROOT,
                stdout=subprocess.PIPE,
            )
            self.assertEqual(nagios.returncode, 3)
            self.assertTrue(nagios.stdout.startswith('UNKNOWN - '))
            self.assertIn('| services_running=', nagios.stdout)

            checkmk = subprocess.run(
                [str(script), '--install-dir', tmp, '--format', 'checkmk', '--timeout', '1'],
                text=True,
                cwd=ROOT,
                stdout=subprocess.PIPE,
            )
            self.assertEqual(checkmk.returncode, 3)
            self.assertIn('"misp_lifecycle_health"', checkmk.stdout)

            prometheus = subprocess.run(
                [str(script), '--install-dir', tmp, '--format', 'prometheus', '--timeout', '1'],
                text=True,
                cwd=ROOT,
                stdout=subprocess.PIPE,
            )
            self.assertEqual(prometheus.returncode, 3)
            self.assertIn('misp_lifecycle_health_status 0', prometheus.stdout)

    def test_shell_scripts_reference_matches_current_command_surface(self):
        shell_docs = (ROOT / 'docs' / 'shell-scripts.md').read_text()
        agents = (ROOT / 'AGENTS.md').read_text()

        main_scripts = [
            'prepare-host-rocky.sh',
            'install.sh',
            'update.sh',
            'backup.sh',
            'restore.sh',
            'doctor.sh',
            'status.sh',
            'healthcheck.sh',
            'admin-credentials.sh',
            'login-check.sh',
            'get-current-misp-versions.sh',
            'reset-installation.sh',
        ]
        for script in main_scripts:
            self.assertIn(f'`{script}`', shell_docs)

        for helper in [
            'lib.sh',
            'fetch-upstream.sh',
            'generate-env.sh',
            'render-compose.sh',
            'bootstrap-tls.sh',
            'validate.sh',
            'up.sh',
            'down.sh',
            'pull.sh',
            'logs.sh',
        ]:
            self.assertIn(f'`{helper}`', shell_docs)

        for artifact in ['misp.sql', 'misp-host-data.tar.gz', 'misp-config.tar.gz', 'SHA256SUMS']:
            self.assertIn(artifact, shell_docs)

        self.assertIn('Destructive commands', shell_docs)
        self.assertIn('DELETE', shell_docs)
        self.assertIn('RESTORE', shell_docs)
        self.assertIn('--machine-readable', shell_docs)
        self.assertIn('--show-password', shell_docs)
        self.assertIn('production-oriented lifecycle manager', agents)
        self.assertNotIn('production-oriented installer/overlay', agents)

    def test_community_health_files_exist_and_are_public_safe(self):
        files = [
            'CODE_OF_CONDUCT.md',
            'CONTRIBUTING.md',
            '.github/PULL_REQUEST_TEMPLATE.md',
            '.github/ISSUE_TEMPLATE/bug_report.yml',
            '.github/ISSUE_TEMPLATE/feature_request.yml',
            '.github/ISSUE_TEMPLATE/documentation.yml',
            '.github/ISSUE_TEMPLATE/config.yml',
        ]
        for rel in files:
            path = ROOT / rel
            self.assertTrue(path.exists(), rel)
            text = path.read_text()
            self.assertTrue(
                'misp-docker-lifecycle-manager' in text.lower()
                or 'misp docker lifecycle manager' in text.lower(),
                rel,
            )
            self.assertNotIn('loc' + '.internal', text)
            self.assertNotIn('192' + '.168.', text)
            self.assertNotIn('/home/' + 'hermes', text)

        contributing = (ROOT / 'CONTRIBUTING.md').read_text()
        self.assertIn('Public-safety rule', contributing)
        self.assertIn('python3 -m unittest discover -s tests', contributing)
        self.assertIn('validated compatible', contributing)
        self.assertIn('CODE_OF_CONDUCT.md', contributing)

        pr_template = (ROOT / '.github' / 'PULL_REQUEST_TEMPLATE.md').read_text()
        self.assertIn('Public-safety checklist', pr_template)
        self.assertIn('Runtime impact', pr_template)
        self.assertIn('Compatibility impact', pr_template)

        bug_template = (ROOT / '.github' / 'ISSUE_TEMPLATE' / 'bug_report.yml').read_text()
        self.assertIn('If this may be a security vulnerability', bug_template)
        self.assertIn('Public-safety confirmation', bug_template)
        self.assertIn('Anonymous SOS report', bug_template)
        self.assertIn('v1.1.0 or commit SHA', bug_template)
        self.assertIn('docs/sos-report.md', bug_template)

        config = (ROOT / '.github' / 'ISSUE_TEMPLATE' / 'config.yml').read_text()
        self.assertIn('blank_issues_enabled: false', config)
        self.assertIn('/security/policy', config)

    def test_security_policy_exists_and_guides_private_reporting(self):
        security = (ROOT / 'SECURITY.md').read_text()
        readme = (ROOT / 'README.md').read_text()
        contributing = (ROOT / 'CONTRIBUTING.md').read_text()
        docs_security = (ROOT / 'docs' / 'security.md').read_text()

        self.assertIn('Supported versions', security)
        self.assertIn('`v1.1.0` | Current stable release line and latest validated-compatible artifact', security)
        self.assertIn('`v1.0.0` | Previous stable release with retained historical compatibility evidence', security)
        self.assertIn('Release candidates and pre-`v1.0.0` tags | Historical and unsupported for routine fixes', security)
        self.assertNotIn('This project is still pre-`v1.0.0`', security)
        self.assertIn('best effort, with no service-level agreement', security)
        self.assertIn('/security/advisories/new', security)
        self.assertIn('Do **not** open a public issue for security vulnerabilities', security)
        self.assertIn('command injection', security)
        self.assertIn('secret', security.lower())
        self.assertIn('reset, restore, update, or rollback behavior', security)
        self.assertIn('Coordinated disclosure', security)
        self.assertIn('[REDACTED]', security)
        self.assertIn('SECURITY.md', readme)
        self.assertIn('SECURITY.md', contributing)
        self.assertIn('../SECURITY.md', docs_security)

    def test_dependency_and_code_scanning_automation_is_configured(self):
        dependabot = (ROOT / '.github' / 'dependabot.yml').read_text()
        codeql = (ROOT / '.github' / 'workflows' / 'codeql.yml').read_text()
        shellcheck = (ROOT / '.github' / 'workflows' / 'shellcheck.yml').read_text()

        self.assertIn('package-ecosystem: "github-actions"', dependabot)
        self.assertIn('interval: "weekly"', dependabot)
        self.assertIn('open-pull-requests-limit: 3', dependabot)
        self.assertIn('area: github-actions', dependabot)

        self.assertIn('name: CodeQL', codeql)
        self.assertIn('languages: python', codeql)
        self.assertIn('queries: security-extended', codeql)
        self.assertIn('security-events: write', codeql)
        self.assertIn('actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0', codeql)
        self.assertRegex(codeql, r'github/codeql-action/init@[0-9a-f]{40}')
        self.assertRegex(codeql, r'github/codeql-action/analyze@[0-9a-f]{40}')
        self.assertIn('github/codeql-action@v4', codeql)
        self.assertNotIn('@v3', codeql)

        self.assertIn('name: ShellCheck', shellcheck)
        self.assertIn('scandir: ./installer', shellcheck)
        self.assertIn('severity: error', shellcheck)
        self.assertRegex(shellcheck, r'ludeeus/action-shellcheck@[0-9a-f]{40}')
        self.assertNotIn('@2.0.0', shellcheck)

    def test_always_running_repository_gate_is_read_only_and_complete(self):
        workflow = (ROOT / '.github' / 'workflows' / 'repository-gates.yml').read_text()
        qa = (ROOT / 'QA.md').read_text()

        self.assertIn('name: Repository gates', workflow)
        self.assertRegex(workflow, r'(?m)^  pull_request:\s*$')
        self.assertNotIn('paths:', workflow)
        self.assertIn('permissions:\n  contents: read', workflow)
        self.assertNotIn('write', workflow)
        self.assertIn('timeout-minutes: 15', workflow)
        self.assertIn('cancel-in-progress: true', workflow)
        self.assertIn('uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0', workflow)
        self.assertIn('fetch-depth: 0', workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertIn('uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1', workflow)
        self.assertIn('python3 -m pip install --require-hashes -r .github/requirements/repository-gates.txt', workflow)
        self.assertIn('python3 -m unittest discover -s tests', workflow)
        self.assertIn('bash -n "$script"', workflow)
        self.assertIn('python3 -m py_compile scripts/*.py tests/*.py', workflow)
        self.assertIn('["git", "ls-files", "-z", "--", "*.yml", "*.yaml"]', workflow)
        self.assertIn('yaml.safe_load(path.read_text())', workflow)
        self.assertIn('CURRENT_SHA: ${{ github.sha }}', workflow)
        self.assertIn('empty_tree=$(git hash-object -t tree /dev/null)', workflow)
        self.assertIn('git diff --check "$empty_tree" "$CURRENT_SHA"', workflow)
        self.assertNotIn('github.event.before', workflow)
        self.assertNotIn('github.event.pull_request.base.sha', workflow)
        self.assertIn('complete current repository tree', qa)
        self.assertIn('including documentation-only changes', qa)
        requirements = (ROOT / '.github' / 'requirements' / 'repository-gates.txt').read_text()
        self.assertIn('PyYAML==6.0.3', requirements)
        self.assertRegex(requirements, r'--hash=sha256:[0-9a-f]{64}')

    def test_maintainer_workflow_documents_repo_operations(self):
        docs_index = (ROOT / 'docs' / 'README.md').read_text()
        maintainer = (ROOT / 'docs' / 'maintainer-workflow.md').read_text()
        changelog = (ROOT / 'CHANGELOG.md').read_text()

        self.assertIn('maintainer-workflow.md', docs_index)
        self.assertIn('GitHub is configured to delete merged branches automatically', maintainer)
        self.assertIn('The GitHub Wiki is not used for canonical docs', maintainer)
        self.assertIn('type: security', maintainer)
        self.assertIn('area: github-actions', maintainer)
        self.assertIn('needs-sos-report', maintainer)
        self.assertIn('SOS report triage', maintainer)
        self.assertIn('do not quote them back in public', maintainer)
        self.assertIn('move the conversation to [`SECURITY.md`](../SECURITY.md)', maintainer)
        self.assertIn('Remove `needs-sos-report` once', maintainer)
        self.assertIn('Dependabot for GitHub Actions updates', maintainer)
        self.assertIn('GitHub Actions annotations report deprecations', maintainer)
        self.assertIn('Official MISP Docker upstream drift PRs', maintainer)
        self.assertIn('| A | An official component release changed, or component defaults changed', maintainer)
        self.assertIn('| B | `docker-compose.yml` service blocks', maintainer)
        self.assertIn('| C | `template.env` key inventory/defaults or selected README operator guidance', maintainer)
        self.assertIn('A+B+C', maintainer)
        self.assertIn('A new upstream commit by itself is comparison context and does not open a PR', maintainer)
        self.assertIn('Never merge the upstream lockfile PR as "validated compatible" evidence by itself', maintainer)
        self.assertIn('Private vulnerability reporting is enabled', maintainer)
        self.assertIn('Branch protection should be added once', maintainer)
        self.assertIn('manager release/ref × official MISP Docker component set = validation status', maintainer)
        self.assertIn('maintainer workflow guide', changelog)

    def test_sos_report_docs_define_public_safe_bug_reporting(self):
        sos = (ROOT / 'docs' / 'sos-report.md').read_text()
        readme = (ROOT / 'README.md').read_text()
        docs_index = (ROOT / 'docs' / 'README.md').read_text()
        contributing = (ROOT / 'CONTRIBUTING.md').read_text()
        security = (ROOT / 'SECURITY.md').read_text()
        bug_template = (ROOT / '.github' / 'ISSUE_TEMPLATE' / 'bug_report.yml').read_text()
        changelog = (ROOT / 'CHANGELOG.md').read_text()

        self.assertIn('Anonymous SOS reports', sos)
        self.assertIn('manual-sos-v1', sos)
        self.assertIn('Prefer over-redaction', sos)
        self.assertIn('Do **not** use a public SOS report for suspected security vulnerabilities', sos)
        self.assertIn('Never include:', sos)
        self.assertIn('`.env` contents', sos)
        self.assertIn('`.installer-state.json` contents', sos)
        self.assertIn('raw logs', sos)
        self.assertIn('database dumps', sos)
        self.assertIn('backup archives', sos)
        self.assertIn('MISP event data', sos)
        self.assertIn('[REDACTED_IP]', sos)
        self.assertIn('[REDACTED_HOST]', sos)
        self.assertIn('[REDACTED_SECRET]', sos)
        self.assertIn('Maintainer triage checklist', sos)
        self.assertIn('needs-sos-report', sos)
        self.assertIn('maintainer-workflow.md#sos-report-triage', sos)
        self.assertIn('docs/sos-report.md', readme)
        self.assertIn('sos-report.md', docs_index)
        self.assertIn('docs/sos-report.md', contributing)
        self.assertIn('docs/sos-report.md', security)
        self.assertIn('Anonymous SOS report', bug_template)
        self.assertIn('I reviewed the report before posting', bug_template)
        self.assertIn('sos report documentation', changelog.lower())
        self.assertIn('one monotonic end-to-end deadline', sos)
        self.assertIn('--timeout SECONDS', sos)

    def test_sos_report_command_generates_sanitized_public_report(self):
        with tempfile.TemporaryDirectory() as td:
            install_dir = Path(td) / 'private-install'
            install_dir.mkdir()
            (install_dir / '.env').write_text(
                '\n'.join([
                    'CORE_TAG=v2.5.43',
                    'MODULES_TAG=v3.0.8',
                    'GUARD_TAG=v1.2',
                    'CORE_RUNNING_TAG=v2.5.43',
                    'MODULES_RUNNING_TAG=v3.0.8',
                    'GUARD_RUNNING_TAG=v1.2',
                    'MYSQL_PASSWORD_VALUE=do-not-print',
                ]) + '\n'
            )
            (install_dir / '.installer-state.json').write_text('{"base_url":"https://private.example.net"}\n')
            output = Path(td) / 'sos.md'
            result = subprocess.check_output([
                str(ROOT / 'installer' / 'sos-report.sh'),
                '--no-docker',
                '--workflow', 'fresh-install',
                '--install-dir', str(install_dir),
                '--output', str(output),
                '--explain-redaction',
            ], text=True, cwd=ROOT)
            self.assertIn('SOS report written', result)
            report = output.read_text()
            self.assertIn('# MISP Docker Lifecycle Manager SOS Report', report)
            self.assertIn('Report format: generated-sos-v2', report)
            self.assertIn('Affected workflow: fresh-install', report)
            self.assertIn('Default install directory used: no', report)
            self.assertIn('CORE_TAG: v2.5.43', report)
            self.assertIn('Docker checks enabled: no', report)
            self.assertIn('Structured health check enabled: no', report)
            self.assertIn('Overall health: not-checked', report)
            self.assertIn('## Deliberately not collected', report)
            self.assertIn('Raw helper, Docker, Compose', report)
            self.assertIn('Backup presence, names, paths, counts', report)
            self.assertIn('Review before sharing publicly', report)
            self.assertIn('does not depend on regex redaction', report)
            self.assertNotIn(str(install_dir), report)
            self.assertNotIn('do-not-print', report)
            self.assertNotIn('private.example.net', report)
            self.assertEqual(oct(output.stat().st_mode & 0o777), '0o600')

    def test_sos_report_command_supports_no_health_mode_with_backup_shape(self):
        with tempfile.TemporaryDirectory() as td:
            install_dir = Path(td) / 'private-install'
            backups = install_dir / 'backups' / 'private-backup-name'
            backups.mkdir(parents=True)
            (install_dir / '.env').write_text('CORE_TAG=v2.5.43\n')
            (install_dir / 'docker-compose.yml').write_text('services: {}\n')
            output = Path(td) / 'sos-no-health.md'
            subprocess.check_call([
                str(ROOT / 'installer' / 'sos-report.sh'),
                '--workflow', 'backup',
                '--install-dir', str(install_dir),
                '--output', str(output),
                '--no-health-commands',
            ], cwd=ROOT)
            report = output.read_text()
            self.assertIn('Docker checks enabled: yes', report)
            self.assertIn('Structured health check enabled: no', report)
            self.assertIn('Overall health: not-checked', report)
            self.assertIn('Backup presence, names, paths, counts', report)
            self.assertNotIn('Backup set count:', report)
            self.assertNotIn('Latest backup detected:', report)
            self.assertNotIn(str(install_dir), report)
            self.assertNotIn('private-backup-name', report)

    def test_sos_redaction_helper_redacts_sensitive_samples(self):
        sample = '\n'.join([
            'url=https://secret.example.net/path',
            'ip=203.0.113.5',
            'email=admin@example.net',
            'token=abcdef0123456789abcdef0123456789',
            'path=/home/example/private',
        ])
        redacted = subprocess.check_output(
            ['python3', str(ROOT / 'scripts' / 'redact-sos-report.py'), '/tmp/private-demo'],
            input=sample,
            text=True,
            cwd=ROOT,
        )
        self.assertIn('https://[REDACTED_HOST]', redacted)
        self.assertIn('[REDACTED_IP]', redacted)
        self.assertIn('[REDACTED_EMAIL]', redacted)
        self.assertIn('[REDACTED_SECRET]', redacted)
        self.assertIn('[REDACTED_PATH]', redacted)
        self.assertNotIn('secret.example.net', redacted)
        self.assertNotIn('203.0.113.5', redacted)
        self.assertNotIn('admin@example.net', redacted)
        self.assertNotIn('/home/example', redacted)

    def test_v1_1_release_is_validated_and_v1_0_evidence_is_preserved(self):
        version = (ROOT / 'VERSION').read_text().strip()
        readme = (ROOT / 'README.md').read_text()
        compatibility = (ROOT / 'docs' / 'compatibility.md').read_text()
        matrix = (ROOT / 'docs' / 'validation' / 'matrix.md').read_text()
        readiness = (ROOT / 'docs' / 'production-readiness.md').read_text()
        final_report = (ROOT / 'docs' / 'validation' / 'compatibility-v1.0.0-misp-core-v2.5.43.md').read_text()
        upstream_report = (ROOT / 'docs' / 'validation' / 'compatibility-v1.0.0-misp-core-v2.5.44.md').read_text()
        v1_1_report = (ROOT / 'docs' / 'validation' / 'compatibility-v1.1.0-misp-core-v2.5.44.md').read_text()
        channels = json.loads((ROOT / '.release-channels.json').read_text())
        changelog = (ROOT / 'CHANGELOG.md').read_text()
        security = (ROOT / 'SECURITY.md').read_text()

        self.assertEqual(version, '1.1.0')
        self.assertIn('Current `VERSION` value on `main`: `1.1.0`', readme)
        self.assertIn('`v1.1.0` release tag', readme)
        self.assertNotIn('🟡 Pending exact-tag validation', readme)
        self.assertIn('Release channels', readme)
        self.assertIn('Latest published', readme)
        self.assertIn('Latest validated', readme)
        self.assertNotIn('**NOT PRODUCTION READY**', readme)
        self.assertIn('git checkout v1.1.0', readme)
        self.assertIn('`v1.0.0` release tag', readme)
        self.assertIn('✅ Validated compatible', readme)
        self.assertIn('`v1.1.0` release tag', compatibility)
        self.assertNotIn('🟡 Pending exact-tag validation', compatibility)
        self.assertIn('compatibility-v1.1.0-misp-core-v2.5.44.md', compatibility)
        self.assertIn('`v1.0.0` release tag', compatibility)
        self.assertIn('compatibility-v1.0.0-misp-core-v2.5.44.md', compatibility)
        self.assertIn('compatibility-v1.0.0-misp-core-v2.5.43.md', compatibility)
        self.assertIn('`v2.5.44`', compatibility)
        self.assertIn('`v3.0.9`', compatibility)
        self.assertIn('`v1.0.0-rc.3` release candidate tag', compatibility)
        self.assertIn('✅ Validated compatible', compatibility)
        self.assertIn('`v1.1.0` release tag', matrix)
        self.assertNotIn('🟡 Pending exact-tag validation', matrix)
        self.assertIn('compatibility-v1.1.0-misp-core-v2.5.44.md', matrix)
        self.assertIn('`v1.0.0` release tag', matrix)
        self.assertIn('compatibility-v1.0.0-misp-core-v2.5.44.md', matrix)
        self.assertIn('compatibility-v1.0.0-misp-core-v2.5.43.md', matrix)
        self.assertIn('`v1.1.0` validated compatible', readiness)
        self.assertIn('core `v2.5.44`, modules `v3.0.9`, guard `v1.2`', readiness)
        self.assertIn('| `v1.1.0` | Current stable release line and latest validated-compatible artifact', security)
        self.assertIn('| `v1.0.0` | Previous stable release with retained historical compatibility evidence', security)
        self.assertIn('## [1.1.0] - 2026-07-21', changelog)
        self.assertIn('## [1.0.0] - 2026-07-15', changelog)
        self.assertIn('Mark final `v1.0.0` as validated compatible', changelog)
        self.assertIn('Overall result | ✅ Validated compatible', final_report)
        self.assertIn('Total duration | 2300 seconds', final_report)
        self.assertIn('MISP core tag | `v2.5.44`', upstream_report)
        self.assertIn('MISP modules tag | `v3.0.9`', upstream_report)
        self.assertIn('targeted lifecycle rerun', upstream_report)
        self.assertIn('Manager commit | `a0172cc1708803ce80f8542ec467515b1c44f5fb`', v1_1_report)
        self.assertIn('Overall result | ✅ Validated compatible', v1_1_report)
        self.assertIn('validation-harness or validation-infrastructure defects', v1_1_report)
        self.assertEqual(channels['schema_version'], 1)
        self.assertEqual(channels['latest_published'], 'v1.1.0')
        self.assertEqual(channels['latest_validated'], 'v1.1.0')
        for channel in ('latest_published', 'latest_validated'):
            self.assertRegex(channels[channel], r'^v\d+\.\d+\.\d+$')
            self.assertIn(f'`{channels[channel]}` release tag', compatibility)

if __name__ == '__main__':
    unittest.main()
