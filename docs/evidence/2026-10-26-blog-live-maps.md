# Blog changes 111–113: live maps and readership

Verified on **2026-10-26**, from the operator Mac through PVE to CT110/114 and
the private staging browser. This task changes the blog's `staging` branch and
the existing homelab integration branch only. The independently activated public
blog remains on its accepted `8e2fcec638e48a9866a985647188f4cb626bb234` release.

## Delivered behavior

- Map indexes, notes and assets live under their article's `/maps/<collection>/`
  path. The publisher's appdata ledger owns readable note routes and former
  source-path aliases; normal vault notes receive no IDs. Original generated
  index/note links redirect to the article-contained addresses.
- All nine course wrappers now embed their original vault drawings. Recursive
  links, nested notes and attachments are selected automatically after Syncthing
  settles. Article filenames and folder names supply headings and menu labels;
  `_index` retains ordering and taxonomy identity. Existing article URLs remain.
- A content-only refresh switches a complete static tree and reloads nginx while
  retaining the web container. It still runs an automatic static build. Code or
  runtime changes use the existing normal deployment path.
- Umami receives note selections, activation, opens, actual readable viewport
  visibility, incremental visible/active milliseconds and completed episodes.
  The [readership report](../../hosts/apps/blog-observability/README.md#note-readership)
  combines counts, total seconds and mean/median completed visible episodes.

## Verification

Application implementation: blog `dc3c2574d61870a133e25d6c5fc8919be9d246c3`,
with final tests/docs in `81cbb673d8857bdee228fe1bc73fd8726cb4f62e`.
CT110/114 source archive: `6bb6a70194943ada0e17150342c04c74aa44a4d1`.
The initial live-map snapshot was
`2291cf3ca3807e7be90a54a7ebb01d8f5214797035dfd9c548b23bff8b87a2a1`,
with eleven drafts including the disposable sync probe and no published wrappers.

Local typecheck, all 84 blog unit tests and the static build pass. The real selected
vault graph also builds in an isolated context. Publisher tests pass (16), as do
editorial-adapter tests (5), staging deployment/rollback tests (10), and authoring
installer tests (2). Publisher lifetime tests pass (3), including preventing a
second writer after a detached Docker client and stopping only the named export
on timeout. Focused Chromium cases cover readable rendering and timing,
map controls, every course, and no-JavaScript reading. The former fixed count of
171 MDL notes was replaced with the actual generated collection length. A legacy
bookmark check then caught 78 formerly exported pages outside the nine current
drawing graphs. All still exist in the vault and are retained through wrapper
`map-include` links, including MDL's `00. Learning Goals`. Notebook attachments
referenced by those pages are available as downloads, never executed.

Four live Chromium cases pass against the new snapshot: all nine primary maps,
their standalone reading pages, heading-only About, real Umami collection and
DNT/blocked-tracker behavior. Ten new note events reached Umami in the focused
reading check. A follow-up verifies standalone-note navigation and its open event
in the database. Read-only aggregation confirms readable note URLs and
5.00-second visible/active episodes for the selected Bayes note and two other
readable overlapping cards. This is synthetic acceptance traffic, not readership
evidence about real visitors. DNT and blocked-tracker cases sent zero events.

The first content cutover exposed an nginx memory-limit failure: the 128 MiB
container used about 67 MiB with its 6,520-line redirect configuration, and a
concurrent `nginx -t` was killed by the container's memory cgroup (kernel-confirmed
exit 137). Automatic recovery retained the previous site but restarted its
container. The staging limit is now 256 MiB to accommodate validation and graceful
reload; the final no-restart acceptance is recorded below separately from this
failed first attempt.

The compatibility snapshot
`aa19d4d40740b13eb59ef8e0afbcd3565cb3388a6952e9a5c6837aa66b08a9b1`
was accepted at 22:34:07 CET with blog `81cbb67`. Container
`c23929e2bb9bc0cc9148a3c0fd47252860985a19aee8cb82543b8add24d744f6`
retained start time `2026-10-26T21:26:34.547836947Z` and restart count zero.
All 1,151 formerly exported Markdown source paths remain in the live collections;
one former hash URL per course, including MDL Learning Goals, redirects to its
correct article-relative page with HTTP 200. The full publisher run took 219
seconds; its execution budget is now ten minutes with a longer systemd deadline.
One already-running job subsequently reached its former 240-second client
timeout, while its detached container finished the timestamped snapshot. The
new runner detects an existing export before starting another and cleans up its
named container on timeout. No concurrent writer was observed. Three browser
cases passed again on the complete compatibility snapshot; a database query
confirmed three Bayes-note opens and populated mean/median fields from the
synthetic checks.

The final end-to-end edit used the Mac note
`Blog sync probe 111-113/one/two/three/four/five/Deep note.md`. Its exact timestamp
`2026-10-26T21:31:04.102Z` appeared at the private generated note URL after normal
Syncthing, publisher and staging timers. Accepted content digest:
`07d0a4b7bfc3987e5fb1cc3d9432af89a66b73a0f24bd2802f96c2a0291f9c10`.
Code remained `81cbb67`; the container ID, start time and zero restart count above
all remained unchanged. No manual deployment or service start advanced that edit.
The hash-checked probe cleanup then removed its three owned Mac files and empty
test directories; its manifest remains in `.blog-publisher-backups/live-sync-111-113/`.
The cleanup export completed successfully with ten drafts, zero published wrappers
and digest `698ff1312e8281e2f1cff0d0fc8313e2bfa52d52610289c9ba4320c7c601a016`.
That snapshot was accepted at 22:50:13 CET, again with the same container lifetime.
The probe article, canonical index, canonical note and former generated index all
return HTTP 404. The original Learning Goals bookmark still redirects to its
readable canonical page with HTTP 200. Disposable local export/build fixtures
were removed; canonical checkouts and unrelated local edits remain intact.

## Source gaps and measurement limits

Three original vault targets are absent and render explicit unavailable cards:

- Applied Image Processing: `05. Model Optimization Based approach`.
- Applied Image Processing: `0. Whiteboard/DSAIT/02. Q2/4120. Applied Image Processing/00. Exam Review`.
- Computer Vision, from `03. Normalisation Techniques.md`: `Normalising Learned features`.

The old copied export had substituted other targets. The new exporter reports the
missing originals in `warnings.json` without rewriting those notes. PDF edition
ambiguities retain the prior export's selections through wrapper `map-links`,
including per-source choices where both editions are used.

Visibility is sampled once per second at the renderer's readable threshold,
clipped to the actual map/browser viewport. Overlapping readable cards can count
simultaneously. Active time pauses after 30 seconds idle; hidden tabs stop both
timers. Abrupt browser exit can lose the final interval/completed episode. The
mean/median report summarizes completed visible episodes, not proven reading or
all-time historical attention. Ordinary standalone note pages retain pageviews.
No physical iPhone test, backup restore or deliberate manual rollback was
performed. Automatic rollback was observed during the memory-limit failure.
An unembedded note renamed and edited in the same cycle may need manual alias
repair: without source IDs, the ledger cannot guarantee recognition when neither
its path, drawing anchor nor content hash survives.

## Retained recovery inputs

Both guest source archives retain `/opt/dothomelab.before-blog111-113-20261026`,
`/opt/dothomelab.before-blog111-113-914e54b`,
`/opt/dothomelab.before-blog111-113-cc9a6c4` and
`/opt/dothomelab.before-blog111-113-fe8efbe`, plus
`/opt/dothomelab.before-blog111-113-97eea2c` and
`/opt/dothomelab.before-blog111-113-6bb6a70`; deployed markers identify their
source. CT110 retains publisher image
`dothomelab/blog-publisher:before-111-113-20261026` and original publisher
state/current under `blog/editorial/before-111-113-20261026/` in canonical appdata.
Staging retains previous release records, images, static trees and immutable
editorial snapshots. No rollback data, images or volumes were pruned.
Use the existing [staging recovery procedure](../../hosts/staging/README.md#recovery-inputs-and-limits)
with those retained inputs; restoring older source alone does not rewind the
publisher history or the chosen content snapshot.

The Mac vault retains created-wrapper manifest
`.blog-publisher-backups/maps-2026-10-26T20-51-31.067Z/created-files.json`,
authoring backups under `.blog-publisher-backups/20261026T215227573836/`, and
wrapper PDF-choice backups under `map-links-2026-10-26T20-59-49.871Z/` and
`map-links-2026-10-26T21-01-29.548Z/` within that same backup root. The additional
reading-page migration backup is `map-links-2026-10-26T21-19-57.799Z/`. Compare later
author edits before restoring files. The maintained migration and acceptance
tools live in `hosts/infra/blog-publisher/`; no maintained script exists only in
temporary transport directories. No task worktree was created.
