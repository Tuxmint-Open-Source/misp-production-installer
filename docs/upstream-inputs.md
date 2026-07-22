# Immutable upstream Git and container input policy

This policy defines how MISP Docker Lifecycle Manager treats upstream Git references, official MISP component tags, runtime container image tags, and future digest/lock metadata.

It preserves the core project boundary: this repository is a lifecycle wrapper around official `MISP/misp-docker`. It does not fork, vendor, or rewrite upstream source trees, and this policy does not claim compatibility with a new upstream component set by itself.

## Input classes

| Class | Examples | Purpose | Compatibility meaning |
| --- | --- | --- | --- |
| Discovery reference | official `MISP/misp-docker` default branch such as `master` | Find current upstream packaging and component defaults | Review prompt only; not immutable evidence |
| Development reference | a PR branch, local branch, or explicit `HEAD` dry run | Test unreleased manager or workflow behavior | Capability evidence only |
| Release identity | manager SemVer tag such as `v1.2.0` | Install, support, and release-audit identity | Can become validated compatible only after exact-tag validation |
| Upstream Git identity | official upstream commit SHA selected by `--upstream-ref` or observed by the watcher | Reproduce the upstream packaging tree used for install/update review | Part of review evidence; not a component compatibility claim by itself |
| Component identity | official MISP core/modules/guard tags such as `v2.5.44`, `v3.0.9`, and `v1.2` | Select runtime MISP component images and compatibility tuples | Compatibility status is tied to the exact manager ref plus these component tags |
| Container image digest | OCI digest for a concrete image manifest | Strongest image-content identity when adopted | Deferred until digest discovery, storage, and operator verification are designed |

## Policy rules

1. Public compatibility claims must identify an exact manager release/ref and official MISP Docker component set.
2. Mutable upstream branches are allowed for discovery and normal update workflows, but they must not be presented as immutable compatibility evidence.
3. Release compatibility claims use the immutable manager tag, not only `main`, a release branch, or a PR branch.
4. The upstream watcher may track the official `MISP/misp-docker` default branch as a review source, but a watcher PR is a review prompt, not proof of compatibility.
5. Component tag changes, Compose behavior changes, or lifecycle-sensitive upstream file changes trigger review and may require validation before public compatibility docs change.
6. Explicit component-tag overrides are allowed only for tags published by the official upstream projects. Custom images or forks are outside the public support claim unless separately documented and validated.
7. Runtime `latest` image tracking is a convenience mode for operators who intentionally accept mutability. It is not the default production recommendation and cannot support a validated-compatible claim.
8. Machine-readable channel metadata such as `.release-channels.json` identifies manager release channels only; it does not replace immutable SemVer tags or compatibility reports.

## Operator guidance

For conservative production operation:

- install the manager from an immutable SemVer tag or validated operator bundle;
- keep `--image-track version-tags` unless you deliberately want moving `latest` images;
- record the upstream Git commit before an update;
- record selected component tags before an update;
- use compatibility reports to select a manager/component tuple that has passed validation.

Useful read-only records before changing a deployment:

```bash
git -C /opt/misp-docker rev-parse HEAD
grep -E '^(CORE|MODULES|GUARD)(_RUNNING)?_TAG=' /opt/misp-docker/.env
./installer/get-current-misp-versions.sh --install-dir /opt/misp-docker
```

## Upstream watcher responsibilities

The upstream watcher records public facts that can affect lifecycle behavior:

- the official upstream commit as comparison context;
- selected lifecycle-sensitive file and tree hashes;
- Compose service, image-expression, and interpolation-key inventories;
- `template.env` key inventory and component tag defaults;
- separately collected official component release tags.

The watcher must not create a compatibility claim. When it detects drift, maintainers decide whether to update assumptions, change docs or code, or run compatibility validation for a deliberately supported exact component set.

## Machine-readable metadata

Current metadata:

- `.release-channels.json` records `latest_published` and `latest_validated` manager tags.
- `.upstream/misp-docker.lock.json` records public upstream facts for review.
- Compatibility reports record the exact manager release/ref and component set that passed validation.

Future metadata may add immutable upstream commit or OCI digest fields only when the project also documents how operators can obtain, compare, and verify those identities without weakening the no-fork/no-vendor model.

## Deferred digest policy

OCI image digests provide stronger image identity than tags, but the project does not yet claim digest-pinned operation as a supported release guarantee.

Adopting digest-pinned images requires a separate implementation decision that covers:

- how official image digests are discovered and stored;
- how multi-architecture manifests are represented;
- how Compose overrides should express tags plus digests;
- how operators verify local pulled images;
- how digest changes interact with upstream drift review and compatibility validation;
- how rollback and restore procedures record image identities.

Until then, validated compatibility is expressed through official component tags plus the exact manager release/ref and validation report.

## Out of scope

This policy does not:

- vendor or fork `MISP/misp-docker`;
- claim compatibility with unvalidated future component tags;
- certify custom images, private registries, or downstream forks;
- replace the release integrity policy for manager artifacts.

## What to read next

- Review manager release integrity in [Release integrity and provenance policy](release/integrity-and-provenance.md).
- Review update behavior in [Upgrade path](upgrade-path.md).
- Review compatibility status in [Compatibility](compatibility.md).
