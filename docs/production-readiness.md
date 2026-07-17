# Production readiness

`v1.0.0` is the first stable release line for the documented single-server Docker lifecycle-manager scope. The immutable release tag passed the documented install, update, recovery, browser, failure-mode, and no-lock-in validation scenarios.

Production readiness here applies only to the public support matrix and explicitly validated manager release/component pairs. It is not a claim that every operating system, topology, proxy, customization, or future MISP component set is supported.

## Current stable-release status

| Area | Status |
| --- | --- |
| Latest manager release | `v1.0.0` |
| Latest validated MISP component set | core `v2.5.44`, modules `v3.0.9`, guard `v1.2` |
| Compatibility status | ✅ `v1.0.0` validated compatible |
| Public compatibility evidence | ✅ [`compatibility.md`](compatibility.md) and [`validation/matrix.md`](validation/matrix.md) |
| Public support scope | ✅ [`support-matrix.md`](support-matrix.md) |
| Production deployment guide | ✅ [`production-deployment.md`](production-deployment.md) |
| Security model | ✅ [`security.md`](security.md) |
| Backup, restore, and rollback | ✅ documented and release-tag validated |
| Browser-facing login | ✅ release-tag validated |
| No-lock-in Compose operation | ✅ release-tag validated |
| Monitoring contract on `main` | ✅ contract/parser and real-deployment producer validation; native platform ingestion remains unvalidated |

## Development line after `v1.0.0`

`main` contains work added after the `v1.0.0` tag. That work is not retroactively part of the stable release artifact.

The monitoring healthcheck is implemented on `main`, contract/parser tested, and exercised against a managed MISP deployment in healthy, UNKNOWN, controlled-CRITICAL, and recovery states. Native ingestion by running Zabbix, Checkmk, Nagios/Icinga, and Prometheus systems remains unvalidated. See [Monitoring](monitoring.md) and the [community testing issue](https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager/issues/62).

A later tagged release must include and validate development-line runtime changes before they become part of the stable release line.

## `v1.0.0` validation coverage

The exact `v1.0.0` tag was validated for:

- direct fresh install;
- reverse-proxy fresh install;
- install/update path with explicit official MISP component tags;
- backup creation;
- restore from backup into a clean deployment scope;
- reset dry-run safety;
- restore-based rollback after a controlled failed update;
- browser-facing login flow;
- failure-mode guardrails;
- no-lock-in/manual Docker Compose usability;
- the official MISP Docker component sets recorded in the compatibility matrix.

See the [validation matrix](validation/matrix.md) for the exact evidence links and limitations.

## Ongoing release gates

Every future release that changes runtime behavior should:

1. keep support and non-goals explicit;
2. validate the immutable release tag rather than only `main`;
3. record the exact official MISP Docker component set;
4. exercise affected install, update, recovery, browser, monitoring, and failure paths;
5. publish a sanitized validation report;
6. avoid extending compatibility claims to untested future component sets.

## What this project does not claim

The current stable line does not claim:

- broad operating-system support beyond the documented validation environment;
- high-availability or multi-node deployment support;
- Kubernetes support;
- support for custom MISP images or forks;
- compatibility with future upstream MISP component sets before validation completes;
- native certification by external monitoring products.

## Evidence policy

Public production-readiness evidence includes:

- manager release/ref;
- official MISP Docker component versions;
- validation date;
- scenario list;
- pass/fail result;
- limitations.

Public evidence must not include private hostnames, private IP addresses, VM identifiers, topology, raw logs, credentials, or private repository paths.

## What to read next

- Return to the [documentation map](README.md).
- Review the public support scope in [Support matrix](support-matrix.md).
- Plan deployment with [Production deployment guide](production-deployment.md).
- Review compatibility evidence in [Compatibility](compatibility.md).
- Review exact validation coverage in [Validation matrix](validation/matrix.md).
