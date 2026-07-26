# Media data contract

This is the stable storage and ownership contract for the six-phase books,
audiobooks, podcasts, and music pipeline. It declares results and access
boundaries and distinguishes active from future applications.

Phase 6 activated the complete contract. Shelfarr owns ebook/audiobook
organization; PinePods owns podcast state and episodes; Lidarr alone owns
permanent-music organization. Aurral and Soularr submit to Lidarr instead of
writing that library. The music-metadata service is the only tag/art writer;
it cannot import, move, rename, or delete audio. Navidrome and Jellyfin consume
the result read-only.

## Canonical host paths

Large media and derived assets live under `/vault/shared/media`:

```text
books/
├── ebooks/
└── pdfs/
comics/
mangas/
audiobooks/
podcasts/
└── pinepods/
music/
aurral-flows/
storyteller/
├── inbox/
└── library/
```

Application databases, configuration, queue state, progress, and small
manifests live under `/srv/appdata/docker` in the exact directories declared by
`provision/inventory.env`: `shelfarr`, `bookorbit`, `audiobookshelf`,
`storyteller`, `pinepods`, `aurral`, `soularr`, `music-metadata`, and
`navidrome`.

CT102 retains the existing read-write `/data` view of shared media. CT112
retains the broad read-only `/data` view. Its existing `/music` and `/podcasts`
binds remain narrow read-write exceptions; PinePods receives only
`/podcasts/pinepods` inside its container. Audiobookshelf's retained podcast
library/state is inactive and does not receive that writable bind after phase
5 acceptance. Storyteller has the additional narrow read-write
`/vault/shared/media/storyteller` bind at `/storyteller`; `mp6` owns that exact
mapping. No service may use it to reach canonical media.

Canonical shared-media directories retain the host `101000:100996` mapping
(guest `1000:996`) and mode `0755`. The PinePods-owned episode subtree plus
Storyteller-owned `inbox` and `library` use host `101000:101000` (guest
`1000:1000`) and mode `0750` so only the narrow Apps service identity can
write them. These exceptions do not change the canonical trees or CT112's
read-only `/data` view.

Aurral receives the canonical `/data/media/music` path read-only and a
separate `/aurral-flows` path read-write. That flow path is a persistent,
narrow host bind from `/vault/shared/media/aurral-flows` into
`/srv/appdata/docker/aurral/flows`; mount propagation makes it visible through
CT112's existing appdata mount without another LXC mount. Navidrome receives
both the permanent library and flow library read-only. Soularr runs on CT102,
stores state only in `/docker/soularr`, and uses
`/data/media/slskd/complete`; slskd sees that same host tree as
`/slskd-downloads/complete` on CT112. Soularr has no direct container mount of
the permanent music root.

The CT112 `music-metadata` container receives the existing narrow `/music`
bind read-write and runs as guest `1000:996`, matching canonical music
ownership. Its only other writable mounts are its canonical appdata and the
single Soularr appdata directory used for the shared job-lock inode. This is
the sole exception to the consumer read-only rule and does not grant write
access to CT112's broad `/data` media tree.

## Shared relative book key

Shelfarr is the sole organizer of canonical ebook and audiobook files. Phase 3
configures the current official `{author}/{title}` path template for both
branches so they produce the same normalized relative `<book-key>` directory.
The required result is equivalent to:

```text
ebooks/<book-key>/Book.epub
audiobooks/<book-key>/Book.m4b
```

For ordered multi-file audio, the result is:

```text
audiobooks/<book-key>/01 - Chapter.mp3
```

The `<book-key>` is one safe, non-empty relative directory name: no absolute
path, `.` or `..` component, separator, or control character. The ebook and
audiobook for the same intended pairing use the byte-identical key. Distinct
editions that must not pair use distinct keys. Filenames and exact Shelfarr
template syntax are deliberately not prescribed here; each application phase
must take that syntax from the current official release and verify the
resulting directory shape.

Storyteller reconciliation compares the exact relative key. It must not guess
from fuzzy title similarity or mutate either canonical source tree. It stages
verified disposable copies into `storyteller/inbox`, and Storyteller moves
only those copies into its owned library.

Audiobookshelf sees the audiobook tree read-only and must not merge tracks,
write embedded tags or covers, or rename files. Shelfarr preserves
multi-file ordering and directory structure, prefers one M4B when the source
offers it, and uses copy-mode completed imports so torrent sources remain
available for seeding. Shelfarr's output-root-relative hidden staging paths are
not used by the active phase-3 acquisition paths: direct providers,
non-admin uploads, and Libation are disabled. Completed-download imports copy
from download-specific qBittorrent/NZBGet paths outside both final libraries.
Those staged downloads are not recovery inputs. Audiobookshelf application
metadata and audiobook progress remain writable only in appdata. Its former
podcast library record, user state, and any old files remain recovery inputs
and are never edited to simulate migration.

PinePods is the sole active owner of podcast subscriptions, episode downloads,
playback progress, and GPodder sync. Its PostgreSQL/config/server-backup state
and latest/previous portable logical dumps live under
`/srv/appdata/docker/pinepods`; its episode files live only under
`/vault/shared/media/podcasts/pinepods`.

## Music ownership

Lidarr is the only service allowed to import, rename, or place files below
`/vault/shared/media/music`. Prowlarr with qBittorrent/NZBGet remains one
acquisition route. Soularr with slskd is the other: Soularr selects a Lidarr
missing album, asks slskd to download into the shared slskd tree, and tells
Lidarr to import from CT102's corresponding path. Its automatic scheduler is
disabled by default so a recovered Lidarr backlog cannot trigger unreviewed
Soulseek downloads; an operator enables it only after curating monitored
artists or runs an explicit guarded cycle.

A file's embedded tags are the portable canonical metadata consumed by Kew,
Navidrome, and Jellyfin. Lidarr selects the MusicBrainz release and owns the
artist/album/track path. The separate music-metadata worker uses only that
exact selected release ID; it writes canonical MusicBrainz tags, multi-value
genres, embedded front art, a 1200-pixel JPEG `cover.jpg`, and album/track
ReplayGain. Its Beets configuration disables copy, move, link, hardlink,
reflink-import, and in-place extension fixes. When neither the exact CAA
release nor its release group has art, it extracts retained embedded art and
normalizes that image to the same JPEG sidecar instead of searching an
unscoped third-party catalogue.
The exact-ID match must still score at least 90%; this explicitly tolerates a
MusicBrainz artist rename such as `Kanye West` to `Ye` while rejecting an
incompatible selected edition.

Lidarr's own tag writer and cover embedder remain disabled. Future imports use
copies rather than hardlinks so metadata writes cannot change an active
torrent payload. For a retained historical hardlink, the worker first
attempts a ZFS copy-on-write clone and falls back to a full copy when the
unprivileged LXC denies the clone ioctl. It requires a one-link result with
identical size and bytes before atomically replacing only the library
directory entry at the same path. It never changes the download-side inode.
It acquires Soularr's existing `.dothomelab-job.lock` around each album,
so Soularr acquisition and WUD replacement of Soularr/slskd cannot overlap a
metadata write. A failed exact match, missing release selection, mixed
directory, or absent art becomes a machine-readable review result; no fallback
metadata guess or audio deletion is allowed.

Aurral sends main-library requests to Lidarr and writes only appdata and its
flow root. Navidrome and Jellyfin scan the permanent library read-only;
Navidrome also scans the flow root read-only. The authenticated Samba Media
share remains a read-only consumer contract for Kew. DroppedNeedle appdata,
image references, and rollback Compose remain available, but the service is
excluded from normal bootstrap, stopped with no restart policy after
acceptance, absent from routes/Homarr, and explicitly denied by the WUD runner.

## Backup boundary

The encrypted appdata job covers `/srv/appdata/docker`, including the active
Storyteller SQLite state and PinePods PostgreSQL/config/dumps. PinePods'
pre-backup hook creates a portable logical dump before the snapshot, and its
isolated restore test proves counts plus application readability without
copying PostgreSQL files. The job does not cover `/vault/shared`.

Canonical books, audiobooks, podcast episodes, music, Aurral flow files, and
large Storyteller inbox/library assets are outside PBS appdata protection.
Storyteller's inbox is disposable staging; its library contains derived but
expensive accepted readalouds and must not be described as restored by the
appdata snapshot. Later phases must classify the remaining media without
implying that an appdata snapshot restores it.
