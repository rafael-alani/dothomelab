# Kavita

The `kavita` Compose project uses the upstream stable
`ghcr.io/kareadita/kavita:latest` channel and runs as Apps UID/GID
`1000:1000`. Nginx Proxy Manager publishes
`https://kavita.rafael.media` only to the LAN and Tailscale with WebSockets.

Kavita's configuration, SQLite database, users, progress, covers, cache, and
built-in backups persist under `/srv/appdata/docker/kavita`. Existing
`/vault/shared/media/books`, `/vault/shared/media/comics`, and
`/vault/shared/media/mangas` are mounted read-only as `/books`, `/comics`, and
`/manga`. Create the first administrator and libraries through the private UI.

The stable rolling image is enrolled in backup-gated WUD. Upstream supports
ordinary pull/redeploy upgrades once an installation is newer than v0.7.6; a
new deployment starts on the current release and does not inherit the legacy
incremental-upgrade constraint. The runner waits for `/api/health` after every
replacement. Treat any future release note that requires an ordered migration
as an override: disable WUD for that upgrade, retain the appdata snapshot and
Kavita's built-in backup, and test the new database before accepting it.

For restore, recover `/srv/appdata/docker/kavita` and the three shared-media
directories, then run bootstrap. Kavita stores built-in backup archives below
`config/backups`; restoring one requires stopping Kavita, copying the archive
contents into the config directory, and starting the same or a compatible
version. Keep recovered data until users, libraries, progress, covers, OPDS,
and representative book/comic reading are verified.
