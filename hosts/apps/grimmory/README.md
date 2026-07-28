# Grimmory

Grimmory is the canonical metadata writer for ebooks at
`https://grimmory.rafael.media`. It uses the official stable rolling
`ghcr.io/grimmory-tools/grimmory:latest` image and private MariaDB 11.4.8.
Application and database state live under `/srv/appdata/docker/grimmory`.

One PVE systemd bind mount exposes only canonical ebooks through Grimmory's
appdata path. The container receives ebooks read-write and audiobooks
read-only:

- `/vault/shared/media/books/ebooks` -> `/library/ebooks`
- `/data/media/audiobooks` -> `/library/audiobooks` (read-only)

Shelfarr remains the ebook organizer and Listenarr the audiobook organizer.
Grimmory cannot move or rename canonical files,
does not receive BookDrop, PDF, comic, manga, or download paths, and writes only
EPUB metadata plus JSON/cover sidecars. Its audiobook library remains useful
for read-only inspection and proposal comparison but cannot publish to audio.

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

The first M4B pilot proved Grimmory v3.2.4 unsafe for this library: applying
metadata to the 80,501,772-byte Alice M4B produced a 107,066-byte file with no
AAC stream or chapters. The exact pre-write bytes were restored from the
focused ZFS snapshot. Grimmory audiobook file writing is therefore disabled,
its audio mount is read-only, and Audiobookshelf is the canonical audio writer.

## Backups and updates

The PVE pre-backup hook creates `latest` and `previous` logical MariaDB dumps
under appdata before the consistent ZFS snapshot. Canonical books and
audiobooks are on `vault/shared` and are not protected by PBS appdata backups.
Take a focused `vault/shared` ZFS snapshot before every metadata publication
batch and verify output hashes and media structure afterward.

Grimmory follows the backup-gated WUD route. MariaDB has `wud.watch=false` and
is updated manually only after a current logical dump and isolated restore
test. The direct health check is `/api/v1/healthcheck`.
