from pathlib import Path
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
        for name in ['install.sh', 'update.sh', 'backup.sh', 'restore.sh', 'doctor.sh', 'status.sh', 'admin-credentials.sh', 'login-check.sh', 'get-current-misp-versions.sh', 'reset-installation.sh']:
            script = ROOT / 'installer' / name
            help_text = subprocess.check_output([str(script), '--help'], text=True, cwd=ROOT)
            self.assertIn('Usage:', help_text, name)
            version_text = subprocess.check_output([str(script), '--version'], text=True, cwd=ROOT).strip()
            self.assertRegex(version_text, r'^misp-docker-lifecycle-manager \d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?')

    def test_version_files_are_consistent(self):
        version = (ROOT / 'VERSION').read_text().strip()
        self.assertRegex(version, r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')
        self.assertIn(f'Current manager version: `{version}`', (ROOT / 'README.md').read_text())
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

    def test_restore_has_destructive_safety_and_imports_backup(self):
        text = (ROOT / 'installer' / 'restore.sh').read_text()
        self.assertIn('--backup-dir', text)
        self.assertIn('Dry-run only', text)
        self.assertIn('Type RESTORE to continue', text)
        self.assertIn('sha256sum -c SHA256SUMS', text)
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
        self.assertIn('Report manual PR fallback', workflow)
        self.assertIn('pull/new/automation/upstream-misp-docker-review', workflow)
        script = (ROOT / 'scripts' / 'check-upstream-misp-docker.py').read_text()
        self.assertIn('Run compatibility validation for the affected manager release/ref', script)
        self.assertIn('validated compatible', script)

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
        self.assertIn('What must be true before `v1.0.0`', readiness)
        self.assertIn('Real restore validation', readiness)
        self.assertIn('Current-release browser login validation', readiness)
        self.assertIn('single-server Docker', support)
        self.assertIn('Explicit non-goals', support)
        self.assertIn('Post-install verification', deployment)
        self.assertIn('No-lock-in operation', deployment)
        self.assertIn('Secret handling', security)
        self.assertIn('Docker privilege model', security)
        self.assertIn('Restore procedure', backup_restore)
        self.assertIn('Restore-based rollback after failed update', backup_restore)
        self.assertIn('misp-config.tar.gz', backup_restore)
        self.assertIn('restore.sh', backup_restore)
        self.assertNotIn('being prepared as `v0.3.3`', compat_report)
        self.assertNotIn('Publish a patch release from the validated `main` line', compat_report)

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
        self.assertIn('git checkout v1.0.0-rc.2', getting_started)
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
            'production-deployment.md',
            'production-readiness.md',
            'security.md',
            'shell-scripts.md',
            'support-matrix.md',
            'troubleshooting.md',
            'upgrade-path.md',
            'versioning.md',
        ]
        for name in major_docs:
            text = (ROOT / 'docs' / name).read_text()
            self.assertIn('## What to read next', text, name)
            self.assertIn('README.md', text, name)

        matrix = (ROOT / 'docs' / 'validation' / 'matrix.md').read_text()
        self.assertIn('## What to read next', matrix)
        self.assertIn('../README.md', matrix)
        release = (ROOT / 'docs' / 'release' / 'release-process.md').read_text()
        self.assertIn('## What to read next', release)
        self.assertIn('../README.md', release)

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

        config = (ROOT / '.github' / 'ISSUE_TEMPLATE' / 'config.yml').read_text()
        self.assertIn('blank_issues_enabled: false', config)
        self.assertIn('/security/policy', config)

    def test_security_policy_exists_and_guides_private_reporting(self):
        security = (ROOT / 'SECURITY.md').read_text()
        readme = (ROOT / 'README.md').read_text()
        contributing = (ROOT / 'CONTRIBUTING.md').read_text()
        docs_security = (ROOT / 'docs' / 'security.md').read_text()

        self.assertIn('Supported versions', security)
        self.assertIn('v1.0.0-rc.2', security)
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
        self.assertIn('github/codeql-action/init@641a925cfafe92d0fdf8b239ba4053e3f8d99d6d', codeql)
        self.assertIn('github/codeql-action/analyze@641a925cfafe92d0fdf8b239ba4053e3f8d99d6d', codeql)
        self.assertNotIn('@v3', codeql)

        self.assertIn('name: ShellCheck', shellcheck)
        self.assertIn('scandir: ./installer', shellcheck)
        self.assertIn('severity: error', shellcheck)
        self.assertIn('ludeeus/action-shellcheck@00cae500b08a931fb5698e11e79bfbd38e612a38', shellcheck)
        self.assertNotIn('@2.0.0', shellcheck)

    def test_maintainer_workflow_documents_repo_operations(self):
        docs_index = (ROOT / 'docs' / 'README.md').read_text()
        maintainer = (ROOT / 'docs' / 'maintainer-workflow.md').read_text()
        changelog = (ROOT / 'CHANGELOG.md').read_text()

        self.assertIn('maintainer-workflow.md', docs_index)
        self.assertIn('GitHub is configured to delete merged branches automatically', maintainer)
        self.assertIn('The GitHub Wiki is not used for canonical docs', maintainer)
        self.assertIn('type: security', maintainer)
        self.assertIn('area: github-actions', maintainer)
        self.assertIn('Dependabot for GitHub Actions updates', maintainer)
        self.assertIn('Private vulnerability reporting is enabled', maintainer)
        self.assertIn('Branch protection should be added once', maintainer)
        self.assertIn('manager release/ref × official MISP Docker component set = validation status', maintainer)
        self.assertIn('maintainer workflow guide', changelog)

    def test_release_candidate_is_validated_but_final_v1_remains_pending(self):
        version = (ROOT / 'VERSION').read_text().strip()
        readme = (ROOT / 'README.md').read_text()
        compatibility = (ROOT / 'docs' / 'compatibility.md').read_text()
        matrix = (ROOT / 'docs' / 'validation' / 'matrix.md').read_text()
        readiness = (ROOT / 'docs' / 'production-readiness.md').read_text()
        rc_report = (ROOT / 'docs' / 'validation' / 'compatibility-v1.0.0-rc.2-misp-core-v2.5.43.md').read_text()
        versioning = (ROOT / 'docs' / 'versioning.md').read_text()
        release_process = (ROOT / 'docs' / 'release' / 'release-process.md').read_text()
        self.assertIn('Use a new release-candidate number, such as `1.0.0-rc.3`', versioning)
        self.assertIn('Keep small documentation polishing under `[Unreleased]`', versioning)
        self.assertIn('Release-candidate documentation follow-ups may also update compatibility, validation, and operator docs', release_process)

        self.assertEqual(version, '1.0.0-rc.2')
        self.assertIn('Current manager version: `1.0.0-rc.2`', readme)
        self.assertIn('`v1.0.0-rc.2` release candidate tag', readme)
        self.assertIn('✅ Validated compatible', compatibility)
        self.assertIn('✅ Validated compatible', matrix)
        self.assertIn('`v1.0.0-rc.2` validated compatible', readiness)
        self.assertIn('Overall result | ✅ Validated compatible', rc_report)
        self.assertIn('final `v1.0.0` release must still be tagged and validated separately', rc_report)

if __name__ == '__main__':
    unittest.main()
