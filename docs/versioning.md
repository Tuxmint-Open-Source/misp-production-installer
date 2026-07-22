# Versioning

This repository has two different version streams. Keeping them separate avoids confusion.

## 1. Manager version

The lifecycle manager is versioned with Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

Examples:

- `0.1.0` — early public base version.
- `0.2.0` — new backwards-compatible installer features.
- `0.2.1` — bugfix release.
- `1.0.0` — stable production API/CLI contract.

The current manager version lives in:

```text
VERSION
```

Every release should also update:

```text
CHANGELOG.md
```

The operational scripts expose the manager version:

```bash
./installer/install.sh --version
./installer/update.sh --version
```

## 2. MISP/misp-docker upstream version

MISP itself is not vendored into this repository. The installer fetches the official upstream:

```text
https://github.com/MISP/misp-docker.git
```

Choose the upstream branch, tag, or commit with:

```bash
./installer/install.sh --upstream-ref <branch-tag-or-commit>
./installer/update.sh --upstream-ref <branch-tag-or-commit>
```

That means:

- Manager version controls this repository's scripts and documentation.
- `--upstream-ref` controls which official MISP Docker code you deploy.

## 3. Compatibility status

Compatibility is tracked as a pair:

```text
misp-docker-lifecycle-manager release/ref × official MISP Docker component set = validation status
```

A release should be called **validated compatible** only after the documented scenarios pass for the exact manager release/ref and component set. For release claims, validate the immutable Git tag, not just `main` or a release branch.

See [`docs/compatibility.md`](compatibility.md), [`docs/validation/matrix.md`](validation/matrix.md), and [Upstream input policy](upstream-inputs.md).

## Recommended release workflow

Use the release-PR workflow in [`docs/release/release-process.md`](release/release-process.md) as the source of truth.

Short version:

1. Feature and fix PRs update code, docs, tests, and the `[Unreleased]` changelog section.
2. A dedicated release PR updates `VERSION`, finalizes `CHANGELOG.md`, and prepares release notes.
3. After the release PR is reviewed and merged into `main`, create the annotated tag from the updated `main` commit.
4. Create and verify the GitHub Release from that tag.

Do not push release commits directly to `main`; use a release PR so the version bump, changelog, release notes, and public-safety checks are reviewed before tagging.

## When to bump which number?

For the current stable line:

- Bump `MAJOR` for breaking changes.
- Bump `MINOR` for backwards-compatible features.
- Bump `PATCH` for backwards-compatible fixes.

## What to read next

- Return to the [documentation map](README.md).
- Review update behavior in [Upgrade path](upgrade-path.md).
- Review compatibility status definitions in [Compatibility](compatibility.md).
- Review upstream input identity rules in [Upstream input policy](upstream-inputs.md).
- Review release mechanics in [Release process](release/release-process.md).
