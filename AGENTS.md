# AGENTS.md

Guidance for AI coding agents and automated contributors working on this repository.

## Project purpose

This repository is a production-oriented lifecycle manager for official MISP Docker deployments.

Its main focus is to be a non-invasive lifecycle wrapper around official
`MISP/misp-docker` for a single-server Docker deployment. It adds safe and
convenient lifecycle management around upstream MISP Docker packaging without
vendoring, forking, or rewriting upstream source trees.

The generated deployment must remain usable as a normal official
`MISP/misp-docker` checkout. If this manager repository is deleted after
install, operators should still be able to manage the deployment manually with
Docker Compose as upstream `misp-docker` intends.

## Hard rules

- Do **not** vendor, fork, or rewrite `MISP/misp-docker` in this repository.
- Keep official upstream clean. Prefer generated `.env`, `docker-compose.override.yml`, scripts, and documentation.
- Preserve the no-lock-in property: this repository must remain an optional lifecycle add-on, not a runtime dependency for the deployed MISP stack.
- Do **not** commit runtime `.env`, `.installer-state.json`, generated secrets, logs, backups, archives, local test output, or Docker volumes.
- Do **not** include real infrastructure details in public content. Use generic examples such as `misp.example.com` and `/opt/misp-docker`.
- Public GitHub text includes code, docs, PR bodies, PR comments, release notes, issues, commit messages, and validation summaries.
- Never print or expose passwords, API keys, private keys, tokens, or generated secrets in examples or validation output.

## Repository workflow

- Use short-lived branches and Pull Requests for changes.
- Do not push directly to `main` except for an explicitly approved repository bootstrap or emergency override.
- Keep PR descriptions short, informative, and public-safe.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes.
- Do not bump `VERSION` in feature/fix PRs. Version bumps happen in dedicated release PRs.
- Release branches are review vehicles only. Tags and GitHub Releases are the permanent release records.

## Validation commands

Run these before opening or updating a PR:

```bash
python3 -m unittest discover -s tests
for f in installer/*.sh; do bash -n "$f"; done
python3 -m py_compile scripts/*.py tests/*.py
git diff --check
```

Also run a public marker scan before posting public text or release notes. Public output must not contain private hostnames, IPs, paths, topology, access methods, credentials, security posture, or lab details.

## Functional expectations

Installer changes should preserve these expectations:

- `install.sh` renders `.env` and `docker-compose.override.yml` deterministically.
- Docker Compose config validates before start.
- First start waits for MISP core readiness.
- MISP database updates run before declaring success.
- Schema readiness is checked before login-dependent workflows.
- `doctor.sh` checks the installed deployment and reports actionable status.
- `backup.sh` creates a DB dump, host-data archive, and checksums.
- `update.sh` backs up before pulling/updating.
- `reset-installation.sh` dry-runs by default and never removes Docker Engine.
- `login-check.sh` never prints the password and attempts logout after successful login.

## Upstream monitoring

- `.upstream/misp-docker.lock.json` stores the last reviewed public upstream state.
- `scripts/check-upstream-misp-docker.py` checks selected official `MISP/misp-docker` inputs.
- `.github/workflows/upstream-misp-docker-watch.yml` runs the monitor on a schedule and opens a PR when relevant drift is detected.
- Treat upstream-monitor PRs as review prompts: decide whether installer code or docs need follow-up changes before merging.

## Release workflow

1. Feature/fix PRs update code, docs, tests, and `[Unreleased]` changelog entries.
2. A dedicated release PR bumps `VERSION`, README current version text, and `CHANGELOG.md` release sections.
3. After the release PR is merged to `main`, create an annotated tag and GitHub Release.
4. Use `.github/RELEASE_TEMPLATE.md` for release notes.

## Useful files

- `README.md` — human quick start and overview.
- `QA.md` — quality gates and acceptance criteria.
- `docs/release/release-process.md` — release workflow.
- `docs/versioning.md` — SemVer guidance.
- `docs/troubleshooting.md` — operator troubleshooting.
- `tests/test_static.py` — static repository safety and workflow tests.
