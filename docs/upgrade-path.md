# Upgrade Path

MISP Docker upgrades have three separate version concepts. Do not treat the
`misp-docker` Git branch as the only version pin.

## Version concepts

### 1. Lifecycle manager version

This repository is versioned separately with `VERSION`, `CHANGELOG.md`, Git tags,
and GitHub Releases.

Example:

```text
misp-docker-lifecycle-manager v0.2.0
```

This controls the helper scripts and documentation, not the MISP application
version inside the containers.

### 2. Official `MISP/misp-docker` checkout

The install directory is an official upstream `MISP/misp-docker` Git checkout.
`--upstream-ref` selects which branch or commit of that repository to use:

```bash
./lifecycle/update.sh \
  --install-dir /opt/misp-docker \
  --upstream-ref master
```

MISP upstream currently does not use Git repository tags as the main release
unit for this Docker packaging.

### 3. Runtime image tags

The official upstream Compose file runs these images:

```text
ghcr.io/misp/misp-docker/misp-core:${CORE_RUNNING_TAG:-latest}
ghcr.io/misp/misp-docker/misp-modules:${MODULES_RUNNING_TAG:-latest}
ghcr.io/misp/misp-docker/misp-guard:${GUARD_RUNNING_TAG:-latest}
```

The official `template.env` declares component versions:

```text
CORE_TAG=...
MODULES_TAG=...
GUARD_TAG=...
```

`--upstream-ref` may point at a branch for discovery/update convenience, but public compatibility evidence is tied to immutable manager refs and official component tags. See [Upstream input policy](upstream-inputs.md) for the distinction between discovery, development, release, and validated-compatibility references.

Upstream publishes images with several tag styles:

- short build commit tags, for example `misp-core:<commit7>`
- `latest`
- component version tags matching `CORE_TAG`, `MODULES_TAG`, and `GUARD_TAG`

## Recommended production mode

Use deterministic component version tags instead of implicit `latest`.

For a normal first install, keep the manager's default upstream ref (`master`) unless you intentionally need an older upstream commit. The manager reads the most recent official component tags from upstream `template.env` and writes them as fixed runtime image tags in `.env`.

The manager defaults to:

```text
CORE_RUNNING_TAG=$CORE_TAG
MODULES_RUNNING_TAG=$MODULES_TAG
GUARD_RUNNING_TAG=$GUARD_TAG
```

That means an update uses the component versions declared by the checked-out
official upstream `template.env`, rather than whatever `latest` points to at pull
time.

## Check current upstream component versions

To see the latest official component versions declared by upstream:

```bash
./lifecycle/get-current-misp-versions.sh
```

This prints upstream versions only. It does not inspect a local install unless
you provide `--install-dir`.

To inspect another upstream ref:

```bash
./lifecycle/get-current-misp-versions.sh --upstream-ref <branch-or-commit>
```

To compare upstream values with a local install:

```bash
./lifecycle/get-current-misp-versions.sh --install-dir /opt/misp-docker
```

## Common workflows

### 1. Fresh install with latest official component versions

Use the default `master` upstream ref and default `version-tags` behavior:

```bash
sudo ./lifecycle/install.sh \
  --install-dir /opt/misp-docker \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --exposure reverse-proxy
```

The installer reads the current upstream `CORE_TAG`, `MODULES_TAG`, and
`GUARD_TAG`, then writes matching `CORE_RUNNING_TAG`, `MODULES_RUNNING_TAG`, and
`GUARD_RUNNING_TAG` values to `.env`.

### 2. Fresh install with specific component versions

Use explicit component tag overrides:

```bash
sudo ./lifecycle/install.sh \
  --install-dir /opt/misp-docker \
  --base-url https://misp.example.com \
  --admin-email admin@example.com \
  --exposure reverse-proxy \
  --core-tag v2.5.40 \
  --modules-tag v3.0.7 \
  --guard-tag v1.2
```

This keeps the upstream checkout clean but pins the runtime images to the exact
component tags you requested.

Only use component combinations that upstream has published to the container
registry. The installer does not build custom images.

### 3. Update to latest official component versions

```bash
sudo ./lifecycle/update.sh --install-dir /opt/misp-docker
```

This is equivalent to:

```bash
sudo ./lifecycle/update.sh \
  --install-dir /opt/misp-docker \
  --upstream-ref master \
  --image-track version-tags
```

### 4. Update to specific component versions

```bash
sudo ./lifecycle/update.sh \
  --install-dir /opt/misp-docker \
  --core-tag v2.5.40 \
  --modules-tag v3.0.7 \
  --guard-tag v1.2
```

The update still backs up first, validates Compose, pulls images, restarts
containers, runs MISP DB updates, and runs `doctor.sh`.

## Update workflow

Default production update:

```bash
./lifecycle/update.sh --install-dir /opt/misp-docker
```

What happens:

1. create a backup
2. fetch official upstream `MISP/misp-docker`
3. fast-forward the current upstream branch, or checkout `--upstream-ref`
4. read `CORE_TAG`, `MODULES_TAG`, and `GUARD_TAG` from upstream `template.env`
5. apply explicit `--core-tag`, `--modules-tag`, or `--guard-tag` overrides when provided
6. set `CORE_RUNNING_TAG`, `MODULES_RUNNING_TAG`, and `GUARD_RUNNING_TAG` to the selected component tags
7. render the Compose override
8. validate `.env` and Docker Compose config
9. pull the selected images
10. start/recreate containers
11. wait for MISP core readiness
12. run MISP database updates
13. verify schema readiness
14. run `doctor.sh`

## Image tracking modes

### `version-tags` default

```bash
./lifecycle/update.sh --install-dir /opt/misp-docker --image-track version-tags
```

Best production default. Pins runtime image tags to the selected component tags.
By default these are read from the checked-out upstream `template.env`; explicit
component tag flags override them.

### `latest`

```bash
./lifecycle/update.sh --install-dir /opt/misp-docker --image-track latest
```

Tracks the newest published upstream images. This is convenient, but less
repeatable because `latest` can move independently of your local expectations.
Use this only when that behavior is intentional.

### `keep`

```bash
./lifecycle/update.sh --install-dir /opt/misp-docker --image-track keep
```

Refreshes component metadata from upstream but does not change existing
`CORE_RUNNING_TAG`, `MODULES_RUNNING_TAG`, or `GUARD_RUNNING_TAG` pins. Use this
when you intentionally manage image pins yourself.

## MISP-Guard

`misp-guard` is optional and controlled by upstream Compose profiles. Even when
not enabled, this installer keeps `GUARD_TAG` and `GUARD_RUNNING_TAG` aligned so
that enabling the profile later is predictable.

## Rollback

A safe rollback starts from the backup created before update.

At minimum, record before updating:

```bash
git -C /opt/misp-docker rev-parse HEAD
grep -E '^(CORE|MODULES|GUARD)(_RUNNING)?_TAG=' /opt/misp-docker/.env
```

Then restore data from the backup and restore the previous upstream checkout and
image tags. Avoid downgrading across unknown database migrations unless you have
tested the rollback path.

## What to read next

- Return to the [documentation map](README.md) and choose the user/operator path.
- Review backup and rollback details in [Backup, restore, and rollback](backup-restore-and-rollback.md).
- Check validated release/component pairs in [Compatibility](compatibility.md).
- Follow day-2 flow in [Operator guide](operator-guide.md).
