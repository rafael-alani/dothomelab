# Architecture

This page describes Git-declared responsibilities and boundaries. Running
counts, deployed revisions, exceptions, and verification dates belong in
[status](status.md). The recovery invariant is defined in the
[rebuild contract](rebuild.md).

## System map

```text
afa — Proxmox VE 9
├── storage contracts
│   ├── rpool/appdata/docker → /srv/appdata/docker (encrypted appdata PBS)
│   └── vault/shared → /vault/shared (large media; outside appdata PBS)
├── CT102 servarr — Debian 12
│   └── gluetun, qbittorrent, nzbget, prowlarr, sonarr, radarr,
│       lidarr, readarr, bazarr, flaresolverr, deunhealth,
│       portainer, portainer_agent, shelfarr, shelfarr-libation, listenarr,
│       soularr, cleanuparr, sortarr,
│       cross-seed: cross-seed, cross-seed-prowlarr-proxy
├── CT110 infra — Debian 12 + Cockpit/Samba/Tailscale
│   ├── infra-services: pihole, homarr, nginx-proxy-manager,
│   │   cloudflare-ddns, helloworld, portainer, portainer_agent
│   ├── n8n
│   ├── pulse
│   ├── wud
│   └── obsidian-sync: syncthing + on-demand Proton Drive CLI
├── CT112 apps — Debian 12
│   ├── aurral
│   ├── audiobookshelf
│   ├── pinepods: pinepods, pinepods-db, pinepods-valkey
│   ├── bar-assistant: bar-assistant, bar-assistant-salt-rim,
│   │   bar-assistant-meilisearch, bar-assistant-redis
│   ├── bookorbit: bookorbit, bookorbit-db
│   ├── grimmory: grimmory, grimmory-db
│   ├── storyteller: storyteller, storyteller-reconciler
│   ├── immich-migration: immich_migration_server,
│   │   immich_migration_machine_learning, immich_migration_redis,
│   │   immich_migration_postgres
│   ├── immichframe
│   ├── kavita
│   ├── media: jellyfin, seerr, jellystat, jellystat-db
│   ├── music-metadata: deterministic Beets tag/art/ReplayGain writer
│   ├── navidrome
│   ├── apps-mealie: mealie
│   ├── loki
│   ├── paperless-ngx: paperless-ngx, paperless-db, paperless-broker
│   ├── paperless-gpt
│   ├── prometheus
│   ├── snapotter: snapotter, snapotter-db, snapotter-redis
│   ├── slskd
│   ├── stirling-pdf
│   ├── apps-services: portainer, portainer_agent
│   ├── wizarr
│   ├── yt-dlp-web-ui
│   └── zotero-webdav
├── CT113 proxmox-backup-server — Debian 13, PBS 4 (no Docker)
├── CT114 staging — Debian 12, isolated appdata
│   └── staging-film-introspect: api + web, follows Git staging branch
├── VM104 homeassistant — HAOS; restored from canonical appdata
└── VM101 — unmanaged by this repository
```

The tree includes declared Paperless-GPT even when its external credential is
missing; it excludes live-only deployments and rollback containers. See
[the live evidence](evidence/2026-10-12-documentation-baseline.md) for those
exceptions. Concrete IP/MAC/resource settings live in
[inventory.env](../provision/inventory.env), not in this diagram.

## Responsibility and data flow

Browser/client → Pi-hole DNS → NPM TLS route → published LXC port → application
→ application-local database/appdata. Internal database/cache containers do not
need a public route. Native SMB is a separate LAN file-access path.

PVE owns datasets, mounts, guest lifecycle, appdata snapshots, and the backup
handoff. Infra owns DNS, proxying, dashboard, native file access/Tailscale,
monitoring, and private automation. Servarr acquires and organizes media. Apps
serves users and exposes only the narrow canonical writers described below.
PBS stores encrypted appdata backup history. Staging builds isolated branch
releases. HAOS keeps Supervisor-managed apps and its native backup/rollback
model; VM101 is excluded from this repository's management.

A repository checkout is exported into each guest as `/opt/dothomelab`, with
`DEPLOYED_COMMIT` identifying the code archive. Runtime appdata and secrets are
separate recovery inputs. Replacing guest roots must not erase durable state.

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
  bind exposes `/vault/shared/media/aurral-flows` through Aurral's appdata path.
  Explicit CT112 `mp7` carries that bind into the guest on cold boot; Aurral
  writes it and Navidrome reads it.
  `/vault/shared/media/podcasts` is additionally
  mounted RW at `/podcasts`; PinePods receives only its `/podcasts/pinepods`
  subtree. Audiobookshelf's retained podcast state has no writable podcast
  bind after phase-5 acceptance. A persistent narrow host bind exposes
  canonical audiobooks through Audiobookshelf's appdata path; only
  Audiobookshelf receives that tree read-write for its verified native
  stream-copy metadata embed tool. Grimmory and other readers see audiobooks
  read-only through `/data`. A separate persistent narrow host bind exposes
  canonical ebooks through Grimmory's appdata path; only Grimmory receives
  that tree read-write. Explicit CT112 `mp8` and `mp9` carry the ebook and
  audiobook binds into the guest on cold boot.
  `/vault/shared/media/storyteller` is mounted RW at `/storyteller` for
  disposable verified staging and Storyteller-owned derived media. Its
  canonical ebook and audiobook inputs remain read-only through `/data`.
- CT113: PBS dataset at `/mnt/datastore/appdata`.
- CT114: only `/srv/appdata/docker/staging` at the same guest path, owned by
  host `100000:100000` (guest root). No production appdata/shared/hardware
  mounts and no production environment or remote Docker socket.

All LXCs are unprivileged. Host IDs `101000:101000` map to guest `1000:1000`;
PBS host IDs `100034:100034` map to guest `34:34`. Inspect `findmnt`, `stat`,
`namei`, and `pct config` before permissions work. Never recursively
`chown`/`chmod` shared or appdata paths without mapping every consumer.

## Canonical media ownership

| Data | Organizer / acquisition | Allowed metadata or derived writer | Readers |
|---|---|---|---|
| Permanent music | Lidarr; Aurral requests; request-scoped Soularr/slskd fallback | music-metadata, exact-release tags/art/ReplayGain with hardlink detachment | Navidrome, Jellyfin, Aurral |
| Aurral flows | Aurral in its separate flow tree | Aurral | Navidrome |
| Ebooks | Shelfarr | Grimmory, reviewed EPUB metadata only | BookOrbit, Kavita, Storyteller |
| Audiobooks | Listenarr | Audiobookshelf, reviewed stream-copy embed only | Audiobookshelf, Grimmory, Storyteller |
| Podcasts | PinePods | PinePods in its own episode subtree | PinePods and supported sync clients |
| Readalouds | Storyteller's exact-key reconciler copies inputs | Storyteller in its separate library | Storyteller/readaloud clients |

The [media data contract](media-data-contract.md) owns exact paths and access
rules. [Service policies](reference/service-policies.md) own upgrade and
publication constraints. A readable mount never grants a consumer permission
to reorganize another application's canonical files.

## Recovery and update boundaries

Appdata PBS includes application state, the production environment, captured
native credentials, and the HAOS VMA under appdata. It excludes guest roots and
shared media, including narrow shared mounts presented beneath appdata paths.
The PBS datastore is on the same physical host and is not off-site protection.
See [operations](operations.md#backup-and-recovery) for coverage and evidence.

Successful scheduled appdata backup → `OnSuccess` WUD handoff → sequential
eligible application updates → health checks, stopping at the first failure.
WUD uses Docker mTLS to remote guests. Databases and special upgrade cohorts
remain manual; there is no central PostgreSQL. Busy media jobs defer relevant
updates. The [WUD runbook](../hosts/infra/wud/README.md) owns these details.

CT114 instead follows an explicit Git branch: build candidate → create an
independent data generation → cut over → verify → accept or restore previous
generation. It receives only staging appdata and scoped secrets, and has no
production/shared/hardware mounts or production Docker socket. See
[staging](../hosts/staging/README.md) for its recovery and external dependencies.

## Source map

- [provision](../provision): inventory, reconciliation, fleet verification.
- [hosts](../hosts): placement-specific Compose, prepare/verify helpers, native
  installers, and detailed service runbooks.
- [scripts](../scripts): guest export, deployment, environment initialization,
  PKI, native recovery capture, and documentation checks.
- [backup](../backup): PBS snapshot/restore and Proton orchestration.
- [clients](../clients): macOS SMB reconnect and SNOWSKY ECHO workflows.
- [docs](README.md): current guides, service policy, decisions, and dated evidence.
