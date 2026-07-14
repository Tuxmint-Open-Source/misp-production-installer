# Architecture

This repository is a lifecycle manager for official MISP Docker deployments. It does not vendor MISP or the official Docker packaging.

```mermaid
flowchart TB
    operator[Operator]
    manager[misp-docker-lifecycle-manager]
    upstream[MISP/misp-docker official upstream]
    source[MISP/MISP source optional future mode]
    installDir[Install directory]
    env[Generated .env]
    override[Generated docker-compose.override.yml]
    compose[Docker Compose]
    misp[MISP stack]
    operator --> manager --> upstream --> installDir --> compose --> misp
    manager -. future source-build mode .-> source
    manager --> env --> compose
    manager --> override --> compose
```

Rule: keep upstream clean. Use `.env`, `docker-compose.override.yml`, scripts, and documented version-gated patches only when no overlay mechanism exists.

## What to read next

- Start at the [documentation map](README.md) if you need the full reader path.
- Check the supported deployment shape in [Support matrix](support-matrix.md).
- Follow the normal lifecycle in [Operator guide](operator-guide.md).
