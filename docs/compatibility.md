# Compatibility with official MISP Docker components

`misp-production-installer` is a lifecycle wrapper around the official [`MISP/misp-docker`](https://github.com/MISP/misp-docker) project.

It does **not** fork, vendor, or replace MISP. The generated deployment remains a normal official MISP Docker checkout with installer-managed configuration and lifecycle helpers.

Because this project and official MISP Docker can change independently, compatibility is tracked as a pair:

```text
misp-production-installer release/ref × official MISP Docker component set = validation status
```

A pair is called **validated compatible** only after the documented validation scenarios pass.

## Latest compatibility status

| Installer release/ref | MISP core | MISP modules | MISP guard | Status | Validated | Report |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `v0.3.3` release candidate | `v2.5.43` | `v3.0.8` | `v1.2` | 🟡 Release/tag validation pending | pending | [`compatibility-v0.3.3-misp-core-v2.5.43.md`](validation/compatibility-v0.3.3-misp-core-v2.5.43.md) |
| current `main` at PR #22 validation time | `v2.5.43` | `v3.0.8` | `v1.2` | ✅ Validated compatible | 2026-07-11 | [`compatibility-v0.3.3-misp-core-v2.5.43.md`](validation/compatibility-v0.3.3-misp-core-v2.5.43.md) |
| `v0.3.2` release tag | `v2.5.43` | `v3.0.8` | `v1.2` | ❌ Validation failed | 2026-07-12 | [`compatibility-v0.3.3-misp-core-v2.5.43.md`](validation/compatibility-v0.3.3-misp-core-v2.5.43.md) |
| `v0.3.1` release | `v2.5.42` | `v3.0.8` | `v1.2` | ⚪ Superseded historical validation | 2026-07-08 | [`real-world-v0.3.1.md`](validation/real-world-v0.3.1.md) |

> [!IMPORTANT]
> The `v0.3.3` release candidate is prepared from the `main` line that passed compatibility validation with MISP core `v2.5.43`. It should be marked **validated compatible** only after the final `v0.3.3` release tag is created and the same compatibility validation passes against that immutable tag.
>
> The `v0.3.2` release tag is **not** marked validated compatible with MISP core `v2.5.43`. Validation exposed the known first-login readiness race that was fixed later on `main`.

## Status definitions

| Status | Meaning |
| --- | --- |
| ✅ Validated compatible | The listed installer release/ref and official MISP component set passed the documented scenarios. |
| 🟡 Pending validation | A new installer release or upstream MISP component set exists, but the combination has not completed validation. |
| ❌ Validation failed | The combination was tested and did not pass the documented scenarios; see linked notes or issues. |
| ⚪ Superseded | Historical validated evidence that remains useful but is not the newest recommended combination. |

## When compatibility must be revalidated

Compatibility validation is required whenever either side changes:

1. This project publishes a new installer release.
2. Official MISP Docker changes inputs that affect this installer, including:
   - `CORE_TAG`, `MODULES_TAG`, or `GUARD_TAG`
   - `template.env`
   - `docker-compose.yml`
   - image expressions
   - service names
   - required/default environment variables
   - startup, migration, health, or readiness behavior

The scheduled upstream drift workflow detects many of these upstream changes and opens an upstream-review PR. That PR is a **review prompt**, not compatibility proof by itself.

## Full compatibility scenario coverage

A full compatibility entry should cover at least:

| Scenario | Purpose |
| --- | --- |
| Direct-QA fresh install | Proves a clean install path works with the component set. |
| Reverse-proxy fresh install | Proves the reverse-proxy deployment shape works with the component set. |
| Install/update path | Proves explicit component tags and update logic work together. |
| Backup/reset/no-lock-in lifecycle smoke | Proves day-2 lifecycle helpers and upstream Docker Compose usability. |
| Failure-mode guardrail smoke | Proves key safety checks fail closed before writing deployment state. |

Browser automation may be recorded separately. If a compatibility run uses CLI login checks but not browser automation, the detailed report says so explicitly.

## Public-safety policy

Public compatibility reports intentionally omit:

- private hostnames and domains
- private IP addresses
- VM IDs
- raw logs
- credentials or generated secrets
- internal topology or access paths
- private repository URLs or local filesystem paths

The public report should show what was validated and what passed, while private raw evidence stays out of the GitHub repository.
