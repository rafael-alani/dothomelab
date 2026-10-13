# Service policies

These are the repository-specific update and data-ownership requirements, moved
from the former long `AGENTS.md` during the documentation pilot on 2026-10-12.
Read the applicable service policy and its `hosts/` README before modifying a
service. Live readiness and drift belong in [status](../status.md); declarations
below do not establish that every service is running. The active user request
and observed live state take precedence over an older inventory snapshot.

## Placement and shared rules

- CT102 project `servarr-hello`: Gluetun plus download/Arr services,
  Deunhealth, Portainer/Agent. Gluetun, qBittorrent, NZBGet, and Prowlarr share
  one network namespace; update that cohort with Compose.
- CT102 project `soularr` supplies Lidarr from CT112 slskd through the shared
  slskd download tree. Its scheduler defaults off until Lidarr monitoring is
  curated; it never mounts the permanent music library directly.
- CT102 project `cleanuparr` is the supported stalled-torrent controller for
  qBittorrent plus Sonarr, Radarr, Lidarr, and Readarr. It is authenticated and
  LAN-only, uses the exact private Servarr network, has no shared-data mount,
  and persists only under canonical appdata. Its exact 2.10.0 digest is
  manually updated with `wud.watch=false`. Queue Cleaner runs every 30 minutes:
  public stalls need 12 strikes, private stalls need 48, meaningful 64 MiB
  progress resets strikes, metadata stalls need 12, and slow/failed-import
  cleaners remain off. Internet/client failures fail closed. Removal goes
  through the owning Arr with blocklisting, and replacement-only Seeker
  searches every five minutes; never delete a managed stalled torrent directly
  in qBittorrent.
- CT110: `infra-services`, `n8n`, `pulse`, `wud`, `obsidian-sync`, plus native
  Cockpit/Samba/Tailscale.
- CT112: `audiobookshelf`, `aurral`, `bar-assistant`, `bookorbit`, `grimmory`,
  `immich-migration`, `immichframe`, `kavita`, `loki`, `media`, `apps-mealie`, `paperless-ngx`,
  `navidrome`, `paperless-gpt`, `pinepods`, `prometheus`, `apps-services`, `slskd`,
  `snapotter`, `stirling-pdf`, `storyteller`, `music-metadata`, `wizarr`,
  `yt-dlp-web-ui`, `zotero-webdav`. Declared normal startup excludes
  DroppedNeedle; the live pending-acceptance exception is preserved below.
- Immich uses its supported PostgreSQL 14/VectorChord image.
- Jellystat uses private PostgreSQL 18. Mealie uses SQLite.
- Paperless-ngx uses private PostgreSQL 18 and Valkey. Paperless-GPT sends
  document content to the configured OpenAI API and remains private to the LAN
  and Tailscale because it has no native authentication. They are separate
  Compose projects joined only by the external `dothomelab-paperless` bridge;
  deploy Paperless-ngx before Paperless-GPT.

## Paperless

- `paperless-ngx` uses `paperless-ngx:latest` and is enrolled in the
  backup-gated WUD route.
- `paperless-gpt` uses `paperless-gpt:latest` and is enrolled in the
  backup-gated WUD route.
- `paperless-db` uses `postgres:18`, not `latest`, and has
  `wud.watch=false`. Update it manually only after a current logical dump and
  successful isolated restore test; PostgreSQL major changes are migration
  tasks.
- `paperless-broker` uses `valkey/valkey:9`, not `latest`, and has
  `wud.watch=false`. Update it manually with Compose after a Paperless
  compatibility check; Valkey major changes are migration tasks.

## Observability

- `prometheus` uses the current LTS image `prom/prometheus:v3.13.1`, not
  `latest`, and has `wud.watch=false`. Update it manually within the 3.13 LTS
  line with readiness/query verification; treat a later major or LTS-line
  change as a TSDB migration task.
- `loki` uses `grafana/loki:3.7.3`, not `latest`, and has
  `wud.watch=false`. Update it sequentially and manually with target-image
  config validation and readiness/query verification because Loki releases
  can change config and storage behavior.
- Both persist under `/srv/appdata/docker`, retain 30 days, and are private
  to LAN/Tailscale through NPM. Loki has no native authentication and no log
  shipper is declared yet; do not make its API public.

## ImmichFrame and Wizarr

- `immichframe` uses the upstream
  `ghcr.io/immichframe/immichframe:latest` channel and is enrolled in the
  backup-gated WUD route. Its configuration is reproducible from Git and the
  scoped `IMMICHFRAME_API_KEY` recovery secret.
- `wizarr` uses the upstream `ghcr.io/wizarrrr/wizarr:latest` channel and is
  enrolled in the backup-gated WUD route. Its SQLite-backed application state
  is protected by the appdata snapshot before update.
- ImmichFrame and the primary `wizarr.rafael.media` route are private to
  LAN/Tailscale. ImmichFrame upstream advises against public exposure.
  The separately authorized `join-stream.rafael.ink` route exposes
  authenticated Wizarr publicly for invitation redemption; generate public
  invitations from that origin. Further Wizarr exposure changes require a
  separate review.

## Bar Assistant and yt-dlp Web UI

- `barassistant/server:v5` and `barassistant/salt-rim:v4` are the upstream
  stable-major channels; Bar Assistant does not publish a `latest` server
  tag. `getmeili/meilisearch:v1.15` follows the upstream instruction to
  never use `latest`, and `redis:8-alpine` stays within Redis major 8.
- All four Bar Assistant containers have `wud.watch=false`. Update the
  complete project manually only after a Bar Assistant export,
  migration-note review, and API/SQLite/search/Redis/UI checks. Do not update
  its API, frontend, search index, or session service independently.
- `yt-dlp-web-ui` uses
  `ghcr.io/marcopiovanello/yt-dlp-web-ui:latest` and is enrolled in
  backup-gated WUD. On 2026-07-25 both upstream-documented `v4` registry
  references returned `manifest unknown`, while the official GHCR `latest`
  manifest resolved. Recheck the registry before changing channels. Its
  config/SQLite/session state is in appdata; downloaded media is under
  `/vault/shared/media/yt-dlp` and is not part of PBS appdata backups.
- Bar Assistant's three NPM routes and the authenticated yt-dlp route are
  private to LAN/Tailscale. Do not expose any of them publicly without a
  separate review.

## SnapOtter and Stirling-PDF

- `snapotter/snapotter:latest` is the upstream latest-release channel and is
  enrolled in backup-gated WUD. SnapOtter automatically applies pending
  schema migrations at application startup, so the PVE pre-backup hook must
  create a current logical dump before the appdata snapshot and WUD handoff;
  the sequential runner must pass `/api/v1/health` before continuing.
- SnapOtter uses application-private `postgres:17-alpine` and
  `redis:8-alpine`, not `latest`. Both have `wud.watch=false`. Update them
  manually only after a current logical dump and successful isolated restore
  test; a PostgreSQL major or Redis major change is a migration task.
- `stirlingtools/stirling-pdf:latest` is the upstream standard image and is
  enrolled in backup-gated WUD. Its settings, account database, custom
  files, pipelines, and OCR data persist in appdata, and the sequential
  runner must pass `/api/v1/info/status` after replacement.
- SnapOtter at `snapotter.rafael.media` and Stirling-PDF at
  `pdf.rafael.media` use application authentication and private NPM routes
  limited to LAN/Tailscale. Complete both forced first-login password changes
  before normal use; do not expose either service publicly without a
  separate review.

## Music

- Aurral uses the exact upstream v2 prerelease
  `ghcr.io/lklynet/aurral:2.0.0-test.7` at the repository-declared digest,
  is manually updated, and has
  `wud.watch=false`. Soularr, Navidrome, and slskd use their official stable
  `latest` channels with digest watching and the backup-gated WUD trigger.
  Navidrome and slskd have meaningful direct service checks.
- A shared nonblocking job lock plus live slskd transfer inspection prevents
  WUD from replacing Soularr or slskd during acquisition/import work.
- Lidarr is the sole owner and organizer of permanent music. Aurral v2
  durably records main-library requests and immediately starts Lidarr's
  torrent/Usenet search. The default fail-closed Soularr scheduler exposes
  only recent Aurral request IDs after a grace period, applies a persistent
  six-hour per-album retry cooldown, then uses the existing external slskd API
  and Soulseek identity. Aurral has no separate Soulseek account and writes
  its appdata, `/vault/shared/media/aurral-flows`, and its narrow slskd
  download bind; it cannot write permanent music. Soularr writes the slskd download tree
  and invokes Lidarr import; Navidrome and Jellyfin read music only.
- DroppedNeedle is excluded from normal Compose startup, Pi-hole/NPM, Homarr,
  and WUD. Its Compose, appdata, and image remain for exact rollback. The
  current live container remains enabled only until an Aurral flow and the
  Soularr import path pass; then stop it with restart disabled. A clean
  bootstrap must never start it as a second permanent-library writer.
- Music, Aurral flows, and slskd downloads remain under `/vault/shared`,
  outside PBS appdata backup. TCP 50300 listens only on the Apps LAN address
  and is not added to the unchanged router's public forward; any inbound
  Soulseek forwarding requires a separate exposure review.

## Audiobookshelf and Kavita

- `ghcr.io/advplyr/audiobookshelf:latest` is upstream's stable release
  channel and is enrolled in backup-gated WUD. Its SQLite configuration and
  metadata persist in appdata; the sequential runner must pass the direct UI
  endpoint after replacement.
- `ghcr.io/kareadita/kavita:latest` is upstream's stable release channel and
  is enrolled in backup-gated WUD. A new deployment starts beyond Kavita's
  legacy pre-v0.7.6 ordered-upgrade boundary; pause WUD and treat any future
  upstream-mandated ordered release as a migration task. The sequential
  runner must pass `/api/health` after replacement.
- Both services run as Apps UID/GID `1000:1000`, keep their application
  databases/state under `/srv/appdata/docker`, and publish private
  LAN/Tailscale NPM routes with native first-run authentication. Kavita's
  books/comics/manga libraries are read-only. Audiobookshelf has the narrow
  reviewed audiobook metadata-write exception described in the Grimmory
  policy below. Podcast downloads remain under `/vault/shared`, outside PBS
  appdata backup.

## Listenarr

- `ghcr.io/listenarrs/listenarr:canary-1.2.2` is pinned at the reviewed OCI
  digest because upstream has no stable release. It has `wud.watch=false`
  and is updated manually only after release-note review, current rollback,
  database migration review, and focused search/client/import verification.
- Listenarr is the sole audiobook acquisition and organization service.
  Shelfarr remains the sole ebook organizer and sees audiobooks read-only.
  Listenarr publishes only to canonical audiobooks, uses dedicated
  qBittorrent category `listenarr`, preserves seeding through hardlink/copy,
  and shares the existing NZBGet `Books` category.
- Listenarr authentication is enabled before first boot. Its administrator
  password and API key live only in `/root/.env`; appdata and latest/previous
  integrity-checked SQLite copies are under `/srv/appdata/docker/listenarr`.
  Audiobooks remain under `/vault/shared`, outside PBS appdata backup.
- Listenarr metadata and cover embedding remain disabled. Audiobookshelf is
  the review-gated canonical audiobook metadata writer and discovers imports
  through its existing library scan.

## Grimmory

- `ghcr.io/grimmory-tools/grimmory:latest` is the official stable rolling
  channel, is backup-gated in WUD, and must pass `/api/v1/healthcheck`.
  Its private `lscr.io/linuxserver/mariadb:11.4.8` has `wud.watch=false`;
  update it manually only after a current logical dump and isolated restore.
- Shelfarr remains the ebook organizer and Listenarr the audiobook
  organizer. Grimmory alone receives the narrow read-write canonical EPUB
  bind. It sees audiobooks read-only; automatic moving, renaming, merging,
  BookDrop, and non-book shared paths are disabled.
- Online metadata proposals fail closed for native review because Grimmory's
  current match score measures completeness, not identity confidence.
  The representative M4B pilot removed its AAC stream and chapters, so its
  exact snapshot bytes were restored and Grimmory audiobook file writing is
  permanently disabled.
- Audiobookshelf is the canonical audiobook metadata writer through its
  narrow read-write bind. Native matching remains review-gated. Its embed
  tool must use stream copy, embed the existing chapters, retain its
  application backup copy, and pass codec/duration/chapter verification.
  Automatic M4B merging, moving, renaming, and unreviewed matching remain
  disabled.
- Grimmory state and logical MariaDB dumps are in appdata. Its canonical
  ebook bind and Audiobookshelf's canonical audiobook bind remain on
  `/vault/shared`, outside PBS appdata backup.

## Storyteller

- `registry.gitlab.com/storyteller-platform/storyteller:latest` is the
  official stable rolling channel and is enrolled in backup-gated WUD.
  The sequential runner must pass `/api/health`, and it must skip replacement
  while reconciliation, inbox import, or a `QUEUED`/`PROCESSING` readaloud is
  active.
- The reconciler matches only the byte-identical two-component
  `{author}/{title}` key, reads canonical ebooks/audiobooks through CT112's
  broad read-only `/data`, and atomically publishes verified disposable
  copies into the narrow read-write `/storyteller/inbox`. It never guesses,
  hard-links, moves, or edits canonical files.
- Storyteller's SQLite/config/manifest and consistent latest/previous SQLite
  backups are in appdata and covered by PBS. Its shared inbox/library and
  accepted readaloud assets are outside appdata PBS; do not call them backed
  up or delete them as cache. The private NPM route is LAN/Tailscale only.

## PinePods

- `madeofpendletonwool/pinepods:latest` is the official stable rolling
  application channel and is enrolled in backup-gated WUD. The sequential
  runner must pass `/api/health` after replacement.
- PinePods-private `postgres:18` and `valkey/valkey:8-alpine` have
  `wud.watch=false`. PostgreSQL uses `PGDATA=/var/lib/pgdata/pgdata` below a
  host bind mounted at `/var/lib/pgdata`; update either major only through a
  compatibility review and current logical-dump/isolated-restore test.
- Database, configuration, server backups, portable latest/previous logical
  dumps, and retained restore-test evidence are in
  `/srv/appdata/docker/pinepods`. Episode downloads are only in
  `/vault/shared/media/podcasts/pinepods`, outside appdata PBS.
- PinePods is the only active podcast subscription/progress service.
  Audiobookshelf remains canonical for audiobooks; its former podcast
  library record, users, appdata, and any old files are retained unchanged.
  Unsupported progress migration must be documented, never implemented by
  editing either database.
- `pinepods.rafael.media` is private to LAN/Tailscale with TLS and
  WebSockets. Built-in GPodder is the supported client-sync interface;
  standard login remains enabled unless a separately tested OIDC recovery
  path is accepted.

## n8n and Pulse

- Both are separate Infra projects on upstream `latest`, backup-gated WUD,
  private LAN/Tailscale routes, and canonical appdata; preserve
  `N8N_ENCRYPTION_KEY` with n8n data.
- Pulse uses `PVEAuditor` for every LXC. Docker telemetry and lifecycle
  actions need a command-enabled agent in every `PULSE_DOCKER_CTIDS` guest;
  keep inventory, bootstrap, and verification current when Docker placement
  changes. Agents self-update with checksum/signature verification; Docker
  image updates stay off and remain exclusive to backup-gated WUD.
- Other services retain native stores. There is no central PostgreSQL.
- CT114 staging uses `hosts/staging/apps.json` and reviewed Compose definitions.
  Its 6-core/16-GiB limits and 500-GiB thin root quota share host capacity;
  the appdata bind is outside that quota. Use `app.staging.rafael.media` with
  the dedicated DNS-01 wildcard certificate and private NPM ACL.
  Its two-minute branch poller builds before cutover and uses independent data
  generations plus health/integrity checks for rollback. This user-requested
  branch update path is separate from WUD; staging images use `wud.watch=false`.
  Film-introspect starts in private demo mode with a dedicated auth secret.
  Never inject production integration keys implicitly. Source bundles, scoped
  environments, databases and rollback generations are canonical appdata.
  See [the staging runbook](../../hosts/staging/README.md); use `./bootstrap.sh --staging-only` for focused
  deployment. Do not delete retained generations/images without cleanup scope.

## Additional established service contracts

- [Shelfarr](../../hosts/servarr/shelfarr/README.md) owns ebook organization.
  Preserve its copy-mode download imports, disabled direct providers/uploads
  and Libation integration, single active library-platform slot, and retained
  Audiobookshelf inventory connection. BookOrbit discovers ebook files through
  its own watcher/scan. Observe the documented old-environment signing-key
  replacement requirement during restore.
- [BookOrbit](../../hosts/apps/bookorbit/README.md) reads its four libraries
  without renaming or embedded metadata writes. Its rolling app is backup-gated;
  private pgvector/PostgreSQL 18 remains manual with logical dump/restore tests.
- [Music metadata](../../hosts/apps/music-metadata/README.md) is a manually
  updated canonical writer. It uses Lidarr's selected release, verifies hardlink
  detachment before tags/art/ReplayGain, acquires the shared job lock, and never
  moves or renames files. Retain its per-album review reports.
- [Cross-seed](../../hosts/servarr/cross-seed/README.md) uses the strict separate
  project and Gluetun-only BitTorrent policy. Preserve private-tracker download
  compatibility and excluded direct-connect sources; use its dedicated deploy
  and approval workflow. Do not bypass the VPN to clear a tracker error.
- [Sortarr](../../hosts/servarr/sortarr/README.md) is read-only analytics;
  Cleanuparr remains the stalled-torrent controller.

## Database and deployment invariants

Keep databases application-local unless a future task proves compatibility,
isolation, backup, recovery, and rollback benefits. Never copy PostgreSQL data
directories between versions/servers. Major/database-extension changes require
logical dumps and tested rollback.

Rolling application tags are allowed when enrolled in backup-gated WUD.
Databases, WUD, Immich, Gluetun, and bespoke upgrade paths remain manual.
Always run `docker compose config` before deployment.
