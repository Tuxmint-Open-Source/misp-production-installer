# Operator bundle

The operator bundle contains the supported lifecycle commands without contributor tests, CI configuration, upstream-watch tooling, or historical validation material.

## Install

Download these two assets from the same immutable GitHub Release:

```text
misp-docker-lifecycle-manager-vX.Y.Z.tar.gz
misp-docker-lifecycle-manager-vX.Y.Z.tar.gz.sha256
```

Verify before extraction:

```bash
sha256sum --check misp-docker-lifecycle-manager-vX.Y.Z.tar.gz.sha256
tar -tzf misp-docker-lifecycle-manager-vX.Y.Z.tar.gz | sed -n '1,20p'
sudo mkdir -p /opt/misp-docker-lifecycle-manager/releases
sudo tar -xzf misp-docker-lifecycle-manager-vX.Y.Z.tar.gz \
  -C /opt/misp-docker-lifecycle-manager/releases
sudo ln -sfn \
  /opt/misp-docker-lifecycle-manager/releases/misp-docker-lifecycle-manager-vX.Y.Z \
  /opt/misp-docker-lifecycle-manager/current
```

Download the archive and checksum from the same GitHub Release. Do **not** pipe downloaded release assets directly into a shell. See the [release integrity and provenance policy](release/integrity-and-provenance.md) for the current checksum, signing, SBOM, and provenance decisions.

Run lifecycle commands from the stable path:

```bash
sudo /opt/misp-docker-lifecycle-manager/current/lifecycle/doctor.sh \
  --install-dir /opt/misp-docker
```

## Upgrade and rollback

Install each verified bundle into its own versioned directory. Change the `current` symlink only after extraction and inspection. Roll back the manager by pointing `current` to the previous versioned directory.

Manager rollback does not roll back MISP data, configuration, images, or the official upstream checkout. Use the documented backup and restore workflow for deployment rollback.

## No lock-in

The manager is installed separately from the official `MISP/misp-docker` checkout. Removing the manager bundle removes its supported lifecycle commands but does not stop or rewrite the deployed Compose application. The deployment remains operable through official upstream Docker Compose workflows.

The full source checkout remains the contributor and development path. For supported operator installs, use the immutable release tag or the checksummed operator bundle from the same GitHub Release after that release has passed exact-tag and packaged-artifact validation. The `v1.3.0` bundle has passed that validation for the documented component tuple. Pull requests and workflow dry runs only build and verify bundle assets without uploading them.

## What to read next

- Return to the [documentation map](README.md) and choose the user/operator path.
- Review release artifact controls in [Release integrity and provenance policy](release/integrity-and-provenance.md).
- Follow the normal lifecycle in [Operator guide](operator-guide.md).
