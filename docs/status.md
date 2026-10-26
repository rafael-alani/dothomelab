# Project status

Focused follow-up **2026-10-26**: the [first production blog activation](evidence/2026-10-25-production-scaffold.md#first-production-activation--october-26-2026)
published accepted `origin/main` revision `8e2fcec638e48a9866a985647188f4cb626bb234`
at **https://rafael.ink** through Cloudflare and NPM to SSD-backed CT115. The
activation guard now tolerates unrelated infrastructure commits, while retaining
production runtime/shared-import drift checks; the first Git fetch allows enough
time for the repository history. Installed platform `fc039780` passed ten
regression tests. Public HTTPS, browser Home/About navigation and production
Umami events passed. Five production probes, seven scrapes, four alert-rule
evaluations, both Grafana datasources and sanitized production Loki ingestion
passed; staging's five probes/seven scrapes stayed healthy. Private listening
and telemetry administration paths return 404. Source archives, release inputs
and a checked NPM rollback copy remain. No live rollback/restore or physical
phone check was performed. Alert notification delivery/external uptime monitoring
remain unconfigured; npm reported 17 dependency advisories during the accepted
application build, without dependency changes in this infrastructure repair.

Focused follow-up **2026-10-26**: the private blog now serves code
`8e2fcec638e48a9866a985647188f4cb626bb234` with editorial digest
`3eacec18a2d12c9962cac2fa007f32d94ed57a948a6019d042f82a609afec19d`.
Eight additional course exports use their own primary mind maps; the reading
identity follows the hamburger and hides in expanded maps. The
[publisher](../hosts/infra/blog-publisher/README.md) installed on CT110 at
`c58f53148bf0cbdb2c55e46c75f0a7571e97d1ea` preserves the About body, editable
at `Blog/about/about.md`. Rafael's subsequent comments in the About route are
preserved: the rendered page shows only its heading, while the biography remains
saved and exported. Its original empty notes are retained under the vault's
`.blog-publisher-backups/about-20261026T203726758329/` (copy back only after
comparing later author edits). Prior publisher images/source archives and staging
release bundles remain; no vault/PBS restore or production publication was performed.
Local checks passed: 82 blog unit tests, static build/typecheck, 15 focused Chromium
cases, three WebKit cases, 11 publisher tests, two installer tests and four
editorial-adapter tests. The About follow-up passes typecheck, 82 unit tests,
static build and the updated no-JavaScript heading-only browser check.
Five live Chromium cases pass against the deployed revision: all nine course
maps and their standalone indexes, heading-only About without JavaScript,
expanded map/header controls at four widths, and desktop/phone direct reading URLs.
Quiet Compose, HTTP health and running container revision checks pass. Physical
iPhone behavior remains untested.

Focused follow-up **2026-10-25**: [SSD production scaffold](evidence/2026-10-25-production-scaffold.md)
created CT115 with isolated appdata, Pulse enrollment, separate production
analytics/dashboard/monitoring and an explicit main-only publication command.
At that checkpoint the blog stayed off and `rafael.ink` retained its placeholder;
remote blog `main` was absent. The October 26 activation above supersedes that
publication state. Shared services were healthy; alert delivery and external
uptime observation remain unconfigured.

Focused follow-up **2026-10-25**: [Obsidian blog publishing](evidence/2026-10-25-obsidian-blog-publisher.md)
adds the CT110 export timer, checked immutable content inputs in CT114, and Mac
Templater authoring. The existing embedded note renders as a labeled draft at
the private staging URL. Published-only exports exclude drafts. Production
hosting/approval handoff and real-photo author acceptance remain outstanding.

Focused follow-up **2026-10-23**: [blog picnic and private audio](evidence/2026-10-23-blog-picnic.md)
deployed blog `0907f6a` to its private staging URL. Real MP3 playback/seek,
persistent player/navigation, and phone layout pass. Only one read-only music
copy is exposed; Vincent remains pending. Main awaits Rafael’s acceptance.

Focused follow-up **2026-10-23**: [Umami/Grafana relocation](evidence/2026-10-23-observability-apps-move.md)
moved the shared services and their data to CT112 at `1abc719`. Logical restore
matched all 27 Umami table counts; Grafana SQLite integrity and 92 table counts
passed. Existing private URLs and authenticated access work; blog/collectors
remain running on CT114. Rollback state is retained outside staging.

Focused follow-up **2026-10-23**: [blog observability](evidence/2026-10-23-blog-observability.md)
adds private Umami/Grafana, five passing blog probes and verified blog access-log
delivery to existing Loki. Browser/database checks agree on 16 fixture pageviews
and four map events; DNT and blocked tracking preserve reading. Blog preview
`eac3c89` remains on staging. No alert receiver, external outage observer, new
resource exporter or database restore proof was provided by that initial rollout.

Last live review: **2026-10-12**, Europe/Amsterdam; PVE `afa`, read-only from the
operator Mac, code baseline `c2661dd`. The [baseline report](evidence/2026-10-12-documentation-baseline.md)
contains commands, full revisions, and limits. Documentation edits on October 13
are not a new live review.

Focused follow-up **2026-10-17**: [staging dashboard and test-app retirement](evidence/2026-10-17-staging-dashboard.md)
installed automatic Homarr enrollment at `77ad73f` and retired the three dummy
Symphony deployments and their routes. Film-introspect remains healthy; the
separate Staging board is generated without changing home-board selections.

Focused follow-up **2026-10-17**: [Proton backup activation](evidence/2026-10-17-proton-backup-activation.md)
confirmed current Mac-to-Infra notes sync and completed Proton login. The first
cloud cycle started at 12:41 CEST with missing Immich-original coverage added.
The cycle stopped at 12:56 CEST on a Proton node-ID validation bug after the
Obsidian upload/read-back; the repair and live retry are tracked in that report.
Scheduling activates only after all four archives verify; completion remains
pending at this checkpoint.

Focused follow-up **2026-10-17**: [Form & Field staging](evidence/2026-10-17-ff-staging.md)
accepted app revision `2ecef28a1` at `ff.staging.rafael.media` with private HTTPS,
working source exports, 37 passing tests, and active branch polling. CT110/114
use homelab implementation `ef8bc7f`; Film-introspect remained healthy. No new
PBS or clean-host restore test was performed.

Focused follow-up **2026-10-18**: [Stillroom staging](evidence/2026-10-18-stillroom-staging.md)
connects CT114 to production Immich 3.0.3 with a dedicated read key and narrow
photos/archive mounts. Only `Archive:` albums qualify; zero candidates or real
moves at handoff. The disposable compatibility gate awaits the user's sample.
68 application tests, live API schema checks, private HTTPS and a disposable
archive-filesystem move/restore passed. CT114 uses homelab implementation
`748016b` plus subsequent evidence updates. Existing staging apps stayed healthy.

Focused follow-up **2026-10-18**: [Blog staging](evidence/2026-10-18-blog-staging.md)
accepted source `dfb3fcd` at private `blog.staging.rafael.media`. GitHub is private;
CT114 uses a dedicated read-only deploy key. Static routing, trusted HTTPS,
client navigation, all four staging apps, and Homarr enrollment passed.

Focused follow-up **2026-10-21**: the [initial screening preview](evidence/2026-10-21-screening-mvp-staging.md)
verified the service link and synthetic note timing, but depended on an
unconfigured Jellyfin account. That dependency is superseded by the
[October 22 standalone pilot](evidence/2026-10-22-screening-standalone-pilot.md):
Meta Egg bundles one real licensed film, Sintel, and its timed English subtitles.
The companion clock works with an external screen; Jellyfin is optional. The
real-film browser check captured a note at 1:56 while playback continued, then
saved at 2:20 and caught up to the correct subtitle. The note persisted after
reload and final deployment. Meta Egg `7b5a53f` and final Film-introspect
`8b909f0` were installed with the homelab runtime configuration from `71321d1`;
all five staging app verifiers passed. Broader catalog coverage and Rafael's
preview acceptance remain open; no candidate is promoted to main.

A [later October 22 discovery fix](evidence/2026-10-22-screening-online-discovery.md)
now resolves **At Eternity's Gate (2018)** online through Meta Egg and returns
its metadata to Film-introspect. Installed: Film-introspect `566d22c`, Meta Egg
`f95343b`, homelab runtime `1ed87e0`. Existing notes and Sintel cues were retained.
Automatic English subtitle lookup/download is implemented but awaits a dedicated
OpenSubtitles API key; this film's transcript and real synchronization remain
unverified. No candidate is promoted to main.

## Observed readiness

| Area | Result | Limit |
|---|---|---|
| PVE / guests | PVE 9.1.2; all five managed LXCs and VM101/104 running | No reboot or rebuild test |
| Storage | `rpool` / `vault` ONLINE; canonical mountpoints match | No new scrub or restore |
| Docker | Running: CT102 21, CT110 12, CT112 44, CT114 2; none reported unhealthy | Some lack health checks; membership differs from Git |
| Access | Homarr, Aurral, PinePods, Zotero root, Film-introspect: DNS and HTTPS 200 | From PVE; no authenticated journey, public ACL, or client test |
| Appdata backup | Oct 12 service succeeded at 02:25:08 CEST; timer scheduled | No archive-content/restore validation |
| WUD handoff | **Failed**, exit 1 at 02:26:31 CEST | Cause/candidate not diagnosed |
| Proton | First four-source cycle started October 17; timer gated on success | First verified cloud cycle pending |

## Drift requiring follow-up

- Guest archives differ: CT102 `a4f1374`, CT110/114 `ef8bc7f`, CT112 `c2661dd`.
  Inspect required changes before targeted sync; markers do not prove every
  installed script matches.
- Infra runs healthy `contentflow-contentflow-1`, absent from this repo's
  declarations; its rebuild/data/update contract is unestablished here.
- Apps runs DroppedNeedle and has no Paperless-GPT container. Preserve
  DroppedNeedle until generated-flow acceptance. The historical GPT blocker is
  its external key; this review did not read/test the key or rerun bootstrap.
- The undeclared `symphony-check.staging.rafael.media` route was retired on October
  17. Old Obsidian/OpenWebUI entries remain outside that focused change. Some legacy routes lack the private inline ACL;
  no complete external exposure review or route cleanup was performed.

## Acceptance and evidence

Earlier tests retain their original scope; none were repeated as authenticated
journeys for this docs review. [The manual](../USER_DOC.md) owns workflow steps.

| Area | Established evidence | Still open or unverified |
|---|---|---|
| Recovery | [Migration samples](compose-project-migration.md), [native state](rebuild.md#recovery-material), [HAOS](haos-vm.md) | Clean-host/destructive VM104 restore; physical provisioning external; broad independent shared-data backup absent |
| Music | [Aurral requests](aurral-v2-request-pipeline-2026-07-26.md), [Soularr import](slskd-purple-rain-import-2026-09-17.md), [metadata](music-metadata-canonicalization-2026-07-26.md) | Generated Aurral flow; device/session playback. Last.fm/Discover acceptance alone does not close the flow gap. |
| Books | [Phase 3](media-pipeline-phase-3-evidence-2026-07-25.md), [Listenarr](listenarr-addition-2026-07-28.md), [metadata pilot](book-metadata-canonicalization-2026-07-26.md) | Physical readers; BookOrbit recovery-account drift. Listenarr search test did not grab a release. |
| Readalouds / podcasts | [Storyteller fixture](media-pipeline-phase-4-evidence-2026-07-25.md), [PinePods/GPodder](media-pipeline-phase-5-evidence-2026-07-26.md) | Other books/formats, physical mobile/ECHO acceptance; no unrestricted metadata safety claim |
| Obsidian / Proton | [October 17 check and activation](evidence/2026-10-17-proton-backup-activation.md): Mac/Infra current; Proton authenticated; first cycle started | Full cycle completion and timer activation; phone pairing; live versioning is disabled |
| Zotero / desktop | [October repair](zotero-lxc-outage-2026-10-07.md), [SMB reconnect](macos-media-reconnect-2026-09-17.md), [routing](macos-media-tailscale-2026-09-24.md) | Native attachment upload/reader refresh and current client sessions |
| Staging | [Platform acceptance](staging-addition-2026-10-04.md), [standalone screening pilot](evidence/2026-10-22-screening-standalone-pilot.md), [online discovery](evidence/2026-10-22-screening-online-discovery.md) | OpenSubtitles key, live transcript retrieval and alignment; broader film/cut coverage and user acceptance; optional Jellyfin device following; clean-host restore |
| Accounts / first use | [Historical state](current-state.md#known-external-or-unfinished-items) | Wizarr setup/redemption, Bar Assistant first-use, authenticated yt-dlp download, SnapOtter/Stirling first-login, Kavita first-use were not reinspected |

Other open items: Loki collects only the blog's declared access logs; fleet-wide
log collection is not configured. Pulse disk/temperature and
Docker image-update actions remain disabled. The October incident leaves the
host restart cause unknown and physical SATA cable/power inspection conditional
on recurring errors. Autostart was checked without rebooting. Retained rollback
assets require a separate cleanup task.

Update this page only when new evidence changes readiness, with date, revision,
environment, and limits. Keep older reports in the [evidence index](evidence/README.md).
