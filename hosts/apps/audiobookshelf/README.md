# Audiobookshelf

The `audiobookshelf` Compose project runs the upstream stable
`ghcr.io/advplyr/audiobookshelf:latest` channel as Apps UID/GID `1000:1000`.
Nginx Proxy Manager publishes `https://audiobookshelf.rafael.media` only to
the LAN and Tailscale and enables WebSockets.

Durable state is split deliberately:

- `/srv/appdata/docker/audiobookshelf/config` stores the SQLite database and
  migrations;
- `/srv/appdata/docker/audiobookshelf/metadata` stores covers, logs, metadata,
  and application backups;
- `/vault/shared/media/audiobooks` is exposed read-only as `/audiobooks`;
- `/vault/shared/media/podcasts` is the only writable shared-media bind and is
  exposed as `/podcasts` for episode downloads.

Create the first administrator and the audiobook/podcast libraries through the
private web UI. The audiobook library is read-only by design, so tools that
rewrite source tags or media files are intentionally unavailable.

The rolling stable image is enrolled in backup-gated WUD. Appdata and the
recovery environment are snapshot-backed before replacement; podcast and
audiobook media are not in the PBS appdata backup. The sequential WUD runner
requires the direct HTTP endpoint to recover before continuing.

For restore, recover `/srv/appdata/docker/audiobookshelf`, `/root/.env`, and
the two shared-media directories, then run bootstrap. Preserve the Docker
installation method because upstream does not support restoring its database
across installation methods. Do not delete a recovered appdata tree until the
root user, libraries, progress, metadata, and representative playback are
verified.
