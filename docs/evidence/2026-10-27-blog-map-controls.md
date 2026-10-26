# Blog map controls and optional starting notes

Verified on **2026-10-27**, Europe/Amsterdam, from the operator Mac through PVE
to CT110/114. Blog candidate `2d25b6db267906ad140d4d236e14abfc31d45135`
is published to `staging`. CT110 uses publisher source
`6a74fa49d6899992c78f15dcf957d470ac2acdc1`; CT114 uses importer source
`b8734c68586bebcdcfdfe1eca8eab434bd5202cd`.

## Delivered behavior

Skip navigation animations is a native saved checkbox. Read notes retains native
link navigation with the same button styling as the canvas actions. Starting note
sits between Fit map and Read notes and is disabled without a matching target.
The optional `starting-note` property accepts an exact note name or source path;
it opens at the note-picker's close view. Blank, missing or ambiguous targets
fall back to Fit map. Automatic initial focus is not a user-selection event.

All nine current Mac vault wrappers and the installed Blog article template have
the field set to `""`, as requested. The additive installer migration preserved
the user's renamed folders and authored text. The repository fallback articles
and maintained template also contain the blank property.

Rich note bodies become readable at 128 × 64 projected pixels, 80% of the old
160 × 80 threshold. Off-canvas cards and bodies unmount instead of loading in an
80px margin. Excalidraw retains its own empty positioning wrappers; returning an
empty fragment avoids its default iframe fallback. Existing viewport-clipped
Umami sampling excludes off-canvas notes, with regression coverage for pan-out,
no new visibility/time events while outside, and re-entry. Sampling remains once
per second; overlapping visible notes may count together.

## Verification

Local macOS checks passed: blog typecheck, 86 unit tests and static build;
17 focused Chromium cases; 14 WebKit cases; and configured starting-note tests
in separate Chromium/WebKit runs using a disposable source copy. The WebKit
configured-note case checks that automatic focus emits no selection event and
the return button emits one. Desktop and phone control screenshots were inspected.
Publisher tests (16), authoring migration tests (3), editorial adapter tests (6),
deployment tests (10), documentation checks and whitespace checks passed.

Eight live Chromium cases passed against the deployed candidate: all nine course
maps, standalone/no-JavaScript reading, the blank starting-note control, responsive
toolbar, DOM continuity during pan/zoom, and real staging Umami ingestion. The
analytics check received 21 successful event responses and requested a standalone
note-open event. Panning fully outside the drawing removed every note card and
produced no further note events after the final visibility sample. This is
synthetic verification traffic, not evidence of real readership.
The separate live checkbox persistence/direct-navigation case also passed.

The new publisher snapshot is
`5066da12b3f5e992f9c5ddcc32a9d461004443e7bf1ab5ca584da1e78650ece1`.
Direct inspection confirms all nine exported map articles carry blank YAML
properties and blank `startingNote` component props. The source graph retains
ten drafts and zero published wrappers.

At 00:42 CET, CT114 accepted that content digest with blog code `2d25b6d` and
configuration `50de96483f78`. Quiet Compose validation, nginx configuration
validation, HTTP health and the normal read-only deployment verifier passed.
The content-only cutover reloaded nginx in the existing healthy web container.

The WebKit reload-position test fails with scroll 1100 restoring to 0. It fails
identically on unchanged baseline `81cbb67` in the isolated source copy. This
existing issue was not changed. The other map, checkbox, no-JavaScript and phone
render-budget cases passed. No physical iPhone, PBS restore or manual release
rollback was tested. Three previously documented missing source-note targets
remain missing; no note was substituted.

## Staging importer repair

The scheduled staging importer had already failed at 00:09 CET after the user's
parent/topic folder renames. It renamed a parent, then read stale child paths
from its pre-rename directory listing. Later attempts refused the retained
incomplete context. A minimized parent-and-child rename regression reproduced
the same FileNotFoundError. Ending that scan after a successful identity match
fixes it; the next folder gets a fresh listing. The source tree and existing
articles remain unchanged outside the disposable build context.

The candidate's incomplete context is retained at
`/var/lib/dothomelab-staging/blog/2d25b6db267906ad140d4d236e14abfc31d45135-8784e5a20f3c61a1637d5f1d3fa64cd369c978ff856535d43035443e56080460.before-import-fix-20261027`.
Earlier failed contexts and release inputs were not deleted. The source swap and
candidate-context rename used the deployment lock; no running guest was stopped.

## Recovery inputs and boundaries

The Mac vault retains verified originals under
`.blog-publisher-backups/starting-notes-20261027T002718225024/`, preserving each
file's relative path. Compare later edits before copying a saved file back.
The migration is idempotent and preserves any nonblank choice.

Both CT110 and CT114 retain `/opt/dothomelab.before-starting-notes-20261027`.
CT110 also retains publisher image
`dothomelab/blog-publisher:before-starting-notes-20261027`. Normal immutable
editorial snapshots, staging release bundles, prior images and static trees
remain. Use the existing staging rollback procedure; code rollback does not
rewind an author's vault edits or publisher history.

The canonical blog and dothomelab checkouts retain their delivered branches.
The temporary local starting-note/baseline fixture was removed after preserving
screenshots. Unrelated artwork and documentation edits remain untouched. Main
and public production were not promoted or deployed.
