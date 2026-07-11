# Upstream MISP Docker review

## Summary

The scheduled upstream monitor detected changes in official `MISP/misp-docker` inputs that this installer depends on.

## Upstream

- Repository: `https://github.com/MISP/misp-docker.git`
- Ref: `master`
- Previous reviewed commit: `6d915d5921183cded7758dad19c8584edbcde642`
- Current commit: `8d226f7e89d3f8efa7ef44ee473c410bc3cdb17f`
- Compare: https://github.com/MISP/misp-docker/compare/6d915d5921183cded7758dad19c8584edbcde642...8d226f7e89d3f8efa7ef44ee473c410bc3cdb17f

## Detected changes

- Upstream commit changed: `6d915d5921183cded7758dad19c8584edbcde642` -> `8d226f7e89d3f8efa7ef44ee473c410bc3cdb17f`
- `component_tags` changed.
- Watched file changed: `template.env`

## Component tags

| Component | Previous | Current |
|---|---:|---:|
| `CORE_TAG` | `v2.5.42` | `v2.5.43` |
| `MODULES_TAG` | `v3.0.8` | `v3.0.8` |
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

## Validation command

```bash
python3 scripts/check-upstream-misp-docker.py --check
```
