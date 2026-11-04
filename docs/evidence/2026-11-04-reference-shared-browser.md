# Shared Reference Boards browser — 2026-11-04

## Release and scope

Reference Boards 0.4.0 is installed in the existing Mac vault from
`c283b662becb4666cfdc1967094a6cf2220cc66b`, published on
`codex/reference-media-boards`. Its bundled JavaScript, stylesheet and manifest
match the committed sources byte-for-byte. The plugin is enabled and reloaded.
The canonical checkout retains the review candidate; no promotion to `main`
or server deployment occurred. Follow-up evidence commits do not change the
installed plugin code.

One CollectionBrowser implements board-add and agent-context modes. Sources
open their actual top-level folders; folders expose immediate children and their
own exact memberships. Back and breadcrumbs follow native parent IDs. Folder
search covers only the displayed level; post search covers the current collection.
Source ordering, removed-membership history and grouped post counts remain intact.

Context mode uses sibling native preview buttons and per-video checkboxes,
not nested interactive controls. Selection is an ordered asset-ID map, persists
through browsing/filtering/sorting, and is limited to 50 unique videos. Individual
removal and clear controls accompany the always-accessible task and export actions.
Carousel member numbers are explicit; images cannot enter a video selection.

Preview and selection use the existing read-only `transcripts` API. Only the
explicit request action uses `request_transcripts`. Cached timestamped text,
quality warnings and loading/pending/retry/unavailable states appear below the
player. Late results cannot render into a different preview, member or closed
browser. Timestamp buttons seek without starting playback. Post provenance is
available in a disclosure so the video and independently scrollable transcript
fit beside the grid. No inference or full-video cache was added on the Mac.

## Native Obsidian verification

Verification used the running Obsidian 1.15.0 app, its current theme, existing
archive and cached transcripts. No scrape, whole-library transcription, provider
change, infrastructure reconfiguration or agent dispatch was performed.

- Instagram displayed flat top-level folders; Grind retained **45 current posts,
  45 with media, zero awaiting**. Its existing seven-video series was searchable.
- Previewing `DesEIfyTofn` loaded paused at 151.2 seconds, with timestamped cached
  text and its provider-duration warning. A timestamp sought to 8.92 seconds;
  explicit playback worked. Switching to `DeerQcfxN_T` loaded its separate
  154.4-second preview paused and displayed the corresponding transcript.
- Checking other cards left the current preview untouched. Switching previews
  left checked videos selected. Tab then Space operated a native checkbox
  without starting playback. Preview borders and checked-member labels show
  different states in the rendered theme.
- Three ready selections survived post search and source/folder navigation.
  Yaay showed top-level boards, then **China inspiration**'s 25 immediate
  subfolders, then **Food** with exactly one post. A scoped `Food` search did
  not expand other branches. The Food video's uncached transcript showed pending.
- Yaay `DX9gwDAjPt3` appeared as one card with four explicit video checkboxes.
  Checking member 2 kept member 1 previewed; previewing member 3 left member 2
  selected. Pending/retry evidence stayed explicit rather than entering an export.
- The context command also opened from the exported Markdown note with no active
  board. The board-add command retained the full-video/excerpt editor and frame
  controls. Adding **Shared browser acceptance - excerpt 3-7s** created an
  independent card with verified stored start/end values **3/7**, loop false.
  Existing board players remained paused on reload.

The private acceptance export is
`References/Briefs/Agent brief 2026-11-04T20-30-34-551Z-bff86a0a.md`
with its sibling JSON. Inspection verified exactly these sources, in this order:
`DeerQcfxN_T`, `DePGBFXtswr`, `DesEIfyTofn` (all Instagram). They contain
**48, 40 and 44 segments**, respectively; the final video's quality warning is
preserved. Previewing a Yaay video did not add it to that export. No transcription
request was needed for those cached videos. The exporter is unchanged by the
subsequent preview-layout refinements.

## Checks and operational limits

Checks on an isolated export of the committed release passed: **17 Node plugin
tests, 21 archive Python tests, 30 client Python tests**. They cover hierarchy,
history/order/counts, independent preview/selection, persistent selection,
carousel IDs, stale responses/close, errors, the 50-video cap, exact export,
missing-evidence rejection and single-player/offline behavior. JavaScript syntax,
whitespace and documentation checks passed. Impeccable's mechanical detector
returned no findings. The client suite reports an existing urllib3 SSL-option
deprecation warning. Other agents' untracked audit tests/files were excluded
from the committed-release check and preserved.

Read-only live checks found the archive endpoint still at `8cfc162`, transcription
timer active, and speech container healthy. Pulse verified all PVE guests and
Docker hosts 102/110/112/114/115. All **35 shared probes** passed; Homarr's six
private staging entries required no changes. The native collector and native
transcription job still lack first-class Pulse completion monitoring, as recorded
in the preceding runbooks; this UI release does not close that gap.

No service, container, image build, mount or credential changed. Existing CT114
and CT115 build caches were **21.07 GB** and **9.7 GB**; their running containers,
images and durable releases were retained. External-network playback, sleep/wake,
and a new frame-capture write were not repeated in this UI-only acceptance;
existing frame controls and model regressions remain available. Fixture failures
establish offline/stale-response handling; no live network outage was induced.

## Retained artifacts and rollback

Rafael's plugin rollback bundles remain under the Mac collector support directory:

- `rollback/20261104T202639Z/reference-boards`: preceding installed 0.3 release;
- `rollback/20261104T203117Z/reference-boards`: initial shared-browser candidate;
- `rollback/20261104T203500Z/reference-boards`: compact-preview candidate.

Restore the exact preceding plugin folder into the vault's
`.obsidian/plugins/reference-boards` and toggle the plugin to roll back code.
Keep these bundles through review acceptance and until their revisions are no
longer needed. Do not roll back the archive catalog, originals or vault data.
The acceptance brief and the `fe24e74f` excerpt card on the existing collection
acceptance board are retained private review evidence, owned by Rafael; remove
only after review if no longer wanted. The isolated test export was disposable
and removed automatically. No duplicate worktree was created; existing other-chat
worktrees and unrelated dirty/untracked documentation and audit work were preserved.
