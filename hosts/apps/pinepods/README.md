# PinePods

The `pinepods` project runs the official
`madeofpendletonwool/pinepods:latest` stable channel with its private
`postgres:18` database and `valkey/valkey:8-alpine` cache. Only the application
publishes a port, at `192.168.0.112:8040`; Nginx Proxy Manager exposes
`https://pinepods.rafael.media` only to LAN and Tailscale clients.

PinePods runs its application processes as Apps UID/GID `1000:1000`.
`/podcasts/pinepods` is its only shared-media bind and maps to
`/opt/pinepods/downloads`. It may not write `/podcasts` generally or any other
shared-media tree. Episode files are canonical PinePods user data under
`/vault/shared` and are outside the encrypted appdata PBS job.

PostgreSQL 18 uses the upstream-required mount outside the image-owned volume:
`/srv/appdata/docker/pinepods/postgres` is mounted at `/var/lib/pgdata`, with
`PGDATA=/var/lib/pgdata/pgdata`. Never attach this directory to another
PostgreSQL major. Use `backup-database.sh` and a tested logical restore for
major upgrades. Portable latest/previous logical dumps, server-generated
backups, and isolated restore evidence are under
`/srv/appdata/docker/pinepods/{backups,restore-tests}` and are included in the
appdata backup.

`scripts/initialize-pinepods-env.py` creates missing database, Valkey, and
administrator recovery values atomically in PVE `/root/.env` without
displaying them. Existing values are preserved. The initial administrator is
created by PinePods' supported bootstrap variables. Standard login remains
enabled; OIDC is optional and is not configured by this phase. If OIDC is
added later, store its client secret only in `/root/.env` and do not disable
standard login until an OIDC login and recovery-admin path are proven.

The built-in GPodder service is available through the same HTTPS origin. Enable
it in **Settings → Podcast Sync Settings**, then connect clients such as
AntennaPod with the PinePods URL and the user's PinePods credentials. OPML
exports preserve subscriptions, not listening progress; GPodder episode
actions are the supported progress-sync path.

The application `latest` image is enrolled in backup-gated sequential WUD and
must pass `/api/health` after replacement. PostgreSQL and Valkey have
`wud.watch=false`; their explicit majors are manual compatibility/migration
tasks. The pre-backup hook refreshes a logical dump before the appdata
snapshot. Run `restore-test.sh` after material schema changes: it restores to
an isolated PostgreSQL 18 container, compares object counts, and starts a
network-isolated PinePods copy against the restored database.

Rollback reverts and syncs the Git commit, then stops normal use of the
PinePods project if necessary. Retain its appdata, dumps, episode subtree,
restore-test artifacts, old images, and all Audiobookshelf podcast state.
Rollback never authorizes deleting or copying PostgreSQL data directories.
