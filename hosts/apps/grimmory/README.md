# Grimmory

Grimmory is the canonical metadata writer for ebooks and audiobooks at
`https://grimmory.rafael.media`. It uses the official stable rolling
`ghcr.io/grimmory-tools/grimmory:latest` image and private MariaDB 11.4.8.
Application and database state live under `/srv/appdata/docker/grimmory`.

Two PVE systemd bind mounts expose only canonical ebooks and audiobooks through
Grimmory's appdata path. The container receives those paths read-write, while
CT112's broad `/data` mount and all other readers stay read-only:

- `/vault/shared/media/books/ebooks` -> `/library/ebooks`
- `/vault/shared/media/audiobooks` -> `/library/audiobooks`

Shelfarr remains the organizer. Grimmory cannot move or rename canonical files,
does not receive BookDrop, PDF, comic, manga, or download paths, and writes only
EPUB and audiobook metadata plus JSON/cover sidecars.

## Matching policy

Google, Goodreads, Amazon, and Audible are enabled. Hardcover stays disabled
until a supported API credential is supplied. Every online metadata refresh
uses Grimmory's native proposal review before anything is applied. This is
intentional: Grimmory's `metadataMatchScore` measures metadata completeness,
not candidate identity confidence, so it must not be treated as a 92-95%
automatic-match gate.

An accepted proposal must agree with the embedded identifier or the
Shelfarr-selected work on title, author, language, and edition/format. Missing
identifiers, multiple plausible editions, language disagreement, and
abridged/unabridged conflicts remain unmodified in the review queue.

Grimmory writes EPUB and M4B/M4A/MP3 tags natively. The first audiobook pilot
must preserve codec, duration, chapters, and chapter boundaries. If it does
not, restore the focused ZFS snapshot, disable Grimmory audiobook file writes,
and use Audiobookshelf's supported metadata workflow for audio while keeping
Grimmory canonical for ebooks.

## Backups and updates

The PVE pre-backup hook creates `latest` and `previous` logical MariaDB dumps
under appdata before the consistent ZFS snapshot. Canonical books and
audiobooks are on `vault/shared` and are not protected by PBS appdata backups.
Take a focused `vault/shared` ZFS snapshot before every metadata publication
batch and verify output hashes and media structure afterward.

Grimmory follows the backup-gated WUD route. MariaDB has `wud.watch=false` and
is updated manually only after a current logical dump and isolated restore
test. The direct health check is `/api/v1/healthcheck`.
