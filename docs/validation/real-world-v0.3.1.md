# Real-world validation: v0.3.1

This document records a public-safe validation run for `misp-production-installer` v0.3.1.

The goal is transparency: show what was actually tested, what passed, what was observed, and what was not claimed.

## Summary

`v0.3.1` was validated on a freshly recreated Rocky Linux virtual machine using the published GitHub release artifact.

The test covered:

- clean VM bootstrapping
- Docker host preparation from a minimal OS state
- fresh install of an older/specific MISP component set
- update from that older component set to latest upstream-declared component tags
- MISP database migrations during install and update
- health checks, login checks, external redirect checks, and real browser login

Result: **passed**.

## Environment

Public-safe environment shape:

| Item | Value |
| --- | --- |
| OS | Rocky Linux 10.2 |
| CPU | 4 vCPU |
| Memory | 8 GB RAM |
| Disk | 50 GB virtual disk |
| Deployment type | Single-server Docker |
| Exposure mode | Direct QA mode for validation |
| DNS | Browser-facing DNS name configured |
| Installer source | Published GitHub release artifact, `v0.3.1` |

The validation intentionally started from a freshly recreated VM instead of a reused application directory.

Private infrastructure details such as internal hostnames, private IP addresses, VM IDs, and lab topology are intentionally omitted.

## Scenarios tested

### 1. Fresh VM and host preparation

Steps:

1. Recreate a fresh VM from a base Rocky Linux template.
2. Configure the VM on the intended test DNS endpoint.
3. Download the published `v0.3.1` release artifact.
4. Run repository validation gates from the release checkout.
5. Run host preparation to install Docker and Docker Compose.

Evidence:

```text
misp-production-installer 0.3.1
unit tests passed
shell syntax checks passed
Docker version 29.6.1
Docker Compose version v5.3.1
```

Result: **passed**.

Observation: the minimal VM template did not include `tar`. The validation workflow avoided relying on that host package by extracting the release artifact with Python's standard `tarfile` module. The installer itself still installed Docker successfully.

### 2. Fresh install with older/specific MISP component versions

Command shape:

```bash
sudo ./installer/install.sh \
  --install-dir /opt/misp-docker \
  --upstream-ref master \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --admin-org ExampleOrg \
  --timezone Europe/Zurich \
  --exposure direct-qa \
  --bootstrap-tls \
  --core-tag v2.5.38 \
  --modules-tag v3.0.7 \
  --guard-tag v1.2
```

Installed runtime tags:

```text
CORE_RUNNING_TAG=v2.5.38
MODULES_RUNNING_TAG=v3.0.7
GUARD_RUNNING_TAG=v1.2
```

Evidence:

```text
Running MISP database updates
All updates completed.
Doctor checks completed.
Installation complete.
```

Post-install checks:

```text
login_success=true
logout_status=200
```

External browser-facing redirect check stayed on the configured non-loopback DNS name and did not redirect to localhost.

Result: **passed**.

### 3. Update from older components to latest upstream-declared components

Command:

```bash
sudo ./installer/update.sh --install-dir /opt/misp-docker
```

Selected latest upstream-declared tags at the time of validation:

```text
CORE_RUNNING_TAG=v2.5.42
MODULES_RUNNING_TAG=v3.0.8
GUARD_RUNNING_TAG=v1.2
```

Evidence:

```text
Backup written
Running MISP database updates
Executing 151.................Done
Executing 152.................Done
Executing 153.................Done
All updates completed.
Doctor checks completed.
```

Final version comparison:

```text
Component  Upstream       Local metadata   Runtime image
---------- -------------- ---------------- ----------------
Core       v2.5.42        v2.5.42          v2.5.42
Modules    v3.0.8         v3.0.8           v3.0.8
Guard      v1.2           v1.2             v1.2
```

Result: **passed**.

### 4. Real browser login

A Playwright-controlled Chromium browser was used from the validation control host.

Evidence:

```text
goto_status=200
initial_url=https://misp.example.com/users/login
loaded_url=https://misp.example.com/users/login
final_url=https://misp.example.com/
title=Events - MISP
browser_login_success=true
```

Result: **passed**.

## Timing notes

Approximate timings from this specific run:

| Phase | Duration |
| --- | ---: |
| Docker host preparation | ~32 seconds |
| Fresh older-component MISP install | ~129 seconds |
| Update from older components to latest components | ~112 seconds |

These timings are environment-specific. Image pulls and extraction dominate the runtime and can be much slower on other networks, hosts, registries, or cold caches.

## What this validates

This validation gives confidence that `v0.3.1` can:

- prepare a fresh Rocky Linux Docker host
- install from the published release artifact
- deploy official `MISP/misp-docker` without vendoring or forking upstream
- install a known older/specific MISP component set
- update that deployment to latest upstream-declared component tags
- run MISP database updates during install and update
- pass doctor and login checks
- serve the browser-facing MISP UI through the configured non-loopback base URL
- support real browser login after first-start initialization completes

## What this does not claim

This validation does **not** claim:

- production readiness
- high availability support
- Kubernetes support
- multi-node support
- every possible MISP component tag combination works
- downgrade or rollback across database migrations is safe
- every operating system or Docker version is supported
- every reverse proxy configuration is validated

## Why this matters

Installer projects need more than static tests. Users need to know that the documented workflow has been exercised in a realistic environment.

This validation combines:

- unit/static checks
- shell syntax checks
- fresh host preparation
- real Docker image pulls
- real MISP database migrations
- operational health checks
- login checks
- real browser login

That provides a more useful trust signal than repository tests alone, while keeping the validation report public-safe and reproducible in shape.
