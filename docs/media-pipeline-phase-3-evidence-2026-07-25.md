# Media pipeline phase 3 evidence

Date: 2026-07-25

Scope: extend the existing Shelfarr deployment to audiobook requests and
completed-download imports, make Audiobookshelf its active library inventory
and scan target, exercise one legal public-domain audiobook lifecycle, and
retain the phase-2 ebook path, Readarr, and Audiobookshelf podcast state.
Production credentials and token values are deliberately absent.

## Upstream and live revalidation

Primary upstream sources were rechecked immediately before implementation:

- Shelfarr's current
  [configuration reference](https://shelfarr.org/configuration.html), current
  `main` commit
  [`fe13918c749295412de0e47bac9c4755296de6a0`](https://github.com/Pedro-Revez-Silva/shelfarr/commit/fe13918c749295412de0e47bac9c4755296de6a0),
  and the live v0.39.1 API and database surfaces;
- Audiobookshelf's
  [v2.35.1 release](https://github.com/advplyr/audiobookshelf/releases/tag/v2.35.1),
  [API reference](https://api.audiobookshelf.org/), Docker/reverse-proxy
  guidance, library settings, user permissions, scan endpoint, playback
  sessions, byte-range file serving, and local/offline session sync;
- LibriVox's public-domain
  [Alice's Adventures in Wonderland, version 6](https://librivox.org/13477)
  recording, the Internet Archive M4B derivative, and
  [Open Library work OL138052W](https://openlibrary.org/works/OL138052W).

The review confirmed these phase constraints:

- Shelfarr v0.39.1 has one active library-platform slot. Audiobookshelf is the
  active target in phase 3; simultaneous active BookOrbit and Audiobookshelf
  clients are not supported.
- Shelfarr's current path and filename templates are `{author}/{title}` and
  `{author} - {title}`. Copy-mode completed imports preserve seeding sources,
  and disabling split audiobook bundle imports preserves ordered multi-file
  releases.
- Audiobookshelf's scan endpoint requires an administrator. Its API key has
  the permissions and library scope of its owning user.
- Audiobookshelf supports one M4B or ordered audio files in one book
  directory. Its API supplies direct byte-range playback, progress/resume, and
  local/offline-session synchronization.
- Audiobookshelf requires WebSocket support behind a reverse proxy.

## Pre-change state, risk, and rollback inputs

PVE, both ZFS pools, canonical datasets, CT102/110/112/113, HAOS VM104, and
VM101 were healthy before change. The four managed LXCs and both VMs remained
running. The daily appdata timer was enabled. Its most recent scheduled run
started at 09:41 CEST, completed successfully at 09:50 CEST with exit status
zero, removed its temporary ZFS snapshot, and handed off to WUD. No on-demand
PBS backup was started for this routine configuration/application change.

The exact pre-phase production environment copy remains mode 0600 at:

```text
/root/.env.pre-shelfarr-audiobookshelf-20260725T202421Z
```

During final verification, a faulty operator harness emitted the pre-rotation
Shelfarr session-signing value. After explicit authorization, only
`SHELFARR_SECRET_KEY_BASE` was replaced atomically without displaying its new
value, and only the Shelfarr container was recreated. This invalidated
existing Shelfarr browser sessions but did not change its SQLite data,
requests, downloads, or media. The safe post-rotation environment rollback
copy is:

```text
/root/.env.post-shelfarr-secret-rotation-20260725T211939Z
```

The earlier copy is retained because deletion was out of scope, but its old
Shelfarr signing value is compromised and must not be restored. A recovery
from an environment snapshot predating the rotation must replace that value
and recreate Shelfarr before use.

Baseline preservation fingerprints included:

```text
Readarr container:
  a90a28ee892f97fab36aa4dced13e711f98b7d2d8878d9512cba5ef9865dfeac
Readarr config.xml SHA-256:
  99288ee54f5a5f656027dc3a7599e3dd77bc99c5b347785d379005f1207652e6
podcast tree SHA-256:
  abcfa6a9d4df344d1781bc2560b5e4cdcae08b39ed303063535e7e1e926a304a
podcast library:
  b77496ac-14ce-48c2-8364-5fc7dd68eab3
podcast libraries/items/episodes:
  1/0/0
```

No service, database, appdata, download, media, failed acceptance record, or
staging artifact was deleted. The failed-upload and superseded empty staging
artifacts are retained for diagnosis and require a separately authorized
cleanup task.

## Declared and deployed integration

Shelfarr remains one two-container project on CT102. No container placement or
declared count changed.

- Ebook and audiobook output roots are `/ebooks` and `/audiobooks`.
- Both use `{author}/{title}` and therefore the same normalized per-book
  relative key. Both use `{author} - {title}` for the organized filename.
- Audiobook preference order is M4B, M4A, MP3, then FLAC. One file is
  preferred, higher bitrate is not preferred, and bundle splitting is off.
- qBittorrent retains `/data/torrents`; NZBGet retains
  `/downloads` backed by `/data/usernet`.
- Imports use copy mode. Download-client incomplete and completed paths are
  outside both final libraries, and torrent payloads remain available for
  seeding.
- The active phase-3 path is completed-download import. Direct providers,
  non-administrator uploads, and Libation acquisition/synchronization remain
  disabled. No output-root-relative staging path is used by that active path.
- Audiobookshelf is Shelfarr's active library platform. The inactive
  BookOrbit connection values remain for rollback, while BookOrbit's
  read-only watcher and daily scan continue to discover ebooks.

`scripts/initialize-shelfarr-audiobookshelf-env.py` uses the supported
Audiobookshelf API and never prints a token. It reconciles:

- the single Books library rooted at `/audiobooks`;
- `Audiobooks only` enabled;
- filesystem watcher disabled and fallback cron `0 4 * * *`;
- folder structure first in metadata precedence;
- a dedicated active `shelfarr-integration` administrator whose accessible
  libraries list contains only the audiobook library and whose unrelated
  download, update, delete, upload, ereader, all-library, all-tag, and
  explicit-content permissions are false;
- one additive active API key named `Shelfarr audiobook library scan`, stored
  only as `AUDIOBOOKSHELF_SHELFARR_API_KEY` in PVE `/root/.env`.

Audiobookshelf remains one CT112 container on the upstream
`ghcr.io/advplyr/audiobookshelf:latest` channel, live at v2.35.1. It now runs
as `1000:1000` with a read-only root filesystem, ephemeral `/tmp`, all
capabilities dropped, `no-new-privileges`, a direct health check, and resource
limits. `/audiobooks` is a read-only bind. `/podcasts` remains the existing
narrow read-write bind. Only `/config` and `/metadata` hold writable
configuration, SQLite state, metadata, progress, and application backups.
Automatic M4B merge, source tag/cover writing, and other canonical-media
mutation remain disabled.

The live result remains 15 containers/two projects on CT102, 11/five on CT110,
and 32/seventeen on CT112: 58 running containers in 24 projects. The clean
build still declares 61 containers in 27 projects. Its three-container gap is
the pre-existing Paperless-GPT, Prometheus, and Loki live-deployment boundary,
not a placement change in this phase.

## Public-domain audiobook acceptance lifecycle

The acceptance file was LibriVox's DRM-free public-domain M4B:

```text
source:
  /vault/shared/usernet/completed/shelfarr-phase3-acceptance/
    AliceWonderland6_librivox.m4b
size:
  80,501,772 bytes
SHA-256:
  fe522ad254a3dc6ea68fea734f5376897fccff588458dc56e35628c1aec8a3ed
```

Shelfarr API request `2` was created by the administrator for Open Library work
`OL138052W`, audiobook media type. It entered Shelfarr's search/selection
workflow. No unreviewed search result, new provider, new credential, or DRM
workflow was enabled.

Two administrator-upload attempts were intentionally retained after they
failed safely with `EXDEV`: separate bind mounts cannot satisfy Shelfarr's
atomic rename requirement even when they resolve to the same host dataset.
Neither attempt published a final file. This live evidence caused the
superseded output-root staging overlays to be removed from the declared
phase-3 design.

The accepted fulfillment placed the verified source in the existing NZBGet
completed tree. The acceptance harness associated that path with Shelfarr's
existing NZBGet client and enqueued Shelfarr's current completed-download
`PostProcessingJob`. This exercised the real remote-path resolution,
copy-mode organizer, filename template, request completion, inventory sync,
and Audiobookshelf post-import scan. It did not claim a new Usenet or
BitTorrent network transfer.

Shelfarr completed download `1` at 100 percent, cleared the request attention
flag, and recorded `request.completed`. The final file is:

```text
/vault/shared/media/audiobooks/Lewis Carroll/
  Alice's Adventures in Wonderland/
    Lewis Carroll - Alice's Adventures in Wonderland.m4b
```

It is 80,501,772 bytes, mode 0640, and mapped to guest `1000:1000`. Its
SHA-256 before and after Audiobookshelf scan, playback, seek, and resume is
the same as the completed-download source:

```text
fe522ad254a3dc6ea68fea734f5376897fccff588458dc56e35628c1aec8a3ed
```

The source was retained. The importer did not flatten the book, alter its
bytes, or remove its completed-download copy.

## Shared key, Audiobookshelf scan, and playback

Shelfarr requests `1` and `2` now report:

```text
ebook:
  /ebooks/Lewis Carroll/Alice's Adventures in Wonderland
audiobook:
  /audiobooks/Lewis Carroll/Alice's Adventures in Wonderland
relative key:
  Lewis Carroll/Alice's Adventures in Wonderland
```

The relative key is byte-identical for both media branches. This is the exact
key that phase 4 may compare; no fuzzy title match is required.

Shelfarr triggered Audiobookshelf's supported scan. Audiobookshelf discovered
item `b72d3be9-70be-458d-92d3-98a391bb19a9` at that relative path with:

```text
title: Alice's Adventures in Wonderland (version 6)
format: one audio/mp4 M4B
files: 1
duration: 10,037.661315 seconds
chapters: 12
missing/invalid: false/false
stored source cover: false
```

The chapter timeline is ordered and contiguous: chapter 1 starts at zero,
chapter 12 ends at 10,037.661315 seconds, and every intervening chapter start
equals the preceding end. Titles run from `01 - Down The Rabbit-Hole` through
`12 - Alice’s Evidence`. This passes the single-M4B branch of the required
single-file-or-ordered-multi-file acceptance.

An authenticated HTML5 playback session returned direct-play method 0. A
64-KiB range request returned HTTP 206 and exactly 65,536 bytes. Progress
synchronized at 321.25 seconds and a new session resumed at exactly 321.25.
Audiobookshelf's supported local/offline session endpoint then accepted HTTP
200, synchronized 654.5 seconds, and a mobile-style session resumed at
654.5. The private UI returned HTTPS 200 with a valid certificate, and a raw
Socket.IO handshake through NPM returned `101 Switching Protocols`.

No physical mobile client was available, so an actual device download is not
claimed. The supported offline synchronization API was exercised instead.

## Phase-2 and retained-service regression

The phase-2 ebook request remains completed for the same Open Library work.
The canonical EPUB remains:

```text
/vault/shared/media/books/ebooks/Lewis Carroll/
  Alice's Adventures in Wonderland/
    Lewis Carroll - Alice's Adventures in Wonderland.epub
```

Its size remains 189,199 bytes and its SHA-256 remains:

```text
4ac9fc092435338fdb28e96b02989a46bbe075ec310f1789db87a653761cce92
```

BookOrbit still inventories book/file `1`. Its browser reader returned HTTP
206 and a valid EPUB ZIP header. Its authenticated download and OPDS
acquisition download both reproduced the same SHA-256. OPDS returned one
matching entry, the KOReader endpoint still required authentication, and
Kobo/KOReader reported no invented physical device.

Readarr retained the same container ID and image, remained healthy, retained
its configuration SHA-256, and passed the complete CT102 Servarr verifier with
60 database records. Its full appdata tree is not used as an immutable digest
because Readarr continuously updates logs and SQLite WAL/SHM files; no Readarr
configuration, API, database, or media mutation was performed by this phase.

The podcast tree SHA-256 remained
`abcfa6a9d4df344d1781bc2560b5e4cdcae08b39ed303063535e7e1e926a304a`.
The same podcast library ID remains present with exactly one podcast library,
zero items, and zero episodes. The `/podcasts` root and its read-write bind
are unchanged.

## Network, UX, updates, backup, and verification

Pi-hole resolves `audiobookshelf.rafael.media` to `192.168.0.110`. Private
HTTPS returns 200 with certificate verification result zero. NPM targets
`192.168.0.112:13378`, enables WebSockets, and retains LAN/Tailscale allow
rules followed by `deny all`. Nginx configuration and NPM SQLite integrity
passed. Homarr remains healthy with 19 managed applications, 57 items, and
133 layouts.

The central WUD dry-run discovered 41 watched containers, all associated with
`docker.backupgated`, including Shelfarr, Shelfarr-Libation, BookOrbit, and
Audiobookshelf. No eligible update was applied. Shelfarr and Audiobookshelf
retain direct sequential HTTP health gates; BookOrbit PostgreSQL remains
excluded from WUD.

Completed checks:

- live `docker compose config --quiet` passed for Shelfarr, BookOrbit,
  Audiobookshelf, and Infra services using a protected temporary production
  dotenv copy that was removed on exit;
- Shelfarr, Audiobookshelf, BookOrbit, CT102 Servarr, and Infra
  NPM/Homarr/DNS focused verifiers passed;
- the Audiobookshelf initializer's `--check` mode passed with one library in
  scope, an active key, and no token output;
- Python compilation, Bash parsing, and `git diff --check` passed;
- direct health, recent error logs, database integrity, UID/GID, mount modes,
  read-only enforcement, hashes, reader/OPDS, playback/range/resume,
  offline-session sync, DNS, HTTPS, WebSockets, Homarr, and WUD checks passed;
- the most recent scheduled appdata backup result remains successful and the
  next normal timer remains scheduled; no on-demand backup was run.

The production bootstrap dry-run stops before mutation at the existing
external boundary because `PAPERLESS_GPT_OPENAI_API_KEY` is absent. A second
dry-run used a mode-0600 temporary environment copy with an explicit
non-production placeholder, completed the entire dry-run path, and removed
the temporary copy. Production was not changed.

`provision/verify.sh` passed ZFS, the media data contract, free-space floors,
CT102/CT112 media access, future appdata permissions, HAOS recovery, and every
LXC mount/configuration check. It then stopped at the exact known live
inventory boundary:

```text
FAIL LXC 112 has 32 active containers; expected 35
```

This phase does not weaken the 35-container clean-build declaration or invent
an OpenAI credential to make the live inventory match it.

## Rollback and remaining boundaries

Rollback is a Git revert of the phase-3 implementation series followed by a
PVE pull, exact guest repository sync, and Compose redeployment on CT102 and
CT112. Re-run the previous Shelfarr configuration to make BookOrbit active if
rolling back the one-platform selection. Leave the additive Audiobookshelf
user/key in place unless a separate credential-removal task explicitly
deactivates it. Do not restore the compromised pre-rotation Shelfarr signing
value; use the protected post-rotation environment copy and current
application data.

Rollback does not delete either Alice source/final file, failed upload record,
completed download, request, application database, old image, or staging
artifact. Those are separate cleanup decisions.

Remaining explicit boundaries:

- no physical Audiobookshelf mobile client was available, so physical
  download/offline playback is not claimed;
- the completed-download import was exercised with a verified public-domain
  file already placed in the completed tree, not a new live Usenet or torrent
  transfer;
- canonical audiobook and ebook media remain outside the PBS appdata backup;
- the full destructive clean-host bootstrap and a complete media restore
  remain untested.
