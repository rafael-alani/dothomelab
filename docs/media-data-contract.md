# Media data contract

This is the stable storage and ownership contract for the six-phase books,
audiobooks, podcasts, and music pipeline. It declares results and access
boundaries; it does not claim that the future applications are deployed.

Phase 3 activated the Shelfarr ebook/audiobook, BookOrbit, and Audiobookshelf
portions of this contract. Remaining services and write exceptions are still
future declarations.

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
PinePods subtree. A later phase may declare another narrow read-write bind only
after verifying the exact current upstream container target. Part 1 reserves
no new `mp` number.

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
from fuzzy title similarity or mutate either canonical source tree.

Audiobookshelf sees the audiobook tree read-only and must not merge tracks,
write embedded tags or covers, or rename files. Shelfarr preserves
multi-file ordering and directory structure, prefers one M4B when the source
offers it, and uses copy-mode completed imports so torrent sources remain
available for seeding. Shelfarr's output-root-relative hidden staging paths are
overlaid by appdata-backed mounts, so staging bytes do not live in either final
shared-media library. Audiobookshelf application metadata and progress remain
writable only in appdata.

## Backup boundary

The encrypted appdata job covers `/srv/appdata/docker`, including future
application databases/configuration/manifests after those services are
deployed. It does not cover `/vault/shared`.

Canonical books, audiobooks, podcast episodes, music, Aurral flow files, and
large Storyteller inbox/library assets are outside PBS appdata protection.
Later phases must classify each as irreplaceable user data or reproducible
derived data and must not imply that an appdata snapshot restores them.
