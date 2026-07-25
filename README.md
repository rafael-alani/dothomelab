# dothomelab

One-command recovery for Rafael’s Proxmox homelab: after installing PVE 9 on node `afa`, importing `vault`, restoring `/vault/shared`, `/srv/appdata/docker`, and `/root/.env`, this repository creates the ZFS datasets and four LXCs, installs every package, restores native credentials/state, deploys all Compose projects, configures PBS and backup-gated updates, and verifies the result; VMs and router mutation remain deliberately out of scope.

## Architecture

```text
afa — Proxmox VE 9 (40 declared Docker containers)
├── CT102 servarr — Debian 12, 13 containers
│   └── gluetun, qbittorrent, nzbget, prowlarr, sonarr, radarr,
│       lidarr, readarr, bazarr, flaresolverr, deunhealth,
│       portainer, portainer_agent
├── CT110 infra — Debian 12, 9 containers + Cockpit/Samba/Tailscale
│   ├── infra-services: pihole, homarr, nginx-proxy-manager,
│   │   cloudflare-ddns, helloworld, portainer, portainer_agent
│   ├── wud
│   └── obsidian-sync: syncthing + on-demand Proton Drive CLI
├── CT112 apps — Debian 12, 18 containers
│   ├── immich-migration: immich_migration_server,
│   │   immich_migration_machine_learning, immich_migration_redis,
│   │   immich_migration_postgres
│   ├── media: jellyfin, seerr, jellystat, jellystat-db
│   ├── apps-mealie: mealie
│   ├── loki
│   ├── paperless: paperless-ngx, paperless-gpt, paperless-db,
│   │   paperless-broker
│   ├── prometheus
│   ├── apps-services: portainer, portainer_agent
│   └── zotero-webdav
├── CT113 proxmox-backup-server — Debian 13, PBS 4 (no Docker)
├── VM101 — unmanaged by this repository
└── VM104 haos14.1 — unmanaged by this repository
```

PVE also owns a fortnightly, two-generation Proton Drive backup of the
Syncthing-received Obsidian vault, `/vault/shared/media/photos`, and
`/root/.env`. The timer remains disabled until Proton login and first restore
tests; see `hosts/infra/obsidian-sync/README.md`.

## Bootstrap

```bash
git clone git@github.com:rafael-alani/dothomelab.git /root/dothomelab
cd /root/dothomelab
./bootstrap.sh
```
