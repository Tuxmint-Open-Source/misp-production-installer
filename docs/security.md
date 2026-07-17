# Security model

This document describes the security posture of the stable `misp-docker-lifecycle-manager` line within its documented support scope.

It focuses on the lifecycle manager and its helper scripts. MISP application security and official Docker image contents remain upstream responsibilities of the official MISP projects.

## Scope

This project manages:

- host preparation helper scripts
- official `MISP/misp-docker` checkout creation/update
- generated `.env` values
- generated Docker Compose override
- backup/update/reset/doctor/login-check helper scripts
- bounded monitoring healthcheck and machine-readable output contracts
- public-safe validation and compatibility documentation

This project does not:

- fork or patch MISP application source code
- replace upstream MISP Docker images
- provide a complete host hardening baseline
- operate a monitoring/SIEM stack
- manage DNS or public certificate issuance for every environment
- provide high-availability clustering

## Secret handling

The installer generates secrets into the deployment `.env` file. Operators must treat that file as sensitive.

Rules:

- Do not commit `.env` or `.installer-state.json`.
- Do not paste generated passwords into public issues or logs.
- Use `admin-credentials.sh` for controlled credential inspection.
- Password-revealing helper options should be used only on trusted terminals.
- Credential-bearing login checks verify TLS and same-origin redirects by default and require positive authenticated-session evidence.
- The explicit `--insecure` login option is limited to isolated validation environments; it must not be used across untrusted networks.
- Backups must be treated as sensitive because they can include database data and generated secrets.

## File permissions

The project aims to use restrictive permissions for generated sensitive artifacts.

Expected behavior:

- backups are created with restrictive permissions
- generated secrets are not printed by default
- login checks do not print passwords
- helper scripts avoid passing database passwords on the process command line where possible

## Docker privilege model

Docker control is root-equivalent on a normal Linux host.

For that reason, host preparation does not add the current user to the Docker group by default. Operators should use `sudo` for Docker lifecycle commands unless they intentionally accept the Docker group trust boundary.

## Destructive operation safeguards

Destructive workflows should fail closed.

Expected safeguards include:

- reset is dry-run by default
- destructive reset requires explicit confirmation
- reset refuses unsafe install directories
- reset targets only deployment-scoped Compose resources
- Docker Engine itself is not removed by reset
- generated deployment state is not written after rejected validation inputs

## Backup sensitivity

Backup outputs can contain:

- MISP event data
- user/account data
- database contents
- host-data archives
- generated secrets or operational metadata

Operators should:

- store backups outside the public web root
- restrict filesystem permissions
- encrypt backups when copied off-host
- test restore procedures before relying on backups
- define retention and deletion policy

## Upstream inheritance

This manager depends on official `MISP/misp-docker` for the application stack and images.

Security fixes in upstream MISP components are tracked through official component tags and upstream drift monitoring. A new upstream component set is not automatically considered compatible with this manager until the documented validation scenarios pass.

## Public validation safety

Public validation artifacts should include enough evidence for customers to understand what passed, but must not disclose private infrastructure or secrets.

Public artifacts may include:

- release/ref
- official component versions
- scenario names
- pass/fail results
- limitations

Public artifacts must not include:

- private hostnames or domains
- private IP addresses
- VM identifiers
- raw logs
- credentials or generated secrets
- internal topology or access paths
- private repository URLs

## Vulnerability reporting

Vulnerability reporting is documented in the repository-level [`SECURITY.md`](../SECURITY.md).

At minimum:

- report suspected vulnerabilities through GitHub private vulnerability reporting or the security advisory workflow;
- do not include private infrastructure details, secrets, logs, database dumps, or backup contents in public issues;
- distinguish project security issues from upstream MISP security issues.

## Stable-release security evidence

The `v1.0.0` line was released with:

- this security model linked from the public documentation;
- documented and exercised restore and rollback workflows;
- a public support matrix;
- exact release-tag compatibility validation;
- public validation artifacts sanitized according to this policy.

New runtime surfaces added after `v1.0.0`, including monitoring, remain development-line work until included in a later tagged release. They must receive focused validation and security review before that release.

## What to read next

- Return to the [documentation map](README.md).
- Review supported scope in [Support matrix](support-matrix.md).
- Review backup sensitivity in [Backup, restore, and rollback](backup-restore-and-rollback.md).
- Review operator commands in [Shell scripts reference](shell-scripts.md).
