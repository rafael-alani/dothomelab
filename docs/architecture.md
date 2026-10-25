# Architecture

Git declares a rebuildable homelab on PVE node `afa`. This page explains its
boundaries; [inventory.env](../provision/inventory.env) owns exact identities and
resources, and [status](status.md) records running state and drift.

## System map

| Host / guest | Responsibility |
|---|---|
| PVE `afa` — `192.168.0.250` | ZFS, guest lifecycle, appdata backup and update handoff |
| CT102 Servarr — `.102` | VPN-backed acquisition and media organization |
| CT110 Infra — `.110` | DNS, NPM, Homarr, SMB/Cockpit/Tailscale, monitoring, automation |
| CT112 Apps — `.112` | User applications, readers, and narrowly scoped metadata writers |
| CT113 PBS — `.159` | Encrypted appdata backup history |
| CT114 Staging — `.114` | Isolated Git-branch builds and application data generations |
| CT115 Production — `.115` | Manual `origin/main` releases; SSD appdata; dormant until explicit activation |
| VM104 HAOS — `.125` | Home Assistant with Supervisor, native backups, and VMA recovery |
| VM101 | Unmanaged by this repository |

LXCs are unprivileged. Docker runs in CT102/110/112/114/115; PBS and the listed Infra
native services run outside Docker. Service definitions live under `hosts/`;
[the manual](../USER_DOC.md#capability-index) maps applications to user goals.

## Network contract

Clients use Pi-hole DNS → NPM TLS routing → a published guest port → the app and
its private database. SMB is a separate LAN-only file-access path.

- PVE uses `vmbr0`, `192.168.0.250/24`, gateway `192.168.0.1`.
- Guest addresses are static with preserved MACs from inventory; router DHCP
  reservations are not rebuild dependencies.
- Pi-hole binds secondary Infra address `192.168.0.100`. The unchanged router
  advertises that DNS address and forwards public TCP 80/443 to `.110`.
- NPM owns routes and certificates. Private managed routes allow LAN/Tailscale;
  older routes can differ. See the [route runbook](../hosts/infra/proxy/README.md).
- WUD reaches remote Docker over mutual TLS on TCP 2376. Never expose 2375.
  Internal database/cache containers do not need public routes.

## Storage and ownership

| Material | Canonical home | Recovery role |
|---|---|---|
| Desired configuration / scripts | Git | Recreate packages, guests, services |
| Secrets | PVE `/root/.env` | Separate protected input; Compose dotenv |
| Databases, application/native state, HAOS VMA | SSD `rpool/appdata/docker` → `/srv/appdata/docker` | Encrypted appdata PBS input |
| Media, photos, Obsidian, downloads | HDD `vault/shared` → `/vault/shared` | Separate recovery input; outside appdata PBS |
| PBS datastore | `vault/pbs_datastore` → `/vault/pbs_datastore` | 2 TiB quota; same physical host |
| Guest roots | PVE guest storage | Replaceable OS/packages/images/cache |

CT102 sees shared data RW at `/data` and appdata at `/docker`; CT110 sees both
canonical paths RW. CT112's broad `/data` is RO, with narrow RW binds for yt-dlp,
music/slskd, podcasts, and Storyteller. Its explicit `mp7`/`mp8`/`mp9` carry the
Aurral flow, Grimmory ebook, and Audiobookshelf audiobook bridges through
appdata paths. Their bytes still belong to `vault/shared`, outside appdata PBS.
CT113 receives its datastore at `/mnt/datastore/appdata`.

Host `101000:101000` maps to guest `1000:1000`; PBS uses host `100034:100034`
for guest `34:34`. Inspect effective mounts and every consumer before permission
work. `/vault/backups` is legacy storage and `/vault/data` contains guest disks;
neither is scratch. Exact mount/writer rules are in the
[media contract](media-data-contract.md) and inventory.

Lidarr organizes music, Shelfarr ebooks, Listenarr audiobooks, and PinePods
podcasts. Grimmory writes reviewed EPUB metadata; Audiobookshelf writes reviewed
audiobook metadata; music-metadata writes selected-release tags/art. Readers
cannot reorganize those libraries. Aurral flows and Storyteller derived assets
have separate trees. [Service runbooks](reference/service-policies.md) own the
publication and rollback requirements.

## Deployment boundaries

Guests receive a Git archive at `/opt/dothomelab`, identified by
`DEPLOYED_COMMIT`. Durable state stays outside their replaceable roots. The
[rebuild contract](rebuild.md) defines required inputs and failure behavior.

Production updates follow successful appdata backup → WUD → sequential eligible
replacement and health checks. Databases and special cohorts remain manual;
there is no central PostgreSQL. [WUD](../hosts/infra/wud/README.md) owns update
rules; [operations](operations.md#backup-and-recovery) summarizes protection.

Shared Umami, its application-local PostgreSQL and Grafana run on CT112 with
state at `/srv/appdata/docker/blog-observability`. Alloy and Blackbox Exporter
stay on CT114; existing private dashboard URLs remain stable. See the
[observability runbook](../hosts/staging/blog-observability/README.md).

CT114 receives `/srv/appdata/docker/staging` (host `100000:100000`, guest
root) and scoped secrets. Only Stillroom additionally receives the authorized
photos/archive binds and dedicated production read API key. No whole production
appdata tree, production environment file, hardware or remote Docker socket is
exposed. Its separate
branch poller builds before cutover, verifies an independent data generation,
and accepts or rolls back. Read the [staging runbook](../hosts/staging/README.md).

The [blog publisher](../hosts/infra/blog-publisher/README.md) reads the synced vault
on CT110 through a read-only container mount. It writes selected article/media
snapshots under staging appdata; CT114 receives those exports, never a vault mount.
The release records both its Git code revision and content digest. Drafts render
only in the private preview; a public build must use the approved published subset.

## Source map

- [provision](../provision): inventory, bootstrap orchestration, fleet checks.
- [hosts](../hosts): Compose, prepare/verify scripts, native installers, runbooks.
- [scripts](../scripts): guest export, deployment, secret initialization, PKI,
  native recovery capture, documentation checks.
- [backup](../backup): PBS and Proton orchestration.
- [clients](../clients): macOS reconnect and SNOWSKY ECHO workflows.

### Stillroom staging data exception

The explicitly authorized Stillroom test adds only photos and archive binds to
CT114. Its container maps the photo tree to production Immich's `/old-photos`
path and writes complete verified bundles into `/archive/temp`. Its dedicated
API key has read permissions only. Stable tracker state survives app release
rollback because originals may have moved outside appdata. See the
[staging runbook](../hosts/staging/README.md#stillroom-external-library-archiving)
and [media contract](media-data-contract.md#photo-archiving).

### Project production

[CT115](../hosts/production/README.md) uses a 64 GiB `local-zfs` root quota
and only `/srv/appdata/docker/production` as its durable SSD bind. It has no
staging/media mounts, shared environment or remote Docker API. Its blog code
comes exclusively from `origin/main`; no background process deploys that branch.
The explicit activation command builds a retained published-only artifact and
switches the existing apex `rafael.ink` route after origin health passes.

The shared CT112 observability services retain separate production website,
dashboard, metric jobs and environment labels. A same-origin collection-only
proxy exposes Umami's script/send endpoints after publication; administration
stays private. Production discovery files remain empty while the app is off.
