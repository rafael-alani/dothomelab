# Canonical book and audiobook metadata evidence

Reconciled with the live homelab on 2026-07-26/27 CEST.

## Decision

The workflow uses existing self-hosted applications rather than a bespoke
matcher:

- Shelfarr remains the sole organizer and naming authority.
- Grimmory is the canonical EPUB metadata and cover writer.
- Audiobookshelf is the canonical audiobook metadata and cover writer.
- BookOrbit, Kavita, Jellyfin, and Storyteller consume the resulting portable
  files and sidecars.

Grimmory's native provider support and proposal-review workflow make it the
best fit for EPUBs. Its `metadataMatchScore` describes metadata completeness,
not identity confidence, so it is not used as an automatic 92-95% edition
match score. Google, Goodreads, Amazon, and Audible are enabled; Hardcover is
disabled until a supported token exists. Proposals must agree with an
embedded identifier or the Shelfarr-selected work on title, author, language,
and edition/format before a reviewer applies them.

Audiobookshelf is the audio fallback because its supported metadata embed task
uses FFmpeg stream copy, preserves chapters, keeps an original-file backup,
and writes portable `metadata.json` and `cover.jpg` sidecars. Automatic
matching, moving, renaming, and M4B merging remain disabled in both writers.

## Least-privilege publication paths

CT112's broad `/data` mount remains read-only. PVE-managed systemd bind mounts
expose only:

- `/vault/shared/media/books/ebooks` at
  `/srv/appdata/docker/grimmory/libraries/ebooks`, then
  `/library/ebooks:rw` in Grimmory;
- `/vault/shared/media/audiobooks` at
  `/srv/appdata/docker/audiobookshelf/libraries/audiobooks`, then
  `/audiobooks:rw` in Audiobookshelf.

Grimmory receives `/data/media/audiobooks` as
`/library/audiobooks:ro` for cataloguing and proposal comparison. Its former
writable audiobook bridge was disabled and retained on PVE as
`/etc/systemd/system/srv-appdata-docker-grimmory-libraries-audiobooks.mount.retired-20260726T224500Z`.

## Alice EPUB acceptance

The representative EPUB embeds the authoritative Project Gutenberg work 11
identifier (`http://www.gutenberg.org/11`), Lewis Carroll, English language,
public-domain subjects/date, and a cover. Its initial SHA-256 was:

```text
4ac9fc092435338fdb28e96b02989a46bbe075ec310f1789db87a653761cce92
```

Grimmory proposed a different combined Penguin edition,
`Alice's Adventures in Wonderland / Through the Looking-Glass`, with extra
contributors and Goodreads ID 24213. The proposal was rejected through
Grimmory's native review API. Other returned candidates were incompatible,
and Google's anonymous API was rate-limited. No fallback metadata was
invented.

The authoritative embedded metadata was accepted unchanged. The final EPUB
hash is identical, `unzip -tqq` passes, and Grimmory published portable
`.metadata.json` and `.cover.jpg` sidecars. This demonstrates fail-closed
edition handling without requiring a custom metadata service.

## Grimmory audiobook rejection and rollback

The original Alice M4B was 80,501,772 bytes with SHA-256:

```text
fe522ad254a3dc6ea68fea734f5376897fccff588458dc56e35628c1aec8a3ed
```

Applying a reviewed proposal with Grimmory v3.2.4 produced a 107,066-byte file
with no AAC audio stream and no chapters. The result failed the media safety
gate immediately. The exact original bytes were restored atomically from
`vault/shared@pre-grimmory-metadata-20260726T221858Z`; the restored size and
hash matched the original. Grimmory audiobook writes were then disabled and
its audiobook mount made read-only.

The corresponding appdata rollback point is
`rpool/appdata/docker@pre-grimmory-deploy-20260726T221858Z`. Grimmory's MariaDB
logical backup also passed an isolated MariaDB 11.4 restore test retained
under `/srv/appdata/docker/grimmory/restore-tests/20260726T222801Z`.

## Audiobookshelf audiobook acceptance

The exact source was verified against the LibriVox and Internet Archive
records for `Alice's Adventures in Wonderland (version 6)`. Audiobookshelf
records:

- work title `Alice's Adventures in Wonderland`;
- subtitle `LibriVox version 6`;
- author Lewis Carroll and narrator StudioMike;
- English, unabridged, publisher LibriVox;
- publication year 2019 and release date 2019-02-12;
- Children's Fiction and Fantasy Fiction genres;
- the source description and LibriVox cover;
- no invented ISBN or Audible ASIN.

Audiobookshelf item
`b72d3be9-70be-458d-92d3-98a391bb19a9` ran the supported native
`embed-metadata` task with original backup and forced chapter preservation.
Its task log reports successful tagging. The accepted file is 80,551,564
bytes with SHA-256:

```text
ee7acd3f7c948d951b9714561a369b238184734f2274526dc3c1dee5b104ada7
```

Verification found:

- AAC audio, embedded MJPEG cover, and the chapter data stream present;
- exact duration `10037.661315` seconds;
- all 12 chapter titles preserved;
- maximum original/new chapter-boundary delta `0.000952` seconds;
- matching extracted AAC payload hashes:
  `550f3dd325f7e7042a71b9dbcf734a284f07cdbfb063739a5d5946d7a68103ce`.

The equal AAC payload hashes prove the operation copied rather than
re-encoded audio. Audiobookshelf retained the exact original at:

```text
/srv/appdata/docker/audiobookshelf/metadata/cache/items/b72d3be9-70be-458d-92d3-98a391bb19a9/Lewis Carroll - Alice's Adventures in Wonderland.m4b
```

That backup still has the original `fe522a...` hash. The canonical audiobook
folder also contains portable `cover.jpg`, `metadata.json`, and
`.metadata.json` sidecars.

## Readers, staging, and routes

The Audiobookshelf initializer reconciles one audiobook library, stores cover
and metadata sidecars with each item, disables the filesystem watcher and
automatic matching, and retains the daily scan as a fallback. Shelfarr's
dedicated integration may trigger only that library's scan.

Storyteller correctly rejected automatic restaging of the already-accepted
Alice fixture after the canonical audiobook hash changed, reporting
`canonical source identity changed after first staging`. No duplicate or
replacement was staged. This is intentional fail-closed behavior for the
pre-existing fixture; new pairs receive canonical metadata before their first
Storyteller staging.

Grimmory is private at `https://grimmory.rafael.media`. Pi-hole, Nginx Proxy
Manager row 62, TLS, WebSockets, LAN/Tailscale allow rules, and `deny all`
were reconciled. Homarr contains one deterministic Grimmory application and a
tile on each of the three managed boards. Pre-change Infra database copies
remain at:

```text
/srv/appdata/docker/infra-nginx-proxy-manager/database.sqlite.pre-grimmory
/srv/appdata/docker/homarr/db.sqlite.pre-grimmory
```

Both databases passed integrity checks and their migrations passed isolated
copy tests before the live write.

## Remaining exception

BookOrbit's runtime and scheduled watcher remain healthy, but the on-demand
scan request returned HTTP 401 because the recovered
`BOOKORBIT_ADMIN_PASSWORD` no longer matches the live account. No credential
was rotated during this metadata task. The recovery credential must be
reconciled in a separately authorized rotation before a forced BookOrbit scan
can be demonstrated.

Canonical ebooks and audiobooks remain on `vault/shared`, outside the
appdata PBS backup. The focused ZFS snapshot is therefore the rollback for
this publication batch; the Audiobookshelf and Grimmory application state,
database dumps, and configuration remain protected by the normal appdata
backup path.
