# Upstream MISP Docker review

## Summary

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

- [ ] Check upstream component tag changes.
- [ ] Check `docker-compose.yml` service names used by installer scripts.
- [ ] Check MISP image expressions and runtime tag variables.
- [ ] Check new or changed required variables in `template.env`.
- [ ] Check health/readiness assumptions.
- [ ] Decide whether installer code changes are needed.
- [ ] Run repository validation before merge.
- [ ] Run compatibility validation for the affected manager release/ref and official MISP component set.
- [ ] Update `docs/compatibility.md` and the matching `docs/validation/compatibility-*.md` report before marking the combination validated compatible.

## Compatibility note

This upstream-review report is a drift-detection prompt, not compatibility proof by itself. A listed component set becomes **validated compatible** only after the documented compatibility scenarios pass and the public compatibility docs are updated.

## Validation command

```bash
python3 scripts/check-upstream-misp-docker.py --check
```
