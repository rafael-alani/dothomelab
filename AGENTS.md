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

Observed 2026-07-25:

| ID | Name | Address | State and role |
|---:|---|---|---|
| host | `afa` | `192.168.0.250` | PVE 9.1.2, ZFS, LXC lifecycle, PBS client |
| 101 | VM101 | `192.168.0.126` | running; unmanaged |
| 102 | `servarr` | `192.168.0.102` | Debian 12; 13 Docker containers |
| 104 | `homeassistant` | `192.168.0.125` | HAOS 18.1; managed recovery |
| 110 | `infra` | `192.168.0.110` | Debian 12; 11 containers + native services |
| 112 | `apps` | `192.168.0.112` | Debian 12; 30 running containers |
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
  narrow mounts support slskd and DroppedNeedle without granting write access
  to the rest of shared media. `/vault/shared/media/podcasts` is additionally
  mounted RW at `/podcasts` for Audiobookshelf downloads; its audiobook
  library and Kavita libraries remain read-only through `/data`.
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
packages, restores credentials, generates Docker mTLS, deploys twenty-five
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
├── servarr/hello/          # one 13-container project
├── infra/
│   ├── services/           # Pi-hole, Homarr, NPM, DDNS, hello, Portainer
│   ├── cockpit/            # Cockpit/Samba/Avahi/WSDD
│   ├── tailscale/          # native Tailscale with appdata state
│   ├── wud/                # central WUD and sequential runner
│   ├── obsidian-sync/      # Syncthing + multi-source Proton CLI runner
│   └── {n8n,pulse}/        # private automation and fleet monitoring
├── apps/{audiobookshelf,bar-assistant,droppedneedle,immich,immichframe,kavita,loki,media,mealie,paperless-gpt,paperless-ngx,prometheus,services,slskd,snapotter,stirling-pdf,wizarr,yt-dlp-web-ui,zotero-webdav}/
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
- CT110: `infra-services`, `n8n`, `pulse`, `wud`, `obsidian-sync`, plus native
  Cockpit/Samba/Tailscale.
- CT112: `audiobookshelf`, `bar-assistant`, `immich-migration`, `immichframe`,
  `kavita`, `loki`, `media`, `apps-mealie`, `paperless-ngx`,
  `paperless-gpt`, `prometheus`, `apps-services`, `slskd`, `droppedneedle`,
  `snapotter`, `stirling-pdf`, `wizarr`, `yt-dlp-web-ui`, `zotero-webdav`.
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
- slskd and DroppedNeedle update policy is explicit:
  - `slskd/slskd:0.25.1` is the exact release DroppedNeedle documents and
    tests against, not `latest`, and has `wud.watch=false`. Update it manually
    only after slskd migration-note review and confirmation that the target
    remains supported by DroppedNeedle. Verify web authentication, Soulseek
    connectivity, shares, search/download, DroppedNeedle API access, and a
    completed import before accepting it.
  - `droppedneedle/droppedneedle:latest` is the upstream production channel and
    is enrolled in backup-gated WUD. Its startup path creates and validates
    working-copy SQLite/settings upgrade backups; the sequential runner must
    also pass `/health` after replacement.
  - slskd application state and DroppedNeedle configuration, SQLite databases,
    cache, plugins, and import staging persist under `/srv/appdata/docker`.
    Music and slskd downloads remain under `/vault/shared`, outside PBS
    appdata backup. Narrow separate binds may make DroppedNeedle use its safe
    copy-and-remove import fallback and briefly require space for both copies.
  - Both NPM routes are private to LAN/Tailscale. TCP 50300 listens only on the
    Apps LAN address and is not added to the unchanged router's public forward;
    any inbound Soulseek forwarding requires a separate exposure review.
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
libraries, and podcast downloads remain excluded.

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
full bootstrap has passed a live read-only dry-run but not a destructive clean
host rebuild.

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
