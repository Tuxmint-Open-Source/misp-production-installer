<!-- Thank you for contributing to MISP Docker Lifecycle Manager. Keep all public text sanitized. -->

## Summary

<!-- What changed and why? -->

## Type of change

- [ ] Documentation only
- [ ] Bug fix
- [ ] New feature or option
- [ ] Security hardening
- [ ] Validation / compatibility evidence
- [ ] Maintenance / CI / repository process

## Public-safety checklist

- [ ] I did not include secrets, tokens, private keys, generated passwords, or `.env` contents.
- [ ] I did not include private hostnames, internal domains, private IPs, VM IDs, topology, or access paths.
- [ ] I did not include raw logs, database dumps, backup contents, or generated configuration archives.
- [ ] Examples use sanitized values such as `misp.example.com`, `admin@example.com`, `/opt/misp-docker`, and `[REDACTED]`.

## Validation

- [ ] `python3 -m unittest discover -s tests`
- [ ] `for f in lifecycle/*.sh installer/*.sh; do bash -n "$f"; done`
- [ ] `python3 -m py_compile scripts/*.py tests/*.py`
- [ ] `git diff --check`
- [ ] Public marker scan over the diff
- [ ] Not applicable / explained below

## Runtime impact

- [ ] No runtime behavior changes
- [ ] Install/update behavior changed
- [ ] Backup/restore/rollback/reset behavior changed
- [ ] Login/browser-facing behavior changed
- [ ] Generated configuration changed

If runtime behavior changed, describe the validation performed:

<!-- public-safe validation summary -->

## Compatibility impact

- [ ] No compatibility-status change
- [ ] Compatibility docs updated
- [ ] Exact-tag validation required before marking validated compatible
- [ ] Exact-tag validation completed and linked in public-safe docs

## Notes for reviewers

<!-- Anything specific reviewers should focus on? -->
