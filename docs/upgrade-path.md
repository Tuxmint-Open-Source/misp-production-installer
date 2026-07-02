# Upgrade Path

Use official upstream refs as the upgrade unit.

```bash
./installer/update.sh --install-dir /opt/misp-docker --upstream-ref <tag-or-commit>
```

The update workflow: backup, fetch official upstream, checkout ref, re-render override, validate Compose, pull/start containers, run doctor checks.
