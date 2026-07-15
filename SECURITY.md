# Security policy

MISP Docker Lifecycle Manager helps operate official `MISP/misp-docker` deployments. Security reports are taken seriously, especially when they affect secret handling, generated configuration, destructive lifecycle operations, or GitHub Actions supply-chain behavior.

## Supported versions

| Version/ref | Security support |
| --- | --- |
| `v1.0.0-rc.3` | Current validated release candidate. Security reports are accepted. |
| `v1.0.0-rc.2` | Validated release candidate. Security reports are accepted. |
| `main` | Development line. Security reports are accepted, but release compatibility still requires exact-tag validation. |
| Older pre-`v1.0.0` tags | Best-effort only unless the issue also affects the current release candidate or `main`. |

This project is still pre-`v1.0.0`. The public API/CLI contract is not final until the stable `v1.0.0` release.

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub's private vulnerability reporting or security advisory workflow:

```text
https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/security/advisories/new
```

Do **not** open a public issue for security vulnerabilities.

If GitHub private reporting is unavailable to you, contact the repository owner through their public GitHub profile and ask for a private security-reporting channel. Do not include vulnerability details in the first public contact.

## What to report privately

Use the private security path for issues such as:

- command injection or unsafe shell argument handling;
- secrets printed to logs, process arguments, public output, or generated files with unsafe permissions;
- unsafe handling of `.env`, generated passwords, private keys, or backup artifacts;
- reset, restore, update, or rollback behavior that can unexpectedly affect resources outside the selected deployment scope;
- generated Docker Compose or environment configuration that weakens security unexpectedly;
- GitHub Actions, release, dependency, or supply-chain issues that could affect users;
- vulnerabilities in validation/reporting workflows that could expose private deployment details.

## What can be a normal public issue

Use public issues for non-sensitive topics such as:

- documentation typos or unclear wording;
- feature requests;
- public-safe bug reports with sanitized examples;
- compatibility questions that do not include private deployment details;
- validation failures with secrets and private infrastructure removed.

For public-safe reproducible bug reports, use the anonymous SOS report guide in [`docs/sos-report.md`](docs/sos-report.md). If an SOS report cannot be safely anonymized, use the private security-reporting path instead.

## Public-safety rules

Never include the following in public issues, pull requests, comments, screenshots, or logs:

- passwords, tokens, API keys, private keys, generated secrets, or `.env` contents;
- private hostnames, internal domains, private IPs, VM IDs, topology, or access paths;
- raw logs that may contain secrets or deployment details;
- database dumps, backup contents, generated configuration archives, or full `.installer-state.json` contents.

Use sanitized examples such as:

```text
misp.example.com
admin@example.com
/opt/misp-docker
[REDACTED]
```

## Useful report contents

A good private security report includes:

- affected version, tag, or commit;
- affected workflow, such as install, update, backup, restore, rollback, reset, login, or GitHub Actions;
- a concise impact summary;
- sanitized reproduction steps;
- expected behavior;
- actual behavior;
- whether the issue appears exploitable remotely, locally, or only with operator privileges;
- any suggested fix, if known.

## Response expectations

This is a small open-source project. Maintainers will make a best-effort attempt to:

1. acknowledge a clear report;
2. confirm whether it affects supported versions;
3. prepare a private or public fix path as appropriate;
4. publish a public advisory or release note when disclosure is appropriate.

Response times are best effort and may vary.

## Coordinated disclosure

Please give maintainers reasonable time to investigate and fix confirmed vulnerabilities before public disclosure.

If a report affects upstream `MISP/misp-docker` or MISP itself rather than this lifecycle manager, maintainers may ask you to report the issue to the relevant upstream project.

## Related documentation

- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security model](docs/security.md)
- [Anonymous SOS reports](docs/sos-report.md)
- [Support matrix](docs/support-matrix.md)
