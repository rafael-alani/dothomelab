# Saved-reference media and project boards research — 2026-10-27

Research draft, not a deployed service or accepted implementation. Inspected
the live homelab, Mac mount/configuration and Rafael's signed-in Yaay web UI;
reviewed current primary documentation and gallery-dl release source.
Repository baseline: `454ac00274ad9acfeda450e7c916596c54d8e210`.
CT110 archive reported `9c2c15414382082ffb787fb4e912002564cbc902`.
Existing unrelated working-tree edits were preserved. No source account was
modified, no downloader/plugin installed, and no media imported.

## Requirements settled in conversation

- Mac-only, network-dependent operation is sufficient; mounted server storage
  is preferred. Preserve the existing Syncthing/Obsidian workflow.
- Away-from-home playback over a private VPN is required. Do not keep offline
  copies of full videos; local notes and thumbnails remain available when the
  server cannot be reached.
- Private reference archive; downloaded material survives unsaving, list
  deletion and disappearance of the source. Deletion is a separate decision.
- Support Instagram Saved and Yaay now; Instagram alone may suffice later.
- Import all existing and future saves from both accounts, including items
  outside named collections. Collection selection is not an import filter.
- Automatic catch-up while the Mac is awake, with occasional login renewal,
  is acceptable.
- Discovery remains in Reels/Yaay. The destination is a mood board, project
  mind map or itinerary containing full videos, excerpts, still frames and
  notes. A separate media-browser-first workflow was rejected.
- Yaay can have multiple nested list levels. Preserve this as a requirement
  even where the inspected browser example exposes only board/section/item.
- Videos and excerpts must play inside their board cards. Choose Canvas or
  Obsidian Excalidraw by the actual result; a separate player is insufficient.
- Playback starts on click, with one clip playing at a time by default. Starting
  another card should pause the previous one; excerpts may loop when selected.
- Source refreshes update the library while preserving project-board layout,
  chosen excerpts and human annotations. Project boards are user-owned.
- Travel planning initially means visual itineraries with map links. Geographic
  maps and route/travel-time calculation are outside this first version.
- Server archive alone is sufficient. Do not add backup coverage for downloaded
  reference media. Existing note/appdata backup policies remain applicable.

## Recommendation and decisive uncertainty

Pilot **Obsidian Canvas plus Media Extended**, using one canonical server
archive. Keep **Bases optional**, as a collection picker rather than the main
workspace. Also compare the already-enabled Obsidian Excalidraw plugin for
the same board. Rafael explicitly accepts either board tool; select it by
inline playback and authoring behavior, not by the earlier Canvas preference.

Media Extended's author explicitly documents opening desktop files outside
the vault without copying them. It also documents timestamp ranges, frame
capture and a Bases-backed media library. These are a much closer match than
building a new gallery application. However, **external-video playback inside
Canvas cards, with correct excerpt boundaries, is not yet verified**. Neither
working playback in a separate pane nor a healthy importer would establish
that the requested board works.

Sources: [external local files](https://mx.aidenlx.site/docs/v4/how-to/load-media/local-file),
[timestamps and clips](https://mx.aidenlx.site/docs/v4/concepts/timestamps),
[media library](https://mx.aidenlx.site/docs/v4/concepts/media-notes),
[plugin overview and frame capture](https://github.com/aidenlx/media-extended).

The next prototype should contain one full Reel, two different excerpts from
that same Reel, one extracted frame with a timestamp backlink, one place card,
and a project note. The video must exist once. Judge that board before building
the full importer. If inline playback fails, change the player
integration or board choice; do not quietly downgrade acceptance to links.

## Observed existing integration

| Component | Read-only observation | Consequence |
| --- | --- | --- |
| Mac SMB | `//afa@192.168.0.110/Media` mounted read-only at `/Volumes/Media` | Existing consumer path can read a new archive below media. |
| Canonical media | `/vault/shared/media`; CT110 Samba `Media` points here | Proposed files belong here, not in a guest root or application database. |
| Syncthing | Healthy CT110 container; folder `mdshx-oxig9`, Send & Receive, `/vault/shared/media/obsidian`, three devices; no configured versioning type | Continue syncing notes, thumbnails and boards; do not add full videos to this folder. No end-to-end sync probe was run. |
| Mac vault | `/Users/rafael/Obsidian/obsidian-cloud-retrieval` | Keep the working vault local. Bases, Canvas and Excalidraw are enabled in configuration. |
| Capacity | `vault/shared` about 18.9 TiB available; rpool about 74.4 GiB available | HDD media capacity is ample at this observation; large clips should not consume SSD appdata. These are rounded ZFS figures, not capacity reservations. |
| Existing download UI | `yt-dlp-web-ui` healthy on CT112 | Useful for individual supported URLs, not evidence of named Instagram/Yaay collection import. |

Checked `pct config 110`, `findmnt`, `stat`, `namei`, sanitized container names
and health, Samba share configuration, Syncthing folder attributes and Mac
mount/plugin configuration. No secrets were printed. CT110 is unprivileged;
host `101000` maps to guest `1000`. No permission changes were made.

The [Media reconnect helper](../../clients/macos-media/README.md) restores the
existing mount on the home LAN. Its current contract is not an automatic remote
Tailscale mount. Rafael now requires remote VPN playback, so this is an
implementation gap rather than an accepted limitation. The repository's
[Samba configuration](../../hosts/infra/cockpit/samba-registry.conf) binds to
loopback/eth0 and permits only loopback and `192.168.0.0/24`; a direct tailnet
connection is not established by that configuration. The existing
[Tailscale provisioner](../../hosts/infra/tailscale/install.sh) declares Infra
as a subnet router, but route approval, effective access rules and successful
remote SMB playback were not verified in this research.

Preserve `/Volumes/Media` as the Mac mount path at home and away. Prefer a
verified private Tailscale endpoint with narrowly scoped SMB access, keeping
Media read-only. Extend the helper's endpoint/identity checks explicitly;
simply removing its LAN guard could connect to an unrelated server on an
overlapping hotel network. Keep Keychain authentication, conflict detection,
serialization with existing clients and refusal to force-unmount busy shares.
Do not create a second `Media-1` mount or change the paths in every board.

[Tailscale subnet routing](https://tailscale.com/docs/features/subnet-routers)
is an alternative transport where effective routing and Samba access permit
it; advertised routes alone do not establish end-to-end access. Confirm the
chosen route from a genuinely external connection. Measure video opening and
seeking there: Tailscale documents that
[direct connections generally outperform relayed connections](https://tailscale.com/docs/reference/connection-types).
If the VPN or server is unreachable, retain the card, thumbnail and annotations
with unavailable playback; do not delete assets or silently create offline
full-video copies. No VPN, Samba or reconnect-helper settings were changed.

The [current backup selection](../../hosts/infra/obsidian-sync/README.md)
covers Obsidian, photos, Immich originals and the environment. PBS covers
appdata, not shared media. Rafael explicitly chose server-only retention for
the new `media/references` archive, without additional backup enrollment.
Putting its catalog in appdata does not protect its videos. No media-recovery
guarantee is part of this design, and no backup or restore was run.

## One asset, many collections and board appearances

Do not make `/yaay/china/shanghai` the canonical location of a video. The
same Instagram Reel can be saved directly, included in several Yaay lists,
used in a film project, and referenced by several places. Renaming a list
should not move its media or break a board.

Proposed layout, not created:

```text
/vault/shared/media/references/
  instagram/<post-id>/<asset-id>.mp4
  tiktok/<post-id>/<asset-id>.mp4
  derived/<asset-id>/frames/<timestamp>.jpg

/srv/appdata/docker/reference-import/
  catalog.sqlite
  inventories/                 # private, sanitized source snapshots

Obsidian vault/
  References/Items/            # one durable source note per post
  References/Collections/      # identities, hierarchy, filtered views
  References/Thumbnails/      # small local browsing images
  Projects/<project>/         # board, excerpt notes, annotations
```

The Mac reads `.../media/references` as `/Volumes/Media/references`. Uploading
is a separate contract: the current `Media` mount is read-only. A future
collector needs a scoped ingest/transfer path and one canonical server writer;
do not turn the Media share writable or use broad Vault administration as
the normal application workflow.

Separate these identities:

| Record | Meaning |
| --- | --- |
| Source item | Original post ID/URL, creator and caption. |
| Asset | One video/image member; a carousel has several assets. |
| Collection | Source-scoped ID, parent ID, label, ordering where available. |
| Membership | Item belongs to collection; many memberships are allowed. |
| Place | Imported name/location/map link with provenance and confidence. |
| Board appearance | Project-specific whole asset, start/end range or still-frame timestamp, plus the user's annotation and layout. |

An excerpt should normally be a **time-range reference to the original**, not
a new trimmed MP4. A still frame is a small derived image with an asset ID and
timestamp backlink. Export a trimmed file only if a later workflow needs it.
Removing a card removes that appearance; it must not delete the source media.
Two projects may select different intervals without rewriting a global range.

Keep the asset bytes addressed by a project appearance immutable. If a source
later supplies different media, record a new asset version rather than silently
replacing the file beneath existing timestamps. Importers own source facts and
collection navigation; they must not regenerate user-authored project boards.
Updating a source note must preserve human fields and note-body annotations.

Keep raw observed collection memberships and historical last-seen state.
Generate human-readable paths such as `Yaay / China / Shanghai` from the
hierarchy. Preserve empty lists and equal names under different IDs. When a
source ID is unavailable, record that limitation rather than pretending a
mutable display label is a stable ID.

## Instagram: collection discovery plus gallery-dl

[Maintained supported-sites documentation](https://gdl-org.github.io/docs/supportedsites.html)
lists Instagram Collections, Saved Posts and Reels with cookie authentication.
The source release inspected was [gallery-dl 1.32.18](https://pypi.org/project/gallery-dl/1.32.18/),
published October 25, 2026. Its source-distribution SHA-256 is
`1c5562af3799a0bec96be0f64d95a416aee688fd09fe3893ca3a6c87bbe65bcd`.
It was inspected without installing or running it against the account.

Active development [moved to Codeberg](https://github.com/mikf/gallery-dl/issues/9374).
Codeberg was unavailable to the research fetch, so the current official
[PyPI source archive](https://files.pythonhosted.org/packages/ec/55/e40b8ce403489e7b3122eee28693efd885ca68256a9c6344fdfbd0842c3e/gallery_dl-1.32.18.tar.gz)
was used instead of relying on frozen GitHub implementation files.

In that release, `extractor/instagram.py:669–696` separates all-saved and
individual-collection extraction. A collection needs its actual
`/USER/saved/NAME/ID` URL. The label comes from the URL; the inspected extractor
does not enumerate the user's collection list. Browser inventory is therefore
needed for automatic discovery of new collections and current labels.

The important importer trap is verified in `job.py:444–519` and
`postprocessor/metadata.py:107–113`: an archive hit skips before the default
file-metadata hook. Downloading one Reel twice with a shared archive can retain
one video but lose its second collection membership. The
[metadata event options](https://gdl-org.github.io/docs/configuration.html#metadataevent)
allow other hooks, but require deliberate configuration and tests.

Recommended flow:

1. Discover actual collection IDs/URLs/labels from the authenticated browser.
2. Record every collection membership in a per-run inventory independently of
   downloading. Include all-saved/unfiled items according to selected scope.
3. Download missing assets once; preserve ordered carousel members.
4. Generate or update only importer-owned note fields, preserving annotations.
5. Mark a scan complete only after pagination finishes. Partial scans cannot
   remove memberships or imply that the library is empty.

An already-downloaded post can be newly assigned to a list, so stopping the
scan at the first known post is insufficient. Browser sessions remain on the
Mac, outside Syncthing/Git/logs. Expiry or rate limiting must produce a visible
needs-sign-in/partial result and conservative retry, not an empty success.
Upstream [saved-post failure reports](https://github.com/mikf/gallery-dl/issues/8738)
illustrate that supported extractors can still break; authenticated success
against Rafael's Instagram account remains untested.

## Yaay: authenticated browser feasibility established, completeness pending

Rafael signed into the official [Yaay web login](https://yaaytravel.com/login)
in this chat's browser. Read-only inspection then established:

- Saved items and Boards are accessible in the signed-in web application.
- A sampled travel board exposes 25 section headings, including repeated labels.
- Selecting an item exposes board, group, membership and item identifiers in
  ordinary navigation URLs.
- The item's Instagram control reveals a standard original Reel link, creator
  and original caption. A loaded video element was present; sound/seeking and
  downloaded-file equivalence were not tested.
- One saved clip can have multiple place matches; some matches explicitly have
  no resolved location.

This supersedes the pasted context's uncertainty about whether any usable web
interface exists. It **does not** prove that every native-app nested list is
represented, every item has an original link, or that a full account crawl
finishes correctly. Account-wide inventories, private board URLs/IDs and
session material are intentionally not embedded in this Git research note.

Build a recursive browser collector against observed UI: board → child list /
section → item → original source and places. Preserve ordering and empty lists;
walk until an observed end and compare available counts. Download from the
original platform through the appropriate maintained downloader. Treat Yaay
playback/CDN URLs as transient transport, not durable source identities.

Yaay's [terms](https://yaaytravel.com/c/terms-and-conditions) restrict automated
extraction. This is an unsupported integration with account/maintenance risk,
not a promised API. Its [privacy policy](https://yaaytravel.com/c/privacy)
provides a data-copy request route, but no guaranteed nested-list/media schema.
No request was sent. A supported account export remains a fallback if browser
parity or future access fails; iOS traffic interception is unnecessary for
the currently observed browser-accessible sample.

## Obsidian implementation choices and alternatives

| Option | Assessment for the clarified workflow |
| --- | --- |
| Canvas + Media Extended | First pilot. Fits notes, reusable whole/range/frame references and current storage. Inline Canvas behavior is the decisive gap. |
| Excalidraw inside Obsidian | Compare the same live note embed if drawing and image arrangement help. Its Markdown embeddables commonly use Canvas nodes, so this shares the unresolved playback dependency. Direct `file:` web cards are rejected by its renderer. |
| Canvas + External File Embed and Link | Lighter external-file plugin with virtual directory mappings; less documented clip/frame workflow. |
| Private HTTP player embedded in a board | Fallback if SMB-backed note rendering fails. Could serve one canonical file with range requests, but adds a service, access control and player integration. |
| TagSpaces or DEVONthink + Obsidian | Technically plausible existing-file browsers, but Rafael rejected the extra media-browser step. Retain as alternatives, not the proposed workflow. |
| Eagle | Its official support index describes copy import rather than indexing. It could own a canonical library, but that is a different storage commitment and still needs acquisition. |
| Eden/Dewey | Potential capture conveniences, not a verified solution for reusable NAS-backed excerpt boards. |

Native [Canvas help](https://obsidian.md/help/plugins/canvas) documents media
from the vault and web cards. The [JSON Canvas format](https://jsoncanvas.org/spec/1.0/)
does not guarantee that Obsidian resolves arbitrary external file paths.
[Bases cards](https://obsidian.md/help/bases/views/cards) support thumbnails;
they are not documented as an autoplaying video wall.

[Media Extended](https://mx.aidenlx.site/docs/v4/concepts/media-notes) uses
Markdown media notes and IDs, and can refresh source metadata. That refresh
overwrites existing fields. Keep importer facts, plugin-owned fields and human
annotations distinct; a source refresh must never overwrite project meaning.
The author discloses v4 is closed source. Its
[installation page](https://mx.aidenlx.site/docs/v4/install) lists 4.2.7/minimum
Obsidian 1.12.0 while the [current plugin directory](https://community.obsidian.md/plugins/media-extended)
lists 4.2.9/minimum 1.14.4. Verify the chosen release manifest and running app
before installation. The Mac bundle reports 1.12.7; that alone does not prove
the running, auto-updated application version.

[External File Embed and Link](https://community.obsidian.md/plugins/external-file-embed-and-link)
supports external video and virtual roots, for example a configured media root
mapped to `/Volumes/Media`. It does not establish Canvas compatibility.

The released [Excalidraw 2.29.0 web renderer](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/view/components/CustomEmbeddable.tsx#L510)
allows HTTP, HTTPS and data URLs but excludes `file:`. Its
[file embeddable implementation](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/view/components/CustomEmbeddable.tsx#L830)
and [Canvas node factory](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/view/managers/CanvasNodeFactory.ts#L132)
host ordinary Markdown through native Canvas nodes when that factory is
available, with workspace leaves for other paths. This is evidence that both
board choices share a rendering dependency, not proof that either runs Media
Extended correctly. Use a live embeddable in Excalidraw; a Markdown-to-image
snapshot cannot provide playback. These sources describe the released plugin,
not a verified installed version on this Mac.

Media Extended's [clip-range guide](https://mx.aidenlx.site/docs/v4/how-to/clip-time-range)
documents inline note embeds with `#t=start,end`, including a stop boundary in
Reading mode. Neither Canvas nor Excalidraw compatibility is established there.
Generate the first external-file embed using its UI rather than copying the
guide's inconsistent example markup. The smallest comparison is the same note
with one full video and two independently bounded clips on both boards. Verify
playback, sound, seeking, stop/loop behavior, resizing, reopening and remounting.
If both succeed, prefer Canvas for its simpler arrangement; choose Excalidraw
when its drawing controls materially improve the board. If both fail, test the
private HTTP player fallback instead of assuming another board plugin will
remove the shared dependency.

Avoid a symlink into the media tree as the default integration.
[Obsidian warns against symlinks](https://obsidian.md/help/symlinks), and
[Syncthing does not follow them](https://docs.syncthing.net/users/faq).
Keep the existing local vault rather than placing its notes/config on the
read-only, intermittently connected Media share. The prior agent's proposal
to replace Syncthing with Headless Sync or LiveSync is unnecessary here.

For completeness, [DEVONthink indexing](https://www.devontechnologies.com/support/faq/copy-files)
references external files without copying; [TagSpaces network locations](https://docs.tagspaces.org/ui/locations/)
support mounted paths but warn about NAS performance, and its
[sidecar metadata](https://docs.tagspaces.org/tagging/) needs write placement.
The existing read-only consumer share cannot silently become their tag writer.
[Eagle's support index](https://en.eagle.cool/support/all-articles) describes its
copy-based library; detailed article bodies were unavailable during research.
[Dewey](https://getdewey.co/how-to-use/sync-instagram-saved-posts/) documents
Instagram collection import, but complete Reel/carousel export still requires
a test. [Eden](https://eden.so/help/library/connect-instagram-saves/) documents
metadata imports and initial collection tags; its
[export](https://eden.so/help/account/export-your-workspace/) omits board layouts.

## Pilot acceptance and unresolved design frontier

First prove the board with a small sample, then prove acquisition with 20–30
items. Include a source shared by Instagram and Yaay, duplicate memberships,
a mixed carousel, a multi-place clip, at least three nested collection levels,
an empty list and repeated labels. Use fixtures for rename/reparent/deletion
tests unless a live test change is explicitly authorized.

Required checks:

1. Whole video, selected start/end range and still frame are useful on the
   actual project board; sound, seek, looping and focus behave correctly.
   Cards remain paused until clicked, and starting another card pauses the
   previous player. This coordination is a requirement, not verified plugin
   behavior.
2. Two projects reuse one original video; their excerpt ranges are independent.
3. A second import creates no duplicate assets/notes and preserves project
   layout, excerpt selections and human annotations. Changed source media
   cannot silently replace the asset used by an existing excerpt.
4. Renaming/reparenting a collection changes navigation without moving media.
5. Interrupted scans, expired login and a missing mount preserve prior state.
6. Unsaved/unavailable sources remain archived and show accurate availability.
7. Mac sleep/remount retains references and the existing read-only boundary.
   Test playback and seeking from a genuinely external network over the VPN,
   returning home, a disconnected VPN, and a conflicting mount path. Both
   locations must resolve the same media references without forced unmounts
   or permanent offline video copies.
8. New private reference notes stay outside Blog publication inputs and contain
   no publication opt-in. Verify generated board/thumbnail content does not leak
   into public exports.
9. Media remains outside backup selections as requested; documentation must
   distinguish retained server files from backed-up notes/catalog state.
10. Both initial and incremental inventories cover all saves, including unfiled
    items. Named-list membership is captured independently of media download
    deduplication; partial scans must not be treated as complete inventories.

The importer should start as a small deterministic job, not a new general
application platform. Reusable deployment/transfer helpers belong in this
repository. A new service would require Compose/mount/backup declarations,
focused checks and Pulse/Homarr enrollment under the existing runbooks.
Neither the healthy legacy Contentflow container nor n8n's presence establishes
an existing acquisition solution; this task does not modify those projects.

The import/playback frontier is settled: all existing and future saves from
both accounts, including unfiled items; click-to-play with one active clip at a
time; source refreshes preserve project layout, excerpts and annotations. Inline
board playback is required, visual itineraries with map links are sufficient,
and reference media gets server-only retention. Remote playback over a private
VPN, without offline full-video copies, is also settled. No further preference
questions are currently needed. Board-tool selection depends on evidence from
the exact inline-playback test, including coordination between players. Remote
reachability and mount recovery require implementation and an off-LAN test;
the current helper and Samba policy do not establish acceptance.

Actual playback and Canvas interaction were not tested because computer-use
access to Obsidian was denied. Browser research and homelab inspection continued
without bypassing that access decision. The design remains a reviewable research
draft, with no production activation or shared-understanding confirmation.
