# Music metadata writer

This project makes embedded file metadata the portable source consumed by
Navidrome, Jellyfin, and Kew. Lidarr remains the sole importer, renamer, and
path owner. This service may change only audio tags, embedded front art,
`cover.jpg`, ReplayGain tags, and its own appdata.

The manually updated image is pinned to the upstream LinuxServer stable image
whose included application is Beets 2.12.0. WUD is disabled for this writer.

For every Lidarr import, the worker reads the selected MusicBrainz release ID
from Lidarr and invokes Beets with that exact ID. It never performs an
unrestricted metadata search. Cover art is tried first for that exact release
and then for its MusicBrainz release group. Both embedded art and a 1200-pixel
JPEG `cover.jpg` are retained for broad client compatibility. If neither CAA
scope has art, the writer extracts the album's already-embedded image,
normalizes it to a 1200-pixel JPEG sidecar, and records that fallback instead
of querying a less deterministic third-party search.

Before any tag write, a multi-linked library file is replaced atomically at
the same path. The writer attempts a ZFS copy-on-write clone first; if the
unprivileged LXC denies the clone ioctl, GNU `cp` falls back to a normal copy.
Either result must have the same size, compare byte-for-byte, and have one
link before the atomic replacement. The torrent/Usenet source inode is
therefore not modified. Lidarr is configured to stop creating hardlinks for
future imports.

The service takes Soularr's existing
`/soularr-state/.dothomelab-job.lock` per album. This prevents Soularr
acquisition and WUD replacement of Soularr/slskd from overlapping a metadata
write. Beets copy, move, link, hardlink, reflink-import, and extension-fix
features are all disabled; Lidarr owns paths.

Existing albums are reconciled explicitly after Lidarr has organized them:

```bash
docker exec music-metadata \
  python3 /opt/dothomelab/worker.py organize
docker exec music-metadata \
  python3 /opt/dothomelab/worker.py reconcile
```

Machine-readable per-album results are retained under
`/srv/appdata/docker/music-metadata/reports`. `tagged_missing_art`,
`unmatched`, `needs_review`, and `needs_organize` are review states; the worker
does not guess or delete the audio.
