# Books, audiobooks, podcasts, and music — delivery plan

Date: 2026-07-25

Status: approved architecture and phased implementation brief. This document
does not record a deployment.

The implementation is deliberately split into six sequential parts. Each part
must leave a usable, verified stopping point and a commit that preserves
one-command recovery. Do not run the parts in parallel: all six touch some
combination of shared storage, bootstrap, WUD, Nginx Proxy Manager, Homarr, and
end-to-end verification.

The copy-ready prompts for the six agents are in
`docs/media-pipeline-agent-prompts-2026-07-25.md`.

## Outcome

The finished system has four clear media pipelines and one first-class bridge
between ebooks and audiobooks:

```text
Books and audiobooks

request
  -> Shelfarr
  -> existing Prowlarr and qBittorrent/NZBGet
  -> canonical ebook and audiobook folders
     -> BookOrbit for reading
     -> Audiobookshelf for listening
     -> automatic exact-pair staging
        -> Storyteller import and alignment
        -> Storyteller apps / readaloud EPUB

Podcasts

subscription
  -> PinePods
  -> PinePods web/mobile/desktop or GPodder-compatible client

Music

discovery/request
  -> Aurral
  -> Lidarr
     -> Prowlarr and qBittorrent/NZBGet
     -> Soularr and slskd
  -> canonical music library
     -> Navidrome
     -> Jellyfin
     -> SMB and Kew
  -> optional Aurral flow library
     -> Navidrome
```

## Decisions that agents must not reopen

### Rolling application images

Application containers use the upstream documented `latest` tag or another
upstream rolling stable channel. A project being young or fast-moving is not,
by itself, a reason to pin its application image.

Every eligible rolling application is enrolled in the existing
success-after-backup, sequential WUD route:

- `wud.watch=true`;
- digest watching enabled;
- trigger `docker.backupgated`;
- a meaningful direct health/readiness check in Compose;
- an application-specific check in the sequential runner;
- image pruning remains disabled so the prior image is locally available.

If an upstream project does not publish `latest`, use its documented rolling
stable channel and record the exception.

Databases, caches, message brokers, and other state engines are different.
Keep their major versions explicit, set `wud.watch=false`, create
application-consistent logical dumps where applicable, and treat every major
change as a migration with an isolated restore test. This is not an exception
to the application-image decision; it is the repository's database safety
policy.

### One canonical file owner

Shelfarr is the only application allowed to move, rename, and organize
canonical ebook and audiobook files after acquisition.

- BookOrbit reads canonical ebooks, PDFs, and comics. Start with physical
  rename and embedded-metadata writing disabled.
- Audiobookshelf reads canonical audiobooks. Its configuration, metadata,
  progress, covers, and application backups remain writable in appdata, but
  its audiobook library remains read-only.
- Storyteller never references, moves, hard-links, or rewrites the canonical
  files. It receives isolated copies and owns those copies.
- Prowlarr never needs a media mount. The download clients see download paths,
  not application appdata.

The same ownership rule applies to music: Lidarr owns the permanent music
library. Navidrome and Jellyfin read it. Aurral flow downloads live in a
separate flow library. Soularr supplies Lidarr through slskd; it does not
become a second permanent-library owner.

### Storyteller is a normal path, not a rare experiment

When the system owns both a DRM-free EPUB and a matching DRM-free audiobook,
the normal expectation is that the pair becomes available to Storyteller.
Storyteller is not limited to a few hand-picked titles.

For new Shelfarr imports, both format branches must use the same normalized
relative book directory key. The exact template syntax must be taken from the
current Shelfarr release, but the resulting structure should be equivalent to:

```text
ebooks/<book-key>/Book.epub
audiobooks/<book-key>/Book.m4b
```

or, for multi-file audio:

```text
audiobooks/<book-key>/audio/01 - Chapter.mp3
```

The Storyteller pairing reconciler uses that shared relative key:

- exactly one EPUB side plus one supported audiobook side is a confident pair;
- it stages isolated copies atomically in one per-book folder;
- it records source identity, size, modification time, hashes, state, and the
  last error in a durable manifest;
- it is idempotent and does not recopy unchanged pairs;
- ambiguous, incomplete, changed, or conflicting pairs enter a review report;
- it never guesses by fuzzy title alone and never mutates either source tree.

This gives nearly all clean new acquisitions an automatic route while keeping
legacy and ambiguous material safe.

Storyteller should auto-import confident pairs using an upstream-supported
import mode. Because the input stage already contains disposable copies,
moving a staged copy into Storyteller-owned storage is acceptable; moving a
canonical source is not. Use a supported Storyteller processing API or the
official `stalign` tool to queue alignment only if the current upstream
interface is stable and can be verified. Never automate alignment by editing
Storyteller's database. If upstream exposes no supported non-interactive
trigger, auto-import every confident pair and document the one remaining bulk
UI action for the “ebook + audiobook, not aligned” view.

### Parallel migration before retirement

Existing services remain available until their replacement has passed
representative use:

- Kavita stays available while BookOrbit is deployed and reading,
  KOReader/Kobo/OPDS, user, progress, and metadata behavior are accepted.
- Readarr stays available while Shelfarr completes ebook and audiobook
  acquisition tests.
- Audiobookshelf keeps its existing podcast data until PinePods subscription,
  playback, download, client sync, backup, and restore checks pass.
- DroppedNeedle and its appdata remain available until the Aurral/Lidarr/
  Soularr/slskd path imports a representative album and Navidrome serves it.

Retirement means removing a service from normal use and automatic startup only
after explicit acceptance. It does not mean deleting appdata, databases,
images, downloads, or media. Destructive cleanup is a later separately
authorized task.

### Private exposure

All new web services are private to LAN and Tailscale through Nginx Proxy
Manager. Do not add public DNS, router forwarding, or a public NPM route.
Use application authentication. Preserve WebSockets where upstream requires
them.

### LXC placement and Compose project boundaries

The placement of the new primary applications is fixed:

| LXC | Primary application | Repository project |
|---|---|---|
| CT102 `servarr` | Shelfarr | `hosts/servarr/shelfarr` |
| CT102 `servarr` | Soularr | `hosts/servarr/soularr` |
| CT112 `apps` | BookOrbit | `hosts/apps/bookorbit` |
| CT112 `apps` | Storyteller | `hosts/apps/storyteller` |
| CT112 `apps` | PinePods | `hosts/apps/pinepods` |
| CT112 `apps` | Aurral | `hosts/apps/aurral` |
| CT112 `apps` | Navidrome | `hosts/apps/navidrome` |

Soularr belongs on CT102 with Lidarr, Prowlarr, and the existing download
automation. It reaches the existing slskd service privately on CT112 and uses
the CT102 read-write `/data` view of the same host-backed slskd download tree.
Both guest paths must be verified to resolve to
`/vault/shared/media/slskd`; no broader CT112 mount and no new CT102 shared
mount are required.

Each primary application above is its own repository-managed Docker Compose
project with its own Compose file, lifecycle, health checks, and verification.
Any database, cache, broker, worker, required companion, or other
application-private supporting container belongs in that primary
application's Compose file and private project network. This includes
BookOrbit's PostgreSQL/pgvector service, PinePods' PostgreSQL and Valkey
services, any Shelfarr-required Libation companion, and any containerized
Storyteller reconciler or worker.

Do not create one catch-all media-pipeline Compose project and do not share an
application-private database or cache between projects. Existing first-class
services and projects remain independent: in particular, `servarr-hello` is
not absorbed into Shelfarr or Soularr, and slskd remains its existing CT112
project rather than becoming a Soularr-private sidecar.

### Authorized acquisition only

Agents may connect Shelfarr, Aurral, Soularr, and the existing download clients
to sources and credentials already selected and controlled by the user. They
must not invent, enable, or document unauthorized direct-download sources,
indexers, credentials, or DRM-removal workflows. Storyteller receives only
DRM-free media the user owns or is authorized to process.

## Responsibility matrix

| Service | Primary responsibility | Canonical media access | May change canonical files? |
|---|---|---|---|
| Shelfarr | requests, search orchestration, completed-download import, ebook/audiobook organization | downloads RW; ebook/audiobook roots RW | yes, sole owner |
| Prowlarr | indexer proxy | none | no |
| qBittorrent/NZBGet | transfer | downloads RW | no |
| BookOrbit | ebook/PDF/comic catalogue, reading, metadata, device sync | book roots RO initially | no |
| Audiobookshelf | audiobook streaming, mobile/offline playback, progress | audiobook root RO | no |
| Storyteller reconciler | exact-pair detection and isolated staging | ebook/audiobook roots RO; inbox RW | no |
| Storyteller | pair import, alignment, readaloud library and progress | Storyteller-owned paths RW | only its copies |
| PinePods | podcast subscriptions, downloads, playback and sync | PinePods podcast subtree RW | yes, within its subtree |
| Aurral | music discovery, requests, and optional generated flows | own data and flow root RW; Lidarr API | no permanent-library writes |
| Lidarr | permanent music library ownership | downloads and music root RW | yes, sole owner |
| Soularr | Soulseek acquisition for Lidarr | slskd downloads RW; Lidarr/slskd APIs | no direct permanent-library writes |
| slskd | Soulseek transfer | slskd download root RW; music share RO | no |
| Navidrome | dedicated music streaming | music and flow roots RO | no |
| Jellyfin | secondary music playback | music root RO | no |

## Data and storage contract

The agents must verify the current upstream layouts before finalizing the
container paths, but the host data classes are fixed:

```text
/srv/appdata/docker/
├── shelfarr/               # database/config/queue state
├── bookorbit/              # app state plus application-local DB and dumps
├── audiobookshelf/         # existing config/metadata/progress
├── storyteller/            # database/config/manifests/cache where supported
├── pinepods/               # app state, DB/cache state and logical dumps
├── aurral/                 # app state
├── soularr/                # config/state
└── navidrome/              # database/cache/config

/vault/shared/media/
├── books/
│   ├── ebooks/
│   └── pdfs/
├── comics/
├── mangas/
├── audiobooks/
├── podcasts/
│   └── pinepods/
├── music/
├── aurral-flows/
└── storyteller/
    ├── inbox/
    └── library/
```

`/srv/appdata/docker` is included in the encrypted appdata backup.
`/vault/shared` is not. Podcast episodes, canonical books/audiobooks/music,
Aurral flows, and large Storyteller assets therefore need to be classified
explicitly as user data or reproducible derived data in each service's restore
documentation. Never imply that PBS appdata snapshots protect those files.

Prefer appdata for small irreplaceable Storyteller database/config/manifest
state and `vault/shared` for large source copies, alignment work, and produced
readaloud assets if the current Storyteller layout supports that split. If
Storyteller requires one indivisible `/data` tree, the Storyteller agent must
measure projected growth and choose a documented layout that cannot silently
fill `rpool/appdata`.

Use only narrow new read-write mounts. Do not make CT112's existing read-only
`/data` mount broadly writable. Do not recursively change ownership or modes
on shared media or appdata.

## Live baseline observed before writing this plan

Read-only inspection on 2026-07-25 found:

- PVE 9.1.2 with healthy pools;
- CT102, CT110, CT112, and CT113 running;
- `rpool/appdata/docker` at 262 GiB used with about 488 GiB available;
- `vault/shared` at 11.3 TiB used with about 19.9 TiB available;
- the appdata backup timer active, its last run successful, and no independent
  WUD timer;
- CT102 running the 13-container `servarr-hello` project, including healthy
  Prowlarr, qBittorrent, NZBGet, Lidarr, and Readarr;
- CT102 has `/vault/shared` read-write at `/data`;
- CT112 running Audiobookshelf, Kavita, slskd, DroppedNeedle, Jellyfin, and the
  other declared Apps projects;
- CT112 has shared media read-only at `/data`, plus narrow read-write mounts
  for podcasts, music, slskd downloads, and yt-dlp downloads;
- the existing book, audiobook, podcast, comic, and manga directories are
  nearly empty, while the music directory contains about 23 GiB;
- the PVE host has 8 logical CPUs and about 14 GiB available memory at idle;
- CT112 has 5 vCPUs, 12 GiB assigned, and about 5.5 GiB available at idle.

The Storyteller phase must therefore treat compute and memory as a measured
capacity gate. It may increase CT112's declared limit only after checking live
host headroom and keeping safe reserve for PVE and the other guests. Otherwise
use conservative single-job processing and prove that unrelated Apps remain
healthy.

## Six sequential parts

| Part | Scope | Deployable stopping point |
|---:|---|---|
| 1 | shared contract, paths, permissions, secret placeholders, backup/WUD/verification scaffolding | current services unchanged; bootstrap and dry-run understand the future paths |
| 2 | Shelfarr ebook branch plus BookOrbit | a user-owned ebook travels through Shelfarr into BookOrbit; Kavita remains available |
| 3 | Shelfarr audiobook branch plus hardened Audiobookshelf integration | a user-owned audiobook travels through Shelfarr into Audiobookshelf; Storyteller-compatible key is present |
| 4 | Storyteller and automatic pair reconciliation/alignment queue | a matched user-owned pair is copied, imported, aligned or safely queued, and playable without canonical mutation |
| 5 | PinePods | podcast subscription, download, playback, client sync, database dump and restore test pass; ABS data remains recoverable |
| 6 | Aurral, Soularr, Navidrome, music-owner reconciliation, and final convergence | a requested album reaches Lidarr through each intended route and streams in Navidrome/Jellyfin; all six parts pass together |

Each part has a detailed copy-ready agent prompt in the companion document.

## Cross-cutting definition of done

Every phase must:

1. read `AGENTS.md`, this plan, the prior phase evidence, and current official
   upstream documentation;
2. inspect live PVE, mounts, Docker, appdata, storage, network, and backup state
   read-only before making changes;
3. preserve secrets in `/root/.env` and add placeholders plus comments to
   `.env.example` without logging production values;
4. keep reproducible configuration, provisioning, verification, proxy, Homarr,
   backup hooks, restore steps, and update policy in Git;
5. run `docker compose config` before every deployment;
6. deploy through the repository, synchronize `/opt/dothomelab`, and keep
   `DEPLOYED_COMMIT` traceable;
7. verify direct health, logs, UID/GID and mount modes, DNS, private HTTPS,
   application behavior, backup coverage, and rollback behavior;
8. use a user-owned or public-domain sample for workflow tests and preserve
   hashes so source-byte mutation is detectable;
9. leave earlier services usable when a later integration fails;
10. record exact evidence, remaining first-run user actions, rollback steps,
    and anything not verified;
11. commit and make the completed phase retrievable through the repository's
    normal clone path.

Do not call a phase complete because containers are merely running. Its
representative end-to-end workflow and data ownership boundary must pass.

## Final user experience

After all six parts:

- Shelfarr is the request surface for ebooks and audiobooks.
- BookOrbit is the canonical reading/progress surface for ebooks, PDFs, and
  comics, including configured Kobo/KOReader/OPDS paths as applicable.
- Audiobookshelf is the canonical listening/progress surface for audiobooks.
- Any clean acquisition with both a matching EPUB and audiobook normally
  appears in Storyteller automatically; uncertain legacy pairs are visible in
  a review report.
- PinePods is the only active podcast subscription/progress system.
- Aurral is the music discovery/request surface, Lidarr owns the permanent
  library, Soularr supplies Soulseek acquisitions through slskd, Navidrome is
  the dedicated Subsonic server, Jellyfin remains a read-only secondary
  scanner, and Kew reads the SMB-mounted music directory locally.

## Primary upstream references

- [Shelfarr documentation](https://shelfarr.org/getting-started.html)
- [Shelfarr repository and BookOrbit integration notes](https://github.com/Pedro-Revez-Silva/shelfarr)
- [BookOrbit repository and Docker quick start](https://github.com/bookorbit/bookorbit)
- [BookOrbit installation guide](https://bookorbit.app/installation)
- [Audiobookshelf Docker guide](https://audiobookshelf.org/docs/documentation/install/docker/)
- [Storyteller self-hosting guide](https://storyteller-platform.dev/docs/installation/self-hosting/)
- [Storyteller adding/import-mode guide](https://storyteller-platform.dev/docs/managing/adding/)
- [Storyteller current scanner and import modes](https://storyteller-platform.dev/blog/20260525_scanner/)
- [Storyteller alignment guide](https://storyteller-platform.dev/docs/managing/aligning/)
- [Official `stalign` announcement](https://storyteller-platform.dev/blog/20260305_stalign/)
- [PinePods repository and Compose quick start](https://github.com/madeofpendletonwool/PinePods)
- [Aurral repository](https://github.com/lklynet/aurral)
- [Aurral documentation](https://docs.aurral.org/)
- [Soularr repository](https://github.com/mrusse/soularr)
- [Navidrome Docker guide](https://www.navidrome.org/docs/installation/docker/)
