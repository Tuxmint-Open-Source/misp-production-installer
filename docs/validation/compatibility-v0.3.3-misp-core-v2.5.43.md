# Compatibility validation: installer v0.3.3 line with MISP core v2.5.43

This document records public-safe compatibility validation for the `misp-production-installer` line being prepared as `v0.3.3`, with the official MISP Docker component set reviewed in PR [#22](https://github.com/Tuxmint-Open-Source/misp-production-installer/pull/22).

The purpose is to show which installer release/ref was tested with which official MISP component versions, what passed, what failed, and what is not claimed.

## Compatibility pair

| Item | Value |
| --- | --- |
| Official MISP Docker component set | core `v2.5.43`, modules `v3.0.8`, guard `v1.2` |
| `v0.3.3` release candidate | 🟡 release/tag validation pending |
| current `main` at PR #22 validation time | ✅ Validated compatible |
| `v0.3.2` release tag | ❌ Validation failed |
| Upstream-review PR | [#22](https://github.com/Tuxmint-Open-Source/misp-production-installer/pull/22) |

> [!IMPORTANT]
> The `v0.3.3` release candidate is prepared from the `main` line that passed compatibility validation with MISP core `v2.5.43`. It should be marked **validated compatible** only after the final `v0.3.3` release tag is created and the same compatibility validation passes against that immutable tag.
>
> The `v0.3.2` release tag is **not** marked validated compatible with MISP core `v2.5.43`. Validation exposed the first-login readiness race that was fixed later on `main`.

## Target official MISP Docker component set

| Component | Previous reviewed tag | Tested tag |
| --- | ---: | ---: |
| MISP core | `v2.5.42` | `v2.5.43` |
| MISP modules | `v3.0.8` | `v3.0.8` |
| MISP guard | `v1.2` | `v1.2` |

## Validation approach

Compatibility is tracked as a pair:

```text
misp-production-installer release/ref × official MISP Docker component set
```

A pair is called **validated compatible** only after the documented scenarios pass.

Private lab identifiers, raw logs, hostnames, IP addresses, VM IDs, credentials, and topology are intentionally omitted from this public report.

## Public-safe environment shape

The validation used clean Rocky Linux virtual machines prepared for single-server Docker deployments.

| Item | Value |
| --- | --- |
| OS family | Rocky Linux |
| Deployment type | Single-server Docker |
| Component selection | Explicit MISP component tags |
| Reverse proxy fixture | Caddy |

The test machines were reset to a clean Docker-ready state before each scenario. Internal infrastructure details are intentionally not published.

## Result summary

| Installer release/ref | Direct fresh install | Caddy reverse proxy | Install/update path | Lifecycle smoke | Failure guardrail | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| current `main` at PR #22 validation time | ✅ passed | ✅ passed | ✅ passed | ✅ passed | ✅ passed | ✅ validated compatible |
| `v0.3.2` release tag | ❌ failed | ❌ failed | ❌ failed | ❌ failed | ✅ passed | ❌ validation failed |

## Current `main` validation details

These scenarios passed for the current public `main` ref at the time PR #22 was reviewed.

### 1. Direct-QA fresh install

Command shape:

```bash
sudo ./installer/install.sh \
  --install-dir /opt/misp-docker \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --admin-org ExampleOrg \
  --exposure direct-qa \
  --bootstrap-tls \
  --core-tag v2.5.43 \
  --modules-tag v3.0.8 \
  --guard-tag v1.2
```

Evidence:

- `install.sh` completed in direct-QA mode.
- `doctor.sh` completed.
- `login-check.sh` passed without printing the password.
- `admin-credentials.sh` default output worked without exposing the password.

Result: **passed**.

### 2. Caddy reverse-proxy fresh install

Evidence:

- `install.sh` completed in reverse-proxy mode.
- Caddy reverse-proxy fixture started.
- `doctor.sh` completed.
- `login-check.sh` passed through the proxied URL.

Result: **passed**.

### 3. Specific component install and update path

Evidence:

- Explicit target component-tag install completed.
- `update.sh` completed with version-tag image tracking.
- `doctor.sh` completed after update.
- `login-check.sh` passed after update.

Result: **passed**.

### 4. Backup, reset dry-run, and no-lock-in smoke

Evidence:

- Fresh install completed.
- `backup.sh` completed.
- `reset-installation.sh` dry-run completed without destructive flags.
- Generated upstream checkout remained usable with normal Docker Compose tooling.
- `login-check.sh` still passed after lifecycle smoke checks.

Result: **passed**.

### 5. Failure-mode guardrail smoke

Evidence:

- Direct-QA loopback `BASE_URL` was rejected.
- Error output identified the invalid direct-QA / `BASE_URL` condition.
- No deployment `.env` was created after the rejected command.

Result: **passed**.

## `v0.3.2` release-tag validation details

The same component set was also tested against the immutable `v0.3.2` release tag.

Result: **failed**.

Observed failure class:

- Fresh installs completed far enough for MISP database updates and `doctor.sh` to pass.
- Immediate `login-check.sh` runs still failed with invalid-credentials/not-ready markers.
- This matches the first-login readiness race fixed later on `main` by waiting for MISP's upstream interactive-login readiness signal.
- The failure-mode guardrail smoke still passed.

This means `v0.3.2` should not be described as validated compatible with MISP core `v2.5.43`.

## What this validates

The completed `main` validation gives confidence that the installer line after the readiness fix works with the official MISP Docker component set reviewed in PR #22:

- fresh direct-QA installation
- fresh reverse-proxy installation
- version-tagged update workflow
- backup workflow
- reset dry-run safety
- no-lock-in Docker Compose usability
- login-check behavior
- basic negative-path guardrails

## Required follow-up

Publish a patch release from the validated `main` line, then validate that release tag against the same official MISP Docker component set. Only then should the public compatibility table show a release-tag entry as **validated compatible**.

## What this does not claim

This report does not claim that every possible production environment or reverse proxy works. It records the specific public-safe scenario coverage that was exercised and passed or failed.

This compatibility run used CLI login checks for the web login flow. It did not repeat the separate Playwright browser-login scenario from the earlier release validation report.

The validation intentionally omits private infrastructure details and raw logs from the public repository.

## Related public artifacts

- Compatibility overview: [`../compatibility.md`](../compatibility.md)
- Upstream-review PR: [#22](https://github.com/Tuxmint-Open-Source/misp-production-installer/pull/22)
- Upstream review report: [`../../.upstream/reports/misp-docker-upstream-review.md`](../../.upstream/reports/misp-docker-upstream-review.md)
- Validation matrix: [`matrix.md`](matrix.md)
