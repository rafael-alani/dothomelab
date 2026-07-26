# Canonical music metadata evidence — 2026-07-26

## Accepted architecture

The permanent music library remains
`/vault/shared/media/music`. Its ownership is deliberately split by concern:

| Concern | Authority |
|---|---|
| Request and acquisition | Aurral, Lidarr, Prowlarr, Soularr, download clients |
| Selected edition, import, paths, and filenames | Lidarr |
| Portable tags, MusicBrainz IDs, ReplayGain, and artwork | `music-metadata` |
| Catalogue, streaming, and presentation | Navidrome and Jellyfin, read-only |
| Local macOS playback | Kew through the read-only `Media` SMB share |

Lidarr is therefore authoritative for *which release and files exist*, but it
is not the sole metadata implementation. The file itself is the portable
metadata record consumed by every player. The `music-metadata` service reads
Lidarr's exact selected MusicBrainz release ID and writes only tags, embedded
front art, album-root `cover.jpg`, and ReplayGain. It cannot import, move,
rename, copy into the library, or delete music.

This avoids making either Navidrome's or Jellyfin's private database canonical.
Those databases are disposable indexes over the same tagged files.

## Upstream basis

The design follows the current upstream behavior documented by:

- [Beets configuration](https://docs.beets.io/en/latest/reference/config.html)
  and [CLI](https://docs.beets.io/en/stable/reference/cli.html): imports can be
  restricted to an exact MusicBrainz ID and path-changing operations can be
  disabled.
- Beets [MusicBrainz](https://docs.beets.io/en/stable/plugins/musicbrainz.html),
  [FetchArt](https://docs.beets.io/en/stable/plugins/fetchart.html),
  [EmbedArt](https://docs.beets.io/en/latest/plugins/embedart.html), and
  [ReplayGain](https://docs.beets.io/en/latest/plugins/replaygain.html)
  plugins: portable IDs, genres, embedded/sidecar art, and player-independent
  loudness metadata.
- [Navidrome tagging](https://www.navidrome.org/docs/usage/library/tagging/)
  and [configuration](https://www.navidrome.org/docs/usage/configuration/options/):
  Navidrome indexes file tags and embedded/sidecar artwork.
- [Jellyfin music organization](https://jellyfin.org/docs/general/server/media/music/):
  one album per folder, embedded tags, and conventional local images such as
  `cover.jpg`.
- MusicBrainz's [release definition](https://musicbrainz.org/doc/Release):
  a release identifies a particular issued edition rather than only a general
  album title.

## Safety and migration

Before the first write, PVE created and retained:

```text
vault/shared@pre-music-metadata-20260726T143014Z
rpool/appdata/docker@pre-music-metadata-20260726T143014Z
```

The pre-migration library contained 987 audio files. Of these, 937 were still
hardlinked to an acquisition tree and 50 already had independent inodes.
There were no canonical album-root cover sidecars.

Lidarr was configured to:

- rename tracks with the repository-declared artist/album/track templates;
- stop creating hardlinks for future imports;
- leave tag, scrub, and embedded-art writes to `music-metadata`.

Before changing an existing multi-linked file, the writer detached the library
path through an atomic, byte-verified copy. A ZFS clone was attempted first;
the unprivileged Apps LXC denied that ioctl, so the verified full-copy fallback
was used. The acquisition inode and torrent payload were never edited.

The writer then reconciled every Lidarr album against only Lidarr's selected
MusicBrainz release ID. It did not perform an unrestricted metadata search.
The strong-match floor is 88% so an exact upstream artist-credit rename such as
Kanye West to Ye can pass while an incompatible edition remains a review
state. Non-audio DVD/Blu-ray media bundled with an exact release are excluded
from the audio-file match. Partial exact releases tag the files that exist but
remain visibly incomplete.

## Live result

Lidarr organized:

```text
artists:     30
albums:      65
track files: 987
missing paths: 0
rename previews remaining: 0
queue: idle
```

The exact-release reconciliation ended with:

```text
tagged:            64 albums
tagged_incomplete:  1 album
audio files:       987
expected tracks:   988
```

The sole incomplete release is Fleetwood Mac's `Tusk`, MusicBrainz release
`8ebec83d-8ebd-4216-98bd-e6bfff17208f`: 40 of 41 files exist. CD 1 track 3,
`Think About Me`, is absent. Lidarr reports 97.5609756% and continues to
monitor the album. No existing file was removed or replaced to conceal the
gap.

Whole-library inspection proved:

```text
FLAC: 688
M4A:   28
MP3:  271
total: 987

readable audio:                  987 / 987
single-link library inodes:      987 / 987
MusicBrainz album ID present:    987 / 987
track and album ReplayGain:      987 / 987
embedded front art:              987 / 987
album-root cover.jpg:              65 / 65
valid <=1200px root cover JPEGs:   65 / 65
```

A Radiohead FLAC was used as a detachment canary. Its encoded audio-stream
SHA-256 remained
`c9a935cce50945092df1ab84723baf21273801e9e9770be20039d17e8a1e7f2d`
before and after canonicalization, while the retained acquisition file stayed
byte-identical to the pre-write snapshot. Only the library file's metadata
container changed.

Reports are retained in root-owned appdata at:

```text
/srv/appdata/docker/music-metadata/reports/
├── lidarr-organize.json
└── reconcile-2026-07-26.jsonl
```

## Consumer acceptance

Navidrome 0.63.2 completed its supported forced scan in 8.25 seconds. Its
read-only database inspection showed:

```text
Music Library songs:        987
Music Library albums:        65
missing files:                0
songs with artwork:         987
songs with MusicBrainz ID:  987
songs with ReplayGain:      987
albums with MusicBrainz ID:  65
albums using embedded art:   65
```

The separate Aurral flow library remains intentionally separate and contains
one generated-flow track.

Jellyfin's read-only library and live filesystem watcher catalogued all 987
audio paths after the tag writes. The focused media verifier passed. Jellyfin
still retains some pre-organization folder classifications in its private
cache. No authenticated Jellyfin UI session was available, so this task did
not extract credentials, edit Jellyfin's database, delete/re-add the library,
or discard play history. If the old presentation remains visible, use the
authenticated library action **Refresh metadata**, with **Replace all
metadata**, once; the tagged files and root covers are already canonical.

Samba now exposes:

- `Media` → `/vault/shared/media`, authenticated and read-only;
- `Vault` → `/vault/shared`, authenticated and read-write for deliberate
  administration.

Kew should mount `Media` and open `/Volumes/Media/music`. Server-side access as
the Samba user `afa` successfully read a representative audio file and its
`cover.jpg`; no active SMB client had to be disconnected when the configuration
was reloaded.

## Rollback and recovery boundary

Routine rollback is to stop `music-metadata`, revert the Lidarr metadata
settings, and leave the preserved files in place. Restoring either retained
ZFS snapshot is a destructive, deliberate downtime operation: inspect current
acquisitions and take a newer safety snapshot before doing so.

The canonical music files and cover sidecars are under `/vault/shared`, not
the PBS-backed appdata dataset. The snapshots above provide local migration
rollback, not independent or off-site protection. The existing broad shared
media backup gap remains unresolved and must not be represented as protected
by the appdata backup.

## Verification

The following focused checks passed after migration:

```text
hosts/apps/music-metadata/verify.sh
hosts/apps/navidrome/verify.sh
hosts/apps/media/verify.sh
hosts/infra/cockpit/verify.sh
provision/verify-media-contract.sh --repository
```

The central WUD music guard also acquired and released the shared Soularr job
lock while slskd transfers were idle. Soularr, slskd, Navidrome, Jellyfin, and
`music-metadata` remained healthy.
