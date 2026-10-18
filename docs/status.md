# Project status

Last live review: **2026-10-12**, Europe/Amsterdam; PVE `afa`, read-only from the
operator Mac, code baseline `c2661dd`. The [baseline report](evidence/2026-10-12-documentation-baseline.md)
contains commands, full revisions, and limits. Documentation edits on October 13
are not a new live review.

Focused follow-up **2026-10-18**: [Proton backup activation](evidence/2026-10-17-proton-backup-activation.md)
confirmed the first complete cloud cycle at **05:53 CEST**. Notes, recovery
environment, Immich originals, and shared photos all passed cloud download and
checksum verification. All 54 photo parts verified; independent inventory and
full-content audits passed for all 43,950 shared-photo files. The timer is now
enabled for daily checks of the 14-day interval. The complete-source audit was
manual for this cycle; it is not yet a scheduled success/retention gate.

## Observed readiness

| Area | Result | Limit |
|---|---|---|
| PVE / guests | PVE 9.1.2; all five managed LXCs and VM101/104 running | No reboot or rebuild test |
| Storage | `rpool` / `vault` ONLINE; canonical mountpoints match | No new scrub or restore |
| Docker | Running: CT102 21, CT110 12, CT112 44, CT114 2; none reported unhealthy | Some lack health checks; membership differs from Git |
| Access | Homarr, Aurral, PinePods, Zotero root, Film-introspect: DNS and HTTPS 200 | From PVE; no authenticated journey, public ACL, or client test |
| Appdata backup | Oct 12 service succeeded at 02:25:08 CEST; timer scheduled | No archive-content/restore validation |
| WUD handoff | **Failed**, exit 1 at 02:26:31 CEST | Cause/candidate not diagnosed |
| Proton | Four-source cloud cycle verified October 18 at 05:53; all 43,950 shared-photo contents audited; timer enabled | Complete-source audit remains manual; full extraction and Immich database restore not tested |

## Drift requiring follow-up

- Guest archives differ: CT102 `a4f1374`, CT110/114 `ee1c217`, CT112 `c2661dd`.
  Inspect required changes before targeted sync; markers do not prove every
  installed script matches.
- Infra runs healthy `contentflow-contentflow-1`, absent from this repo's
  declarations; its rebuild/data/update contract is unestablished here.
- Apps runs DroppedNeedle and has no Paperless-GPT container. Preserve
  DroppedNeedle until generated-flow acceptance. The historical GPT blocker is
  its external key; this review did not read/test the key or rerun bootstrap.
- NPM retains an undeclared `symphony-check.staging.rafael.media` route and old
  Obsidian/OpenWebUI entries. Some legacy routes lack the private inline ACL;
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
| Obsidian / Proton | [October 17 check and activation](evidence/2026-10-17-proton-backup-activation.md): Mac/Infra current; all four cloud archives verified; complete shared-photo inventory/content audit; timer enabled | Complete-source audit remains manual; phone pairing; live versioning is disabled |
| Zotero / desktop | [October repair](zotero-lxc-outage-2026-10-07.md), [SMB reconnect](macos-media-reconnect-2026-09-17.md), [routing](macos-media-tailscale-2026-09-24.md) | Native attachment upload/reader refresh and current client sessions |
| Staging | [October acceptance](staging-addition-2026-10-04.md) | Production integrations, dependency availability, clean-host restore |
| Accounts / first use | [Historical state](current-state.md#known-external-or-unfinished-items) | Wizarr setup/redemption, Bar Assistant first-use, authenticated yt-dlp download, SnapOtter/Stirling first-login, Kavita first-use were not reinspected |

Other open items: Loki has no declared log shipper; Pulse disk/temperature and
Docker image-update actions remain disabled. The October incident leaves the
host restart cause unknown and physical SATA cable/power inspection conditional
on recurring errors. Autostart was checked without rebooting. Retained rollback
assets require a separate cleanup task.

Update this page only when new evidence changes readiness, with date, revision,
environment, and limits. Keep older reports in the [evidence index](evidence/README.md).
