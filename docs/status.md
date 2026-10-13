# Project status

Live observations: **2026-10-12**, Europe/Amsterdam. Documentation pilot
prepared across October 12–13 for review. Code baseline: `c2661dd`
(`c2661ddd1d2ca2db757f911c05d3606934b2ccdb`). Environment: production PVE `afa`,
with read-only inspection from the operator Mac. Guest revisions differ below.
Evidence: [documentation baseline](evidence/2026-10-12-documentation-baseline.md).

This page owns current readiness. [USER_DOC.md](../USER_DOC.md) owns capabilities
and instructions; dated reports own the details of earlier acceptance. An old
passing check is not silently promoted to a fresh one by updating this page.

## Readiness observed in this review

| Area | Result | Limit |
|---|---|---|
| PVE / guests | PVE 9.1.2; CT102/110/112/113/114 and VM101/104 running | No reboot or clean-host recovery test |
| Storage | `rpool` and `vault` ONLINE; canonical dataset mountpoints match | No new scrub, file-integrity, or restore test |
| Active Docker inventory | CT102: 21; CT110: 12; CT112: 44; CT114: 2 | Counts include live-only/retained services; no active unhealthy status reported, but some have no health check |
| Representative access | Homarr, Aurral, PinePods, Zotero root, Film-introspect: DNS to Infra and HTTPS 200 | Checked from PVE; no authenticated task, public deny test, or client acceptance |
| Daily appdata service | `Result=success`, exit 0; completed Oct 12 at 02:25:08 CEST; timer scheduled | No archive-content or restore validation performed |
| WUD handoff service | **Failed**, exit 1; completed Oct 12 at 02:26:31 CEST | Cause and affected update not diagnosed in the docs task |
| Proton backup | Host timer disabled | No new evidence of login, verified upload, or restoration |
| Documentation pilot | New reading map/manual/guides and retained history | Awaiting Rafael's review before a reusable skill is designed |

## Observed drift and follow-up work

| Finding | Consequence / next task |
|---|---|
| CT102 archive is `a4f1374`; CT110/114 are `ee1c217`; CT112 is `c2661dd` | Different `DEPLOYED_COMMIT` values; inspect the needed changes before targeted sync. A revision marker does not prove every installed script matches it. |
| Infra has healthy `contentflow-contentflow-1`, absent from this checkout's Compose declarations | Its rebuild/data/update contract is not established by this repo. Reconcile ownership in a separate task. |
| DroppedNeedle is running; Paperless-GPT has no container | Equal Apps counts do not mean desired membership matches. Preserve DroppedNeedle until generated-flow acceptance; verify the required external GPT key before deployment. |
| NPM retains an enabled `symphony-check.staging.rafael.media` route but only Film-introspect is declared/running in CT114 | An enabled route does not establish a live supported application. Reconcile after inspecting ownership. |
| Several legacy NPM routes have no inline `deny all` and access-list ID 0 | Do not describe all hostnames as private. A complete external exposure review was not performed. |
| Legacy Obsidian/OpenWebUI proxy entries remain | Do not treat them as currently supported services; no cleanup was performed. |

## Previously verified workflows

These are historical evidence, with no new authenticated acceptance in this
documentation review. Use each report's own revision, sample, and limitations.

| Manual workflow | Existing evidence | Still not established by that evidence |
|---|---|---|
| [Music request/import](../USER_DOC.md#request-and-listen-to-music) | [Aurral request pipeline](aurral-v2-request-pipeline-2026-07-26.md), [Soularr import repair](slskd-purple-rain-import-2026-09-17.md) | Generated flow plus device-specific Feishin/Kew/Jellyfin playback |
| [Ebook/audiobook paths](../USER_DOC.md#acquire-and-read-books) | [Phase 3](media-pipeline-phase-3-evidence-2026-07-25.md), [Listenarr](listenarr-addition-2026-07-28.md) | Listenarr report's search test did not grab a release; physical reader setup remains separate |
| [Reviewed metadata](../USER_DOC.md#review-book-metadata) | [Book publication](book-metadata-canonicalization-2026-07-26.md), [music publication](music-metadata-canonicalization-2026-07-26.md) | No unrestricted automatic matching or safety claim for every format |
| [Readaloud](../USER_DOC.md#create-an-aligned-readaloud) | [Phase 4](media-pipeline-phase-4-evidence-2026-07-25.md) | Representative retained fixture, not every book/client |
| [Podcasts and GPodder](../USER_DOC.md#subscribe-to-and-sync-podcasts) | [Phase 5](media-pipeline-phase-5-evidence-2026-07-26.md) | Physical mobile client and ECHO hardware acceptance |
| [Zotero attachments](../USER_DOC.md#sync-zotero-attachments) | [Service checks](../hosts/apps/zotero-webdav/README.md), [October repair](zotero-lxc-outage-2026-10-07.md) | Specific client upload/reader refresh remains a user action |
| [Obsidian receipt](../USER_DOC.md#sync-obsidian-and-access-shared-files) | [Canonical paths and laptop seed](syncthing-canonical-paths-2026-07-26.md) | Current laptop sync, phone pairing, and independent off-site recovery |
| [Desktop SMB](../USER_DOC.md#use-desktop-media-and-snowsky-echo) | [Reconnect](macos-media-reconnect-2026-09-17.md), [Tailscale routing](macos-media-tailscale-2026-09-24.md) | Every client/session and uninterrupted network-switch playback |
| [Staging](../USER_DOC.md#test-a-staging-branch) | [October staging acceptance](staging-addition-2026-10-04.md) | Real production integrations and destructive clean-host restore |
| [Recovery](operations.md#backup-and-recovery) | [Migration restore samples](compose-project-migration.md), [native state](rebuild.md#recovery-material), [HAOS](haos-vm.md) | Full clean-host rebuild and destructive VM104 restore |

## Known limitations and unverified work

- **Recovery:** physical PVE/network/disk provisioning is external. Full
  destructive clean-host and VM104 restore acceptance remain outstanding.
  Shared media lacks broad independent backup. PBS success does not close that
  gap; retain an off-host encryption key.
- **Proton:** the runner is installed with a disabled timer. The historical
  Syncthing laptop seed and private GUI succeeded; phone pairing, Proton login,
  first checksum-restored generations, and enabling the timer are still not
  evidenced. Do not repeat the obsolete claim that the laptop/GUI were never set up.
- **Paperless-GPT:** historical blocker is the missing external OpenAI key; this
  review confirmed no container but did not read or test the key. The old full
  production dry-run stopped there; no new bootstrap dry-run was run.
- **Music:** generated Aurral flow acceptance is pending. Its Last.fm setup and
  Discover refresh have historical evidence; those are not a completed flow.
  Live DroppedNeedle and its restart policy must stay unchanged until acceptance.
- **Accounts and devices:** earlier reports leave Wizarr first-admin/invitation,
  Bar Assistant first-use, authenticated yt-dlp download, SnapOtter/Stirling
  first-login setup, Kavita first-use, and physical reader/mobile checks open.
  They were not reinspected; do not infer they are complete from health.
- **BookOrbit:** the older report found administrator recovery-credential drift;
  its current alignment is unverified. Do not rotate it merely to make docs pass.
- **Observability:** Loki has no declared log shipper. Pulse physical-disk/
  temperature collection and Docker image-update actions stay disabled.
- **Incident follow-up:** the October 7 report leaves the cause of the host
  restart unknown and physical SATA cable/power inspection conditional on
  recurring errors. Autostart changes were verified without a reboot test.
- **Cleanup:** retained containers, snapshots, dumps, volumes, images, and legacy
  state remain a separately scoped cleanup task.

## Updating this page

Update a row only when new evidence changes it. Record date, revision,
environment, method, and limits; link the affected manual workflow and evidence.
Do not refresh dates automatically or use this page as a running issue log.
Older broad observations remain in [current-state.md](current-state.md),
explicitly preserved as a historical snapshot, and the [evidence index](evidence/README.md).
