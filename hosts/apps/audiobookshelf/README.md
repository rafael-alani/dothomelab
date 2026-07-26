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
- `/vault/shared/media/audiobooks` is exposed through a persistent narrow host
  bind as read-write `/audiobooks`;
- the former Podcasts library record remains in SQLite, but its `/podcasts`
  container bind is intentionally absent after PinePods phase-5 acceptance.

Create the first administrator and the audiobook library through the private
web UI. The exact audiobook library contract is:

- media type `Books`, name `Audiobooks`, and the sole folder `/audiobooks`;
- `Audiobooks only` enabled;
- filesystem watcher disabled, with `0 4 * * *` as a daily fallback scan;
- folder structure first in metadata precedence;
- no automatic match or M4B merge. Reviewed recording metadata and covers may
  be embedded with Audiobookshelf's native stream-copy tool only.

`scripts/initialize-shelfarr-audiobookshelf-env.py` reconciles those settings
through the supported API and creates a dedicated `shelfarr-integration`
administrator limited to this one library. Audiobookshelf currently requires
administrator status for `POST /api/libraries/:id/scan`; all unrelated user
permissions are false. The scoped application key is written atomically only
to PVE `/root/.env` and is never printed. Shelfarr triggers a scan after an
import and synchronizes Audiobookshelf inventory; the daily scan is only a
fallback. Disabling the file watcher avoids partially grouping a book while
Shelfarr is still organizing it.

The existing Podcasts library record remains rooted at `/podcasts` and is not
changed by the initializer. It is inactive because the container no longer
receives that path; its appdata and old shared files remain recovery inputs.
PinePods is the active podcast service.

Audiobookshelf is the canonical audiobook metadata writer because Grimmory
v3.2.4 removed the AAC stream and chapters from the representative Alice M4B.
For each reviewed recording, update Audiobookshelf metadata from an exact
source, then run its native `embed-metadata` task with file backup enabled.
That task uses FFmpeg stream copy and embeds the existing chapter list. Verify
codec, duration, chapter count, and chapter boundaries before accepting the
result. The first pilot for a new format/codec requires a focused
`vault/shared` ZFS snapshot. Automatic matching, M4B merging, moving, renaming,
and unreviewed source mutation remain disabled.

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
the audiobook and retained legacy-podcast shared-media directories, then run
bootstrap. Bootstrap preserves a
valid scoped application key or creates a new additive key if the recovered
value is absent or invalid; it never deletes an older key automatically.
Preserve the Docker installation method because upstream does not support
restoring its database across installation methods. Do not delete a recovered
appdata tree until the root user, podcast and audiobook libraries, progress,
metadata, scoped scan trigger, and representative playback are verified.
