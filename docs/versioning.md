# Versioning

This repository has two different version streams. Keeping them separate avoids confusion.

## 1. Installer version

The installer itself is versioned with Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

Examples:

- `0.1.0` — early public base version.
- `0.2.0` — new backwards-compatible installer features.
- `0.2.1` — bugfix release.
- `1.0.0` — stable production API/CLI contract.

The current installer version lives in:

```text
VERSION
```

Every release should also update:

```text
CHANGELOG.md
```

The operational scripts expose the installer version:

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

- Installer version controls this repository's scripts and documentation.
- `--upstream-ref` controls which official MISP Docker code you deploy.

## Recommended release workflow

1. Make code and documentation changes.
2. Run tests and shell syntax checks:

   ```bash
   python3 -m unittest discover -s tests
   for f in installer/*.sh; do bash -n "$f"; done
   ```

3. Update `VERSION` and `CHANGELOG.md`.
4. Commit the change.
5. Create a Git tag matching the version:

   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin main v0.1.0
   ```

6. Create a GitHub release from the tag.

## When to bump which number?

While the project is below `1.0.0`:

- Bump `PATCH` for bug fixes and documentation clarifications.
- Bump `MINOR` for new commands, options, or deployment features.
- Bump to `1.0.0` once the CLI and operator workflow feel stable.

After `1.0.0`:

- Bump `MAJOR` for breaking changes.
- Bump `MINOR` for backwards-compatible features.
- Bump `PATCH` for backwards-compatible fixes.
