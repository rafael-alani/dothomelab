# dothomelab

One-command recovery for Rafael’s Proxmox homelab: after installing PVE 9 on node `afa`, importing `vault`, restoring `/vault/shared`, `/srv/appdata/docker`, and `/root/.env`, this repository creates the ZFS datasets and four LXCs, restores the managed Home Assistant OS VM, installs every package, restores native credentials/state, deploys all Compose projects, configures PBS and backup-gated updates, and verifies the result. VM101 and router mutation remain deliberately out of scope.

## Architecture

```text
afa — Proxmox VE 9 (57 declared Docker containers)
├── storage contracts
│   ├── rpool/appdata/docker → /srv/appdata/docker (encrypted appdata PBS)
│   └── vault/shared → /vault/shared (large media; outside appdata PBS)
├── CT102 servarr — Debian 12, 13 containers
│   └── gluetun, qbittorrent, nzbget, prowlarr, sonarr, radarr,
│       lidarr, readarr, bazarr, flaresolverr, deunhealth,
│       portainer, portainer_agent
├── CT110 infra — Debian 12, 11 containers + Cockpit/Samba/Tailscale
│   ├── infra-services: pihole, homarr, nginx-proxy-manager,
│   │   cloudflare-ddns, helloworld, portainer, portainer_agent
│   ├── n8n
│   ├── pulse
│   ├── wud
│   └── obsidian-sync: syncthing + on-demand Proton Drive CLI
├── CT112 apps — Debian 12, 33 containers
│   ├── audiobookshelf
│   ├── bar-assistant: bar-assistant, bar-assistant-salt-rim,
│   │   bar-assistant-meilisearch, bar-assistant-redis
│   ├── immich-migration: immich_migration_server,
│   │   immich_migration_machine_learning, immich_migration_redis,
│   │   immich_migration_postgres
│   ├── immichframe
│   ├── droppedneedle
│   ├── kavita
│   ├── media: jellyfin, seerr, jellystat, jellystat-db
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

Phase 1 declares the future books/audiobooks/podcasts/music paths and access
boundaries without deploying new applications; see
`docs/media-data-contract.md`.

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
