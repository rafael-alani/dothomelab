# Service policies and runbooks

Read the applicable runbook before changing a service. It owns detailed image,
configuration, data, and verification rules; Compose owns exact image references.
This index highlights exceptions rather than maintaining a second copy of every
runbook. Live readiness belongs in [status](../status.md).

## Shared update rules

Production rolling applications are eligible only through the backup-gated
[WUD path](../../hosts/infra/wud/README.md). Databases, WUD, Immich, Gluetun, and
special cohorts remain manual. Keep databases application-local; major/extension
changes need logical dumps, isolated restore tests, and rollback. Never copy
PostgreSQL data directories between versions/servers. Validate Compose before
deployment; [AGENTS](../../AGENTS.md) retains authorization and secret rules.

| Service / owning runbook | Constraint to check first |
|---|---|
| [WUD](../../hosts/infra/wud/README.md) | Backup `OnSuccess` is the only automatic production handoff; sequential health checks, busy-job guards, retained images, and Docker mTLS |
| [Cleanuparr](../../hosts/servarr/cleanuparr/README.md) | Exact manual digest; strike/progress thresholds and replacement-only Seeker; remove through the owning Arr, never directly in qBittorrent |
| [Cross-seed](../../hosts/servarr/cross-seed/README.md) | Dedicated deploy/approval path; strict matching, private-tracker compatibility, Gluetun-only BitTorrent |
| [Sortarr](../../hosts/servarr/sortarr/README.md) | Read-only analytics; does not replace Cleanuparr |
| [Aurral](../../hosts/apps/aurral/README.md) | Exact manually updated prerelease; Lidarr requests, shared slskd identity, separate flows; no permanent-library writes |
| [Soularr](../../hosts/servarr/soularr/README.md) | Fail-closed request scope, grace period, six-hour retry cooldown, shared job lock, Lidarr import |
| [slskd](../../hosts/apps/slskd/README.md) | WUD transfer guard; downloads are separate from canonical music; TCP 50300 has no declared public forward |
| [Music metadata](../../hosts/apps/music-metadata/README.md) | Manual writer; selected-release matching, verified hardlink detachment, shared lock, no moves/renames |
| [Navidrome](../../hosts/apps/navidrome/README.md) | Read-only music and flows; direct health check after WUD replacement |
| [DroppedNeedle](../../hosts/apps/droppedneedle/README.md) | Excluded from normal bootstrap/routes/WUD; preserve the live container and restart policy until Aurral flow and Soularr import acceptance pass |
| [Shelfarr](../../hosts/servarr/shelfarr/README.md) | Ebook copy-mode imports; disabled direct providers/Libation; one active platform slot; old-environment signing-key restore exception |
| [Listenarr](../../hosts/servarr/listenarr/README.md) | Exact manual canary digest; sole audiobook organizer; no metadata/cover embedding; authenticated first boot |
| [BookOrbit](../../hosts/apps/bookorbit/README.md) | Four read-only libraries, own watcher/scan; manual pgvector/PostgreSQL major |
| [Grimmory](../../hosts/apps/grimmory/README.md) | Reviewed EPUB publication only; permanently prohibit audiobook writes after failed M4B pilot; MariaDB updates require dump/restore |
| [Audiobookshelf](../../hosts/apps/audiobookshelf/README.md) | Reviewed stream-copy embed with file backup and codec/duration/chapter checks; no auto-match/merge; preserve inactive podcast state |
| [Kavita](../../hosts/apps/kavita/README.md) | Read-only libraries; any upstream ordered-upgrade requirement overrides normal WUD |
| [Storyteller](../../hosts/apps/storyteller/README.md) | Exact author/title pairs, verified copies, no canonical mutation; busy queue/import blocks WUD; accepted readalouds are not cache |
| [PinePods](../../hosts/apps/pinepods/README.md) | Sole active podcasts; narrow episode tree; GPodder progress, no database-edited migration; retain standard login until OIDC recovery is tested |
| [Paperless-ngx](../../hosts/apps/paperless-ngx/README.md) / [GPT](../../hosts/apps/paperless-gpt/README.md) | Deploy ngx first; private shared bridge; GPT needs a real OpenAI key and sends document content externally; PDF replacement stays disabled |
| [ImmichFrame](../../hosts/apps/immichframe/README.md) | Private slideshow; scoped read key; preserve restored SQLite configuration |
| [Wizarr](../../hosts/apps/wizarr/README.md) | Private admin origin; authorized public invitations use `join-stream.rafael.ink` |
| [Bar Assistant](../../hosts/apps/bar-assistant/README.md) | All four containers updated manually together after export, migration review, and API/database/search/Redis/UI checks |
| [yt-dlp](../../hosts/apps/yt-dlp-web-ui/README.md) | Backup-gated GHCR `latest`; recheck registry before changing channel; downloads are outside appdata |
| [SnapOtter](../../hosts/apps/snapotter/README.md) | Startup migrations require a fresh pre-backup logical dump; application `/api/v1/health` gate; database/cache updates need isolated restore |
| [Stirling-PDF](../../hosts/apps/stirling-pdf/README.md) | Authenticated private route and first-login setup; `/api/v1/info/status` update gate |
| [Zotero](../../hosts/apps/zotero-webdav/README.md) | Private personal-attachment WebDAV; verify authenticated byte round-trip |
| [n8n](../../hosts/infra/n8n/README.md) | Private editor/webhooks; preserve encryption key with appdata; review major migrations |
| [Pulse](../../hosts/infra/pulse/README.md) | PVEAuditor plus command-enabled agents in every `PULSE_DOCKER_CTIDS` guest; signed/checksummed agent updates; Docker image updates disabled |
| [Staging](../../hosts/staging/README.md) | Separate branch poller/data generations; scoped secrets; only Stillroom has authorized photos/archive mounts and a production read API key; no unscoped generation cleanup |
| [Blog observability](../../hosts/staging/blog-observability/README.md) | Private staging Umami/Grafana, local PostgreSQL 17, Blackbox probes and scoped Alloy journal shipping; all images manual; retain analytics/dumps on blog rollback; alert rules have no notification receiver |

## Policies without a dedicated service runbook

- **Servarr cohort:** Gluetun, qBittorrent, NZBGet, and Prowlarr share a network
  namespace. Update that cohort with Compose, preserving the VPN-only policy.
- **Immich / Jellystat / Mealie:** Immich uses supported PostgreSQL 14/VectorChord;
  Jellystat uses private PostgreSQL 18; Mealie uses SQLite. Keep native stores.
- **Paperless dependencies:** PostgreSQL 18 and Valkey 9 have `wud.watch=false`.
  PostgreSQL image updates require a logical dump and isolated restore; Valkey
  updates require compatibility review and Compose. Major changes are migrations.
- **Prometheus:** manually update within the declared 3.13 LTS line
  (`prom/prometheus:v3.13.1`), with readiness/query checks. A later major/LTS line
  is a TSDB migration task; `wud.watch=false`.
- **Loki:** `grafana/loki:3.7.3`, `wud.watch=false`; update manually/sequentially
  with target-image config validation and readiness/query checks. It has no
  native authentication; keep its API private. The declared
  [blog Alloy shipper](../../hosts/staging/blog-observability/README.md) forwards
  only sanitized staging blog access records; readiness does not prove ingestion.
  Both observability stores use appdata, 30-day retention, and private NPM routes.

## Infrastructure and recovery procedures

| Area | Owning runbook |
|---|---|
| DNS / proxy reconciliation | [NPM routes](../../hosts/infra/proxy/README.md) |
| Native file access | [Cockpit / Samba](../../hosts/infra/cockpit/README.md) |
| Syncthing / scoped Proton backup | [Obsidian sync](../../hosts/infra/obsidian-sync/README.md) |
| Appdata backup / restore | [PBS](../../backup/pbs/README.md), [rebuild](../rebuild.md) |
| Home Assistant VM | [HAOS](../haos-vm.md) |
| Canonical media paths and permissions | [Media contract](../media-data-contract.md) |
| Desktop clients | [macOS media](../../clients/macos-media/README.md), [SNOWSKY ECHO](../../clients/snowsky-echo/README.md) |
