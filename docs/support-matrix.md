# Support matrix

This page defines the public support scope of the stable release line. `v1.3.1` is the latest published and latest validated-compatible release.

Anything outside this matrix may still work, but it is not part of the validated support contract unless a later compatibility report says so explicitly.

## Supported stable scope

| Area | Supported scope | Notes |
| --- | --- | --- |
| Deployment model | single-server Docker | This project is not a clustered or high-availability orchestrator. |
| Upstream MISP source | official [`MISP/misp-docker`](https://github.com/MISP/misp-docker) | The manager does not fork, vendor, or rewrite MISP. |
| Installer host OS | Rocky Linux family | Broader OS support requires separate validation. |
| CPU architecture | x86_64 | Host preparation enforces this with the OS family unless an expert testing override is supplied; other architectures require separate validation. |
| Reverse proxy model | external reverse proxy in front of the local HTTPS endpoint | Caddy is the first validated fixture. |
| Direct-QA mode | validation and controlled QA only | Direct-QA is not the recommended long-term public exposure mode. |
| MISP component selection | official component tags from upstream or explicit official tags | Custom images/forks are not covered. |
| Lifecycle helpers | install, doctor, login check, healthcheck, anonymous SOS report, backup, restore, update, reset dry-run, restore-based rollback, no-lock-in Compose usage | Exact `v1.3.1` compatibility is validated for the component tuple listed in the compatibility matrix. |

## Explicit non-goals

The stable release does not claim support for:

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

## Support expectations

Community support is best effort and has no service-level agreement. Use public GitHub issues for sanitized bugs, questions, and feature requests. Use the private path in [`SECURITY.md`](../SECURITY.md) for suspected vulnerabilities or reports that cannot be explained safely in public.

Routine fixes target the current stable release and `main`; historical release candidates and pre-`v1.0.0` tags are not maintained release lines.

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

- Return to the [documentation map](README.md) and choose the user/operator path.
- Try the first install path in [Getting started](getting-started.md).
- Plan a real deployment with [Production deployment guide](production-deployment.md).
- Check validated component sets in [Compatibility](compatibility.md).
