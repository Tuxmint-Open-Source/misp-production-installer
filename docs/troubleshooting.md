# Troubleshooting

## Cannot log in to the MISP Web UI

First verify which administrator account the installer generated:

```bash
./installer/admin-credentials.sh --install-dir /opt/misp-docker
```

The password is hidden by default. To print it on a trusted terminal:

```bash
./installer/admin-credentials.sh --install-dir /opt/misp-docker --show-password
```

Then run the normal deployment checks:

```bash
./installer/doctor.sh --install-dir /opt/misp-docker
```

You can also test the Web UI login flow from the server without printing the
password:

```bash
./installer/login-check.sh --install-dir /opt/misp-docker
```

If the credentials are correct but login still fails:

1. Confirm the browser uses the same URL as `BASE_URL` in `.env`.
2. Wait for `doctor.sh` to complete successfully; MISP may need database updates
   after the first container start.
3. Check that the login page is not cached from a previous failed deployment.
4. Rotate the admin password inside MISP after the first successful login.

Do not paste real passwords into public issues or Pull Requests. If you need to
share troubleshooting output, redact the password and use generic hostnames.

## Docker Compose output is noisy

The official upstream Compose file references many optional variables for SMTP,
OIDC, LDAP, S3, proxying, and build-time tuning. Docker Compose warns when those
optional variables are not set, even though it then defaults them to blank.

The installer wrapper sets missing optional Compose variables to empty values
only for the `docker compose` process. This keeps `.env` readable and makes
commands such as `status.sh`, `doctor.sh`, and `update.sh` much quieter.

## CSRF error after login

Verify Redis-backed PHP sessions. `REDIS_PASSWORD` must be URL-safe because PHP receives it in a Redis session save path. This installer generates it as 64-character hex.

## Healthcheck fails but public URL works

Healthchecks use container-local `https://localhost/users/heartbeat`, not public DNS or reverse proxy paths.

## Backup permission errors

The backup script uses `sudo tar` because MISP containers can create root-owned files in bind mounts.
