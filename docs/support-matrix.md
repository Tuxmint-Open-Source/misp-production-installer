# Support matrix

This page defines the public support scope intended for the first production-ready major release.

Anything outside this matrix may still work, but it is not part of the validated support contract unless a later compatibility report says so explicitly.

## Intended `v1.0.0` support scope

| Area | Supported for `v1.0.0` | Notes |
| --- | --- | --- |
| Deployment model | single-server Docker | This project is not a clustered or high-availability orchestrator. |
| Upstream MISP source | official [`MISP/misp-docker`](https://github.com/MISP/misp-docker) | The manager does not fork, vendor, or rewrite MISP. |
| Installer host OS | Rocky Linux family | Broader OS support requires separate validation. |
| CPU architecture | x86_64 | Other architectures require separate validation. |
| Reverse proxy model | external reverse proxy in front of the local HTTPS endpoint | Caddy is the first validated fixture. |
| Direct-QA mode | validation and controlled QA only | Direct-QA is not the recommended long-term public exposure mode. |
| MISP component selection | official component tags from upstream or explicit official tags | Custom images/forks are not covered. |
| Lifecycle helpers | install, doctor, login check, backup, restore, update, reset dry-run, restore-based rollback, no-lock-in Compose usage | Final `v1.0.0` still requires exact release-tag validation before production claims. |

## Explicit non-goals for `v1.0.0`

The first major release should not imply support for:

- Kubernetes
- multi-node or high-availability MISP clusters
- managed database services
- custom MISP images or forks
- custom MISP plugin stacks beyond upstream defaults
- offline installation
- broad Linux distribution coverage beyond the validated host OS family
- automatic DNS management
- automatic certificate issuance for every reverse-proxy environment
- long-term monitoring/alerting stack management

## Compatibility is still versioned separately

Supported deployment scope and MISP component compatibility are separate questions.

Compatibility is tracked as:

```text
misp-docker-lifecycle-manager release/ref × official MISP Docker component set = validation status
```

See [`compatibility.md`](compatibility.md) for the current validated combinations.

## How support expands

Support can expand only when both are true:

1. The public docs describe the new scope clearly.
2. A public-safe validation report records the relevant scenario coverage.

Examples:

- Nginx reverse-proxy support should be added only after an Nginx fixture is validated.
- Another Linux distribution should be listed only after fresh install/update validation passes on that distribution.
- Restore support for a final release should be listed as release-tag validated only after a restore drill passes for that exact release tag.

## What to read next

- Return to the [documentation map](README.md).
- Try the first install path in [Getting started](getting-started.md).
- Plan a real deployment with [Production deployment guide](production-deployment.md).
- Check validated component sets in [Compatibility](compatibility.md).
