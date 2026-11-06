# Live n8n workflows and homelab automation opportunities — 2026-10-27

## Finding

The live n8n instance has **five workflows, two active schedules, and no archived
workflows**. All five belong to Contentflow. The schedules are configured, but
their intended real inputs are absent: the selected Obsidian `Publishing` folder
does not exist and the incoming-media mount contains zero files. There are zero
Contentflow jobs and delivery receipts. External publishing and archive moves
are disabled. This is installed automation scaffolding, not an operational
cross-service homelab automation suite.

The strongest next use of n8n is to combine information from existing apps into
useful decisions: operational exceptions, document deadlines, dinner preparation,
media readiness, reading notes, and publishing feedback. Keep domain operations
with their existing owners. The recommendations below are proposals; none was
installed, activated, or exercised against real user content.

## Evidence and scope

Inspected on October 27, 2026, around **20:00–20:07 CET (Europe/Amsterdam)**,
using SSH to PVE and `pct exec` into guests. The observation window is a snapshot,
not a historical availability audit.

- Inspected PVE guest state, all containers including stopped containers in each
  of the five Docker LXCs, n8n workflow/editor/published-version metadata,
  execution metadata, credential **types/counts only**, relevant container mounts,
  selected nonsecret configuration flags, and aggregate Contentflow database counts.
- Compared every running container with authenticated, paginated Pulse resources.
  Read Prometheus probe, scrape, alert and Alertmanager APIs. No workflow POST,
  smoke test, media scan, archive operation, publishing action or service restart
  was triggered. Production remained unchanged.
- SQLite connections used `mode=ro`. Private note bodies, document contents,
  execution payloads, token values and recovery secrets were not exported.
  Pulse credentials were consumed on PVE through the repository dotenv parser.
- n8n is **2.31.6**, verified through the container CLI and image label. Its
  timezone is `Europe/Amsterdam`; it uses its own SQLite store and has only the
  canonical n8n appdata mount. It has no shared-media or Docker-socket mount.
- All five deployed Contentflow modules inspected (`service`, `server`,
  `curation`, `publishers`, `archive_api`) matched the local source byte-for-byte
  by SHA-256. The source checkout is `/Users/rafael/Repos/n8n`, revision
  `5ac453771bad66662275362217394a59cfb07d7f`. It was read, not modified.
- Local homelab HEAD at inspection was
  `3a32ab971e95c909a1e6ca3fecb56ef5a45c9118`; CT110/114/115 each reported
  `/opt/dothomelab/DEPLOYED_COMMIT` as
  `9c2c15414382082ffb787fb4e912002564cbc902`.
- Official documentation and first-party API specifications establish proposed
  integration capabilities. Except for the monitoring reads above, authenticated
  application API contracts, user permissions and real notification delivery were
  not tested. Current upstream documentation may be newer than installed software.

## Every current n8n workflow

All HTTP steps call the private Contentflow companion on its shared Docker
network, using the same stored header-auth credential and a 120-second node
timeout. The two active graphs match their published versions. No workflow has
an assigned error workflow; HTTP nodes have no explicit retry policy.

| Workflow and ID | Trigger and actual graph | Intended result | Current usefulness |
| --- | --- | --- | --- |
| **Contentflow · Ready notes** — `177f2c3476244507` | Active, every 5 minutes; also manual. `Scan` → `Dispatch`: POST `/v1/scan`, then `/v1/dispatch`. | Select explicitly ready notes and destinations, prepare revision-bound bundles, then export, hand off or publish supported targets. | Selected `Publishing` folder absent; zero jobs/receipts; external publishing disabled and platform credentials absent. |
| **Contentflow · Incoming media** — `25743fe3d634f519` | Active, every 60 minutes; also manual. POST `/v1/curate`. | Incrementally review new/changed files in bounded batches and write private suggestions. | Mount remains `/opt/contentflow/examples/media`, with zero files. Latest curation-state write observed at 20:00:54 CET. |
| **Contentflow · Archive preview** — `70d695ca9251cb68` | Manual, inactive. POST `/v1/archive/plan`. | Resolve an explicitly selected Immich album, or exact file paths through the companion, into an immutable plan. | Workflow still contains its album-ID placeholder; Immich connection and archive source/destination are unconfigured. |
| **Contentflow · Apply reviewed archive** — `953ded497ba492a5` | Manual, inactive. POST `/v1/archive/apply`. | Move precisely the previously reviewed selection after matching the saved plan ID and confirmation. | Both plan/confirmation placeholders remain; archive enabled flag is false and required writable mounts are absent. |
| **Contentflow · Integration smoke test** — `11483fa18ec33569` | Manual, inactive. POST `/v1/smoke`. | Exercise synthetic ingestion, deduplication, export/handoff, curation, archive and restore using temporary fixtures. | Useful as an integration test, not a content workflow. Historical September success is documented; it was not rerun during this inspection. |

### What Ready notes actually does

Only `contentflow.status: ready` plus an explicit target list opts a note in.
Contentflow builds an inventory, checks IDs and source revisions, produces a
bundle, and records per-note-revision/per-target delivery state. Changed source
bytes are a new revision; duplicate prevention is not a blanket guarantee that
later edits cannot create another post. Uncertain delivery outcomes require
reconciliation rather than an automatic resend.

Its installed adapters have these boundaries:

- **Website:** writes a local article/assets bundle and HTML preview. This adapter
  does not deploy the current `rafael.ink` site.
- **LinkedIn/X:** text/link adapters exist, but no account credentials are
  configured. Native media and attachment-bearing articles use a manual handoff.
  This inspection does not establish present-day platform API/account acceptance.
- **Substack:** prepares an editor/import handoff.
- **Medium:** contains a legacy-token draft adapter; no credential is configured
  and no current platform compatibility is claimed.

The global publishing flag blocks API publication; local exports and manual
handoffs can still be possible when real eligible inputs exist. Today there are
none in the configured folder. The missing-source/incomplete-inventory cases
return a paused result through HTTP 200, so HTTP/node success alone would not
prove that anything was published.

### What Incoming media actually does

It uses file metadata and bounded hashing to flag empty files, camera-style
filenames, video review candidates and exact duplicates among sufficiently
hashed new/cached files. It does not inspect pixels, recognize people, judge
visual quality, validate audio/video integrity, delete duplicates or alter
originals. Its persistent cursor advances across batches. The current empty
example mount makes it a scheduled no-op for real media.

The installed module also contains optional Immich metadata-review logic, but
the active workflow calls filesystem `/v1/curate`; the helper's existence does
not mean a live Immich workflow is connected.

### What the archive pair would require

Preview saves a plan; it is not itself a move. Apply requires the exact saved
plan and confirmation, explicit source/destination configuration, and the
separately enabled writable deployment. Album selection additionally needs an
Immich read credential and verified external-library path mapping. The archive
must remain outside active Immich import roots. Current placeholders and missing
configuration make both workflows unfinished. Do not schedule Apply or bypass
the separate Stillroom review/acceptance path.

### Execution evidence and its limits

The four non-smoke workflows suppress saved successful execution data; the
smoke workflow retains success/manual records. All five retain errors by
workflow setting. At the final read there were **zero non-deleted execution
records**. Recent schedule rows were already marked for deletion: their stored
`running` field must not be treated as evidence of hung executions.

The recent schedule metadata and hourly curation-state timestamp show activity.
They do not establish a 30-day success rate or completed real publication. No
retained failure is not proof that no past failure occurred. n8n documents
selective execution persistence and a two-stage pruning process in its
[execution-data guide](https://docs.n8n.io/hosting/scaling/execution-data/).
Business outcomes need their own small, privacy-preserving status records:
last checked, input missing/empty, items queued, items completed, oldest pending
item and last actionable error.

## Live service coverage

All six managed LXCs are running. **VM104 Home Assistant is running; VM101 is
stopped.** Pulse agreed with both VM states. ZFS reported all pools healthy.
No reason for VM101's stopped state was established, and it was not started.

| Guest | Running Docker containers | Matched online in Pulse | Relevant capabilities |
| --- | ---: | ---: | --- |
| CT102 Servarr | 21 | 21 | Acquisition, download queues, subtitles, media library organization |
| CT110 Infra | 19 | 19 | n8n/Contentflow, monitoring, analytics, sync, DNS/proxy, update management |
| CT112 Apps | 42 | 42 | Documents, meals/drinks, photos, video, music, books, podcasts |
| CT114 Staging | 6 | 6 | Four app previews and local telemetry |
| CT115 Production | 1 | 1 | Local telemetry; blog serving is native |
| CT113 PBS | — | Guest online | Backup server; not a declared Docker host |
| **Total Docker** | **89** | **89** | No missing/extra online container names in the comparison |

The direct Docker enumeration found no stopped containers in those five guests
at this snapshot. All **34 configured endpoint probes** and **42 scrape targets**
were passing. Some probes accept authentication challenges; this does not prove
an authenticated journey or a working integration for every app. Prometheus
returned no active alerts and **no active or dropped Alertmanager endpoints**.
There is no ntfy or Alertmanager container in this inventory.

### Complete container inventory used for this research

- **CT102:** shelfarr-libation, shelfarr, lidarr, radarr, qbittorrent, sonarr,
  nzbget, soularr, prowlarr, portainer_agent, portainer, cross-seed, bazarr,
  flaresolverr, cross-seed-prowlarr-proxy, listenarr, gluetun, sortarr,
  cleanuparr, deunhealth, readarr.
- **CT110:** grafana, prometheus, observability-fleet, umami, umami-db, blackbox,
  loki, pulse, homarr, cloudflare-ddns, portainer_agent, portainer, syncthing,
  pihole, wud, nginx-proxy-manager, contentflow-contentflow-1, n8n, helloworld.
- **CT112:** jellyfin, stirling-pdf, slskd, audiobookshelf, zotero-webdav, wizarr,
  seerr, paperless-ngx, mealie, bookorbit, immichframe, jellystat, grimmory,
  storyteller, navidrome, portainer_agent, portainer, kavita, snapotter,
  grimmory-db, music-metadata, aurral, pinepods, pinepods-db, pinepods-valkey,
  storyteller-reconciler, bookorbit-db, paperless-db, paperless-broker,
  droppedneedle, yt-dlp-web-ui, bar-assistant-salt-rim, bar-assistant,
  bar-assistant-redis, bar-assistant-meilisearch, snapotter-db, snapotter-redis,
  jellystat-db, immich_migration_server, immich_migration_machine_learning,
  immich_migration_redis, immich_migration_postgres.
- **CT114:** blog-observability-alloy-1, staging-film-introspect-web-1,
  staging-film-introspect-api-1, staging-meta-egg-api-1,
  staging-stillroom-archiver-1, staging-ff-web-1.
- **CT115:** production-observability-alloy-1.

Container presence is not a mandate to activate an unused feature. In particular,
the retained Readarr, DroppedNeedle and Shelfarr Libation containers do not
override current service policies. The `immich_migration_*` names identify live
production Immich services, not disposable migration leftovers. Paperless-GPT
is absent from this runtime inventory despite historical dashboard/docs entries.

Native services also matter: the CT110 blog publisher, CT114/115 blog web
services, CT110 Samba/Tailscale, and CT114 staging service were running. The
blog's lack of a Docker web container is expected. PBS, scheduled backup jobs,
the WUD handoff, staging deployment runner and native publication retain their
existing ownership; see [architecture](../architecture.md),
[service policies](../reference/service-policies.md),
[observability](../../hosts/infra/observability/README.md), and
[the media contract](../media-data-contract.md).

## Recommended order

These priorities are judgment based on the live setup and the primary-source
research below. Effort is relative integration complexity, not a delivery estimate.

| Order | Proposal | Why now | Effort / missing prerequisite |
| --- | --- | --- | --- |
| 1 | Contentflow failure, no-input and stale-heartbeat reporting | Today's schedules can look healthy while doing no useful work | Small–medium; chosen private delivery channel and business-status output |
| 2 | Homelab exception brief plus recovery evidence | Monitoring already has broad coverage but no Prometheus notification delivery | Medium; narrow status collector and explicit routing |
| 3 | Paperless deadlines | Practical reminders from an existing document store | Small–medium; reviewed date fields and scoped account |
| 4 | Mealie + Bar Assistant dinner/shopping brief | Joins two live apps into one useful household plan | Medium; actual meal plan, shelves and ingredient/unit mapping |
| 5 | Film-night readiness | Explains whether requested media is actually playable with desired subtitles | Medium; stable cross-app IDs and authenticated APIs |
| 6 | Reading/listening journal | Converts completed listening into draft notes for review | Medium; user-scoped progress and narrow Obsidian write interface |
| 7 | Blog feedback and sync-lag explanation | Builds on working native publication and shared Umami | Small–medium; sanitized publisher status and production-only analytics |
| 8 | Photo review shortlist | Makes the existing curation idea useful without moving originals | Medium; authorized real inputs and dedicated Immich read access |

## Detailed proposals and primary sources

### 1. Failure and silence detector for Contentflow

**Flow:** n8n Error Trigger → normalize workflow name/execution link/failed node →
redact payload → deduplicate → private notification. Separately, a small external
readiness and last-success monitor detects a stopped scheduler or dead n8n.

**Why it helps:** both scheduled workflows currently have no error workflow.
An idle-but-healthy Contentflow run and a failed run should be distinguishable.
Track last successful scan, items found, items completed, and oldest pending
item; a green workflow execution alone does not prove useful work occurred.

**Supported interface:** one Error Trigger workflow can serve multiple workflows,
and receives execution/workflow context. Trigger failures can lack an execution
ID or link. [n8n error handling](https://docs.n8n.io/flow-logic/error-handling/).
`/healthz` only proves reachability; `/healthz/readiness` includes database
connection/migration readiness. Metrics require enabling them on self-hosted
n8n. [n8n monitoring](https://docs.n8n.io/hosting/logging-monitoring/monitoring/).

**Gap/acceptance:** select an actual notification destination; no ntfy is present.
Test one controlled failure and one stale-heartbeat condition without processing
real content. The watchdog must not depend solely on n8n. A host-wide outage
also requires observation outside this Proxmox machine.

### 2. Homelab exception brief and incident enrichment

**Flow:** Grafana/Pulse incident or timed API reads → add deployment revision,
recent backup status, affected guest and user-facing URL → send one meaningful
incident/change notice, with a morning digest for nonurgent items.

**Value:** answers “what needs my attention?” across the fleet. Keep existing
monitoring responsible for detection; use n8n for adding context and routing.
Do not implement an automatic restart loop or let n8n push production releases.

Grafana can POST alert JSON to a webhook contact point, with Basic/header auth
and optional HMAC/timestamp protection. Its documentation explicitly discourages
secrets in webhook URLs. [Grafana webhook integration](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/).
If Alertmanager is added later, it already provides alert grouping, deduplication,
silences and inhibition; those need not be rebuilt in n8n.
[Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/).

**Gap/acceptance:** Pulse inventory reads were verified, but a dedicated notification source
and delivery destination still need configuration. Grafana's webhook route is a researched option, not evidence
that existing Prometheus rules already feed Grafana-managed notifications.
No Alertmanager or ntfy service is presently installed. Deliver one real test
incident and resolution to the chosen channel and prove repeat events stay quiet.

### 3. Recovery-readiness report

**Flow:** read existing PBS/Proton job results and restore-test evidence → compare
freshness with each data class's schedule → report missing/late/failed coverage.
Keep “last backup success”, “last verification”, and “last restore test” separate.

**Value:** stitches together protection evidence without introducing a competing
backup system. Warn if photographs/shared data are assumed covered by appdata
PBS; describe actual scope. Never launch extra backups or delete retained
generations merely to build the report. This recommendation follows repository
policy and depends on local supported status surfaces, not an unverified PBS
API integration. Have a maintained narrow collector supply sanitized JSON if
the existing jobs expose only local state.

**Acceptance:** deliberately stale fixture evidence produces one notice;
current production evidence produces an accurate scope statement and no claim
of recovery beyond tested evidence. No root/PVE credentials should be placed
inside generic n8n Code nodes.

### 4. Paperless deadlines and household admin inbox

**Flow:** Paperless date/custom-field scheduled event → authenticated n8n webhook
→ combine due dates, missing required metadata and unresolved items → private
digest linking to documents; optional approved task creation afterward.

**Value:** invoices, renewals, warranty expiries and documents awaiting a decision
are actionable. Keep OCR, tagging, correspondents and permissions in Paperless.
Its native workflows already support document added/updated/scheduled triggers,
custom date fields, day offsets and outgoing webhook actions.
[Paperless workflows](https://docs.paperless-ngx.com/usage/#workflows),
[official usage source](https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/dev/docs/usage.md).

**Gap/acceptance:** establish actual custom fields, document permissions and
verified dates; do not invent due dates using an LLM without review. Check that
local webhook policy permits the private n8n destination.
[Paperless webhook settings](https://docs.paperless-ngx.com/configuration/#workflow-webhooks).
If uploading is ever added, upload acceptance is asynchronous: follow the returned
task UUID to completion before reporting a document imported.
[Paperless API](https://docs.paperless-ngx.com/api/).

### 5. “Why is my requested media not ready?”

**Flow:** Seerr request/issue event → wait a sensible interval → correlate request
with Sonarr/Radarr queue/history and Jellyfin visibility → one report explaining
requested, downloading, imported, available, or blocked.

**Value:** cross-service explanation is more useful than another “new movie”
message. Seerr already has user preferences and many direct notification agents;
use its native notifications for simple availability updates.
[Seerr notifications](https://docs.seerr.dev/using-seerr/notifications/).
Its webhook supports event-specific custom JSON and authentication headers.
[Seerr webhook](https://docs.seerr.dev/using-seerr/notifications/webhook/).
Sonarr and Radarr expose queue/history/health interfaces in their official
OpenAPI descriptions. [Sonarr API specification](https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/Sonarr.Api.V3/openapi.json),
[Radarr API specification](https://raw.githubusercontent.com/Radarr/Radarr/develop/src/Radarr.Api.V3/openapi.json).

**Boundary:** report stalled items; leave deletion/replacement to Cleanuparr and
the owning Arr. Avoid qBittorrent file deletion or changes to the VPN policy.
Jellyfin's optional webhook plugin can emit user-filtered events, but its
installation/configuration must be verified first.
[Jellyfin notifications](https://jellyfin.org/docs/general/server/notifications/).
**Acceptance:** trace one test request end to end by stable IDs, without broadly
rescanning libraries or assuming matching titles identify the same media.

**Film-night readiness** is a more personal version of recommendation 5: take a
small chosen watchlist and report which titles are playable in Jellyfin with
the desired audio/subtitle languages, which are importing, and which need a
decision. Bazarr's official movie API source exposes Radarr IDs, language profile,
subtitles and missing subtitles; its wanted API can filter by Radarr ID. Episode
wanted data carries Sonarr episode/series IDs. Use those stable IDs to join
systems. [Bazarr movie API source](https://raw.githubusercontent.com/morpheus65535/bazarr/master/bazarr/api/movies/movies.py),
[Bazarr movie wanted API](https://raw.githubusercontent.com/morpheus65535/bazarr/master/bazarr/api/movies/wanted.py),
[Bazarr episode wanted API](https://raw.githubusercontent.com/morpheus65535/bazarr/master/bazarr/api/episodes/wanted.py).
These are current upstream sources, not confirmation of installed route schemas.
Credentials for a read-only workflow must be configured; Bazarr's shared
API key is not proven to enforce read-only access. Desired language/profile settings matter, including whether embedded
tracks count; “not listed as wanted” alone does not prove the desired subtitle
is visible and usable in Jellyfin. Leave search/download/synchronization to
Bazarr. [Bazarr setup and language profiles](https://wiki.bazarr.media/Getting-Started/Setup-Guide/).

### 6. Mealie preparation and shopping brief

**Flow:** today's planned meal → gather preparation reminders and shopping items
→ combine into one household reminder; optionally show it through Home Assistant
or an already chosen notification app.

**Value:** add context such as “thaw tomorrow's dinner tonight” and consolidate
shopping actions. Mealie already has meal planning and shopping lists, so n8n
should not maintain another authoritative copy. Mealie webhooks are scheduled
around meal plans; its notifiers are event-driven, and recipe actions can POST
recipe JSON. [Mealie features](https://mealie.io/documentation/getting-started/features/).
User API tokens, recipe/list extras and pagination support richer integration.
[Mealie API](https://mealie.io/documentation/getting-started/api-usage/).

**Gap/acceptance:** actual household, plan usage and preferences need inspection.
Keep recipe/member data scoped to that household. Generate one fixture brief,
then one real-plan brief; verify time in Europe/Amsterdam and repeated deliveries.

**Dinner and drinks brief** extends recommendation 6: combine the chosen Mealie
menu with Bar Assistant's available-ingredient cocktail options and one shopping
checklist. Bar Assistant already models personal and shared shelves, ingredient
substitution and “can make” filtering, so reuse its calculations rather than
recreating them in n8n. [Bar Assistant usage](https://docs.barassistant.app/).
The installed API serves its own documentation at `/docs`; inspect that for
version-correct endpoints/auth before implementing a cross-service list.
[Bar Assistant API FAQ](https://docs.barassistant.app/faq/).
Start with a read-only preview rather than syncing inventories or creating
duplicate shopping lists. Keep personal shelf and shared bar identities explicit.

### 7. Reading/listening journal with a weekly review queue

**Flow:** Audiobookshelf listening sessions/completed progress → detect newly
finished items → make a draft private reading note with title, dates and source
links → weekly review prompt. Later, add Zotero collection changes to a research
inbox, with explicit user authorization and a narrow Obsidian writer contract.

Audiobookshelf exposes own-user listening sessions/stats and media progress, so
there is no need for direct database reads or progress rewrites.
[Audiobookshelf API](https://api.audiobookshelf.org/#get-your-listening-sessions).
Zotero provides a versioned Web API with dedicated keys for private libraries;
its WebDAV storage alone is not that metadata API.
[Zotero Web API](https://www.zotero.org/support/dev/web_api/v3/basics).

**Value/boundary:** record what was actually read/listened to; never invent notes
or book summaries as if Rafael authored them. Use item IDs and completion state
to avoid duplicates. PinePods owns podcasts here, so do not restart Audiobookshelf
podcast acquisition. A stopped VM101 means Symphony-dependent downstream actions
are a gap, not an assumed available integration.

### 8. Blog publication and readership brief

**Flow:** read native publisher status + public HTTP checks + production-only
Umami statistics → one weekly list of newly published pages, broken links,
traffic changes and useful reader engagement patterns.

**Value:** feedback on publishing, without inserting n8n into the working
publish-on-status path. Keep drafts private; use the production website ID and
environment labels. Umami's API supports authenticated JSON access to analytics,
and official guidance demonstrates scheduled stats/top-pages comparisons.
[Umami API overview](https://docs.umami.is/docs/api),
[Umami API reporting example](https://docs.umami.is/docs/guides/embed-analytics-in-your-app).
For custom course-map events, use the installed version's event API and the
existing meaning of those events; do not confuse visits with completed reading.
[Umami event statistics](https://docs.umami.is/docs/api-reference/get-website-event-stats).

**Gap/acceptance:** match the installed Umami version's schema; current docs may
describe newer response fields. A quiet private analytics endpoint is not proof
of WAN availability. Test the report against the dashboard and exclude staging.

### 9. Photo curation reminder and archive handoff

**Flow:** read authorized Immich albums/recent assets → collect candidates for
review → provide links or a private contact sheet → hand accepted selections to
the existing archive app/workflow, using its explicit contract.

**Value:** “these photos still need sorting” or a private monthly selection is
useful; another upload, face-recognition or deletion engine is not. Immich's
v3.0.3 specification provides album, metadata-search and permission declarations.
Use this versioned source if it matches the running installation, then verify
live pagination and exact key privileges.
[Immich v3.0.3 API specification](https://raw.githubusercontent.com/immich-app/immich/v3.0.3/open-api/immich-openapi-specs.json).
API keys can be permission-restricted.
[Immich CLI/key guidance](https://docs.immich.app/features/command-line-interface/).

**Boundary:** no automatic photo deletion, moving canonical files or public
album sharing. Stillroom's pending acceptance should not be bypassed by n8n.
Do not equate an Immich archive flag with a verified file archive/backup.

### 10. Sync and publishing lag diagnosis

**Flow:** periodic sparse Syncthing folder status + native publisher status +
staging/production revision → identify the stage that is delayed → alert only
after the expected grace period or on a change in failure reason.

Syncthing's events endpoint accepts a last-seen ID, but its finite event buffer
means polling can miss events; detect gaps and reconcile state. Folder status
exposes pending bytes/files, pull errors and current state, and documentation
warns that this status call is relatively expensive.
[Syncthing events](https://docs.syncthing.net/rest/events-get.html),
[Syncthing folder status](https://docs.syncthing.net/rest/db-status-get.html).

**Value/boundary:** answers “my save hasn't appeared: sync, export, build or
serve?” without adding a competing publish trigger, browser refresh or new
polling delay to content publication. Never auto-resolve conflict files.

## Lower-priority options and things to leave native

- Navidrome listening discovery/curated playlists can be joined with personal
  preferences, but native smart playlists already cover simple filter-based
  lists. Its Subsonic API includes playlists, album lists, stars and playback
  state. It does not count a stream as played unless scrobbling is submitted.
  [Navidrome API compatibility](https://www.navidrome.org/docs/developers/subsonic-api/).
- Home Assistant can receive an n8n-created summary or provide context, but
  device control and time-sensitive automations should remain there. HA has
  rich native triggers and a token-authenticated REST API for states, actions
  and events. [HA automation triggers](https://www.home-assistant.io/docs/automation/trigger/),
  [HA REST API](https://developers.home-assistant.io/docs/api/rest/).
- ntfy would be an optional delivery service, not an existing one. It supports
  HTTP publication, priorities and links/actions. If added, use authenticated
  private delivery and consider what appears on phone lock screens.
  [ntfy publishing](https://docs.ntfy.sh/publish/).
- Do not build n8n replacements for WUD/PBS execution, PVE lifecycle, automatic
  media cleanup, native blog publishing, Aurral/Soularr acquisition, or HA safety
  automations. No general root SSH/Docker socket attachment is needed for the
  high-value read-and-notify ideas.

## Design requirements for the first implementation

These are recommendations, not changes made during this task.

1. **Version-gate features.** The installed n8n is 2.31.6. Current upstream
   Schedule Trigger docs explicitly describe changed default timing from 2.45.0;
   do not attribute that scheduler to this installation. Set
   `Europe/Amsterdam` explicitly and verify execution times across DST.
   [Schedule Trigger](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/).
2. **Use authenticated private webhooks.** Basic/header/JWT authentication and
   separate test/production webhook URLs are documented. Keep production URLs
   private here, and verify source-specific auth compatibility before enabling.
   [n8n Webhook](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/).
3. **Preserve durable item identities.** Record source, item ID, source version,
   intended action and completion state. Retry transient reads; do not blindly
   replay writes. Data tables can store cross-run markers, but a check-then-write
   is not proof of atomic uniqueness under concurrent executions. Use the owning
   app's idempotency support, serialization or a unique constraint as needed.
   [n8n data tables](https://docs.n8n.io/data/data-tables/).
4. **Do not use staticData as a critical queue.** n8n documents it as experimental,
   unavailable for persistence during manual tests, and potentially unreliable
   at high execution frequency. [n8n static data](https://docs.n8n.io/code/cookbook/builtin/get-workflow-static-data/).
5. **Bound execution pressure.** Self-hosted regular mode has no production
   concurrency limit by default; the documented limit queues excess production
   executions but excludes manual, sub-workflow, error and CLI executions.
   This is resource control, not a transactional lock.
   [n8n concurrency](https://docs.n8n.io/hosting/scaling/concurrency-control/).
6. **Minimize retained sensitive payloads.** Keep diagnostic failures without
   retaining full documents/tokens/photo binaries unnecessarily; configure
   pruning and inspect actual settings rather than assuming defaults. Execution
   records and binary data can grow substantially.
   [n8n execution data](https://docs.n8n.io/hosting/scaling/execution-data/).
7. **Credential scope must be real.** n8n's current docs say non-Enterprise API
   keys have full access to the account's resources/capabilities; do not label a
   Community-edition key “read-only” solely because this workflow only does GETs.
   Service-specific limited users/keys may still restrict source access.
   [n8n API authentication](https://docs.n8n.io/api/authentication/).
8. **Test outcomes rather than node success alone.** Require a happy path, one
   unavailable upstream, a duplicate event, a replay after partial completion,
   a permissions failure, and the resulting private notification. Include quiet
   periods and a no-data case. Alerts can fail too; independent monitoring must
   observe the notification workflow.

The newer public API documentation mentions idempotency keys for supported n8n
POSTs, but this research did not establish that support in 2.31.6. Do not rely
on that feature for the plan. No third-party API's exactly-once semantics were
verified, and no credential or notification delivery acceptance was performed.


## Implementation shape and boundaries

The first useful slice would be three small workflows:

1. **Workflow error handler:** Error Trigger → allowlist workflow/node/time/link
   → group repeated incidents → private delivery. Do not forward full error
   payloads or documents. Attach it to both scheduled Contentflow workflows.
2. **Daily exceptions brief:** Schedule → read monitoring and narrow job-status
   feeds → classify unavailable/stale/no-input/action-needed → suppress unchanged
   notices → compose one brief. Missing `Publishing` is an explicit setup gap;
   an empty incoming folder is an explicit no-input state, not an outage. Record
   separate last-attempt, last-success and last-useful-result timestamps.
3. **Paperwork due:** Paperless native scheduled webhook, or bounded scheduled
   API reads if the installed version requires that → validate reviewed dates
   and document permissions → group items → deliver one reminder with private
   links. Key reminders by document ID, relevant date and reminder stage, so
   repeated source events do not create duplicates.

For operational incidents, the current Prometheus rule evaluator needs a
notification path. A suitable durable design is **Prometheus → Alertmanager →
n8n enrichment/delivery**, with an independent critical-alert route. Alertmanager
would be a new service requiring its own scoped implementation. A smaller initial
n8n brief can read the existing Prometheus API; that is useful reporting but is
not a substitute for independent alert delivery. Grafana contact points are an
alternative only if the relevant alert evaluations are actually connected to
Grafana's notification system. Merely adding a contact point will not route the
current Prometheus rules. See the official
[Prometheus alerting overview](https://prometheus.io/docs/alerting/latest/overview/)
and [HTTP API](https://prometheus.io/docs/prometheus/latest/querying/api/).

No delivery channel was chosen or tested in this task. An existing authenticated
Home Assistant notification setup could be reused if present; email or another
private channel are alternatives. ntfy is optional new infrastructure. A
same-host watchdog cannot report a complete PVE/power/network outage on its own;
an external observer is a separate requirement.

Use narrowly scoped application APIs. Where backup/publisher state exists only
as host-local files, a maintained collector in `dothomelab` should expose an
allowlisted status document. Do not grant n8n the whole PVE environment, SSH root
identity, media library or Docker socket simply to construct a report. A writing
integration with Obsidian needs a new narrow, explicit interface: the current
Contentflow vault mount is intentionally read-only. The running Zotero WebDAV
container supplies attachment storage, not a local Zotero metadata API.

Keep WUD's backup gate, app-local databases, native blog publication, staging
branch rules, and explicit production authorization unchanged. Let Arrs organize
media, Cleanuparr manage its established recovery flow, PinePods own podcasts,
and the approved metadata tools own their respective files. Never use these
ideas to activate autonomous archive moves, production releases, public sharing,
container restarts or media deletion. These are concrete boundaries of this
homelab, not missing n8n features.

## Report validation and remaining gaps

This report is a local research draft in the canonical homelab checkout. The
existing unrelated documentation edits were preserved. No n8n or application
repository files were changed, no service was deployed, and no runtime cleanup
was needed. Documentation links and whitespace are checked with the repository
checker and `git diff --check`.

Remaining implementation inputs are the desired notification destination,
actual document/date conventions, household meal/shelf usage, selected media
languages/watchlist, user-scoped app permissions, real Contentflow input folders,
and whether the older Contentflow publishing/archive direction is still wanted
alongside native blog publishing and Stillroom. None blocks describing the
current system; each matters before implementing its associated proposal.

No live backup/restore, publication, real archive, authenticated end-user app
journey, WAN test or notification delivery was performed. No historical n8n
success percentage can be reconstructed from the retained metadata inspected.
