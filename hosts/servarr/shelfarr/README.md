# Shelfarr

Shelfarr is the sole physical organizer for acquired ebooks and audiobooks. It
runs on CT102 and uses only the existing Prowlarr, qBittorrent, and NZBGet
services. It does not declare an indexer or direct-download provider.

Ebooks are written to `/ebooks/{author}/{title}/{author} - {title}.ext`, where
`/ebooks` is the narrow read-write bind for
`/vault/shared/media/books/ebooks`. Audiobooks use the same relative
`{author}/{title}` book key and are written beneath `/audiobooks` as either one
named M4B or an ordered, unflattened multi-file release. Bundle splitting is
disabled. M4B is preferred, but M4A, MP3, and FLAC remain supported; an
approved-format allowlist is intentionally not set. Existing download trees
are mounted at their unchanged `/data/torrents` and `/downloads` paths.
`/downloads` is backed by the existing CT102 `/data/usernet` tree for NZBGet.
Completed imports use copy mode, preserving torrent payloads for seeding.
qBittorrent and NZBGet incomplete/completed trees remain at their existing
download roots, outside both final libraries. Phase 3 imports only through
Shelfarr's completed-download path in copy mode; that path copies directly
from the download-specific source and does not use output-root staging.
Direct-download providers, non-admin uploads, and Libation are disabled.
Current upstream administrator uploads require a hidden same-filesystem
staging path beneath the output root, so they are not the fulfillment path for
this phase. Staged/completed download sources are not part of PBS appdata
backup and are not recovery inputs.

Shelfarr's one supported active library-platform slot points to
Audiobookshelf. Its application key belongs to the dedicated
`shelfarr-integration` Audiobookshelf administrator, which can see only the
`/audiobooks` library and has every unrelated user permission disabled. Admin
status remains necessary because Audiobookshelf's scan endpoint requires it.
The key is generated through the supported API by
`scripts/initialize-shelfarr-audiobookshelf-env.py`, stored only as
`AUDIOBOOKSHELF_SHELFARR_API_KEY` in PVE `/root/.env`, and passed to Shelfarr
without being displayed.

Current Shelfarr supports only one active library platform, not simultaneous
Audiobookshelf and BookOrbit integrations. BookOrbit remains the canonical
ebook reader: its read-only filesystem watcher and daily scan discover
Shelfarr ebook imports while Audiobookshelf receives the supported post-import
scan trigger and inventory sync. The inactive BookOrbit connection values are
preserved for rollback; this does not authorize BookOrbit to rename media.

qBittorrent retains its current LAN password. The reconciliation helper adds
only the exact `servarr-hello_default` private subnet to qBittorrent's
authentication bypass, allowing Shelfarr to use the already-authorized
internal endpoint without storing or rotating the shared qBittorrent password.

The current upstream Compose contract includes the Libation companion.
`shelfarr-libation` therefore runs only as an uncredentialed, internal
companion. Its Shelfarr connection, synchronization, scheduled synchronization,
and automatic backup remain disabled. Enabling Audible backup is a separate
credentialed migration task and requires a review of the two-container update
cohort.

Persistent application state is `/docker/shelfarr`; recovery secrets are only
in PVE `/root/.env`. Both rolling application containers are backup-gated WUD
participants. Verify with `./verify.sh`.

The Shelfarr signing value was rotated on 2026-07-25 after an operator
verification harness exposed its predecessor. Do not restore
`SHELFARR_SECRET_KEY_BASE` from an environment snapshot predating
`20260725T211939Z`; generate a replacement and recreate only Shelfarr after
such a restore. The protected live rollback copy from the rotation is
`/root/.env.post-shelfarr-secret-rotation-20260725T211939Z`.
