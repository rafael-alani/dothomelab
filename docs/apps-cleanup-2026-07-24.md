# Apps cleanup and deployment — 2026-07-24

This is the completion record for moving CT112's remaining application
services out of legacy Portainer stacks. The deployed source commit is recorded
in `/opt/dothomelab/DEPLOYED_COMMIT` on Apps and Infra.

## Active projects

| Compose project | Services | Persistent state | Verified image |
|---|---|---|---|
| `immich-migration` | Immich server, machine learning, Valkey, PostgreSQL 14/VectorChord | `/srv/appdata/docker/immich` plus read-only `/data/media/photos` | protected existing v3.0.3 deployment |
| `media` | Jellyfin, Seerr, Jellystat 1.1.11, PostgreSQL 18 | `/srv/appdata/docker/{jellyfin,seerr,jellystat}` | Jellystat `sha256:23c908aa24b3`; PostgreSQL `sha256:1bf3d6960db4` |
| `apps-mealie` | Mealie v3.21.0 with SQLite | `/srv/appdata/docker/mealie` | `sha256:a14c033391ae` |
| `apps-services` | Portainer CE and Agent 2.39.5 | `/srv/appdata/docker/portainer` | server `sha256:be26dc26896a`; agent `sha256:e4ff0a7073d5` |
| `zotero-webdav` | Zotero-compatible WebDAV | `/srv/appdata/docker/zotero-webdav` | `sha256:7da8f5372c94` |

All application containers above except Immich use the central
`docker.backupgated` WUD trigger. Jellystat PostgreSQL, every Immich service,
and WUD itself remain excluded. Portainer's tag filter permits only 2.39 LTS
patch releases. The final dry run discovered all 26 opted-in containers across
Infra, Apps, and Servarr, associated all 26 with the trigger, and found no
eligible update.

## Restore and verification notes

The supplied ignored Mealie ZIP was restored into a clean v3.21.0 SQLite
deployment with Mealie's backup API. The focused check found 11 recipes and 1
user; `/`, `/login`, and `/api/app/about` responded. For a future rebuild
without restored appdata, start a clean Mealie deployment and use:

```bash
MEALIE_RESTORE_URL=http://192.168.0.112:9925 \
  hosts/apps/mealie/restore-backup.sh /path/to/mealie-backup.zip
```

The restore endpoint uses the bootstrap account only on a clean installation
and logs the session out after importing the saved accounts. Keep the ZIP
outside Git.

Jellystat intentionally has a fresh database. Complete its initial UI setup
against Jellyfin after restore. Portainer intentionally has a clean database;
complete the initial administrator setup after restore. Run the focused
project scripts after deployment:

```bash
hosts/apps/mealie/verify.sh
hosts/apps/media/verify.sh
hosts/apps/services/verify.sh
```

Zotero WebDAV is private at `https://zotero.rafael.media/zotero/`. Its
verification rejected unauthenticated access, then completed authenticated
PROPFIND, PUT, GET, byte comparison, and DELETE over HTTPS. Infra NPM also
served the route through its online Tailscale address. NPM allows only
`192.168.0.0/24` and `100.64.0.0/10`, then denies all other sources; the public
DNS answer is an unroutable RFC1918 address rather than a public origin. See
`hosts/apps/zotero-webdav/README.md` for desktop settings and credential
retrieval. The NPM database copy made before adding the route is
`database.sqlite.pre-zotero-20260724` beside the live NPM database.

## Removed legacy resources

The following were individually attributed and removed; no broad Docker prune
was used:

- legacy Mealie containers `legacy_mealie` and `legacy_mealie_postgres`,
  volumes `mealie_mealie-data`, `mealie_mealie-pgdata`,
  `mealie2_mealie-data`, and `mealie2_mealie-pgdata`, network
  `mealie_default`, v2.4.2/PostgreSQL 15 images, and Compose source 14;
- legacy Jellystat volumes `jellystat_jellystat-backup-data` and
  `jellystat_postgres-data`, its unused old application image, PostgreSQL 15.2
  image, and Compose source 17;
- standalone `legacy_portainer`, `portainer_data`, and the Portainer CE 2.21.5
  image;
- unused old-project `immich_model-cache` and Compose source 18, after proving
  that no container used either and that the active migration uses an SSD bind
  mount instead;
- GitLab CE's unused image and Compose source 20. No GitLab container, network,
  volume, SSD appdata, NPM route, Pi-hole record, Homarr app, or WUD entry
  remained.

The protected `immich-migration` container IDs, network, and mounts matched the
pre-cleanup baseline exactly. Its focused verifier again reported v3.0.3, all
four containers healthy, unchanged database counts, and all ten selected paths
readable.
