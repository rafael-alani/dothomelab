# Reference Boards clipboard and ordered context — 2026-11-04

## Release and scope

Reference Boards 0.5.0 is installed in the existing Mac Obsidian vault. The
release is `6f1ccf58c6eaaa2c18d13b1a8b766f5c89098636`, published on
`codex/reference-media-boards` and retained in the canonical checkout. It builds
on the [shared browser](2026-11-04-reference-shared-browser.md). A concurrent
archive audit commit was preserved; this change does not deploy its server code.
Main is not promoted. Source accounts, archive storage, providers, inference and
infrastructure configuration are unchanged.

## Delivered behavior

- Cards remain a browsing grid. Carousel video checkboxes now sit below the
  preview, labeled **Video N**; single videos use **Include this video**. Preview
  and selection remain independent, with a selected count under each chosen card.
- The current preview and the bottom selection list survive navigation and
  search across collections and sources. Navigation pauses playback. A selected
  title opens that exact video, including its carousel member.
- The bottom list has a menu handle left of each title for dragging rows, plus
  Up/Down keyboard movement. Export episode numbering follows the final order.
  Selection deduplicates by asset ID and retains the existing 50-video limit.
- **Copy text** copies Markdown with an optional task, complete ordered cached
  transcripts, timestamps, source links, provenance and quality warnings. It
  requires every selected transcript. Clipboard failures preserve the selection.
- **Capture this frame** records explicitly chosen stills from selected previews,
  up to 50. Captures pause playback, retain timestamps, reject duplicates and
  remove frames when the owning video is deselected. Undecoded initial frames
  receive a tiny paused seek; a still-blank result fails instead of exporting it.
- **Copy images** writes one labeled PNG sheet, ordered by episode and timestamp.
  Paste text first, then copy/paste images; each action replaces the clipboard.
  Images include only chosen frames and do not require speech transcripts.
- **Save agent brief** creates private Markdown and JSON provenance plus a PNG
  when frames were chosen. The Markdown embeds the PNG; a browser agent may need
  the image attached separately. Clipboard actions create no vault files. Closing
  the browser discards its unsaved selection.

See the [user workflow](../../USER_DOC.md#give-reference-videos-to-an-agent) and
[client runbook](../../clients/reference-media/README.md#agent-context-and-provider-settings).

## Verification

The committed `d78cb91` build passed an isolated Git-archive run of 21 Node plugin
tests, 24 server tests, 34 desktop tests and the documentation checker. The final
mouse-event refinement passed the 21 plugin tests again. JavaScript syntax and
whitespace checks pass. The focused tests cover navigation, stale transcripts,
exact ordered export, mouse and keyboard reorder handlers, copying failures,
missing evidence, frame selection/removal, image-sheet provenance, and blank
initial-frame decoding. The Impeccable source scan reported no regex findings;
its native-page contrast and element checks do not run on these source files.

Actual Obsidian 1.15.0 acceptance used existing cached media only:

- Instagram / Grind: `DesEIfyTofn` and `DeerQcfxN_T`, with 44 and 48 transcript
  segments. Native checkboxes remain below the preview. Seeking/capture stays
  paused; warnings remain visible. Initial-frame capture was corrected after a
  real blank-image failure and verified visually after the correction.
- Switching to Yaay / All saved and searching retains the prior preview and
  ordered selection. `DX9gwDAjPt3` remains one card with four explicit choices.
  Checking video 2 does not switch the currently previewed video. Its five cached
  transcript segments became ready during this session; no request was made.
- A native Chrome paste into a disposable, localhost-only acceptance page received
  9,740 characters for the initial two-video text selection and a 1280 × 688 PNG.
  The corrected sheet visibly contains both frames with episode/time labels.
  No evidence was sent to an external agent or website.
- The real save action produced
  `References/Briefs/Agent brief 2026-11-04T21-20-33-941Z-c04aa052.md` and sibling
  JSON/PNG. File inspection confirms exactly the three selected assets in order:
  `cdf69c1c…cca8f`, `a8cf1c2b…851f6`, `74c7a9ec…4a0b6`.
  The manifest records frames at 8.920 seconds for episode 1 and 0.001 seconds for
  episode 2. The 565,251-byte PNG was opened and visually checked. The note embeds
  the same PNG. This private acceptance artifact is retained for Rafael's review.

Mouse dragging passed on the final `6f1ccf5` installed build: the third selected
row was dragged to first position and then back to third, restoring the original
order. Earlier native-drag and pointer-capture variants did not move rows reliably
in this environment; the final implementation tracks mouse movement/release on
the modal document and cancels on Escape/window blur/close. Keyboard Up/Down
movement also passed in the actual app. The user's three original choices, order,
`test` task, Yaay search and independent video-3 preview were restored. Copy text
with the dance video's retry receipt correctly reported one missing transcript
and preserved all three choices, instead of silently omitting that evidence.

## Operations and rollback

Pulse verification passed for PVE inventory and Docker coverage on CT102, 110,
112, 114 and 115. Homarr's check on PVE returned six applications, unchanged;
35 shared monitoring probes passed. The initial local Homarr invocation failed
because it requires PVE; the correct host invocation passed. No service runtime,
container, deployment cache or durable application data was created or removed.
Native transcription-job monitoring limitations remain unchanged.

The installer retained plugin rollbacks under
`~/Library/Application Support/dothomelab-references/rollback/`:

- `20261104T205116Z/reference-boards`: preceding 0.4.0 installed plugin.
- `20261104T211418Z/reference-boards`: initial 0.5.0 clipboard candidate.
- `20261104T212341Z/reference-boards`: decoded-frame and pointer-drag candidate.

These are operator-owned rollback artifacts; retain until Rafael accepts the
new release. To return to the previous accepted behavior, reinstall the plugin
from review commit `c283b662` using the documented installer, then toggle Reference
Boards off/on. This restores plugin code, not deleted selections or notes.
The acceptance brief and PNG are private review artifacts; originals remain
immutable in the read-only archive. The localhost paste-test tab, server and disposable HTML fixture were removed
after acceptance. No temporary worktree was created. Other
worktrees and unrelated working-tree documentation were preserved.

## Requested vault cleanup after acceptance

Rafael confirmed physical dragging, then requested cleanup of `References`.
On 2026-11-04, 43 inspected demo, acceptance and redundant export files were
removed from the vault: 12 under `Board acceptance`, 19 under `Projects`, three
under `Frames`, seven brief-export files, and the two root example drawings.
The drawings contained only example embeddables; project notes contained only
their original demonstration/placeholder annotations. A backlink scan found only
generated folder indexes outside that removal set. Those two indexes were pruned.

The named seven-episode Markdown brief and its evidence JSON remain. The removed
timestamp-named seven-episode copy has identical Markdown, task and evidence;
its JSON creation timestamp differs. The two later acceptance brief pairs and
the clipboard acceptance PNG were test artifacts. The active catalog, archive
status, source/collection notes, thumbnails and retained brief files were checked
against 6,196 pre-cleanup SHA-256 values and remained unchanged. The remaining
top-level entries are `Archive.md`, `Briefs`, `Catalog.json`, `Collections`,
`References.md`, `Sources` and `Thumbnails`. Projects/Frames are created again
when the user adds a real card or capture.

Before removal, all 43 files and both original indexes were copied and their
hashes verified under the private, non-synced recovery directory:
`~/Library/Application Support/dothomelab-references/cleanup/20261104T224616Z`.
Its `manifest.json` records paths/hashes and `README.md` explains restoration:
copy selected files from `files/` back into the vault at the same relative paths,
without overwriting newer work; let Waypoint regenerate folder indexes. Rafael
owns this snapshot. Retain until the cleanup is accepted and examples are no
longer wanted; no automatic deletion is scheduled. This is a verified copy of
the listed files, not a whole-vault or server recovery test. No plugin, collector,
server media, service, secret, integration, or runtime configuration changed.
