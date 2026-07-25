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
private web UI. The exact audiobook library contract is:

- media type `Books`, name `Audiobooks`, and the sole folder `/audiobooks`;
- `Audiobooks only` enabled;
- filesystem watcher disabled, with `0 4 * * *` as a daily fallback scan;
- folder structure first in metadata precedence;
- no automatic match, M4B merge, embedded source-tag writing, source-cover
  writing, or other source-media mutation.

`scripts/initialize-shelfarr-audiobookshelf-env.py` reconciles those settings
through the supported API and creates a dedicated `shelfarr-integration`
administrator limited to this one library. Audiobookshelf currently requires
administrator status for `POST /api/libraries/:id/scan`; all unrelated user
permissions are false. The scoped application key is written atomically only
to PVE `/root/.env` and is never printed. Shelfarr triggers a scan after an
import and synchronizes Audiobookshelf inventory; the daily scan is only a
fallback. Disabling the file watcher avoids partially grouping a book while
Shelfarr is still organizing it.

The existing Podcasts library remains rooted at `/podcasts` and is not changed
by the initializer. The audiobook library is read-only by design, so
Audiobookshelf cannot rewrite source tags, covers, chapter files, or names.
Application metadata, playback progress, users, API keys, and application
backups remain writable in `/config` and `/metadata`.

The rolling stable image is enrolled in backup-gated WUD. Appdata and the
recovery environment are snapshot-backed before replacement; podcast and
audiobook media are not in the PBS appdata backup. The sequential WUD runner
requires the direct HTTP endpoint and container health check to recover before
continuing. The container uses a read-only root filesystem, an ephemeral
`/tmp`, no Linux capabilities, and `no-new-privileges`.

Focused verification runs `PRAGMA integrity_check` through Audiobookshelf's
bundled SQLite runtime. Its current schema uses aggregate `ORDER BY` trigger
syntax that Debian 12's older system SQLite cannot parse even though the
application-created database is valid.

For restore, recover `/srv/appdata/docker/audiobookshelf`, `/root/.env`, and
the two shared-media directories, then run bootstrap. Bootstrap preserves a
valid scoped application key or creates a new additive key if the recovered
value is absent or invalid; it never deletes an older key automatically.
Preserve the Docker installation method because upstream does not support
restoring its database across installation methods. Do not delete a recovered
appdata tree until the root user, podcast and audiobook libraries, progress,
metadata, scoped scan trigger, and representative playback are verified.
