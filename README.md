# MISP Docker Lifecycle Manager

> [!IMPORTANT]
> **Release channels**
>
> | Channel | Version | Meaning |
> | --- | --- | --- |
> | Latest published | `v1.3.1` | Newest normal SemVer release |
> | Latest validated | `v1.3.0` | Newest immutable release tag that passed the full compatibility matrix |
>
> Select through these channels, but install and report the immutable SemVer tag. The machine-readable source is [`.release-channels.json`](.release-channels.json); mutable `stable` and `latest` Git tags are intentionally not used.

A non-invasive lifecycle manager for official `MISP/misp-docker` single-server Docker deployments.

Current `VERSION` value on `main`: `1.3.1`. The `v1.3.1` release packages lifecycle hardening and is pending exact-tag/package-artifact validation. The immutable `v1.3.0` tag and published operator-bundle artifact remain validated compatible with the component set listed below.

MISP Docker Lifecycle Manager helps operators install, configure, validate, update, back up, restore, and safely remove MISP Docker deployments while keeping the generated deployment a normal official upstream checkout.

## What it is

This project is an operational wrapper around official `MISP/misp-docker`.

It adds:

- install and host-preparation helpers;
- generated `.env` values and Compose overrides;
- deterministic component tag handling;
- health, status, login, and credential checks;
- monitoring healthcheck and machine-readable output contracts;
- backup, restore, update, and restore-based rollback workflows;
- reset/removal helpers with safety checks;
- compatibility and validation documentation;
- optional operator-bundle packaging for release assets, validated for the documented scope.

It does **not** fork, vendor, or copy MISP. It does **not** replace upstream `MISP/misp-docker`. It is not a Kubernetes, high-availability, or multi-node orchestration layer.

There is no lock-in: after a successful install, `/opt/misp-docker` remains a normal official `MISP/misp-docker` checkout that can be managed manually with Docker Compose.

## Start here

| Reader path | Read this |
| --- | --- |
| New user/operator | [`docs/README.md`](docs/README.md), then [`docs/getting-started.md`](docs/getting-started.md) |
| Production operator | [`docs/support-matrix.md`](docs/support-matrix.md), then [`docs/production-deployment.md`](docs/production-deployment.md) |
| Day-2 operations | [`docs/operator-guide.md`](docs/operator-guide.md), [`docs/upgrade-path.md`](docs/upgrade-path.md), and [`docs/backup-restore-and-rollback.md`](docs/backup-restore-and-rollback.md) |
| Compatibility/release evidence | [`docs/compatibility.md`](docs/compatibility.md) and [`docs/validation/matrix.md`](docs/validation/matrix.md) |
| Contributor/maintainer | [`docs/README.md`](docs/README.md#contributors-and-maintainers) and [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Troubleshooting/support | [`docs/troubleshooting.md`](docs/troubleshooting.md) and [`docs/sos-report.md`](docs/sos-report.md) |
| Security report | [`SECURITY.md`](SECURITY.md) |

## Quick test path

For a first test install using the stable release, read [`docs/getting-started.md`](docs/getting-started.md). The shortened path is:

```bash
git clone https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager.git
cd misp-docker-lifecycle-manager
git checkout v1.3.1
sudo ./lifecycle/prepare-host-rocky.sh
sudo ./lifecycle/install.sh \
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
sudo ./lifecycle/doctor.sh --install-dir /opt/misp-docker
sudo ./lifecycle/login-check.sh --install-dir /opt/misp-docker
sudo ./lifecycle/admin-credentials.sh --install-dir /opt/misp-docker
```

For production planning, reverse-proxy details, recovery, updates, and limitations, use the documentation map instead of treating this quick path as the full guide.

## Compatibility status

Compatibility is tracked as an explicit pair:

```text
manager release/ref × official MISP Docker component set = status
```

| Manager release/ref | MISP core | MISP modules | MISP guard | Status |
| --- | ---: | ---: | ---: | --- |
| `v1.3.1` release tag | `v2.5.44` | `v3.0.9` | `v1.2` | 🟡 Pending validation |
| `v1.3.0` release tag | `v2.5.44` | `v3.0.9` | `v1.2` | ✅ Validated compatible |
| `v1.2.0` release tag | `v2.5.44` | `v3.0.9` | `v1.2` | ✅ Validated compatible |
| `v1.1.0` release tag | `v2.5.44` | `v3.0.9` | `v1.2` | ✅ Validated compatible |
| `v1.0.0` release tag | `v2.5.44` | `v3.0.9` | `v1.2` | ✅ Validated compatible |
| `v1.0.0` release tag | `v2.5.43` | `v3.0.8` | `v1.2` | ✅ Validated compatible |

See [`docs/compatibility.md`](docs/compatibility.md) and [`docs/validation/matrix.md`](docs/validation/matrix.md) for status definitions, detailed reports, limitations, and retained historical evidence.

## Version model

There are three separate version concepts:

| Concept | Controlled by | Purpose |
| --- | --- | --- |
| Lifecycle manager version | this repo's `VERSION`, Git tags, GitHub Releases | Version of these helper scripts and docs |
| Upstream checkout | `--upstream-ref` | Official `MISP/misp-docker` branch/commit used in `/opt/misp-docker` |
| Runtime component images | `CORE_RUNNING_TAG`, `MODULES_RUNNING_TAG`, `GUARD_RUNNING_TAG` | Actual MISP container image tags used by Docker Compose |

Check current upstream component versions:

```bash
./lifecycle/get-current-misp-versions.sh
```

Compare a local install against upstream:

```bash
./lifecycle/get-current-misp-versions.sh --install-dir /opt/misp-docker
```

For update policy and version details, see [`docs/upgrade-path.md`](docs/upgrade-path.md), [`docs/versioning.md`](docs/versioning.md), and [`docs/upstream-inputs.md`](docs/upstream-inputs.md).

## Design principles

1. Keep official upstream clean.
2. Prefer generated `.env` and `docker-compose.override.yml` over upstream file patches.
3. Pin runtime component tags instead of relying on implicit Docker `latest` behavior.
4. Back up before updates and use restore-based recovery for rollback drills.
5. Wait for application-owned readiness before declaring login ready.
6. Keep production claims tied to exact release-tag validation.

## Release readiness

`v1.3.1` is the latest published release and is pending exact-tag/package-artifact validation for the listed component set. `v1.3.0` remains the latest validated-compatible release; its immutable tag and published operator-bundle artifact passed the required lifecycle matrix for the documented scope.

See [`docs/production-readiness.md`](docs/production-readiness.md).

## Contributing

Contributions are welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) for the public-safety rules, PR workflow, validation commands, and compatibility-claim expectations.

The monitoring healthcheck is contract/parser tested and has passed healthy, UNKNOWN, controlled-CRITICAL, and recovery checks on a managed MISP deployment. Native ingestion by Zabbix, Checkmk, Nagios/Icinga, and Prometheus remains community-testing work. Operators with those systems are invited to contribute through [monitoring issue #62](https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/issues/62) after reading [`docs/monitoring.md`](docs/monitoring.md).

Please keep public examples sanitized and avoid committing generated secrets, runtime `.env` files, raw logs, private infrastructure details, or deployment-specific credentials.

Useful project docs:

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`AGENTS.md`](AGENTS.md)
- [`QA.md`](QA.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`docs/release/release-process.md`](docs/release/release-process.md)
