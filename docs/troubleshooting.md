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
password. On successful login, the script also performs a best-effort logout.
The default output is written for human operators:

```bash
./installer/login-check.sh --install-dir /opt/misp-docker
```

For automation, monitoring, or AI-agent diagnostics, use stable key/value output:

```bash
./installer/login-check.sh --install-dir /opt/misp-docker --machine-readable
```

If the credentials are correct but login still fails:

1. Confirm the browser uses the same URL as `BASE_URL` in `.env`.
2. Wait until install/update prints `MISP reports interactive login is ready.`;
   MISP may show the login form before the generated admin account can be used.
3. Confirm the generated login details without printing the password:
   `./installer/admin-credentials.sh --install-dir /opt/misp-docker`.
4. Check that the login page is not cached from a previous failed deployment.
5. Rotate the admin password inside MISP after the first successful login.

Do not paste real passwords into public issues or Pull Requests. If you need to
share troubleshooting output, redact the password and use generic hostnames.

## Installer fails at `Running MISP database updates`, but login works later

On a fresh start, the container-local heartbeat can respond before the upstream
MISP entrypoint has finished database and application initialization. During that
window `Admin runUpdates` may fail with a CakePHP database connection error, and
the database logs may show temporary access-denied messages for the MISP user.

This is a MISP startup/initialization timing issue, not a Docker image-tag or
package-install failure. Re-run the installer from a clean reset with the current
scripts, or run:

```bash
./installer/doctor.sh --install-dir /opt/misp-docker
./installer/login-check.sh --install-dir /opt/misp-docker
```

If the stack becomes usable after several minutes, the first start was simply
slow. If it never becomes usable, inspect the MISP and database logs with generic
redaction before sharing them publicly.

Newer installer versions wait for the upstream log line `MISP is now live. Users
can now log in.` before reporting that interactive login is ready. This is a
better readiness signal than the login form being visible.

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

## Browser redirects to localhost

`BASE_URL` is MISP's public application URL. Do not use `https://localhost` for
direct-QA installs unless the browser is running on the same host. A remote
browser will follow redirects to its own `localhost`, not the MISP server.

For direct-QA mode, use a DNS name or non-loopback address that users can reach.
The installer rejects loopback `BASE_URL` values in direct-QA mode to prevent
misleading validation.

## Database connection errors after first start

Official MISP Docker expects `MYSQL_PASSWORD` to be alphanumeric. Special
characters can break the generated CakePHP database configuration during first
start. This installer generates MySQL passwords with hex characters only; if you
manually edit `.env`, keep `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD`
alphanumeric.

## Backup permission errors

The backup script uses `sudo tar` because MISP containers can create root-owned files in bind mounts.
