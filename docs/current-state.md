# Current state

Last reconciled with the live PVE host on 2026-07-25. SnapOtter and
Stirling-PDF were deployed and verified during this reconciliation. Historical
migration evidence remains in
`docs/compose-project-migration.md` and `docs/apps-cleanup-2026-07-24.md`.

## Live architecture

| System | Live workload | Durable state |
|---|---|---|
| PVE `afa` | PVE 9.1.2; `rpool` and `vault` healthy | Git, `/root/.env`, appdata, shared data, PBS datastore |
| CT102 `servarr` | one 13-container Compose project | `/srv/appdata/docker` at `/docker`; `/vault/shared` at `/data` |
| CT110 `infra` | 9 active containers plus Cockpit, Samba, Tailscale | both canonical datasets mounted read-write |
| CT112 `apps` | 16 containers in seven Compose projects | appdata read-write; shared data read-only |
| CT113 `proxmox-backup-server` | PBS 4.2.3 | `vault/pbs_datastore`, quota 2 TiB |
| VM101 | running, unmanaged | outside repository scope |
| VM104 HAOS | stopped, unmanaged | outside repository scope |

Active container counts and names are kept in the README architecture tree.
All application Compose files, focused prepare/verify scripts, Cockpit/Samba
configuration, PBS client tooling, WUD runner, and restore logic are in Git.

The repository now additionally declares two four-container projects,
`paperless` and `bar-assistant`, plus the one-container `prometheus`, `loki`,
`immichframe`, `wizarr`, and `yt-dlp-web-ui` projects for CT112, private NPM
routes, and Homarr tiles. The 2026-07-25 live preflight found no existing
state, containers, routes, or Homarr entries for those projects; Apps ports
9090, 3100, 8080, and 5690 were free and appdata had about 522 GiB available.
Paperless deployment remains pending until the
Paperless/OpenAI variables documented in `.env.example` are added to
`/root/.env`. ImmichFrame likewise requires a scoped Immich API key. Prometheus,
Loki, and Wizarr require no new production secret, but their live deployment
and route/dashboard reconciliation are also unverified. At that preflight the
live Apps count remained 12 containers in five projects while the repository
declared 25 containers in twelve projects. Bar Assistant and yt-dlp Web UI add
Apps ports 8200-8202 and 3033, which were free, plus a narrow future read-write
bind of `/vault/shared/media/yt-dlp`; the directory and mount do not yet exist
live. Their four production credentials are documented in `.env.example`.

The three-container `snapotter` production project and one-container
`stirling-pdf` project are now live as separate Compose projects on Apps. They
use ports 1349 and 8084, private `snapotter.rafael.media` and
`pdf.rafael.media` routes, and two Homarr applications. All four containers
are healthy with zero restarts; focused verification observed SnapOtter 2.1.0
and Stirling-PDF 2.14.2. The five recovery variables documented in
`.env.example` are present in production `/root/.env` without entering Git.
The focused live rollout brings Apps to 16 containers in seven projects while
Git declares the complete 33-container, eighteen-project Apps generation.

The repository now additionally declares separate `slskd` and
`droppedneedle` projects, bringing the desired Apps generation to 31
containers in sixteen projects and the homelab total to 53 containers in
twenty projects. The 2026-07-25 read-only preflight found ports 5030, 50300,
and 8688 free; no matching containers, projects, appdata, NPM routes, or
DroppedNeedle Homarr application; healthy ZFS pools; about 521 GiB free
appdata and 19.9 TiB free on `vault/shared`; and NPM/Homarr SQLite integrity
`ok`. The existing music path is mapped to Apps UID 1000 and writable by that
owner. `/vault/shared/media/slskd` and both new LXC mounts do not exist live.
All six slskd recovery variables are absent from production `/root/.env`, so
this remains a committed recovery declaration rather than a live rollout.

The repository now also declares the one-container `audiobookshelf` and
`kavita` projects. The desired Apps generation is 33 containers in eighteen
projects and the homelab total is 55 containers in twenty-two projects. Their
ports 13378 and 5000 are free and neither appdata tree exists. Existing NPM
rows are stale (`192.168.0.109` for Audiobookshelf and `0.0.0.0` for Kavita);
Homarr has split duplicate app definitions, including `homarr.dev` dashboard
links. The committed reconcilers adopt those hostnames, make both routes
private, and replace the duplicates with 14 deterministic managed apps and 42
tiles across the three boards. Shared audiobook/podcast/book/comic/manga
directories already exist. Bootstrap adds only a narrow writable podcast
mount; all other libraries stay read-only. No production secret is required,
but this remains pending with the earlier complete Apps generation.

## New recovery implementation

The repository now declares and automates:

- canonical ZFS child datasets and properties;
- the four LXC identities, resources, root sizes, static IP/MAC addresses,
  mounts, TUN devices, GPU devices, startup order, and OS templates;
- Debian/Docker/PBS/native package installation;
- PBS datastore reuse, users/token/ACL, retention, GC, full verification, and
  the PVE backup client configuration;
- appdata copy or latest-snapshot restore;
- internal Docker mTLS generation and WUD configuration;
- native Cockpit account, Samba password database, and Tailscale state restore;
- all Compose preparation/deployment and end-to-end verification.

The entrypoint is `./bootstrap.sh`; full behavior and safety constraints are in
`docs/rebuild.md`. A read-only live dry-run completed successfully. A real
clean-host rebuild has not been performed, so complete bare-metal recovery is
not yet verified.

## Native state capture

`scripts/capture-native-recovery.sh` ran successfully on 2026-07-24. It briefly
stopped only Tailscale and SMB, copied consistent state into appdata, restarted
both, and verified Tailscale online plus the `afa` Samba account. The captured
files are mode 0600 and mapped to guest root:

```text
/srv/appdata/docker/
├── infra-samba/private/passdb.tdb
├── tailscale/tailscaled.state
└── recovery/
    ├── infra-afa.shadow-hash
    ├── pbs-root.shadow-hash
    └── pbs-appdata.key
```

Snapshot `host/afa-appdata/2026-07-24T12:38:45Z` now contains these files and
the final same-day Apps/NPM/Obsidian state. Its upload and server-side
verification succeeded. A targeted client restore recovered all five native
files and matched their live bytes, UID, GID, and mode.

## Data and database policy

- Large application-independent data is under `/vault/shared`.
- Persistent Docker state and application-local databases are under
  `/srv/appdata/docker`.
- Immich retains PostgreSQL 14/VectorChord; Jellystat retains private
  PostgreSQL 18; Mealie uses SQLite. The declared Paperless project retains
  private PostgreSQL 18 and Valkey. There is no central PostgreSQL service.
- Prometheus and Loki retain their local TSDB/filesystem data under appdata
  with 30-day retention. Loki has no declared log shipper yet.
- Wizarr retains its SQLite-backed application state under appdata.
  ImmichFrame is environment-driven and keeps an optional Config override
  directory under appdata.
- Bar Assistant retains SQLite application data, its Meilisearch index, and
  Redis session/cache state under appdata. yt-dlp keeps only configuration,
  SQLite, and sessions there; downloads belong under
  `/vault/shared/media/yt-dlp`.
- SnapOtter retains files/AI packs, private PostgreSQL 17, Redis 8, logical
  dumps, and restore-test evidence under appdata. Stirling-PDF retains its
  settings/account database, custom files, pipelines, and OCR data there.
- slskd retains configuration, databases, logs, and its disk-backed share
  index under appdata. DroppedNeedle retains configuration, SQLite databases,
  cache, plugins, and import staging there. The music library and slskd
  downloads stay under `/vault/shared`; narrow separate read-write binds avoid
  exposing unrelated media but may make DroppedNeedle use its safe
  copy-and-remove import fallback.
- Audiobookshelf retains its SQLite configuration, migrations, metadata,
  covers, logs, and application backups under appdata. Kavita retains its
  SQLite state, users, progress, covers, cache, and built-in backups there.
  Audiobooks, podcasts, books, comics, and manga remain under `/vault/shared`;
  only podcasts receive a narrow writable Apps bind.
- Guest roots contain replaceable packages, images, caches, logs, and runtime
  configuration only.
- `/vault/shared` still lacks broad independent backup; PBS resides on the same
  `vault` pool and does not protect against pool loss. A two-generation Proton
  backup is implemented for only the Obsidian and photos subtrees, but is not
  protection until login, first upload, and restore tests succeed.

## Backup and updates

The daily PVE timer freezes CT102/110/112, snapshots appdata, resumes the
guests, and uploads encrypted appdata plus `/root/.env`. Retention is 7 last,
14 daily, 8 weekly, and 12 monthly; prune is daily, GC weekly, and full
verification monthly. A successful backup alone starts sequential WUD updates.
The SnapOtter PostgreSQL pre-backup hook is installed live and produced a
current logical dump, roles, row counts, and checksums before passing an
isolated PostgreSQL 17 restore test. The declared Paperless deployment adds a
separate pre-backup logical PostgreSQL dump hook; that hook remains pending
live verification with the rest of the Paperless deployment.
Prometheus and Loki are pinned, excluded from WUD, and require manual,
backup-first updates with focused config/readiness/query checks.
ImmichFrame and Wizarr use their upstream `latest` channels and join the
backup-gated WUD route.

Bar Assistant uses four non-`latest` major/minor channels and is excluded from
WUD so it can be updated as one compatibility cohort. yt-dlp Web UI uses the
currently published upstream GHCR `latest` channel and joins the backup-gated
WUD route; both documented `v4` registry references were absent during the
2026-07-25 validation.

SnapOtter's application and Stirling-PDF use their upstream `latest` channels
and are live in the backup-gated WUD route with direct post-replacement HTTP
checks. SnapOtter PostgreSQL 17 and Redis 8 are not `latest`; both have
`wud.watch=false` and require manual, backup-first migration. The installed
SnapOtter pre-backup hook adds a portable PostgreSQL dump, and the successful
isolated restore-test evidence is retained under appdata.

slskd is pinned to the exact 0.25.1 release documented and tested by
DroppedNeedle and has `wud.watch=false`; update it manually as a compatibility
task after backup and an end-to-end search/download/import test. DroppedNeedle
uses the upstream `latest` production channel and joins backup-gated WUD. Its
startup upgrade path retains and validates SQLite/settings working copies, and
the WUD runner adds a direct `/health` check.

Audiobookshelf and Kavita use their upstream stable `latest` channels and join
backup-gated WUD. Both run as Apps UID/GID 1000:1000 and receive direct
post-replacement HTTP checks. Kavita's legacy ordered-upgrade rule applies
only to pre-v0.7.6 databases; any future upstream-mandated ordered upgrade must
pause WUD and be handled as a migration task.

The new 246.784 GiB logical snapshot completed at 14:47 CEST, reused 99.1%,
removed its temporary ZFS snapshot, and successfully handed off to WUD; no
update was reported. Verify-new finished `OK` at 15:44 CEST. Prior evidence
also includes a 10,018-file temporary restore and a 200-file
byte/UID/GID/mode sample. This proves encrypted backup integrity and sampled
restore paths, not the new complete bootstrap.

The repository also installs a disabled PVE Proton unit. Once explicitly
activated, it uses a daily persistent due-check to run one real cycle every 14
days for the Syncthing-received Obsidian vault, the 194 GB photos tree, and
`/root/.env`. Each source retains at most two remote generations; all uploaded
archive parts are downloaded and SHA-256 checked. This has not yet been
deployed, authenticated, or restore-tested live.

## Known external or unfinished items

- PVE installation and physical pool/disk creation remain manual. Bootstrap
  imports an existing `vault` and never guesses destructive disk operations.
- The router is verified only as a contract: DNS must remain
  `192.168.0.100`, and TCP 80/443 must forward to `192.168.0.110`.
- VM101 and HAOS VM104 are intentionally ignored.
- Obsidian Syncthing is deployed receive-only, but laptop/phone pairing, GUI
  authentication/private routing, multi-source Proton deployment/login, first
  checksum-restored Obsidian/photos/environment generations, and PVE timer
  enablement remain user steps.
- Retained migration snapshots, volumes, images, dumps, and Immich rollback
  assets still require a separate explicitly authorized cleanup.
- Paperless deployment requires new production database/admin/API secrets and
  an OpenAI API key in `/root/.env`. Paperless-GPT will send selected document
  content to OpenAI; automatic PDF upload/replacement remains disabled.
- Prometheus/Loki deployment, private NPM routes, Homarr tiles, and a
  post-deployment backup remain unverified live. Loki is an ingestion/query
  backend rather than a log collector; add Grafana Alloy in a separate task
  before expecting host or container logs to appear.
- ImmichFrame/Wizarr deployment, private NPM routes, Homarr tiles, and a
  post-deployment backup remain unverified live. ImmichFrame needs a dedicated
  read-only Immich API key; Wizarr needs first-run administrator setup and a
  verified Jellyfin invitation flow.
- Bar Assistant/yt-dlp deployment, the targeted yt-dlp shared-data bind,
  eighteen consolidated private NPM routes, sixteen managed Homarr apps, and a
  post-deployment backup remain unverified live. Add the four credentials from
  `.env.example` before a complete committed apply.
- SnapOtter and Stirling-PDF are deployed with their private NPM routes,
  Homarr apps, recovery variables, logical dump, and isolated restore test
  verified. Their forced first-login password changes (and Stirling-PDF MFA)
  remain user steps. The deployment happened after the latest successful
  encrypted appdata backup; do not claim post-deployment backup protection
  until the next scheduled run completes successfully.
- slskd/DroppedNeedle deployment, two narrow shared-data mounts, two private
  NPM routes, two Homarr apps, first-run DroppedNeedle administrator setup,
  slskd API pairing, a permitted search/download/import test, and a
  post-deployment backup remain unverified live. Add the six slskd variables
  from `.env.example`; the repository does not add a public TCP 50300 router
  forward.
- Audiobookshelf/Kavita deployment, the narrow podcast mount, adoption of the
  two stale NPM routes, Homarr duplicate cleanup, first administrators/library
  setup, representative playback/reading, and a post-deployment backup remain
  unverified live. They add no recovery secret.
- n8n and Pulse are declared as separate Infra projects. The desired Infra
  generation is 11 containers in five projects with a 4 GiB LXC limit, and the
  homelab total is 57 containers in twenty-four projects. Pulse's read-only PVE
  source covers every LXC; unified agents in CT102/110/112 cover Docker.
  Deployment evidence is in `docs/n8n-pulse-addition-2026-07-25.md`.
