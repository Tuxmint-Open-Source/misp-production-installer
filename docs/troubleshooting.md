# Troubleshooting

## CSRF error after login

Verify Redis-backed PHP sessions. `REDIS_PASSWORD` must be URL-safe because PHP receives it in a Redis session save path. This installer generates it as 64-character hex.

## Healthcheck fails but public URL works

Healthchecks use container-local `https://localhost/users/heartbeat`, not public DNS or reverse proxy paths.

## Backup permission errors

The backup script uses `sudo tar` because MISP containers can create root-owned files in bind mounts.
