# dothomelab

One-command recovery for Rafael’s Proxmox homelab: after installing PVE 9 on node `afa`, importing `vault`, restoring `/vault/shared`, `/srv/appdata/docker`, and `/root/.env`, this repository creates the ZFS datasets and four LXCs, restores the managed Home Assistant OS VM, installs every package, restores native credentials/state, deploys all Compose projects, configures PBS and backup-gated updates, and verifies the result. VM101 and router mutation remain deliberately out of scope.

## Architecture

```text
afa — Proxmox VE 9 (70 declared Docker containers)
├── storage contracts
│   ├── rpool/appdata/docker → /srv/appdata/docker (encrypted appdata PBS)
│   └── vault/shared → /vault/shared (large media; outside appdata PBS)
├── CT102 servarr — Debian 12, 17 containers
│   └── gluetun, qbittorrent, nzbget, prowlarr, sonarr, radarr,
│       lidarr, readarr, bazarr, flaresolverr, deunhealth,
│       portainer, portainer_agent, shelfarr, shelfarr-libation, soularr,
│       cleanuparr
├── CT110 infra — Debian 12, 11 containers + Cockpit/Samba/Tailscale
│   ├── infra-services: pihole, homarr, nginx-proxy-manager,
│   │   cloudflare-ddns, helloworld, portainer, portainer_agent
│   ├── n8n
│   ├── pulse
│   ├── wud
│   └── obsidian-sync: syncthing + on-demand Proton Drive CLI
├── CT112 apps — Debian 12, 42 containers
│   ├── aurral
│   ├── audiobookshelf
│   ├── pinepods: pinepods, pinepods-db, pinepods-valkey
│   ├── bar-assistant: bar-assistant, bar-assistant-salt-rim,
│   │   bar-assistant-meilisearch, bar-assistant-redis
│   ├── bookorbit: bookorbit, bookorbit-db
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
├── VM104 homeassistant — HAOS; restored from canonical appdata
└── VM101 — unmanaged by this repository
```

VM104 uses HAOS rather than Home Assistant Container so Supervisor-managed
apps, HAOS A/B rollback, and native protected backups remain supported. Its
verified full VMA recovery image and protected native backups are below
`/srv/appdata/docker/home-assistant`; see `docs/haos-vm.md`.

The media data contract is active: Shelfarr is CT102's sole ebook and
audiobook organizer, BookOrbit reads the canonical ebook/PDF/comic trees,
Audiobookshelf reads canonical audiobooks without write access, PinePods owns
podcast subscriptions/downloads/progress in its narrow shared subtree, and
Storyteller stages exact matched pairs into an isolated library for
user-approved alignment. Lidarr is the sole permanent-music organizer and
selected-release authority. The narrow music-metadata service writes exact
MusicBrainz tags, embedded front art, `cover.jpg`, and ReplayGain without
moving files; it breaks imported hardlinks with verified copy-on-write or
byte-identical copy detachment first. Aurral
v2 durably records requests and starts Lidarr's torrent/Usenet search; its
request-scoped Soularr fallback supplies only unresolved recent requests
through the shared slskd identity. Aurral owns only its separate flow library,
and Navidrome plus Jellyfin read music without write access. DroppedNeedle is
retained only as a stopped rollback profile. See
[the media contract](docs/media-data-contract.md),
[phase 2 evidence](docs/media-pipeline-phase-2-evidence-2026-07-25.md),
[phase 3 evidence](docs/media-pipeline-phase-3-evidence-2026-07-25.md),
[phase 4 evidence](docs/media-pipeline-phase-4-evidence-2026-07-25.md),
[phase 5 evidence](docs/media-pipeline-phase-5-evidence-2026-07-26.md),
[Aurral v2 request evidence](docs/aurral-v2-request-pipeline-2026-07-26.md),
[canonical music metadata evidence](docs/music-metadata-canonicalization-2026-07-26.md),
and
[stalled-download recovery evidence](docs/cleanuparr-stalled-download-recovery-2026-07-26.md).

PVE also owns a fortnightly, two-generation Proton Drive backup of the
Syncthing-received Obsidian vault, `/vault/shared/media/photos`, and
`/root/.env`. The timer remains disabled until Proton login and first restore
tests; see `hosts/infra/obsidian-sync/README.md`.

The authenticated Syncthing GUI is private at
`https://syncthing.rafael.media`: Syncthing remains bound to CT110 loopback,
while Pi-hole and NPM provide exact local DNS, TLS, WebSockets, and
LAN/Tailscale-only access.

## Bootstrap

```bash
git clone https://github.com/rafael-alani/dothomelab.git /root/dothomelab
cd /root/dothomelab
./bootstrap.sh
```
