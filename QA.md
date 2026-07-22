# QA.md

Quality goals and acceptance criteria for this repository.

`doctor.sh` validates a specific installed deployment. This document defines the broader repository-level quality gates for humans and coding agents.

## Goals

A change is successful when it keeps the project:

- production-oriented
- upgrade-friendly
- public-safe
- operator-readable
- testable
- aligned with official upstream MISP Docker packaging

## Repository quality gates

Before a PR is ready for review:

```bash
python3 -m unittest discover -s tests
for f in installer/*.sh; do bash -n "$f"; done
python3 -m py_compile scripts/*.py tests/*.py
git diff --check
```

The always-running `Repository gates` GitHub workflow applies these read-only checks to every pull request, including documentation-only changes, and to every push to `main`. It also parses every tracked YAML file and checks the complete current repository tree for whitespace errors, avoiding assumptions about event history or parent availability. Specialized CodeQL and ShellCheck workflows remain additional path-scoped checks.

The repository must not contain:

- runtime `.env`
- `.installer-state.json`
- generated secrets
- private keys
- credentials or tokens
- logs or backups
- local test archives
- real infrastructure details

## Public-safety gate

All public content must be sanitized:

- code
- docs
- examples
- PR bodies and comments
- release notes
- issues
- commit messages
- validation summaries

Use generic examples such as:

```text
misp.example.com
admin@example.com
/opt/misp-docker
```

Do not include private hostnames, real IPs, private paths, topology, access methods, security posture, credentials, or lab details.

## Installer acceptance criteria

A successful install path should:

1. generate a complete `.env` with required values
2. render `docker-compose.override.yml`
3. validate `.env`
4. validate Docker Compose config
5. fetch official upstream `MISP/misp-docker`
6. start the stack
7. wait for container-local MISP heartbeat
8. run MISP database updates
9. verify schema readiness required by first interactive login
10. run `doctor.sh`

## Day-2 operation acceptance criteria

### `doctor.sh`

Must check:

- required `.env` values
- Docker Compose config
- `BASE_URL` DNS lookup from the host
- container-local MISP heartbeat
- schema readiness
- Docker Compose service status

### `backup.sh`

Must create:

- database dump
- host-data archive
- checksums

Backups must be suitable for verification with checksum tooling.

### `update.sh`

Must:

- create a backup before update
- fetch the requested upstream ref
- restart/update the stack
- run MISP database updates
- verify schema readiness
- run `doctor.sh`

### `reset-installation.sh`

Must:

- dry-run by default
- require explicit destructive confirmation
- remove only deployment-scoped Compose resources and the selected install directory
- leave Docker Engine installed
- avoid global Docker prune operations

### `admin-credentials.sh`

Must:

- show the configured admin email
- hide the password by default
- print the password only with an explicit flag and warning text

### `login-check.sh`

Must:

- read credentials from `.env`
- preserve cookies and CSRF fields
- verify TLS by default and refuse plain HTTP before credential submission
- reject cross-origin redirects, including redirects that could replay a credential POST
- require positive same-origin authenticated-session evidence rather than absence of known errors
- emit stable machine-readable reasons for expected transport and authentication failures
- reject simultaneous `--strict-tls` and `--insecure`
- never print the password
- report login status markers
- attempt logout after successful login

### `sos-report.sh`

Must:

- emit only bounded allowlisted enums, booleans, numeric counts, validated public tags, restricted versions, and fixed health-check IDs/statuses
- never copy raw subprocess output or health summaries into the report
- never collect URLs, hosts, IPs, emails, topology, backup metadata, logs, generated configuration, or MISP business data
- avoid the credential-bearing login check
- reject free-form workflow labels and symlink output targets
- write reports atomically with mode `0600`
- fail closed for malformed, duplicate, oversized, or private-registry-like component-tag inputs

## Upstream drift acceptance criteria

The upstream monitor should keep these assumptions reviewable without opening PRs for unrelated upstream commits:

- official `MISP/misp-docker` upstream commit as comparison context, not a drift signal by itself
- full hashes for `template.env`, `docker-compose.yml`, initialization/configuration scripts, MISP environment definitions, supervisor process definitions, Nginx routing, and guard runtime files
- selected README operator-section hashes for getting started, configuration, optional guard, authentication, production, SELinux/root-CA handling, database management, troubleshooting, and versioning
- component tags for core, modules, and guard
- runtime image tag defaults
- active and commented `template.env` key inventories without recording values
- Compose service names, complete service-block hashes, image expressions, and interpolation-variable inventory
- A/B/C classifications and structured added/removed key/service deltas in review reports

The parser has fixture-driven unit tests for commit-only movement, component-tag drift, Compose service drift, environment inventory privacy, operator-guidance drift, and the compatibility-proof boundary.

When the scheduled workflow opens an upstream review PR, a maintainer should decide whether code or documentation changes are needed before merging the baseline update.

## Release acceptance criteria

A release is ready when:

- `VERSION` contains the target SemVer version
- README current version text matches `VERSION`
- `CHANGELOG.md` has a dated release section
- GitHub Release notes follow `.github/RELEASE_TEMPLATE.md`
- all validation commands pass
- release text is public-safe
- tag is created from merged `main`, not from an unmerged branch
- compatibility claims are based on the immutable release tag, not only `main` or a release branch
- release/component pairs are marked **validated compatible** only after the documented compatibility scenarios pass

## Release integrity acceptance criteria

Release-integrity policy changes should keep these guarantees explicit:

- immutable SemVer tags are the installation and support identity;
- generated release assets include companion SHA-256 files when published;
- operator-bundle archives are deterministic and record source commit plus per-file digests;
- checksums are documented as corruption/mismatch detection, not as cryptographic authenticity;
- signing, SBOM, provenance, and attestations are either implemented with user verification steps or explicitly deferred;
- user instructions verify before extraction and avoid unsafe download-and-execute patterns;
- compatibility claims remain separate from artifact-integrity claims.

## Definition of done

A PR is done when:

- scope is clear
- docs are updated if user-facing behavior changed
- `[Unreleased]` changelog is updated if appropriate
- tests and shell syntax checks pass
- public marker scan passes
- PR text is short, informative, and public-safe
