# Project status

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

Focused follow-up **2026-10-21**: [Film-introspect / Meta Egg screening MVP](evidence/2026-10-21-screening-mvp-staging.md)
adds a private stateless Meta Egg API and the Film-introspect note-and-catch-up
workflow. Both final application revisions passed staging verification and trusted
HTTPS health checks; the synthetic local browser check preserves a held timestamp
while the clock advances. Jellyfin credentials
are absent pending explicit approval for restricted-account provisioning; actual
movie/cut/subtitle lookup, live synchronization and user acceptance remain open.
The failure message confirms the Film-introspect → Meta Egg connection; no
candidate was promoted to main.

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
| Staging | [Platform acceptance](staging-addition-2026-10-04.md), [screening MVP preview](evidence/2026-10-21-screening-mvp-staging.md) | Screening Jellyfin connection, real-film timing and user acceptance; dependency availability; clean-host restore |
| Accounts / first use | [Historical state](current-state.md#known-external-or-unfinished-items) | Wizarr setup/redemption, Bar Assistant first-use, authenticated yt-dlp download, SnapOtter/Stirling first-login, Kavita first-use were not reinspected |

Other open items: Loki has no declared log shipper; Pulse disk/temperature and
Docker image-update actions remain disabled. The October incident leaves the
host restart cause unknown and physical SATA cable/power inspection conditional
on recurring errors. Autostart was checked without rebooting. Retained rollback
assets require a separate cleanup task.

Update this page only when new evidence changes readiness, with date, revision,
environment, and limits. Keep older reports in the [evidence index](evidence/README.md).
