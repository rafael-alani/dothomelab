# Shelfarr

Shelfarr is the sole physical organizer for acquired ebooks and audiobooks. It
runs on CT102 and uses only the existing Prowlarr, qBittorrent, and NZBGet
services. It does not declare an indexer or direct-download provider.

Ebooks are written to `/ebooks/{author}/{title}/{author} - {title}.ext`, where
`/ebooks` is the narrow read-write bind for
`/vault/shared/media/books/ebooks`. Audiobooks use the same relative
`{author}/{title}` book key. Existing download trees are mounted at their
unchanged `/data/torrents` and `/downloads` paths. `/downloads` is backed by
the existing CT102 `/data/usernet` tree for NZBGet.

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
