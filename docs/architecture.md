# Architecture

This repository is an installer/overlay project. It does not vendor MISP or the official Docker packaging.

```mermaid
flowchart TB
    operator[Operator]
    installer[misp-production-installer]
    upstream[MISP/misp-docker official upstream]
    source[MISP/MISP source optional future mode]
    installDir[Install directory]
    env[Generated .env]
    override[Generated docker-compose.override.yml]
    compose[Docker Compose]
    misp[MISP stack]
    operator --> installer --> upstream --> installDir --> compose --> misp
    installer -. future source-build mode .-> source
    installer --> env --> compose
    installer --> override --> compose
```

Rule: keep upstream clean. Use `.env`, `docker-compose.override.yml`, scripts, and documented version-gated patches only when no overlay mechanism exists.
