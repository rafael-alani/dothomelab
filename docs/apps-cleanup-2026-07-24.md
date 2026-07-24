# Apps cleanup and deployment — 2026-07-24

This is the completion record for moving CT112's remaining application
services out of legacy Portainer stacks. The deployed source commit is recorded
in `/opt/dothomelab/DEPLOYED_COMMIT` on Apps and Infra.

## Current status

The live audit later on 2026-07-24 found all five projects running. The
non-secret media, Mealie, Portainer, and Immich verifiers passed; Zotero
retained its earlier same-day authenticated end-to-end evidence. Apps Portainer
has an administrator, Jellystat has one populated `app_config` row and reports
setup state 2, Mealie still has 11 recipes and 1 user, and Immich retains its
complete baseline.

The latest recurring PBS snapshot completed at 02:05 CEST before these projects
were finalized later that morning. The migration is operationally complete,
but the current Apps state still needs a newer successful PBS snapshot and a
temporary restore check before its rollback assets can be reconsidered.

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
patch releases. The final Apps-migration dry run discovered 26 opted-in
containers across Infra, Apps, and Servarr, associated all 26 with the trigger,
and found no eligible update. The later addition of Syncthing raised the live
total to 27.

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
and replaces that account after importing the saved accounts. The supplied
legacy ZIP did not include `data/.secret`, so the clean deployment kept its new
signing key and all browser tokens from the source instance became invalid.
Clear all cookies/site data for `mealie.rafael.media` before signing in to the
restored account; otherwise the UI can accept the password and then send the
stale token to `/api/users/self`, which returns 401. If a future ZIP does
include `data/.secret`, restart Mealie after restoring it so every server
module reloads the restored key. Keep the ZIP outside Git.

Jellystat intentionally began with a fresh database; the live instance is now
configured, but a future restore to an empty database still requires its UI
setup against Jellyfin. Portainer intentionally began with a clean database;
the live instance now has an administrator, but a future clean restore still
requires initial administrator setup. Portainer closes its admin-initialization
window after five minutes; if the status API returns
`Redirect-Reason: AdminInitTimeout`, run
`pct exec 112 -- docker restart portainer` and finish setup promptly. Run the
focused project scripts after deployment:

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
  `mealie_default`, and v2.4.2/PostgreSQL 15 images; Compose source 14 was
  already absent;
- legacy Jellystat volumes `jellystat_jellystat-backup-data` and
  `jellystat_postgres-data`, its unused old application image, PostgreSQL 15.2
  image; Compose source 17 was already absent;
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
