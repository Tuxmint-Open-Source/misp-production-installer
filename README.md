# MISP Docker Lifecycle Manager

> [!CAUTION]
> **NOT PRODUCTION READY**
>
> This repository is under active development. APIs, configuration, behavior, and data structures may change without notice.
> Do not use this project in production environments yet.

A non-invasive lifecycle manager for official `MISP/misp-docker` single-server Docker deployments.

Current manager version: `1.0.0-rc.2`

MISP Docker Lifecycle Manager helps operators install, configure, validate, update, back up, restore, and safely remove MISP Docker deployments while keeping the generated deployment a normal official upstream checkout.

## What it is

This project is an operational wrapper around official `MISP/misp-docker`.

It adds:

- install and host-preparation helpers;
- generated `.env` values and Compose overrides;
- deterministic component tag handling;
- health, status, login, and credential checks;
- backup, restore, update, and restore-based rollback workflows;
- reset/removal helpers with safety checks;
- compatibility and validation documentation.

It does **not** fork, vendor, or copy MISP. It does **not** replace upstream `MISP/misp-docker`. It is not a Kubernetes, high-availability, or multi-node orchestration layer.

There is no lock-in: after a successful install, `/opt/misp-docker` remains a normal official `MISP/misp-docker` checkout that can be managed manually with Docker Compose.

> [!IMPORTANT]
> This project was renamed before the final `v1.0.0` release from its original `misp-production-installer` identity to `misp-docker-lifecycle-manager`.
> Because the project is still pre-`v1.0.0`, new release candidates use the new name as authoritative and do not promise compatibility with every historical pre-1.0 metadata marker. GitHub redirects the old repository URL to the renamed repository.

## Start here

| If you want to... | Read this |
| --- | --- |
| get oriented | [`docs/README.md`](docs/README.md) |
| do a first test install | [`docs/getting-started.md`](docs/getting-started.md) |
| follow the normal operator lifecycle | [`docs/operator-guide.md`](docs/operator-guide.md) |
| decide whether the project fits your use case | [`docs/support-matrix.md`](docs/support-matrix.md) |
| plan a real deployment | [`docs/production-deployment.md`](docs/production-deployment.md) |
| understand backup, restore, and rollback | [`docs/backup-restore-and-rollback.md`](docs/backup-restore-and-rollback.md) |
| check validated MISP component sets | [`docs/compatibility.md`](docs/compatibility.md) |
| troubleshoot a failure | [`docs/troubleshooting.md`](docs/troubleshooting.md) |
| report a reproducible bug safely | [`docs/sos-report.md`](docs/sos-report.md) |
| inspect every command | [`docs/shell-scripts.md`](docs/shell-scripts.md) |
| report a security vulnerability | [`SECURITY.md`](SECURITY.md) |

## Quick test path

For a first release-candidate test, read [`docs/getting-started.md`](docs/getting-started.md). The shortened shape is:

```bash
git clone https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager.git
cd misp-docker-lifecycle-manager
git checkout v1.0.0-rc.2
sudo ./installer/prepare-host-rocky.sh
sudo ./installer/install.sh \
  --install-dir /opt/misp-docker \
  --upstream-ref master \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --admin-org ExampleOrg \
  --timezone Europe/Zurich \
  --exposure reverse-proxy
```

After installation:

```bash
sudo ./installer/doctor.sh --install-dir /opt/misp-docker
sudo ./installer/login-check.sh --install-dir /opt/misp-docker
sudo ./installer/admin-credentials.sh --install-dir /opt/misp-docker
```

For production planning, reverse-proxy details, recovery, updates, and limitations, use the documentation map instead of treating this quick path as the full guide.

## Compatibility status

Compatibility is tracked as an explicit pair:

```text
manager release/ref × official MISP Docker component set = status
```

| Manager release/ref | MISP core | MISP modules | MISP guard | Status |
| --- | ---: | ---: | ---: | --- |
| `v1.0.0-rc.2` release candidate tag | `v2.5.43` | `v3.0.8` | `v1.2` | ✅ Validated compatible |
| `v1.0.0-rc.1` release candidate tag | `v2.5.43` | `v3.0.8` | `v1.2` | ✅ Validated compatible |
| `v0.3.3` release tag | `v2.5.43` | `v3.0.8` | `v1.2` | ✅ Validated compatible |
| `v0.3.2` release tag | `v2.5.43` | `v3.0.8` | `v1.2` | ❌ Validation failed |

See [`docs/compatibility.md`](docs/compatibility.md) and [`docs/validation/matrix.md`](docs/validation/matrix.md) for status definitions, detailed reports, and limitations.

## Version model

There are three separate version concepts:

| Concept | Controlled by | Purpose |
| --- | --- | --- |
| Lifecycle manager version | this repo's `VERSION`, Git tags, GitHub Releases | Version of these helper scripts and docs |
| Upstream checkout | `--upstream-ref` | Official `MISP/misp-docker` branch/commit used in `/opt/misp-docker` |
| Runtime component images | `CORE_RUNNING_TAG`, `MODULES_RUNNING_TAG`, `GUARD_RUNNING_TAG` | Actual MISP container image tags used by Docker Compose |

Check current upstream component versions:

```bash
./installer/get-current-misp-versions.sh
```

Compare a local install against upstream:

```bash
./installer/get-current-misp-versions.sh --install-dir /opt/misp-docker
```

For update policy and version details, see [`docs/upgrade-path.md`](docs/upgrade-path.md) and [`docs/versioning.md`](docs/versioning.md).

## Design principles

1. Keep official upstream clean.
2. Prefer generated `.env` and `docker-compose.override.yml` over upstream file patches.
3. Pin runtime component tags instead of relying on implicit Docker `latest` behavior.
4. Back up before updates and use restore-based recovery for rollback drills.
5. Wait for application-owned readiness before declaring login ready.
6. Keep production claims tied to exact release-tag validation.

## Release readiness

`v1.0.0-rc.2` is validated compatible with the documented MISP Docker component set, but the project still keeps the public production warning until final `v1.0.0` is tagged and validated separately.

See [`docs/production-readiness.md`](docs/production-readiness.md).

## Contributing

Contributions are welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) for the public-safety rules, PR workflow, validation commands, and compatibility-claim expectations.

Please keep public examples sanitized and avoid committing generated secrets, runtime `.env` files, raw logs, private infrastructure details, or deployment-specific credentials.

Useful project docs:

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`AGENTS.md`](AGENTS.md)
- [`QA.md`](QA.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`docs/release/release-process.md`](docs/release/release-process.md)
