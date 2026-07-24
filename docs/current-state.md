# Current state and original-plan outcome

Last reconciled against the live Proxmox host on 2026-07-24 at approximately
11:45 CEST. This file distinguishes deployed state from historical migration
records and future work.

## Current architecture

| System | Live state | Git-managed workload |
|---|---|---|
| Proxmox `afa` | PVE 9.1.2; `rpool` and `vault` healthy | Host backup/update units are defined in `backup/pbs`; complete host/guest provisioning is not in Git |
| CT102 `servarr` | Running; focused verifier passed | One 13-container `servarr-hello` project |
| CT110 `infra` | Running; service and Cockpit verifiers passed | `infra-services`, `wud`, and `obsidian-sync`; native Cockpit/Samba is installed from Git |
| CT112 `apps` | Running; media, Mealie, Portainer, and Immich verifiers passed; Zotero retained same-day end-to-end evidence | `immich-migration`, `media`, `apps-mealie`, `apps-services`, and `zotero-webdav` |
| CT113 `proxmox-backup-server` | Running PBS 4.2.3 | Protected PBS appliance with the `appdata` datastore on `vault/pbs_datastore` |
| VM101 | Running | Not provisioned or configured by this repository |
| VM104 `haos14.1` | Stopped, despite `onboot=1` | Not provisioned or configured by this repository |

The application LXCs use copied Git archives under `/opt/dothomelab`, not Git
working trees. `DEPLOYED_COMMIT` was `6788748` on Servarr,
`f10395998caf935c4e910f6bcf698245a94ed18a` on Infra, and `796d0a4` on Apps
during this audit. The differing commits reflect each guest's last relevant
deployment; resync a guest before deploying a newer repository change.

## Service and data placement

- Servarr runs Gluetun, qBittorrent, NZBGet, Prowlarr, Sonarr, Radarr, Lidarr,
  Readarr, Bazarr, FlareSolverr, Deunhealth, Portainer, and Portainer Agent.
  `/vault/shared` is writable at `/data`; SSD appdata is available at
  `/docker`.
- Infra runs Pi-hole, Homarr, Nginx Proxy Manager, Cloudflare DDNS,
  `helloworld`, Portainer, Portainer Agent, central WUD, and Syncthing. Pi-hole
  retains service IP `192.168.0.100`; the LXC remains `192.168.0.110`.
- Apps runs Immich v3.0.3, Jellyfin, Seerr, Jellystat 1.1.11, Mealie v3.21.0,
  Portainer 2.39.5, and Zotero WebDAV. The Apps mount of `/vault/shared` is
  read-only at `/data`; GPU devices are passed through for Jellyfin.
- Persistent Docker state is bind-mounted from `/srv/appdata/docker`. Large
  shared media, downloads, and the Obsidian vault are under `/vault/shared`.
- Samba exports authenticated `Vault` and `Media` shares for
  `/vault/shared` and `/vault/shared/media`. `/srv/appdata/docker` is not
  exported.

Live focused checks reported:

- 30 Sonarr series, 747 Radarr movies, 25 Prowlarr indexers, 159 Lidarr
  artists, 60 Readarr authors, and 746 qBittorrent torrent records;
- 36 NPM proxy hosts and 6 certificates with SQLite integrity `ok`;
- Immich's preserved baseline of 3 users, 25,780 assets, 24 albums, and all 10
  sampled managed/external paths readable;
- Mealie SQLite integrity `ok`, with 11 recipes and 1 user;
- an initialized Apps Portainer administrator and one populated Jellystat
  `app_config` row.

These counts are operational checks, not desired fixed values; they naturally
change with normal use.

## Database policy

The original unified PostgreSQL direction is no longer the project design.
There is no `platform/postgres` service.

- Immich keeps its supported PostgreSQL 14/VectorChord database with its
  required extension set.
- Jellystat keeps a private PostgreSQL 18 service in the `media` project.
- Mealie uses SQLite.
- Other applications retain their native stores.

The isolation is intentional: the two PostgreSQL consumers have different
major versions, image/extension requirements, upgrade procedures, and recovery
boundaries. A future consolidation is allowed only when it improves
compatibility and recovery rather than merely reducing the container count.

## Backup and update state

The deployed PBS flow is real and active:

- the daily PVE timer freezes LXCs 102, 110, and 112, snapshots
  `rpool/appdata/docker`, resumes them, and sends encrypted appdata plus
  `/root/.env` to PBS;
- the latest observed snapshot was
  `host/afa-appdata/2026-07-24T00:05:46Z`, a 245.833 GiB logical backup;
- retention is 7 last, 14 daily, 8 weekly, and 12 monthly; prune is daily,
  garbage collection weekly, and full verification monthly;
- a prior temporary restore recovered 10,018 files, with a 200-file
  byte/UID/GID/mode sample matching the source;
- `OnSuccess=dothomelab-wud-update.service` ran after the 2026-07-24 backup;
  the current Git-copied runner found 27 watched containers, all associated
  with `docker.backupgated`, and no eligible update.

The limitations matter:

- the last snapshot predates the final Apps cleanup/deployment,
  Zotero-route/NPM, and Obsidian appdata changes later on 2026-07-24. The SMB
  definitions are in Git, but the Samba password database is outside appdata;
- no database-specific pre/post backup hooks are installed; the recurring job
  relies on a brief LXC freeze plus a ZFS snapshot, while Immich's retained
  logical dumps are migration artifacts rather than a fresh dump on every
  daily run;
- the configured automatic verification job is monthly, not a separate daily
  verify-new job;
- `/vault/shared` is not independently backed up. PBS resides on the same
  `vault` pool, so copying shared data into that datastore would not protect
  against loss of the pool;
- the appdata restore mechanism was tested, but a complete bare-metal rebuild
  of PVE, guests, native service credentials, Docker TLS, all applications, and
  shared data has not been exercised end to end;
- the installed `/usr/local/sbin/dothomelab-wud-runner` is older than the
  Git-copied runner. It lacks the repository's newer external checks for Infra
  NPM and Infra/Apps Portainer/Agents, so the live success-gated update path
  needs that executable refreshed before those checks are real.

## Incomplete current work

### Obsidian sync and Proton backup

The base is deployed and Syncthing is healthy. Its server folder is
`Receive Only`, uses the placeholder ID `obsidian-vault`, and has staggered
365-day versioning at `/versions`. It currently lists only the server device.
The GUI has no username, no NPM route matching Syncthing exists, no
checksum-verified Proton archive is recorded, and the Proton timer is disabled.

The remaining work is laptop/phone pairing with the existing laptop folder ID,
GUI authentication, a private NPM route, Proton authentication, the first
upload/download/checksum restore test, workflow tests, and only then timer
enablement.

### Retained rollback assets

The active legacy Portainer stacks and Watchtower were removed, but selected
old named volumes, images, ZFS snapshots, Immich containers/directories, and
logical dumps remain intentionally retained. They are not part of the active
architecture. Cleanup requires a separate task because removing them closes
rollback paths.

### Recovery reproducibility

Compose applications, deployment scripts, Cockpit/Samba configuration, and
appdata restore tooling are in Git. Proxmox installation, ZFS creation/import,
guest creation, LXC package installation, router reservations, complete NPM
state, Docker TLS secret recovery, Samba password recreation, VM101, and HAOS
still require manual steps or restored state.

## Outcome against the initial plan

### Not implemented at all

1. **Unified/central PostgreSQL:** no shared PostgreSQL platform was created.
   This was consciously rejected in favor of application-local databases.
2. **Git-driven Proxmox and guest provisioning:** the repository does not
   create PVE, ZFS pools/datasets, LXCs, VM101, or HAOS. It starts at an
   already-created guest and deploys applications into it.
3. **Automatic verification of every new PBS snapshot:** the live PBS
   configuration has a monthly full verification job, but no separate daily
   verify-new job.

### Partially implemented

1. **Git as source of truth:** all active Docker applications use Git-managed
   Compose, verification scripts, and recorded deployment commits. It is
   partial because guest definitions, VM101/HAOS, router configuration, some
   live NPM/UI state, and credentials remain outside Git, and the installed WUD
   runner currently lags the copied repository version.
2. **Disposable guest roots:** application state was moved to bind-mounted SSD
   appdata and large shared data to `vault`, so the important data no longer
   depends mainly on guest roots. It is partial because guest OS/package
   creation is not automated and native credentials/state such as Samba's
   password database must be recreated manually.
3. **Complete recovery set:** Git, encrypted appdata snapshots, `/root/.env`,
   retained database dumps, and shared data have defined roles. It is partial
   because the roughly 11.3 TiB shared dataset lacks independent protection,
   the planned Proton flow covers only Obsidian and is not operational, some
   secrets require separately maintained off-host copies, and no full
   bare-metal rebuild has proven the whole set.
4. **Database backup consistency:** all appdata-writing LXCs are briefly
   frozen around the ZFS snapshot, and Immich has retained tested migration
   dumps. It is partial because there are no recurring logical-dump hooks for
   Immich or Jellystat.
5. **Restore documentation/automation:** appdata has a restore command and
   every Compose project has prepare/verify guidance. It is partial because
   there is no one-command host/guest rebuild, and several UI/credential steps
   remain manual.
6. **Migration cleanup:** active services were moved and obsolete Apps
   resources were selectively removed. It is partial because rollback assets
   were intentionally retained and Immich cleanup/manual review has not closed.
7. **Obsidian off-site protection:** the Compose project, Syncthing policy,
   Proton image, backup script, and systemd units exist. It is partial because
   pairing, authentication, routing, first verified restore, and timer
   activation are unfinished.
8. **Backup-gated container updates:** PBS `OnSuccess=`, central WUD, mutual
   TLS, opt-in labels, sequential updates, health waits, and no-prune rollback
   are deployed. It is partial because the installed runner lacks the newest
   Infra/Apps external API checks present in Git; only the copied runner was
   current during this audit.

The remaining initial goals are substantially implemented: active application
services use Git-managed Compose; Docker state is under
`/srv/appdata/docker`; large application-independent data is under
`/vault/shared`; the production environment comes from one Proxmox
`/root/.env`; PBS retention/prune/GC and the success-gated WUD chain are active;
and the legacy Watchtower/Portainer-stack runtime was removed.
