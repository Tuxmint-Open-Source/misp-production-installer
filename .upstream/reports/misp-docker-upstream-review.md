# Upstream MISP Docker review

> Historical disposition: reviewed. The component set below was subsequently validated with the immutable `v1.0.0` lifecycle-manager release; see [`docs/compatibility.md`](../../docs/compatibility.md) and the linked detailed reports. This retained report is evidence of the prior review prompt, not a current pending review.

This report is a review prompt, not compatibility proof.

The scheduled upstream monitor detected changes in official `MISP/misp-docker` inputs that this installer depends on.

## Upstream

- Repository: `https://github.com/MISP/misp-docker.git`
- Ref: `master`
- Previous reviewed commit: `8d226f7e89d3f8efa7ef44ee473c410bc3cdb17f`
- Current commit: `223b675c4480730832f928e113b6f2e5260b450d`
- Compare: https://github.com/MISP/misp-docker/compare/8d226f7e89d3f8efa7ef44ee473c410bc3cdb17f...223b675c4480730832f928e113b6f2e5260b450d

## Detected changes

- Upstream commit changed: `8d226f7e89d3f8efa7ef44ee473c410bc3cdb17f` -> `223b675c4480730832f928e113b6f2e5260b450d`
- `component_tags` changed.
- Watched file changed: `template.env`

## Component tags

| Component | Previous | Current |
|---|---:|---:|
| `CORE_TAG` | `v2.5.43` | `v2.5.44` |
| `MODULES_TAG` | `v3.0.8` | `v3.0.9` |
| `GUARD_TAG` | `v1.2` | `v1.2` |

## Watched files

- `template.env`

## Review checklist

- [x] Checked upstream component tag changes.
- [x] Checked `docker-compose.yml` service assumptions used by lifecycle-manager scripts.
- [x] Checked MISP image expressions and runtime tag variables.
- [x] Checked changed environment-variable requirements represented by this historical report.
- [x] Checked health/readiness assumptions.
- [x] Decided whether lifecycle-manager code or documentation changes were needed.
- [x] Ran repository validation before merge.
- [x] Ran compatibility validation for the immutable `v1.0.0` manager release and official component set.
- [x] Updated `docs/compatibility.md` and matching detailed reports only after the scenarios passed.

## Compatibility note

This upstream-review report is a drift-detection prompt, not compatibility proof by itself. A listed component set becomes **validated compatible** only after the documented compatibility scenarios pass and the public compatibility docs are updated.

## Validation command

```bash
python3 scripts/check-upstream-misp-docker.py --check
```
