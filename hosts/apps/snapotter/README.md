# SnapOtter

The `snapotter` project follows the upstream production topology: the
`snapotter/snapotter:latest` application, private `postgres:17-alpine`, and
private `redis:8-alpine`. Nginx Proxy Manager publishes
`https://snapotter.rafael.media` only to the LAN and Tailscale.

Durable application files, AI packs, PostgreSQL, Redis AOF state, logical
dumps, and retained restore-test evidence are below
`/srv/appdata/docker/snapotter`. Processing workspace is also on canonical
appdata so large jobs do not consume the LXC root disk.

The application follows upstream `latest` and is enrolled in backup-gated WUD.
PostgreSQL and Redis are pinned to majors 17 and 8 with `wud.watch=false`.
Change either database major only as a manual migration after a current logical
dump and successful isolated restore test.

Before manual database work:

```bash
pct exec 112 -- /opt/dothomelab/hosts/apps/snapotter/backup-database.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/snapotter/restore-test.sh
```

The initial username and password are read from `/root/.env`, are used only
when the first administrator is created, and never belong in Git. SnapOtter
forces an initial password change. Keep the route private even after that
change.
