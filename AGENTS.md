---
name: homelab-operator
description: Operate Rafael's Proxmox homelab over SSH using Git-managed Docker Compose, shared ZFS storage, service-local databases, and verified backups.
---

# Homelab operator

Use this skill to inspect, repair, document, migrate, or deploy services in Rafael's homelab.

## Goals

1. Prefer reproducible Docker Compose services, including Docker inside LXCs where practical.
2. Use `git@github.com:rafael-alani/dothomelab.git` as the source of truth for Compose files, scripts, templates, and restore documentation.
3. Keep the repository README brief, with two operational sections:
   - **Back up before migration**: everything non-reproducible that must be preserved.
   - **Bootup / restore**: rebuild from the repository, the production `/root/.env` on the Proxmox host, and the required application/database backups.
4. Back up SSD appdata and `/root/.env` to the HDD-backed Proxmox Backup Server datastore, and distinguish a successful upload from a verified restore.
5. Keep databases application-local unless a future migration has a concrete compatibility, isolation, backup, and recovery benefit. There is no central PostgreSQL platform.
6. Store large application-independent data under `/vault/shared`.
7. Keep persistent Docker application state on SSD under `/srv/appdata/docker` and back it up separately to the HDD pool.
8. Keep guest root disks limited mainly to the OS, packages, logs, and replaceable runtime data. Git currently reproduces applications, not complete Proxmox guest creation.

Short-term requirements come from the active task prompt and take priority unless they conflict with the safety rules below.

## Sources of truth

Use this order:

1. The active user request.
2. Live state observed on the machines.
3. The `dothomelab` repository.
4. This inventory, which is a snapshot and may be stale.

Always verify live state before changing it.

## SSH access

SSH to the Proxmox host, then operate LXCs with `pct exec`; do not configure or depend on SSH inside them.

```bash
ssh root@192.168.0.250
ssh root@192.168.0.250 -- pct exec <VMID> -- <command>
ssh afa@192.168.0.126                     # VM 101
```

For pipes, expansion, multiple commands, or changing directories, invoke a shell inside the LXC:

```bash
ssh root@192.168.0.250 "pct exec 102 -- bash -lc 'cd /opt/dothomelab && docker compose ls'"
```

Use `pct enter <VMID>` only for a genuinely interactive shell. `pct exec` works only for LXCs; use direct SSH for VM 101 and task-specific supported access for HAOS.

The operator machine uses `~/.ssh/homelab` for `192.168.0.*` and `~/.ssh/github` for `github.com` through `~/.ssh/config`. Do not store passwords, private keys, tokens, or secrets in this skill or Git. Never disable host-key checking or expose credentials in commands, logs, issues, commits, or pull requests.

## Network and guest inventory

Live status observed 2026-07-24: LXCs 102, 110, 112, and 113 and VM 101
were running; HAOS VM 104 was stopped even though it has `onboot=1`.

| VMID | Name | Type | IP | Role | Preferred access |
|---:|---|---|---|---|---|
| host | `afa` | Proxmox host | `192.168.0.250` | ZFS, guest lifecycle, mounts, PBS | `ssh root@192.168.0.250` |
| 101 | `VM 101` | VM | `192.168.0.126` | General Linux VM | `ssh afa@192.168.0.126` |
| 102 | `servarr` | LXC | `192.168.0.102` | Media automation/downloads | `pct exec 102` |
| 104 | `haos14.1` | VM | `192.168.1.125` | Home Assistant OS | UI/console or supported tooling |
| 110 | `infra` | LXC | `192.168.0.110` | DNS, proxy, dashboard, Cockpit | `pct exec 110` |
| 112 | `apps` | LXC | `192.168.0.112` | Applications and media frontends | `pct exec 112` |
| 113 | `proxmox-backup-server` | LXC | `192.168.0.159` | PBS for encrypted appdata backups | `pct exec 113` |

### Network rules

- Pi-hole runs in Docker on `infra` but keeps `192.168.0.100` as a secondary service address; CT110 itself remains `192.168.0.110`.
- Nginx Proxy Manager on LXC 110 is the reverse proxy. New Docker services normally publish a port on their host LXC IP; add the matching proxy host instead of assigning a separate LAN IP to each container.
- LXC addresses follow `192.168.0.<VMID>`. Addresses above `100` are manually assigned/reserved on the router because the DHCP pool ends at `100`; configure the router-side address before relying on a new guest IP.
- For a new service, verify the guest IP and port, add DNS through Pi-hole, then route the hostname through Nginx Proxy Manager to `<guest-IP>:<published-port>`.
- Confirm live state with `pct list`, `pct config <VMID>`, `pct exec <VMID> -- hostname -I`, `qm list`, and `ip neigh` before changes.

## Storage model

- `rpool`: SSD-backed Proxmox system and guest storage.
- `vault`: large HDD ZFS pool.
- `vault/shared` mounted at `/vault/shared`: shared large data.
- `vault/pbs_datastore`: dedicated HDD-backed PBS datastore target.
- `rpool/appdata/docker` mounted at `/srv/appdata/docker`: SSD-backed persistent Docker appdata that must be backed up.

| Data class | Canonical location |
|---|---|
| Movies, series, music, photos, books, downloads, other large user data | `/vault/shared` |
| Docker configs, application databases, metadata, persistent state | `/srv/appdata/docker` on `rpool`, backed up to PBS on `vault` |
| Compose files, scripts, templates, restore docs | `dothomelab` repository |
| Secrets | production `.env` stored on the Proxmox host, outside Git |
| Guest operating systems | guest root disks under `rpool/data`; rebuildable from Git and the recovery set |

`/vault/backups` is legacy directory-style `vzdump` storage, not a PBS datastore. `/vault/data` contains Proxmox-managed guest disks; never treat either path as disposable backup scratch space.

Known shared top-level directories are `/vault/shared/{compose,linux-restore,media,temp,torrents,usernet}`; `compose` is current/legacy Portainer data, not the long-term source of truth.

### Mount rules

1. Configure ZFS datasets and LXC bind mounts on Proxmox, not inside guests.
2. Use host-directory bind mounts for shared files. Never mount one block filesystem read-write in multiple guests.
3. Preserve numeric UID/GID ownership during migration.
4. Before changing permissions, inspect `findmnt`, `stat`, `namei`, and `pct config`.
5. Never recursively `chown` or `chmod` `/vault/shared` or `/srv/appdata/docker` without mapping all consuming UIDs/GIDs.
6. Use read-only mounts for consumers that do not need writes, such as Jellyfin media libraries.
7. Verify mounts and permissions from both the host and every affected guest.

## Current service placement

Observed live on 2026-07-24. All three Docker hosts use Git-managed Compose.
The non-secret focused verifiers run during the audit passed; Zotero retains
same-day end-to-end verification evidence. Verify live state again before
changing it.

### LXC 102 — Servarr

The only Compose project is Git-managed `servarr-hello` at `hosts/servarr/hello/compose.yaml`: Gluetun, qBittorrent, NZBGet, Prowlarr, Sonarr, Radarr, Lidarr, Readarr, Bazarr, FlareSolverr, Deunhealth, Portainer, and Portainer Agent. The legacy `servarr` and `watchtower` projects were removed on 2026-07-23.

- Host `/vault/shared` is mounted read-write at `/data`; host `/srv/appdata/docker` is mounted at `/docker`.
- qBittorrent, NZBGet, and Prowlarr use Gluetun's container network namespace. Keep Gluetun manual in WUD and update that cohort with Compose.
- Portainer and its agent are 2.39.5, WUD-eligible, and Portainer persists at `/docker/servarr-portainer`. The original `portainer_data` volume and `rpool/appdata/docker@pre-servarr-migration-20260723` remain rollback assets.
- Run `hosts/servarr/hello/verify.sh` after changes. The reusable migration process and observed problems are in `docs/compose-project-migration.md`.
- CT102's 8 GiB root was reduced from 92% to 34% on 2026-07-23 by preserving its legacy config archive under `/docker/migration-rollback/servarr-20260723`, pruning only unused images, cleaning the APT cache, and capping journals at 100 MiB. Active images and all volumes were retained.

### LXC 110 — Infra

The Compose projects are Git-managed `infra-services` at
`hosts/infra/services/compose.yaml`, central `wud` at
`hosts/infra/wud/compose.yaml`, and `obsidian-sync` at
`hosts/infra/obsidian-sync/compose.yaml`. The legacy `proxy` project was
removed on 2026-07-23.

- NPM, Pi-hole, Homarr, and Portainer persist under `/srv/appdata/docker`; Cockpit is reproducibly installed from Git into the guest OS.
- Cockpit Files and Cockpit File Sharing provide privileged local browsing and Samba management. Git imports the real Samba registry configuration from `hosts/infra/cockpit/samba-registry.conf`; the authenticated, macOS-optimized `Vault` and `Media` shares expose `/vault/shared` and `/vault/shared/media`. Never export `/srv/appdata/docker` over SMB.
- Portainer and Agent are matching 2.39.5 releases and WUD-eligible. Their old volumes and named pre-migration root/appdata snapshots remain rollback assets.
- Run `hosts/infra/services/verify.sh` and `hosts/infra/cockpit/verify.sh` after changes; see `docs/compose-project-migration.md` for migration evidence.

### LXC 112 — Apps

Observed 2026-07-24, the only Compose projects are:

- `immich-migration`: healthy Immich v3.0.3 with PostgreSQL 14/VectorChord and pinned Valkey. All four services remain manual in WUD; retained rollback containers, dumps, snapshots, and backups require a separate explicit cleanup task.
- `media`: Jellyfin, Seerr, fresh Jellystat 1.1.11, and its private PostgreSQL 18. The applications use backup-gated WUD; the database is excluded. Jellyfin sees `/data/media` read-only.
- `apps-mealie`: Mealie v3.21.0 with SQLite at `/srv/appdata/docker/mealie`; the restored state contains 11 recipes and 1 user.
- `apps-services`: matching Portainer CE/Agent 2.39.5 with data at `/srv/appdata/docker/portainer`; WUD is restricted to the 2.39 LTS patch line.
- `zotero-webdav`: authenticated personal-library attachment storage at `/srv/appdata/docker/zotero-webdav`, privately routed as `https://zotero.rafael.media/zotero/` through Infra NPM/Pi-hole/Tailscale.

GitLab and the legacy Jellystat, Mealie, and standalone Portainer artifacts
were removed. The protected pre-v3 Immich rollback set was deliberately
retained. New Apps state is below `/srv/appdata/docker`; databases and
`immich-migration` remain excluded from automatic updates. Deployments under
`/opt/dothomelab` are copied artifacts without Git metadata, so record their
source commit in `/opt/dothomelab/DEPLOYED_COMMIT`.

Run each project's focused `verify.sh` after changes. Avoid exhaustive scans of the approximately 212 GiB Apps dataset; treat `immich-migration`, `/srv/appdata/docker/immich`, `/data`, shared media, and retained Immich recovery assets as high-risk and inspect them only as required by an explicit task.

### Obsidian sync and off-site backup

Observed 2026-07-24: the Git-managed base is deployed on Infra and Syncthing
2.1.2 is healthy. The server folder is `Receive Only` with staggered 365-day
versioning at `/versions`, but it lists only the server device, the GUI has no
username, no NPM Syncthing route exists, no checksum-verified Proton archive is
recorded, and the Proton timer is disabled. Device pairing, GUI credentials,
Proton login/first restore-verified upload, NPM routing, and timer enablement
remain explicit user steps.

- The Infra project at `hosts/infra/obsidian-sync/` combines Syncthing with an on-demand/profile Proton Drive CLI job. Keep Syncthing config, index, and device keys under `/srv/appdata/docker/syncthing`; keep the plaintext vault at `/vault/shared/media/obsidian`.
- Configure laptop and phone as `Send & Receive`. The laptop is the operational/recovery authority, not an exclusive protocol writer; configure the server as `Receive Only` so server-local changes are not propagated while laptop/phone changes are applied and redistributed.
- Define `.stignore` before seeding: exclude volatile workspace/OS/temp files and any plugin secrets; decide deliberately which Obsidian config, plugins, and vault-local `.trash` data sync across desktop and mobile.
- Prefer Obsidian's vault-local trash, then enable server-side staggered versioning with agreed retention (initial target 365 days) at `/vault/shared/media/.obsidian-versions` on the same filesystem. Keep `ignoreDelete=false`; versioning and ZFS parity are not backups.
- Mount the vault read-write only into Syncthing and read-only into the Proton job. Keep the Syncthing GUI private and authenticated; do not expose it publicly.
- Make Proton a one-way, point-in-time backup with explicit conflict behavior, retention, success reporting, and no cloud-to-vault path. Persist its supported encrypted credential store and cache under appdata; never commit sessions, GPG material, or credentials.
- Before first sync, confirm the phone uses a maintained Syncthing client, take a laptop backup, and seed carefully so stale server/phone state cannot merge unexpectedly. Verify phone-to-server-to-laptop edits, conflicts, deletions/version recovery, Proton upload, and a checksum-validated restore.

## Repository contract

A suitable structure is:

```text
dothomelab/
├── hosts/
│   ├── servarr/hello/compose.yaml
│   ├── infra/services/compose.yaml
│   ├── infra/cockpit/
│   ├── infra/obsidian-sync/compose.yaml
│   ├── apps/media/compose.yaml
│   ├── apps/immich/compose.yaml
│   ├── apps/mealie/compose.yaml
│   ├── apps/services/compose.yaml
│   ├── apps/zotero-webdav/compose.yaml
│   └── infra/wud/compose.yaml
├── docs/current-state.md
├── docs/compose-project-migration.md
├── backup/
├── scripts/
├── .env.example
├── .gitignore
└── README.md
```

Rules:

1. Use explicit bind mounts and documented absolute paths.
2. For ordinary homelab applications, upstream rolling tags such as `latest`, `release`, or another documented stable channel are acceptable and may be updated by WUD only through the backup-gated flow below.
3. Keep each database with its application. Database major upgrades and extension changes require an explicit migration task, a logical dump where supported, and verified rollback.
4. Follow an application's recommended release channel when it has upgrade-specific requirements. WUD does not add services or supply newly required environment variables.
5. Commit `.env.example`, never the production `.env`; the user places the production `~/.env` on the Proxmox host for deployments.
6. Run `docker compose config` before deployment.
7. Make live deployments traceable to a commit and record the deployed image digest for automatic updates.
8. Prefer repository deployments over editing Portainer stacks.
9. First reproduce current behavior in Git; refactor only after a working rollback point exists.

## Container update automation

### Placement and eligibility

- Watchtower was removed from Servarr and must not be added to new stacks; retire any other legacy instance only after its replacement WUD path is verified.
- Run one central WUD as its own Compose project on `infra`, separate from application stacks. It watches infra through the local socket and apps/servarr through Docker API port 2376 with mutual TLS; never expose unauthenticated port 2375.
- Keep Docker API CA and client keys outside Git and treat them as root credentials. Bind each daemon to its LXC address, verify certificate SANs, and retain an off-host CA copy.
- Start monitor-only with `WATCHBYDEFAULT=false`; opt containers in with labels. Mutable tags require digest watching. Keep databases, WUD itself, and applications with bespoke upgrade procedures manual until explicitly tested.
- Prefer WUD's Docker trigger for rolling tags because the Docker Compose trigger edits Compose files and only works for locally watched containers.
- On 2026-07-24 the Git-copied runner discovered 27 watched containers, all
  associated with `docker.backupgated`, and no update. The installed
  `/usr/local/sbin/dothomelab-wud-runner` was older than the repository copy:
  it lacked Infra NPM, Infra/Apps Portainer and Agent external checks plus the
  expanded dry-run report. Reinstall it from Git before relying on those
  checks during a real update.

### Ownership

| Component | Responsibility |
|---|---|
| PBS backup service | Quiesce applications as configured, snapshot appdata, upload it, clean up, and return success or failure. |
| Proxmox systemd | Provide the success-only handoff and run the updater sequentially; this is the bridge between PBS and WUD. |
| Central WUD | Scan all three Docker hosts, select eligible versions, expose update state, and replace containers when its API trigger is invoked. |
| Operator | Opt services in, define health checks and exceptions, approve unusual upgrades, and handle failed rollbacks. |

### Automatic flow

1. The existing daily PBS timer starts `dothomelab-appdata-backup.service`; it remains the only clock-based update schedule.
2. The installed backup unit has `OnSuccess=dothomelab-wud-update.service`. Systemd starts the updater only after the backup script, including upload and cleanup, exits successfully; backup failure must not enqueue an update.
3. The updater has no timer. It enters infra with `pct exec` and calls the central WUD API over loopback to scan and enumerate eligible updates across all three Docker hosts.
4. For each update, record the current image digest, invoke the local WUD Docker trigger, then wait for Docker health plus any documented service-specific check before continuing.
5. On any WUD, update, or health-check failure, stop the run, retain the previous image for rollback, report the failed host/container, and do not touch remaining services.

- Mutation triggers must use `AUTO=false`; WUD may scan at any time without updating outside the PBS success chain. Notification-only triggers may use `AUTO=true`.
- WUD calls these API executions manual, but the systemd updater invokes them automatically; no person or 04:00 timer is part of the normal flow.
- Keep `PRUNE=false` so the previous image remains available. Use a separate updater lock to reject duplicate runs.
- Full PBS verification and restore tests remain separate from this ordering guarantee. Starting the updater directly by hand is exceptional and requires first confirming a fresh successful backup.
- The repository runner performs external checks after replacing Infra NPM or
  any Infra/Servarr/Apps Portainer and Agent; process state alone is
  insufficient. The live installed runner must be refreshed before this claim
  is true for Infra and Apps.

## Database placement

The original central PostgreSQL idea was abandoned. Current databases are
deliberately application-local:

- Immich uses its supported PostgreSQL 14/VectorChord image and retains the
  extensions required by the migrated database.
- Jellystat uses a private PostgreSQL 18 service in the `media` project.
- Mealie uses SQLite.
- NPM, the Arr applications, Portainer, Pi-hole, Homarr, Seerr, and Syncthing
  retain their application-native stores.

Do not create `platform/postgres` or move a database merely for uniformity.
Before any future database move, verify external database support, required
major/extensions, privileges, logical export/import, failure isolation, and a
tested rollback path. Never copy PostgreSQL data directories between servers.

## Backup requirements

Classify each dependency as reproducible, Git-managed configuration, secret, database, persistent appdata, or user data. Before migration, capture guest configuration, Compose files, mounts, ownership, versions, and application-consistent database dumps.

Deployed design and current limits:

- PBS 4.2.3 runs in protected unprivileged LXC 113 with
  `/vault/pbs_datastore` bind-mounted at `/mnt/datastore/appdata`; never store
  the datastore in the LXC root disk.
- The daily job freezes LXCs 102, 110, and 112, snapshots
  `rpool/appdata/docker`, resumes the guests, and uploads encrypted appdata plus
  `/root/.env`. No database-specific pre/post hooks are installed.
- Retention is `keep-last=7`, `keep-daily=14`, `keep-weekly=8`, and
  `keep-monthly=12`; prune is daily, garbage collection weekly, and the
  configured full verification job is monthly.
- Guest roots are intentionally excluded. Git does not yet provision complete
  guests, so a bare-metal rebuild still requires manual Proxmox/LXC setup.
- `/vault/shared` is not copied into PBS because the datastore is on the same
  `vault` pool. Most shared data therefore has no independent backup. The
  Obsidian Proton subset is designed but not operational yet.
- The latest successful encrypted snapshot observed was
  `host/afa-appdata/2026-07-24T00:05:46Z` (02:05 CEST). It predates the final
  Apps, Zotero-route/NPM, and Obsidian appdata changes made later that morning;
  those changes need the next successful backup and a restore check. Samba's
  definitions are in Git, while its password database is outside appdata and
  must be recreated after a clean guest rebuild.
- An earlier 10,018-file temporary restore and a 200-file byte/ownership sample
  were validated. This proves the appdata restore mechanism, not a complete
  bare-metal restore of every service.
- Keep the PBS encryption key and administrator password off-host without
  committing them. Legacy `/vault/backups` and named rollback snapshots/volumes
  remain preserved until separately authorized cleanup.

A backup is complete only when its restore procedure is documented and minimally verified.

## Execution workflow

1. **Scope**: identify target hosts/services, end state, data at risk, downtime, rollback, and verification.
2. **Inspect read-only**: verify Proxmox, ZFS, mounts, Docker projects, health, logs, and permissions relevant to the task.
3. **Create rollback**: use database dumps, ZFS snapshots, PBS, copied config, and/or Git commits as appropriate. Check capacity first.
4. **Change incrementally**: migrate one service or data class at a time; keep old state until verification passes.
5. **Verify end to end**: container health, logs, HTTP/API, database records, mount read/write behavior, UID/GID, proxy/DNS, workflows, and backups.
6. **Record**: update Compose/config, `.env.example`, backup requirements, restore steps, exceptions, verification commands, and unresolved risks.

Useful baseline commands:

```bash
# Proxmox
pveversion -v
pct list
qm list
zpool status -x
zfs list -o name,used,avail,refer,mountpoint
cat /etc/pve/storage.cfg

# Docker host
docker version
docker compose ls
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
findmnt
df -hT
```

Do not print secrets while inspecting Compose or container environments.

## Safety boundaries

The agent may inspect all listed machines and make changes directly required by the active task, while preserving user data and a rollback path.

Require explicit task-level authorization and a verified backup/rollback plan before:

- destroying ZFS datasets/pools, formatting disks, or changing partitions;
- destroying guests or deleting guest disks;
- running `docker compose down -v`, deleting volumes, or pruning volumes;
- recursively deleting appdata or user media;
- broad recursive ownership/permission changes;
- deleting old databases after migration;
- rebooting hosts, shutting down guests, or making disruptive DNS/network/firewall/SSH changes;
- exposing an internal service publicly;
- rotating shared credentials.

Never claim a backup, migration, or repair succeeded without verification evidence. Stop and report when live state contradicts the requested plan in a way that risks data loss.
