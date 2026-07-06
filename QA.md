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
git diff --check
```

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
- never print the password
- report login status markers
- attempt logout after successful login

## Release acceptance criteria

A release is ready when:

- `VERSION` contains the target SemVer version
- README current version text matches `VERSION`
- `CHANGELOG.md` has a dated release section
- GitHub Release notes follow `.github/RELEASE_TEMPLATE.md`
- all validation commands pass
- release text is public-safe
- tag is created from merged `main`, not from an unmerged branch

## Definition of done

A PR is done when:

- scope is clear
- docs are updated if user-facing behavior changed
- `[Unreleased]` changelog is updated if appropriate
- tests and shell syntax checks pass
- public marker scan passes
- PR text is short, informative, and public-safe
