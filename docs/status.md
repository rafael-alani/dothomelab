# Project status

Focused release **2026-10-27**: [course-map opening and production acceptance](evidence/2026-10-27-blog-map-production.md)
published blog `1de2b14` to `https://rafael.ink` with all nine course maps. Each
opens fitted before zooming to its configured starting note; controls use the
requested label and responsive rows. Ten live browser cases and both real
analytics cases pass. Stored note events, fresh sanitized logs and all five
current production probes were verified. Publication folder-history and
monitoring-target fixes are installed from homelab `ebc39f9`. Previous releases
remain retained; three pre-existing missing source-note targets, independent WAN
verification and an actual rollback/restore remain outside this acceptance.

Focused check **2026-10-27**: [shared observability on Infra](evidence/2026-10-27-shared-observability-infra.md)
moved the existing Umami, Grafana, Prometheus, Loki and Blackbox services to CT110.
The shared dashboards filter project/environment/guest/service; Umami retains
separate website IDs. Both blog environments send to the shared backend, with
only small local log collectors on CT114/115. Browser events and stored counts,
sanitized log ingestion, dashboard datasources, endpoint checks, Pulse coverage
and Homarr tiles were verified. Original data/history and rollback copies remain;
collection had a cutover gap. Notification delivery and WAN monitoring remain
unconfigured. That observability task did not promote or redeploy public blog code.

Focused check **2026-10-27**: [Pulse availability and dashboard coverage](evidence/2026-10-27-pulse-dashboard-coverage.md)
verified HTTPS authentication, all 92 running Docker containers across five
Docker LXCs, all six LXCs and both VMs. The reported access failure was not
reproduced from the home network; the route remains LAN/Tailscale-only. Homarr's
six staging tiles are synchronized, but shared Grafana/Umami and the public blog
have no tile. Agent completion now explicitly requires Pulse and Homarr checks.

Focused follow-up **2026-10-27**: the blog now accepts blank descriptions and
treats each Obsidian export as the complete content tree. Deleted folders,
articles and maps no longer return from Git; rerunning the authoring installer
does not recreate deleted starter notes. Blog implementation `223f288f` and
verification record `944cc301` preserve Rafael's site name/homepage sentence and
remove descriptive filler. Homelab implementation `68cba604` is installed on
CT110/CT114; health checks use Home so About remains optional.

All 44 Blog description properties were cleared with verified originals in the
Mac vault's `.blog-publisher-backups/descriptions-20261027T084406717599/`.
`changed-files.json` identifies the notes; `authoring-files.json` identifies four
guide/template edits. Restore individual files only after comparing subsequent
author changes. The synced export
`97852657583716210cf018321ad4cedfa45601a0bb770dd0f919ea0724049924`
has 44 empty preview descriptions, 34 empty published descriptions, nine private
maps and no published maps. Ideology is absent in both trees. The three previously
unavailable source-note targets remain unchanged.

The normal publisher/staging timers delivered that digest with blog `944cc301`
to the private preview. All 21 sitemap pages pass live metadata checks: normal
and Open Graph descriptions are blank except Rafael's homepage sentence. Live
desktop/phone no-JavaScript empty-section and 404 checks pass, as do deployment
health and quiet Compose validation. `/ideology` returns 404 and its link is
absent from the open menu. This final content-only update used the existing
static-tree refresh.

Local checks pass: blog typecheck, 87 unit tests, static build, five focused
Chromium cases, 19 exporter tests, four installer tests, seven editorial tests
and the static activation regression. Desktop and phone screenshots were
inspected. Prior source archives are retained on CT110/CT114 at
`/opt/dothomelab.before-copy-20261027` and
`/opt/dothomelab.previous-before-copy-20261027`; the first matches the previous
installed archive byte-for-byte. Publisher image
`dothomelab/blog-publisher:before-copy-20261027` and prior staging releases remain.
Rollback requires deliberately reinstalling the saved publisher/source revision
and selecting a retained staging release; no live rollback or data restore was
performed. At that point public production remained at `8e2fcec6`; that authoring
task did not promote main or activate production.

Focused follow-up **2026-10-27**: [blog URL renames](evidence/2026-10-27-blog-url-renames.md)
makes folder and article names determine canonical paths while permanent IDs
retain former addresses for redirects. The publisher also tracks folder history;
the staging importer excludes renamed draft-map fallbacks from public inputs.
The private preview now uses `/technical-write-ups/ai`; 29 HTTPS redirect/destination
pairs and the browser topic-to-map journey pass. The report records regression
checks, installed revisions and retained rollback inputs. That URL task did not change production.

Focused follow-up **2026-10-27**: [blog map controls and starting notes](evidence/2026-10-27-blog-map-controls.md)
adds the native navigation checkbox, matching canvas actions, optional blank
starting-note fields and the initial stricter off-canvas rendering. The follow-up
sets MDL's introduction and restores prior card retention/preloading in a separate
commit, keeping off-canvas Umami filtering. A regression also fixes
staging imports after simultaneous parent/topic folder renames. The report
records checks, retained rollback inputs and the pre-existing WebKit reload gap.

Focused follow-up **2026-10-26**: [blog changes 111–113](evidence/2026-10-26-blog-live-maps.md)
move all nine private course maps onto the original Syncthing vault graph, with
article-relative reading links and publisher-owned route history. Filenames and
folder names supply labels; ordering stays in `_index`. Content-only updates use
an atomic static-tree refresh without replacing the web container. A timestamped
Mac edit five folders deep reached staging through the normal timers with code,
container ID, start time and restart count unchanged. Live browser
checks pass for all nine maps and real Umami note visibility/time events; the
read-only report returns counts, totals and mean/median completed episodes.
Three original note targets remain unavailable and are named in the evidence.
This change stays on staging; no production release or main promotion occurred.

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

Focused follow-up **2026-10-27**: [Proton reverification](evidence/2026-10-17-proton-backup-activation.md#reverification-october-27-2026)
confirmed the October 18 four-source success, matching current cloud checksum
lists, all 54 photo parts, and successful environment/Immich sample downloads.
The timer is healthy; the next full scheduled run is expected November 2.
[V5 was subsequently restored](evidence/2026-10-17-proton-backup-activation.md#v5-restoration-and-deployment-protection-october-27-2026)
at `4bcab90`, with a separately installed, immutable-image runtime and deployment
downgrade guards. Live service/readiness checks passed. Today's check did not
repeat full photo or Obsidian payload downloads; the next full v5 production
cycle and later note changes await the scheduled run.

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
| Proton | October 18 cycle verified; October 27 cloud checks passed; v5 restored with protected runtime at `4bcab90`; timer active | Next full v5 production cycle pending; full payload re-download not repeated today |

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
| Obsidian / Proton | [October 27 restoration](evidence/2026-10-17-proton-backup-activation.md#v5-restoration-and-deployment-protection-october-27-2026): v5 protected runtime ready; sync idle/current; cloud generation present; timer healthy | Next full v5 cycle and later notes await scheduled backup; phone pairing; live versioning disabled |
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
