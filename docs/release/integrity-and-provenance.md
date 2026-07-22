# Release integrity and provenance policy

This policy defines what operators can verify for MISP Docker Lifecycle Manager releases and what the project intentionally defers until sustainable controls exist.

It applies to release tags, GitHub Releases, generated operator-bundle assets, release documentation, and compatibility claims. It does not replace validation: a release artifact is considered validated compatible only when the documented manager release/ref and official MISP Docker component set pass the compatibility matrix.

## Threat model

| Control | Protects against | Does not protect against |
| --- | --- | --- |
| Immutable SemVer Git tags | Accidental installation from a moving branch or ambiguous source ref | A compromised maintainer account or unsigned tag forgery |
| GitHub Release assets attached to the same tag | Downloading the wrong artifact for a release | A compromised GitHub release channel |
| Companion SHA-256 files | Transfer corruption, truncated downloads, or accidental asset mismatch | Malicious replacement when the checksum is replaced too |
| Deterministic operator-bundle builds | Undetected local packaging drift and non-reproducible archive bytes | Compromise of the source commit before review |
| Read-only build/verify job before release upload | Accidental publication of unverified bundle output | All supply-chain risks in GitHub-hosted infrastructure |
| Exact-tag compatibility reports | Unsupported compatibility claims for unvalidated release/component pairs | Future upstream component changes or untested local customizations |

## Release identity

Every normal release uses an immutable SemVer tag such as `v1.2.0`. Operators should install, verify, and report that exact tag. The project intentionally does not create moving Git tags named `stable` or `latest`.

GitHub's Latest Release marker describes publication recency only. Compatibility evidence is tracked separately through `.release-channels.json`, the compatibility matrix, and detailed validation reports.

## Current minimum controls

Every release must provide these controls before it is presented as a normal release:

1. a reviewed release PR that updates `VERSION`, `CHANGELOG.md`, release-facing docs, and tests;
2. an immutable SemVer Git tag created after the release PR merges;
3. a GitHub Release attached to that exact tag;
4. public release notes that distinguish validation already completed from validation still pending;
5. repository gates on the release PR and merge commit;
6. no mutable `stable` or `latest` Git aliases.

Releases that publish an operator bundle must also provide:

1. a deterministic archive built from the selected Git tag;
2. `OPERATOR-BUNDLE-MANIFEST.json` inside the archive, recording the source ref, source commit, and per-file SHA-256 digests;
3. a companion `.sha256` file uploaded to the same GitHub Release;
4. build/verify in a read-only workflow job before upload;
5. checksum verification before installation in user-facing instructions;
6. exact-tag and packaged-artifact lifecycle validation before the bundle is recommended for the documented production scope.

## Operator verification steps

For source-checkout installations:

```bash
git clone https://github.com/Tuxmint-Open-Source/misp-docker-lifecycle-manager.git
cd misp-docker-lifecycle-manager
git fetch --tags origin
git checkout vX.Y.Z
git rev-parse HEAD
./installer/install.sh --version
```

Compare the checked-out tag and reported version with the selected release and compatibility report.

For operator-bundle installations, download the archive and its checksum from the same GitHub Release, then verify before extraction:

```bash
sha256sum --check misp-docker-lifecycle-manager-vX.Y.Z.tar.gz.sha256
tar -tzf misp-docker-lifecycle-manager-vX.Y.Z.tar.gz | sed -n '1,20p'
```

Do not pipe downloaded release assets directly into a shell. Extract into a reviewed directory and run lifecycle commands explicitly.

## Adopt/defer decisions

| Mechanism | Current decision | Rationale |
| --- | --- | --- |
| SHA-256 companion files for generated release assets | Adopted | Low-friction corruption and mismatch detection; already enforced for operator bundles. |
| Immutable SemVer release tags | Adopted | Required for reproducible installation, support, and validation evidence. |
| Deterministic operator-bundle build manifests | Adopted | Lets operators and maintainers tie an archive back to a reviewed source commit and runtime allowlist. |
| Signed Git tags | Deferred | Useful, but the project must first document key identity, rotation, loss, and verification support before making signing a release guarantee. |
| Signed release assets | Deferred | Same identity and rotation requirements as signed tags; checksum files remain the current minimum. |
| SBOMs | Deferred | The manager bundle is mostly shell/Python source and documentation; an SBOM format and operator value need a separate design before adoption. |
| Build provenance or attestations | Deferred | Valuable for larger supply-chain programs, but requires a sustainable issuer, verification workflow, and failure policy. |
| OCI image digests for upstream MISP containers | Deferred to the upstream-input policy | Container input pinning belongs with the immutable upstream Git and container input policy tracked separately. |

Deferred means not implemented and not claimed. Future PRs may adopt a deferred mechanism only when user-facing verification instructions, key/identity handling, CI permissions, and failure behavior are documented and tested.

## CI and permission expectations

Release automation should use least privilege:

- build and verification jobs use read-only repository contents permission;
- upload/publish jobs request write permission only when needed;
- artifacts transferred from read-only jobs to write-capable jobs are short-lived and re-verified before upload;
- action references remain pinned to immutable commits;
- release upload commands name the target repository explicitly.

The release process must not use release-write credentials for anonymous upstream collection, untrusted parsing, or pull-request code execution.

## Compatibility boundary

Integrity controls identify what artifact an operator has. They do not prove compatibility by themselves.

Compatibility claims must name the exact tuple:

```text
manager release/ref × official MISP Docker component set = validation status
```

A checksum-verified artifact is only described as validated compatible after the documented lifecycle matrix passes for that exact manager release/ref and component set.

## Future changes

Changing this policy is release-relevant work. A PR that adopts signing, SBOMs, provenance, or attestations must update this policy, release instructions, operator verification steps, and tests in the same change or in a clearly linked sequence.
