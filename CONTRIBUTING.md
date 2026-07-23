# Contributing

Thank you for considering a contribution to MISP Docker Lifecycle Manager.

This project is a non-invasive lifecycle manager for official `MISP/misp-docker` single-server Docker deployments. Contributions should preserve that design: no vendoring, forking, or rewriting upstream MISP source trees.

## Start here

Before opening an issue or pull request, read:

- [`README.md`](README.md) for the project overview;
- [`docs/README.md`](docs/README.md) for the documentation map;
- [`docs/operator-guide.md`](docs/operator-guide.md) for the normal lifecycle;
- [`docs/support-matrix.md`](docs/support-matrix.md) for supported and unsupported use cases;
- [`docs/security.md`](docs/security.md) for the security model.

## Public-safety rule

This is a public repository. Do **not** include any real deployment-sensitive information in issues, pull requests, comments, commits, screenshots, or logs.

Do not post:

- passwords, tokens, API keys, private keys, generated secrets, or `.env` contents;
- private hostnames, internal domains, private IPs, VM IDs, topology, or access paths;
- raw logs that may contain secrets or deployment details;
- database dumps, backup contents, or generated configuration archives.

Use sanitized examples such as:

```text
misp.example.com
admin@example.com
/opt/misp-docker
[REDACTED]
```

## Good issue reports

For bugs, include an anonymous SOS report when possible. Start with [`docs/sos-report.md`](docs/sos-report.md), review the report before posting, and paste only public-safe values.

For bugs, include:

- the manager version or Git commit;
- the affected workflow, such as fresh install, update, backup, restore, rollback, reset, doctor/status, or login check;
- the command shape you ran, with secrets and deployment-specific values removed;
- expected behavior;
- actual behavior;
- relevant sanitized output summary, not raw logs;
- whether the issue is reproducible on a fresh install.

If you are unsure whether something is security-sensitive, do not open a public issue with details. Use [`SECURITY.md`](SECURITY.md) instead.

## Pull request workflow

1. Create a focused branch from `main`.
2. Keep each PR scoped to one concern.
3. Update docs and tests when behavior changes.
4. Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes.
5. Do not bump `VERSION` in feature/fix PRs. Version bumps happen in dedicated release PRs.
6. Keep PR text public-safe and sanitized.

## Validation before opening a PR

Run:

```bash
python3 -m unittest discover -s tests
for f in lifecycle/*.sh; do bash -n "$f"; done
python3 -m py_compile scripts/*.py tests/*.py
git diff --check
```

Also review the diff for public-sensitive markers before posting it.

## Runtime changes

Runtime changes are higher risk than documentation-only changes. If a PR changes install, update, backup, restore, reset, login, monitoring healthcheck, exposure mode, or generated configuration behavior, include clear validation evidence.

For changes that affect user/browser-facing behavior, validate the real external path, not only container-local health checks.

## Monitoring integration contributions

The healthcheck command has automated contract/parser tests, but the project does not currently operate dedicated Zabbix, Checkmk, Nagios/Icinga, or Prometheus server infrastructure. Real integration reports and focused adapter contributions are welcome.

For a monitoring integration report or PR, include only public-safe information:

- monitoring product and version;
- manager release/ref and healthcheck command shape;
- output format tested;
- whether ingestion, status mapping, metrics, and recovery worked;
- sanitized expected/observed results;
- any adapter configuration that is generic and contains no infrastructure details.

Do not claim vendor certification. See [`docs/monitoring.md`](docs/monitoring.md) for the current evidence matrix and validation helper.

## Documentation changes

Documentation-only changes are welcome. Keep docs concise, link to the canonical page instead of duplicating long procedures, and preserve the human reader journey through [`docs/README.md`](docs/README.md).

## Compatibility claims

Do not mark a release/component pair as **validated compatible** unless the documented scenarios passed for the exact release/ref and official MISP Docker component set.

For release claims, validate the immutable Git tag, not only `main` or a release branch.

## Code of Conduct

Participation in this project is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
