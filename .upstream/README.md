# Upstream monitoring

This repository tracks selected public inputs from the official `MISP/misp-docker` repository.

The goal is not to mirror upstream. The goal is to make lifecycle-sensitive drift visible and reviewable before manager assumptions become stale, without opening review PRs for unrelated upstream commits.

## What is monitored

The scheduled monitor records the upstream commit as comparison context. Commit movement by itself is not drift.

High-signal public inputs include:

```text
template.env
docker-compose.yml
core/files/entrypoint.sh
core/files/entrypoint_nginx.sh
core/files/configure_misp.sh
core/files/utilities.sh
core/files/etc/misp-docker/**
core/files/etc/supervisor/**
core/files/etc/nginx/**
guard/files/**
```

It extracts and records:

- SHA-256 hashes of direct runtime/configuration files and relevant public configuration trees;
- `CORE_TAG`, `MODULES_TAG`, and `GUARD_TAG`;
- `CORE_RUNNING_TAG`, `MODULES_RUNNING_TAG`, and `GUARD_RUNNING_TAG` active defaults;
- active and commented `template.env` key names, never values;
- Compose service names, all image expressions, complete service-block fingerprints, and interpolation-variable names;
- independent hashes for selected upstream README sections covering installation, configuration, optional guard, authentication, production, SELinux/root-CA handling, database backup/restore, troubleshooting, and versioning.

The watcher deliberately does not track Kubernetes/Helm or experimental Podman details because this project supports the documented single-server Docker Compose scope.

## Review classes

Generated reports suggest review classes but never infer compatibility:

```text
A = component or runtime image tag defaults
B = Compose/runtime/configuration/readiness/process behavior
C = template environment inventory or selected operator guidance
```

Reports include structured additions/removals for Compose services, interpolation variables, and template key names. Hashes and extracted facts identify review surfaces; maintainers must still inspect the upstream compare diff.

## Baseline

The current reviewed upstream state is stored in:

```text
.upstream/misp-docker.lock.json
```

This file is intentionally committed. It is the review baseline used by the scheduled workflow. It contains public upstream facts only and excludes environment values.

## Reports

When relevant upstream drift is detected, the workflow writes a public-safe review report to:

```text
.upstream/reports/misp-docker-upstream-review.md
```

The report is used as the pull-request body. It contains a review checklist but no private infrastructure details. A report is a review prompt, not compatibility proof.

## Scheduled workflow

The workflow runs daily and can also be started manually:

```text
.github/workflows/upstream-misp-docker-watch.yml
```

It uses a single concurrency group and bounded job timeouts. A read-only collector job executes the focused watcher/publication tests and collects anonymous public upstream state into a short-lived artifact. Only a guarded second job on the canonical `main` branch receives the narrowly scoped permissions needed to publish a review PR.

The publisher does not trust the transferred files merely because the collector created them. It requires exactly the fixed lock/report pair, validates their size and schema, recomputes lifecycle-sensitive drift against the committed baseline, and requires the report to match the locally rendered result before writing the two allowlisted repository paths.

If no relevant upstream drift is detected, no PR is opened.

If relevant upstream drift is detected, the workflow opens or updates a PR with:

```text
.upstream/misp-docker.lock.json
.upstream/reports/misp-docker-upstream-review.md
```

A maintainer then reviews whether manager code, documentation, or compatibility validation needs follow-up.

## Compatibility boundary

The governing model remains:

```text
manager release/ref × official MISP Docker component set = validation status
```

Neither an upstream commit, a watcher report, nor a merged lock update establishes compatibility. The exact documented validation scenarios must pass before a pair is marked **validated compatible**.

## Manual checks

Run a local check without changing files:

```bash
python3 scripts/check-upstream-misp-docker.py
```

Update the baseline/report locally:

```bash
python3 scripts/check-upstream-misp-docker.py --write
```

Fail when lifecycle-sensitive drift is detected:

```bash
python3 scripts/check-upstream-misp-docker.py --check
```

Run the focused parser and publication-boundary contract tests:

```bash
python3 -m unittest tests.test_upstream_watcher tests.test_upstream_publication
```
