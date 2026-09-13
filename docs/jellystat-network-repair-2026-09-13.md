# Jellystat database network repair — 2026-09-13

## Incident

Jellystat 1.1.12 intermittently reported setup state `0` and returned HTTP 403
from `POST /auth/createuser`, even though its PostgreSQL database contained a
complete application login, Jellyfin connection, and populated statistics.
Nginx Proxy Manager forwarded the request normally; the 403 came from
Jellystat.

The Apps Docker network had assigned the same MAC address
`02:42:ac:16:00:03` to two live endpoints:

- `jellystat-db` at `172.22.0.3`;
- `seerr` at `172.22.0.4`.

The duplicate bridge MAC intermittently directed PostgreSQL traffic to the
wrong container. Jellystat logged repeated `Connection terminated due to
connection timeout` errors. Its database wrapper converts query failures to an
empty result, so the setup-state endpoint misleadingly returned state `0`.
When database access happened to succeed, the existing complete configuration
made `/auth/createuser` correctly return 403.

## Repair

The deployed `hosts/apps/media/compose.yaml` matched Git commit
`1e6a43fdd1b473285e916659a0761608042e8018` and passed `docker compose config`.
Only the stateless `seerr` container was force-recreated. Its bind-mounted
configuration at `/srv/appdata/docker/seerr/config` was not changed. Docker
then assigned the expected unique endpoint address and MAC:

```text
jellyfin      172.22.0.2  02:42:ac:16:00:02
jellystat-db  172.22.0.3  02:42:ac:16:00:03
seerr         172.22.0.4  02:42:ac:16:00:04
jellystat     172.22.0.5  02:42:ac:16:00:05
```

## Verification

- A TCP connection from `jellystat` to `jellystat-db:5432` succeeded.
- Direct and NPM-proxied `/auth/isConfigured` both returned state `2` with
  Jellystat version 1.1.12.
- The proxied Jellystat UI returned HTTP 200.
- `hosts/apps/media/verify.sh` passed.
- Seerr, Jellystat, and Jellystat PostgreSQL were running and healthy.

The media verifier now rejects duplicate container MAC addresses and executes
`SELECT 1` through Jellystat's own PostgreSQL pool. This detects both the
specific bridge collision and application-to-database connectivity failures
that the previous local PostgreSQL health check could miss.
