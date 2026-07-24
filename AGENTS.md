---
name: homelab-operator
description: Operate Rafael's Git-rebuilt Proxmox homelab safely.
---

# Homelab operator

## Mission

Given an installed PVE 9 node named `afa`, an importable `vault`, current
`/vault/shared`, `/srv/appdata/docker`, `/root/.env`, and this repository,
`./bootstrap.sh` must recreate the current LXC homelab without relying on guest
roots. VMs and destructive physical-disk provisioning are out of scope.

Priority order:

1. Active user request.
2. Live state observed on the machines.
3. This repository.
4. This snapshot document.

Always inspect live state before changing it. Never claim recovery, backup, or
migration success without verification evidence.

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

Observed 2026-07-24:

| ID | Name | Address | State and role |
|---:|---|---|---|
| host | `afa` | `192.168.0.250` | PVE 9.1.2, ZFS, LXC lifecycle, PBS client |
| 101 | VM101 | `192.168.0.126` | running; unmanaged |
| 102 | `servarr` | `192.168.0.102` | Debian 12; 13 Docker containers |
| 104 | `haos14.1` | `192.168.1.125` | stopped; unmanaged |
| 110 | `infra` | `192.168.0.110` | Debian 12; 9 containers + native services |
| 112 | `apps` | `192.168.0.112` | Debian 12; 12 containers |
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
| Guest roots | replaceable OS/packages/images/logs/cache |

`rpool` is SSD-backed; `vault` is HDD-backed. `/vault/backups` is legacy
directory storage, not PBS. `/vault/data` contains PVE-managed disks. Never
treat either as scratch.

Mounts:

- CT102: shared RW at `/data`; appdata RW at `/docker`.
- CT110: shared RW at `/vault/shared`; appdata RW at canonical path.
- CT112: shared RO at `/data`; appdata RW at canonical path.
- CT113: PBS dataset at `/mnt/datastore/appdata`.

All LXCs are unprivileged. Host IDs `101000:101000` map to guest `1000:1000`;
PBS host IDs `100034:100034` map to guest `34:34`. Inspect `findmnt`, `stat`,
`namei`, and `pct config` before permissions work. Never recursively
`chown`/`chmod` shared or appdata paths without mapping every consumer.

## One-command recovery

```bash
git clone git@github.com:rafael-alani/dothomelab.git /root/dothomelab
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
datasets, downloads templates, creates four LXCs, installs Docker/PBS/native
packages, restores credentials, generates Docker mTLS, deploys nine Compose
projects, configures backups/WUD, and verifies the result. It never creates or
formats physical pools/disks. Full behavior and failure semantics are in
`docs/rebuild.md`.

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
│   └── obsidian-sync/      # Syncthing + on-demand Proton backup
├── apps/{immich,media,mealie,services,zotero-webdav}/
└── pbs/                    # PBS package/datastore/job/identity installer
backup/pbs/                 # PVE backup, restore, and WUD systemd chain
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
- CT110: `infra-services`, `wud`, `obsidian-sync`, plus native
  Cockpit/Samba/Tailscale.
- CT112: `immich-migration`, `media`, `apps-mealie`, `apps-services`,
  `zotero-webdav`.
- Immich uses its supported PostgreSQL 14/VectorChord image.
- Jellystat uses private PostgreSQL 18. Mealie uses SQLite.
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
snapshot. Guest roots and `/vault/shared` are excluded.

Retention is 7 last, 14 daily, 8 weekly, 12 monthly; prune daily, GC weekly,
full verification monthly, and verify-new enabled. PBS on `vault` is not
off-site protection for shared data. Keep the PBS encryption key off-host; a
key inside its own encrypted backup cannot unlock that backup.

`OnSuccess=dothomelab-wud-update.service` is the only automatic update handoff.
Backup failure must not enqueue WUD. WUD updates one eligible container at a
time, waits for health/external checks, stops on first failure, and keeps old
images (`PRUNE=false`). Do not add Watchtower or a WUD timer.

Restore evidence includes a 10,018-file temporary restore, a 200-file
byte/UID/GID/mode sample, and the five-file native-state restore above. The
full bootstrap has passed a live read-only dry-run but not a destructive clean
host rebuild.

## Known unfinished work

- VM101 and HAOS are intentionally unmanaged.
- Physical PVE installation, bridge creation, and pool/disk creation are
  prerequisites, not automated.
- `/vault/shared` lacks independent backup.
- Obsidian still needs laptop/phone pairing, GUI auth/private route, Proton
  login, first checksum-verified restore, and timer enablement.
- Retained migration snapshots/volumes/images/dumps require a separate cleanup
  task.

## Execution and safety

1. Scope data risk, downtime, rollback, and verification.
2. Inspect PVE/ZFS/mounts/guests/Docker/logs read-only.
3. Create an appropriate rollback point and check capacity.
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
