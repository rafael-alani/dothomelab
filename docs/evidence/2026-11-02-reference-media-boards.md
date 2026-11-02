# Saved-reference media and Obsidian boards — 2026-11-02

## Delivered behavior

The [agreed research](2026-10-27-reference-media-boards-research.md) is implemented
as a native restricted PVE archive endpoint, an awake-only Mac collector and a
small Obsidian integration. Excalidraw is the primary board format after live
comparison with Canvas; both support inline Media Extended players. There is
no new web application, public player, container or offline full-video cache.

Open `References/Start here — reference board.excalidraw` in the existing local
vault. It contains an archived real video, two independent excerpts, a still,
instructions and a China itinerary card. `References/Second project.excalidraw`
uses the same immutable video with its own 6–9-second looping excerpt. The
[desktop runbook](../../clients/reference-media/README.md) owns usage and setup;
the [endpoint runbook](../../hosts/infra/reference-media/README.md) owns recovery.

Originals are eagerly downloaded before Obsidian use. The scheduled collector
runs every ten minutes while awake, advances bounded inventory pages and takes
up to twelve queued posts per run. Opening a card never starts acquisition.
`References/Archive` is the current import/status view. Initial backfill is
ongoing, not complete; future catch-up uses the same resumable queue.

## Environment and revisions

Work uses the canonical `/Users/rafael/Repos/dothomelab` checkout on
`codex/reference-media-boards`, without a task worktree or promotion to main.
The initial unrelated dirty/untracked files were preserved in recovery branch
`recovery/reference-media-before-20261102` at
`a7679564d4b8cf393561f5c7162bb5a6dde599cb`; those working changes remain intact.
Use `git show <recovery-ref>:<path>` to retrieve a preserved file without resetting
this checkout. No secrets were placed in that snapshot.

Initial native endpoint release is
`fb5814fb639d1e88dced6c6e4ff62547ae85350a`; initial verified plugin release is
`8b0c7f4b5afd58cbc30c28adc4a869605cec506a`. The collector first ran automatically
from `742ad5030974d2c478681c3dc9fb207f40d679a2`. Final installation/publish records
are appended below after checks. Existing guest archives retain
`db2f54f33797f0cb63879a1ca7f4a4a5527f230b`; narrow native/client deployment did not
replace newer whole-guest sources with this checkout.

Observed Obsidian 1.14.5 on the Mac; existing Media Extended and Excalidraw
plugins were used. Acquisition pins gallery-dl 1.32.19 and Playwright 1.64.1.
The dedicated signed-in Chrome profile uses normal macOS Keychain integration,
with cookies passed in memory. Profile/key/checkpoints stay in private local
Application Support, outside Git and Syncthing.

PVE `afa` and all six LXCs were running; VM101 remained stopped and untouched.
CT110 retains its existing appdata/shared mounts and native Samba services.
Both storage pools were healthy. Shared storage had about 18.7 TiB free; appdata
had about 74 GiB free. No ownership change was recursive and no unrelated
consumer mount changed. Existing Syncthing folder `mdshx-oxig9` remained
send/receive, three devices, versioning disabled.

## Import evidence

- Representative sample: 24 successfully archived source posts, 329 carousel
  image/video assets, including four video files and a mixed carousel. One
  unavailable/HTTP-400 post was recorded as a failure instead of successful empty
  media. Repeating the same sample retained exactly 329 assets: idempotent.
- Yaay: authenticated full web sync reached terminal board and saved pages;
  690 saved records, 66 boards, 195 sections, plus All/Unfiled = 263 collections.
  All 1,388 membership instances were retained, including three repeated entries.
  All root board IDs matched the visible UI. Both user-selected China boards'
  section headings matched the captured hierarchy. Saved records retained 1,450
  place entries, including 1,365 with coordinates. No location was inferred from
  unrelated video content.
- Instagram: independently scrolled Saved collection grid exposed 26 named
  collections plus All Posts. Pagination is still partial; named-list membership
  and Unfiled are not certified complete until every feed reaches its terminal
  page. Partial snapshots never retire preceding memberships.
- At the recorded completed-run snapshot: 50 source posts archived, 355 actual
  media assets plus one calibration video; 1,822 distinct posts pending across
  1,928 source records. Counts keep advancing and queue size can grow while older
  inventory is discovered. Zero acquisition retries in that scheduled run.
- Successful temporary downloads were removed after receipts. The downloads
  directory was empty at inspection; no full-video copies were left in the vault.
  One 64-byte failed-sample record remains for diagnosing its unavailable source.

The observed Yaay web schema exposes boards and sections. Arbitrarily deeper
recursive trees, empty/repeated names and rename/reparent behavior pass fixtures;
levels absent from the native app's web synchronization cannot be inferred or
claimed as live coverage. Saved soundtrack entries in Instagram's separate
Audio picker are outside the saved image/video-post collector.

## Acceptance and limits

| Check | Result and method |
|---|---|
| Canvas versus Excalidraw | Both rendered inline local-file video on the real Mac. Excalidraw chosen per user preference; it requires Media Extended and Reference Boards for the demonstrated behavior. |
| Actual full video and bounded clips | Real 20.755782-second archived video, 2–6 and 10–14-second cards; play/pause and clip endpoint observed in native UI. |
| Paused start / coordination | Three main-board cards began paused; starting excerpt A paused the full video. Reopening the second project's looping clip showed paused at 0 of 3 seconds. |
| Looping | Second project manually started, continued through multiple 6–9-second loops, then paused. Stock Media Extended loop autoplay needed the integration's manual-start guard. |
| Add / edit / capture | Native commands added an embeddable, edited bounds and captured a calibration frame. One-time real example includes a derived first frame and manually inserted China place card. |
| Project independence / annotations | Separate notes own ranges on the two real boards. Model/client tests change a range or refresh metadata while retaining independent card data and annotations. Importer never writes Projects, Frames or drawings. |
| Source removal / hierarchy mutations | Fixtures exercise unsave/deletion, rename/reparent, empty and repeated lists, multiple/repeated memberships and unavailable records; assets and history remain. No destructive live account changes. |
| Resume / bad scan / corruption | Fixtures cover interrupted pagination, resumed cursor without duplicates, delta-page rejection, failed/partial scans, cycles and corrupt upload rejection. |
| Home mount | Native Media mount remains read-only, nodev/nosuid; reconnect LaunchAgent last exit 0. Direct Codex process access differs under macOS Network Volumes permissions. |
| Safe unmount | Normal `diskutil unmount /Volumes/Media` refused while the volume was in use. No forced unmount occurred; mount remained healthy. Successful stale-remount and a sleep/wake cycle remain unverified. |
| Private VPN | Inspected Infra online identity and advertised `192.168.0.0/24` route; helper pins that peer and preserves the existing SMB URL. Samba reload/testparm passed. Genuine external playback/remount and VPN-failure acceptance deferred by Rafael. |
| Blog isolation | Current selected blog manifest had zero References inputs. Private notes remain outside Blog; frontmatter `private` is descriptive, not exporter access control. |
| Automated checks | Six archive, six client and two model tests passed; shell/JS/Python syntax passed. Documentation and final publication checks recorded below. |
| Integration health | Quiet live Syncthing Compose validation passed. Pulse verifier passed for PVE/LXCs/declared Docker workloads. Homarr staging check returned unchanged, six apps. No separate UI tile applies to this background collector. |

Pulse does not monitor this native request endpoint or the Mac collector process.
Their dedicated application-health coverage is a remaining monitoring gap;
Obsidian status and local worker state expose progress and errors. Existing host,
container and shared dashboard coverage remains healthy. Complete backfill,
external playback, sleep/wake recovery and a clean-host rebuild are not claimed.

## Rollback and retained artifacts

Pause the idle collector by booting out `media.rafael.reference-collector` from
launchd. Restore a retained LaunchAgent/release to roll back code; do not revert
the catalog or delete originals. Restore a prior plugin folder and toggle it in
Obsidian. Client runbooks contain the exact commands. Canonical upload objects
are immutable and the protocol has no delete operation.

| Artifact / owner | Reason and cleanup condition |
|---|---|
| Mac `~/Library/Application Support/dothomelab-references/releases/<revision>`, `agent.before-*`, `config.before-*`, and `rollback/<timestamp>/reference-boards`; reference client | Retained client/plugin rollback until accepted replacement and remote tests. Credentials remain private outside Git. |
| Mac `download-9yfrwmu6` inside the same support directory; sample importer | 64-byte failed-source record; remove after diagnosing or accepting that source failure. No full media retained there. |
| PVE `/usr/local/lib/dothomelab-reference-media/releases/<revision>` and appdata `authorized_keys.before-20261102T140509Z`; archive endpoint | Exact code/enrollment rollback; retain until newer protocol acceptance. Keep catalog and objects regardless. |
| CT110 `/srv/appdata/docker/infra-samba/reference-vpn-rollback/20261102T140721Z/registry.conf`; Samba | Pre-enrollment registry; retain until genuine remote playback acceptance. Restore with `net conf import`, validate, reload. No credential rotation. |
| Mac Media reconnect `.before-*` binary/plist/Fish copies; reconnect installer | Prior safe LAN behavior, retained until sleep/remote acceptance. |
| Vault `References/Board acceptance`, initial integration-created project notes and `media-lib` calibration references; board acceptance | Comparison/diagnostic examples retained for reviewing playback differences; user can remove cards/notes without deleting originals. |
| Recovery branch `recovery/reference-media-before-20261102`; repository | Preserves pre-existing local work. Remove only after its owner confirms all unrelated changes retained. |

No task container, image build or build cache was created. CT114 retained
21.07 GB build cache (20.97 GB reclaimable), CT115 9.7 GB; these predate this task
and were not pruned. All six staging containers and the one production container
were active; no task-created orphan runtime remained. Other chat worktrees were
preserved; no duplicate checkout was created for this task.

Map URL preservation follows Google's [Maps URL requirements](https://developers.google.com/maps/documentation/urls/get-started):
keep `api` and place IDs, strip tracking. Previously incomplete map links use
observed coordinates as a fallback, never invented locations.
