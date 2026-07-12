# Validation and compatibility matrix

This matrix summarizes public-safe compatibility and validation coverage.

It is not a guarantee that every environment or component combination works. It records the installer/MISP component combinations that were actually exercised and the scenarios that passed or failed.

## Compatibility combinations

| Installer release/ref | MISP core | MISP modules | MISP guard | Compatibility status | Fresh install | Reverse proxy | Update path | Lifecycle smoke | Guardrails | Report |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| `v1.0.0-rc.1` release candidate | `v2.5.43` | `v3.0.8` | `v1.2` | 🟡 Pending exact-tag validation | pending | pending | pending | pending | pending | pending release-candidate validation |
| `v0.3.3` release tag | `v2.5.43` | `v3.0.8` | `v1.2` | ✅ Validated compatible | ✅ | ✅ | ✅ | ✅ | ✅ | [`compatibility-v0.3.3-misp-core-v2.5.43.md`](compatibility-v0.3.3-misp-core-v2.5.43.md) |
| current `main` at PR #22 validation time | `v2.5.43` | `v3.0.8` | `v1.2` | ✅ Validated compatible | ✅ | ✅ | ✅ | ✅ | ✅ | [`compatibility-v0.3.3-misp-core-v2.5.43.md`](compatibility-v0.3.3-misp-core-v2.5.43.md) |
| `v0.3.2` release tag | `v2.5.43` | `v3.0.8` | `v1.2` | ❌ Validation failed | ❌ | ❌ | ❌ | ❌ | ✅ | [`compatibility-v0.3.3-misp-core-v2.5.43.md`](compatibility-v0.3.3-misp-core-v2.5.43.md) |
| `v0.3.1` release | `v2.5.42` | `v3.0.8` | `v1.2` | ⚪ Superseded historical validation | ✅ | — | ✅ | — | — | [`real-world-v0.3.1.md`](real-world-v0.3.1.md) |

## Status legend

| Status | Meaning |
| --- | --- |
| ✅ Validated compatible | The listed installer release/ref and official MISP component set passed the documented scenarios. |
| 🟡 Pending validation | A new installer release or upstream MISP component set exists, but the combination has not completed validation. |
| ❌ Validation failed | The combination was tested and did not pass the documented scenarios; see the detailed report. |
| ⚪ Superseded | Historical validated evidence that remains useful but is not the newest recommended combination. |

## Scenario legend

- **Fresh install**: clean install with explicit official MISP component tags.
- **Reverse proxy**: reverse-proxy deployment shape was exercised with the documented fixture.
- **Update path**: `update.sh` was exercised after an explicit component-tag install.
- **Lifecycle smoke**: backup, reset dry-run, and generated upstream Docker Compose usability were exercised.
- **Guardrails**: an intentionally invalid install command failed safely before rendering deployment state.

## Detailed reports

- [`compatibility-v0.3.3-misp-core-v2.5.43.md`](compatibility-v0.3.3-misp-core-v2.5.43.md)
- [`real-world-v0.3.1.md`](real-world-v0.3.1.md)
