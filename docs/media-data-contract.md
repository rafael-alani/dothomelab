# Media data contract

This is the stable storage and ownership contract for the six-phase books,
audiobooks, podcasts, and music pipeline. It declares results and access
boundaries and distinguishes active from future applications.

Phase 4 activated the Shelfarr ebook/audiobook, BookOrbit, Audiobookshelf, and
Storyteller portions of this contract. PinePods and the music applications
remain future declarations.

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
`storyteller`, `pinepods`, `aurral`, `soularr`, and `navidrome`.

CT102 retains the existing read-write `/data` view of shared media. CT112
retains the broad read-only `/data` view. Its existing `/music` and `/podcasts`
binds remain narrow read-write exceptions for current services and the
PinePods subtree. Storyteller has the additional narrow read-write
`/vault/shared/media/storyteller` bind at `/storyteller`; `mp6` owns that exact
mapping. No service may use it to reach canonical media.

Canonical shared-media directories retain the host `101000:100996` mapping
(guest `1000:996`) and mode `0755`. Storyteller-owned `inbox` and `library`
use host `101000:101000` (guest `1000:1000`) and mode `0750` so only the narrow
Apps service identity can write derived copies. This exception does not change
the canonical trees or CT112's read-only `/data` view.

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
metadata and progress remain writable only in appdata.

## Backup boundary

The encrypted appdata job covers `/srv/appdata/docker`, including the active
Storyteller SQLite database, config, watcher snapshots, secret file, manifest,
and latest/previous consistent database copies. It does not cover
`/vault/shared`.

Canonical books, audiobooks, podcast episodes, music, Aurral flow files, and
large Storyteller inbox/library assets are outside PBS appdata protection.
Storyteller's inbox is disposable staging; its library contains derived but
expensive accepted readalouds and must not be described as restored by the
appdata snapshot. Later phases must classify the remaining media without
implying that an appdata snapshot restores it.
