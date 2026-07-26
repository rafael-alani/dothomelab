---
name: homelab-operator
description: Operate Rafael's Git-rebuilt Proxmox homelab safely.
---

# Homelab operator

## Mission

Given PVE 9 node `afa`, importable `vault`, current `/vault/shared`,
`/srv/appdata/docker`, `/root/.env`, and this repository, `./bootstrap.sh` must
recreate the LXC homelab without LXC guest roots and restore managed HAOS
VM104 from canonical appdata. VM101 and physical disk provisioning are out of
scope.

Priority order:

1. Active user request.
2. Live state observed on the machines.
3. This repository.
4. This snapshot document.

Always inspect live state first. Verify application changes proportionately; only claim backup/recovery success when the task includes them and evidence exists.

## Repository end-state contract

Every change and commit must preserve this invariant: given clean PVE 9,
importable `vault` with `/vault/shared`, current Docker appdata (restored,
supplied with `--appdata-source`, or via `--restore-latest`), `/root/.env`,
declared hardware, and unchanged router, `./bootstrap.sh` recreates the managed
LXCs without guest-root backups.

Keep reproducible desired state and verification in Git; keep secrets/durable data
in recovery inputs. Update provisioning, Compose, `.env.example`, verification,
and docs together. Completed recovery changes must be committed and retrievable
by the clone path, contain no production secrets, pass relevant checks, and
record unverified or external prerequisites.

## Access

```bash
ssh root@192.168.0.250
ssh root@192.168.0.250 -- pct exec <CTID> -- <command>
ssh root@192.168.0.250 "pct exec <CTID> -- bash -lc '<commands>'"
ssh afa@192.168.0.126  # VM101 only
```

Use `pct exec`, not SSH inside LXCs. The operator uses `~/.ssh/homelab` for
`192.168.0.*` and `~/.ssh/github` for GitHub via SSH config. Never disable host
key checking or print/store credentials, tokens, private keys, or production
environment values.

## Inventory

Observed 2026-07-26:

| ID | Name | Address | State and role |
|---:|---|---|---|
| host | `afa` | `192.168.0.250` | PVE 9.1.2, ZFS, LXC lifecycle, PBS client |
| 101 | VM101 | `192.168.0.126` | running; unmanaged |
| 102 | `servarr` | `192.168.0.102` | Debian 12; 17 Docker containers |
| 104 | `homeassistant` | `192.168.0.125` | HAOS 18.1; managed recovery |
| 110 | `infra` | `192.168.0.110` | Debian 12; 11 containers + native services |
| 112 | `apps` | `192.168.0.112` | Debian 12; 41 containers in 23 active projects |
| 113 | `proxmox-backup-server` | `192.168.0.159` | Debian 13; PBS 4.2.3 |

See the README for the exact architecture tree and container names.

## Network contract

- PVE uses `vmbr0`, `192.168.0.250/24`, gateway `192.168.0.1`.
- Clean-build LXCs use static addresses and preserved MACs from
  `provision/inventory.env`; router DHCP reservations are not required.
- Pi-hole runs on Infra but binds secondary service address `192.168.0.100`.
- Nginx Proxy Manager runs on Infra. Applications publish on their LXC address;
  NPM routes hostnames to those ports.
- The unchanged router must advertise DNS `192.168.0.100` and forward public
  TCP 80/443 to `192.168.0.110`. The repository does not mutate the router or
  expose new services publicly.
- Central WUD reaches Apps/Servarr Docker on TCP 2376 with mutual TLS. Never
  expose unauthenticated Docker TCP/2375.
- Verify with `pct config`, `hostname -I`, `ip route`, DNS queries, NPM APIs,
  and external HTTPS checks.

## Storage

| Data | Canonical location |
|---|---|
| Docker state and application databases | `rpool/appdata/docker` → `/srv/appdata/docker` |
| Shared media/downloads/Obsidian | `vault/shared` → `/vault/shared` |
| PBS datastore | `vault/pbs_datastore` → `/vault/pbs_datastore`, quota 2 TiB |
| Compose/scripts/docs | this Git repository |
| Secrets | production `/root/.env`, never Git |
| LXC guest roots | replaceable OS/packages/images/logs/cache |
| HAOS VM104 | verified VMA and native backups under `/srv/appdata/docker/home-assistant` |

`rpool` is SSD-backed; `vault` is HDD-backed. `/vault/backups` is legacy
directory storage, not PBS. `/vault/data` contains PVE-managed disks. Never
treat either as scratch.

Mounts:

- CT102: shared RW at `/data`; appdata RW at `/docker`.
- CT110: shared RW at `/vault/shared`; appdata RW at canonical path.
- CT112: shared RO at `/data`; appdata RW at canonical path;
  `/vault/shared/media/yt-dlp` is additionally mounted RW at `/downloads`.
  The existing music library is additionally mounted RW at `/music`, and
  `/vault/shared/media/slskd` is mounted RW at `/slskd-downloads`; these two
  narrow mounts support slskd and retained DroppedNeedle rollback without
  granting write access to the rest of shared media. A persistent narrow host
  bind exposes `/vault/shared/media/aurral-flows` through Aurral's appdata path
  without adding an LXC mount; Aurral writes it and Navidrome reads it.
  `/vault/shared/media/podcasts` is additionally
  mounted RW at `/podcasts`; PinePods receives only its `/podcasts/pinepods`
  subtree. Audiobookshelf's retained podcast state has no writable podcast
  bind after phase-5 acceptance. A persistent narrow host bind exposes
  canonical audiobooks through Audiobookshelf's appdata path; only
  Audiobookshelf receives that tree read-write for its verified native
  stream-copy metadata embed tool. Grimmory and other readers see audiobooks
  read-only through `/data`. A separate persistent narrow host bind exposes
  canonical ebooks through Grimmory's appdata path; only Grimmory receives
  that tree read-write.
  `/vault/shared/media/storyteller` is mounted RW at `/storyteller` for
  disposable verified staging and Storyteller-owned derived media. Its
  canonical ebook and audiobook inputs remain read-only through `/data`.
- CT113: PBS dataset at `/mnt/datastore/appdata`.

All LXCs are unprivileged. Host IDs `101000:101000` map to guest `1000:1000`;
PBS host IDs `100034:100034` map to guest `34:34`. Inspect `findmnt`, `stat`,
`namei`, and `pct config` before permissions work. Never recursively
`chown`/`chmod` shared or appdata paths without mapping every consumer.

## One-command recovery

```bash
git clone https://github.com/rafael-alani/dothomelab.git /root/dothomelab
cd /root/dothomelab
./bootstrap.sh
```

Useful modes:

```bash
./bootstrap.sh --dry-run
./bootstrap.sh --appdata-source /recovery/appdata/docker
./bootstrap.sh --restore-latest
./provision/verify.sh
```

The script validates PVE/network/hardware, imports `vault`, reconciles child
datasets, downloads templates, restores VM104, creates four LXCs, installs Docker/PBS/native
packages, restores credentials, generates Docker mTLS, deploys thirty-two
Compose projects, configures backups/WUD, and verifies the result. It never
creates or formats physical pools/disks. Full behavior and failure semantics
are in `docs/rebuild.md`.

The production env is Compose dotenv syntax and may not be shell-sourceable.
Use `hosts/common/load-env.sh`; never `source /root/.env` directly.

## Repository map

```text
bootstrap.sh
provision/{bootstrap.sh,inventory.env,verify.sh}
hosts/
├── common/                 # Docker base, dotenv parser, Docker API TLS
├── servarr/{cleanuparr,hello,shelfarr,soularr}/
├── infra/
│   ├── services/           # Pi-hole, Homarr, NPM, DDNS, hello, Portainer
│   ├── cockpit/            # Cockpit/Samba/Avahi/WSDD
│   ├── tailscale/          # native Tailscale with appdata state
│   ├── wud/                # central WUD and sequential runner
│   ├── obsidian-sync/      # Syncthing + multi-source Proton CLI runner
│   └── {n8n,pulse}/        # private automation and fleet monitoring
├── apps/{audiobookshelf,aurral,bar-assistant,bookorbit,droppedneedle,immich,immichframe,kavita,loki,media,mealie,navidrome,paperless-gpt,paperless-ngx,pinepods,prometheus,services,slskd,snapotter,stirling-pdf,storyteller,wizarr,yt-dlp-web-ui,zotero-webdav}/
└── pbs/                    # PBS package/datastore/job/identity installer
backup/{pbs,proton}/        # PVE backup, restore, Proton, and WUD units
scripts/                    # deploy, sync, PKI, native recovery capture
docs/
```

Guest deployments are Git archives at `/opt/dothomelab`. `DEPLOYED_COMMIT`
must match the intended Git commit. `scripts/sync-guest-repo.sh` stages the new
copy and retains the prior copy as `/opt/dothomelab.previous`.

## Application and database policy

- CT102 project `servarr-hello`: Gluetun plus download/Arr services,
  Deunhealth, Portainer/Agent. Gluetun, qBittorrent, NZBGet, and Prowlarr share
  one network namespace; update that cohort with Compose.
- CT102 project `soularr` supplies Lidarr from CT112 slskd through the shared
  slskd download tree. Its scheduler defaults off until Lidarr monitoring is
  curated; it never mounts the permanent music library directly.
- CT102 project `cleanuparr` is the supported stalled-torrent controller for
  qBittorrent plus Sonarr, Radarr, Lidarr, and Readarr. It is authenticated and
  LAN-only, uses the exact private Servarr network, has no shared-data mount,
  and persists only under canonical appdata. Its exact 2.10.0 digest is
  manually updated with `wud.watch=false`. Queue Cleaner runs every 30 minutes:
  public stalls need 12 strikes, private stalls need 48, meaningful 64 MiB
  progress resets strikes, metadata stalls need 12, and slow/failed-import
  cleaners remain off. Internet/client failures fail closed. Removal goes
  through the owning Arr with blocklisting, and replacement-only Seeker
  searches every five minutes; never delete a managed stalled torrent directly
  in qBittorrent.
- CT110: `infra-services`, `n8n`, `pulse`, `wud`, `obsidian-sync`, plus native
  Cockpit/Samba/Tailscale.
- CT112: `audiobookshelf`, `aurral`, `bar-assistant`, `bookorbit`, `grimmory`,
  `immich-migration`, `immichframe`, `kavita`, `loki`, `media`, `apps-mealie`, `paperless-ngx`,
  `navidrome`, `paperless-gpt`, `pinepods`, `prometheus`, `apps-services`, `slskd`,
  `snapotter`, `stirling-pdf`, `storyteller`, `wizarr`, `yt-dlp-web-ui`,
  `zotero-webdav`. DroppedNeedle is a stopped rollback profile, not an active
  project.
- Immich uses its supported PostgreSQL 14/VectorChord image.
- Jellystat uses private PostgreSQL 18. Mealie uses SQLite.
- Paperless-ngx uses private PostgreSQL 18 and Valkey. Paperless-GPT sends
  document content to the configured OpenAI API and remains private to the LAN
  and Tailscale because it has no native authentication. They are separate
  Compose projects joined only by the external `dothomelab-paperless` bridge;
  deploy Paperless-ngx before Paperless-GPT.
- Paperless update policy is explicit:
  - `paperless-ngx` uses `paperless-ngx:latest` and is enrolled in the
    backup-gated WUD route.
  - `paperless-gpt` uses `paperless-gpt:latest` and is enrolled in the
    backup-gated WUD route.
  - `paperless-db` uses `postgres:18`, not `latest`, and has
    `wud.watch=false`. Update it manually only after a current logical dump and
    successful isolated restore test; PostgreSQL major changes are migration
    tasks.
  - `paperless-broker` uses `valkey/valkey:9`, not `latest`, and has
    `wud.watch=false`. Update it manually with Compose after a Paperless
    compatibility check; Valkey major changes are migration tasks.
- Observability update policy is explicit:
  - `prometheus` uses the current LTS image `prom/prometheus:v3.13.1`, not
    `latest`, and has `wud.watch=false`. Update it manually within the 3.13 LTS
    line with readiness/query verification; treat a later major or LTS-line
    change as a TSDB migration task.
  - `loki` uses `grafana/loki:3.7.3`, not `latest`, and has
    `wud.watch=false`. Update it sequentially and manually with target-image
    config validation and readiness/query verification because Loki releases
    can change config and storage behavior.
  - Both persist under `/srv/appdata/docker`, retain 30 days, and are private
    to LAN/Tailscale through NPM. Loki has no native authentication and no log
    shipper is declared yet; do not make its API public.
- ImmichFrame and Wizarr update policy is explicit:
  - `immichframe` uses the upstream
    `ghcr.io/immichframe/immichframe:latest` channel and is enrolled in the
    backup-gated WUD route. Its configuration is reproducible from Git and the
    scoped `IMMICHFRAME_API_KEY` recovery secret.
  - `wizarr` uses the upstream `ghcr.io/wizarrrr/wizarr:latest` channel and is
    enrolled in the backup-gated WUD route. Its SQLite-backed application state
    is protected by the appdata snapshot before update.
  - ImmichFrame and the primary `wizarr.rafael.media` route are private to
    LAN/Tailscale. ImmichFrame upstream advises against public exposure.
    The separately authorized `join-stream.rafael.ink` route exposes
    authenticated Wizarr publicly for invitation redemption; generate public
    invitations from that origin. Further Wizarr exposure changes require a
    separate review.
- Bar Assistant and yt-dlp Web UI update policy is explicit:
  - `barassistant/server:v5` and `barassistant/salt-rim:v4` are the upstream
    stable-major channels; Bar Assistant does not publish a `latest` server
    tag. `getmeili/meilisearch:v1.15` follows the upstream instruction to
    never use `latest`, and `redis:8-alpine` stays within Redis major 8.
  - All four Bar Assistant containers have `wud.watch=false`. Update the
    complete project manually only after a Bar Assistant export,
    migration-note review, and API/SQLite/search/Redis/UI checks. Do not update
    its API, frontend, search index, or session service independently.
  - `yt-dlp-web-ui` uses
    `ghcr.io/marcopiovanello/yt-dlp-web-ui:latest` and is enrolled in
    backup-gated WUD. On 2026-07-25 both upstream-documented `v4` registry
    references returned `manifest unknown`, while the official GHCR `latest`
    manifest resolved. Recheck the registry before changing channels. Its
    config/SQLite/session state is in appdata; downloaded media is under
    `/vault/shared/media/yt-dlp` and is not part of PBS appdata backups.
  - Bar Assistant's three NPM routes and the authenticated yt-dlp route are
    private to LAN/Tailscale. Do not expose any of them publicly without a
    separate review.
- SnapOtter and Stirling-PDF update policy is explicit:
  - `snapotter/snapotter:latest` is the upstream latest-release channel and is
    enrolled in backup-gated WUD. SnapOtter automatically applies pending
    schema migrations at application startup, so the PVE pre-backup hook must
    create a current logical dump before the appdata snapshot and WUD handoff;
    the sequential runner must pass `/api/v1/health` before continuing.
  - SnapOtter uses application-private `postgres:17-alpine` and
    `redis:8-alpine`, not `latest`. Both have `wud.watch=false`. Update them
    manually only after a current logical dump and successful isolated restore
    test; a PostgreSQL major or Redis major change is a migration task.
  - `stirlingtools/stirling-pdf:latest` is the upstream standard image and is
    enrolled in backup-gated WUD. Its settings, account database, custom
    files, pipelines, and OCR data persist in appdata, and the sequential
    runner must pass `/api/v1/info/status` after replacement.
  - SnapOtter at `snapotter.rafael.media` and Stirling-PDF at
    `pdf.rafael.media` use application authentication and private NPM routes
    limited to LAN/Tailscale. Complete both forced first-login password changes
    before normal use; do not expose either service publicly without a
    separate review.
- Music update and data policy is explicit:
  - Aurral uses the exact upstream v2 prerelease
    `ghcr.io/lklynet/aurral:2.0.0-test.7` at the repository-declared digest,
    is manually updated, and has
    `wud.watch=false`. Soularr, Navidrome, and slskd use their official stable
    `latest` channels with digest watching and the backup-gated WUD trigger.
    Navidrome and slskd have meaningful direct service checks.
  - A shared nonblocking job lock plus live slskd transfer inspection prevents
    WUD from replacing Soularr or slskd during acquisition/import work.
  - Lidarr is the sole owner and organizer of permanent music. Aurral v2
    durably records main-library requests and immediately starts Lidarr's
    torrent/Usenet search. The default fail-closed Soularr scheduler exposes
    only recent Aurral request IDs after a grace period, applies a persistent
    six-hour per-album retry cooldown, then uses the existing external slskd API
    and Soulseek identity. Aurral has no separate Soulseek account and writes
    only its appdata plus
    `/vault/shared/media/aurral-flows`. Soularr writes the slskd download tree
    and invokes Lidarr import; Navidrome and Jellyfin read music only.
  - DroppedNeedle is excluded from normal Compose startup, Pi-hole/NPM, Homarr,
    and WUD. Its Compose, appdata, and image remain for exact rollback. The
    current live container remains enabled only until an Aurral flow and the
    Soularr import path pass; then stop it with restart disabled. A clean
    bootstrap must never start it as a second permanent-library writer.
  - Music, Aurral flows, and slskd downloads remain under `/vault/shared`,
    outside PBS appdata backup. TCP 50300 listens only on the Apps LAN address
    and is not added to the unchanged router's public forward; any inbound
    Soulseek forwarding requires a separate exposure review.
- Audiobookshelf and Kavita update policy is explicit:
  - `ghcr.io/advplyr/audiobookshelf:latest` is upstream's stable release
    channel and is enrolled in backup-gated WUD. Its SQLite configuration and
    metadata persist in appdata; the sequential runner must pass the direct UI
    endpoint after replacement.
  - `ghcr.io/kareadita/kavita:latest` is upstream's stable release channel and
    is enrolled in backup-gated WUD. A new deployment starts beyond Kavita's
    legacy pre-v0.7.6 ordered-upgrade boundary; pause WUD and treat any future
    upstream-mandated ordered release as a migration task. The sequential
    runner must pass `/api/health` after replacement.
  - Both services run as Apps UID/GID `1000:1000`, keep their application
    databases/state under `/srv/appdata/docker`, and publish private
    LAN/Tailscale NPM routes with native first-run authentication. Audiobooks,
    books, comics, and manga are read-only shared libraries. Podcast downloads
    remain under `/vault/shared`, outside PBS appdata backup.
- Grimmory update and data policy is explicit:
  - `ghcr.io/grimmory-tools/grimmory:latest` is the official stable rolling
    channel, is backup-gated in WUD, and must pass `/api/v1/healthcheck`.
    Its private `lscr.io/linuxserver/mariadb:11.4.8` has `wud.watch=false`;
    update it manually only after a current logical dump and isolated restore.
  - Shelfarr remains the organizer. Grimmory alone receives the narrow
    read-write canonical EPUB bind. It sees audiobooks read-only; automatic
    moving, renaming, merging, BookDrop, and non-book shared paths are
    disabled.
  - Online metadata proposals fail closed for native review because Grimmory's
    current match score measures completeness, not identity confidence.
    The representative M4B pilot removed its AAC stream and chapters, so its
    exact snapshot bytes were restored and Grimmory audiobook file writing is
    permanently disabled.
  - Audiobookshelf is the canonical audiobook metadata writer through its
    narrow read-write bind. Native matching remains review-gated. Its embed
    tool must use stream copy, embed the existing chapters, retain its
    application backup copy, and pass codec/duration/chapter verification.
    Automatic M4B merging, moving, renaming, and unreviewed matching remain
    disabled.
  - Grimmory state and logical MariaDB dumps are in appdata. Its canonical
    ebook bind and Audiobookshelf's canonical audiobook bind remain on
    `/vault/shared`, outside PBS appdata backup.
- Storyteller update and data policy is explicit:
  - `registry.gitlab.com/storyteller-platform/storyteller:latest` is the
    official stable rolling channel and is enrolled in backup-gated WUD.
    The sequential runner must pass `/api/health`, and it must skip replacement
    while reconciliation, inbox import, or a `QUEUED`/`PROCESSING` readaloud is
    active.
  - The reconciler matches only the byte-identical two-component
    `{author}/{title}` key, reads canonical ebooks/audiobooks through CT112's
    broad read-only `/data`, and atomically publishes verified disposable
    copies into the narrow read-write `/storyteller/inbox`. It never guesses,
    hard-links, moves, or edits canonical files.
  - Storyteller's SQLite/config/manifest and consistent latest/previous SQLite
    backups are in appdata and covered by PBS. Its shared inbox/library and
    accepted readaloud assets are outside appdata PBS; do not call them backed
    up or delete them as cache. The private NPM route is LAN/Tailscale only.
- PinePods update and data policy is explicit:
  - `madeofpendletonwool/pinepods:latest` is the official stable rolling
    application channel and is enrolled in backup-gated WUD. The sequential
    runner must pass `/api/health` after replacement.
  - PinePods-private `postgres:18` and `valkey/valkey:8-alpine` have
    `wud.watch=false`. PostgreSQL uses `PGDATA=/var/lib/pgdata/pgdata` below a
    host bind mounted at `/var/lib/pgdata`; update either major only through a
    compatibility review and current logical-dump/isolated-restore test.
  - Database, configuration, server backups, portable latest/previous logical
    dumps, and retained restore-test evidence are in
    `/srv/appdata/docker/pinepods`. Episode downloads are only in
    `/vault/shared/media/podcasts/pinepods`, outside appdata PBS.
  - PinePods is the only active podcast subscription/progress service.
    Audiobookshelf remains canonical for audiobooks; its former podcast
    library record, users, appdata, and any old files are retained unchanged.
    Unsupported progress migration must be documented, never implemented by
    editing either database.
  - `pinepods.rafael.media` is private to LAN/Tailscale with TLS and
    WebSockets. Built-in GPodder is the supported client-sync interface;
    standard login remains enabled unless a separately tested OIDC recovery
    path is accepted.
- n8n and Pulse update policy is explicit:
  - Both are separate Infra projects on upstream `latest`, backup-gated WUD,
    private LAN/Tailscale routes, and canonical appdata; preserve
    `N8N_ENCRYPTION_KEY` with n8n data.
  - Pulse uses `PVEAuditor` for every LXC. Docker telemetry needs a command-disabled
    agent in every `PULSE_DOCKER_CTIDS` guest; keep inventory, bootstrap, and
    verification current when Docker placement changes. Agents self-update with
    checksum/signature verification; Docker updates stay off.
- Other services retain native stores. There is no central PostgreSQL.

Keep databases application-local unless a future task proves compatibility,
isolation, backup, recovery, and rollback benefits. Never copy PostgreSQL data
directories between versions/servers. Major/database-extension changes require
logical dumps and tested rollback.

Rolling application tags are allowed when enrolled in backup-gated WUD.
Databases, WUD, Immich, Gluetun, and bespoke upgrade paths remain manual.
Always run `docker compose config` before deployment.

## Native recovery state

`scripts/capture-native-recovery.sh` ran successfully on 2026-07-24 and stored:

```text
/srv/appdata/docker/
├── infra-samba/private/passdb.tdb
├── tailscale/tailscaled.state
└── recovery/{infra-afa.shadow-hash,pbs-root.shadow-hash,pbs-appdata.key}
```

It briefly stopped/restarted only SMB/Tailscale and verified both. Bootstrap
recaptures this state after rebuilding. These files are sensitive, mode 0600,
and must never be logged or committed.

Snapshot `host/afa-appdata/2026-07-24T12:38:45Z` contains this recovery set and
the final same-day application state. Upload, cleanup, WUD handoff, and
server-side verify-new all succeeded. A targeted restore of all five files
matched the live bytes and UID/GID/mode; this is not a full appdata restore.

## Backup and updates

The PVE timer runs `dothomelab-appdata-backup.service` daily. It runs optional
hooks, freezes CT102/110/112, snapshots `rpool/appdata/docker`, resumes guests,
uploads encrypted appdata plus `/root/.env`, then removes only its temporary
snapshot. LXC guest roots and `/vault/shared` are excluded; the separately
verified VM104 VMA under appdata is included. yt-dlp downloads, Audiobookshelf
libraries, preserved old podcast files, and PinePods episode downloads remain
excluded.

A separate PVE-controlled Proton runner is installed disabled. After Syncthing
pairing, Proton browser login, and first restore tests, its daily persistent
due-check performs one real cycle every 14 days for
`/vault/shared/media/obsidian`, `/vault/shared/media/photos`, and `/root/.env`.
It permanently retains at most two timestamped generations per source and
downloads every uploaded archive part for SHA-256 verification. Large staging
lives under `/vault/shared/.proton-backup-work`; the environment exists in
CT110 `/run` only for the job.

Retention is 7 last, 14 daily, 8 weekly, 12 monthly; prune daily, GC weekly,
full verification monthly, and verify-new enabled. These are scheduled
maintenance: routine changes do not start a backup or wait for PBS
verification. Check recent timer success; run an on-demand backup only when
task-specific durable-data risk justifies it. PBS on `vault` is not off-site
protection for shared data. Keep the encryption key off-host.

`OnSuccess=dothomelab-wud-update.service` is the only automatic update handoff.
Backup failure must not enqueue WUD. WUD updates one eligible container at a
time, waits for health/external checks, stops on first failure, and keeps old
images (`PRUNE=false`). Do not add Watchtower or a WUD timer.

Restore evidence includes a 10,018-file temporary restore, a 200-file
byte/UID/GID/mode sample, and the five-file native-state restore above. The
placeholder-complete bootstrap has passed a live read-only dry-run, but the
current production dry run stops at the deliberately absent
`PAPERLESS_GPT_OPENAI_API_KEY`. No destructive clean-host rebuild has run.

## Known unfinished work

- VM101 is intentionally unmanaged. HAOS VM104 is restored from its verified
  canonical VMA only when absent; a destructive full restore test is pending.
- Physical PVE installation, bridge creation, and pool/disk creation are
  prerequisites, not automated.
- `/vault/shared` lacks broad independent backup; the scoped Obsidian/photos
  Proton path is not protection until it is deployed and restore-tested.
- Obsidian still needs laptop/phone pairing, GUI auth/private route, Proton
  deployment/login, first checksum-verified restores for all three sources, and
  PVE timer enablement.
- Aurral's user-supplied Last.fm API key, integration username, account
  history profile, and real Discover refresh are verified. A real generated
  flow still needs to be generated and served from the separate flow library.
  Until that acceptance passes, keep the live DroppedNeedle container and its
  restart policy unchanged even though Git retains it only as a rollback
  profile.
- Paperless-GPT still needs a user-supplied OpenAI API key. Do not start it
  with a dummy value merely to satisfy the intended project membership.
- Feishin, Kew on macOS, and authenticated Jellyfin music playback remain
  device/session-only acceptance checks; do not infer them from server-side
  mount or catalogue evidence.
- Retained migration snapshots/volumes/images/dumps require a separate cleanup
  task.

## Execution and safety

1. Scope data risk, downtime, rollback, and verification.
2. Inspect PVE/ZFS/mounts/guests/Docker/logs read-only.
3. Use task-specific rollback for destructive, schema, or durable-data changes;
   routine changes rely on the scheduled appdata job and never wait for PBS.
4. Change one service/data class at a time.
5. Run focused `prepare.sh`/`verify.sh` plus end-to-end DNS/proxy/data checks.
6. Record desired state, restore steps, evidence, and unresolved risks in Git.

Require explicit task-level authorization and verified rollback before:

- destroying/formatting pools, datasets, partitions, guests, or guest disks;
- `docker compose down -v`, deleting volumes/databases, or pruning volumes;
- recursively deleting/chowning/chmodding appdata or shared data;
- deleting rollback snapshots, dumps, volumes, images, or legacy databases;
- rebooting PVE, stopping guests, disruptive DNS/network/firewall/SSH changes;
- public exposure or shared-credential rotation.

Never use `/`, `~`, `$HOME`, an unresolved variable, or broad glob as a
destructive target. Stop when live state contradicts the plan in a way that
risks data loss.
