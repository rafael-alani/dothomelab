# Reference archive source and file audit — 2026-11-04

The archive is **not fully up to date with both sources**. Its 1,890 canonical
post identities and current memberships match fresh source observations, and
all 3,343 real stored objects pass integrity checks. However, one Yaay saved
carousel has 20 available images absent from the archive, and Yaay's rendered
board, section and post order differs from the installed picker. Zero pending
posts and completion receipts do not establish source completeness.

This supersedes the completeness claim in the earlier
[collection-browser baseline](2026-11-04-reference-collection-browser.md).
No inventory, receipt, media, annotation, daily due time, mount or production
runtime was changed by this audit. Reusable audit tools and this report are
delivered on `codex/reference-media-boards`.

## Evidence and coverage

Authenticated native Chrome was used for Instagram Saved/Grind and the disputed
original. With explicit user authorization, the existing authenticated collector
Chrome profile was also used in isolated audit mode, under its worker lock.
Ordinary native Chrome was logged out of Yaay; the collector profile was logged
in and provided both complete pagination and rendered UI access. No current
source authentication or rate-limit failure prevented the scans.

Fresh inventory collection ran 21:14:39–21:37:28 CET on November 4; a clean Yaay
repeat ran 21:37:28–21:37:57. All 66 Yaay boards were subsequently inspected,
including a resumed pass for initially timed-out boards. The final All saved
grid inspection ended at 21:54:45 CET. These are observations over an interval,
not an atomic snapshot of two independently editable services.

Private sanitized evidence is retained under
`/Users/rafael/Library/Application Support/dothomelab-references/reconciliation/`:

| Directory/file | Evidence |
| --- | --- |
| `20261104-independent-audit/instagram-observed.json` | Every Instagram item, native carousel member, collection, membership and observed grid position |
| `20261104-independent-audit/pagination.json` | Original page/cursor ledger, including an observer teardown error described below |
| `20261104-independent-audit/pagination-final.json` | Instagram pages from the first scan and Yaay pages from the clean repeat, with provenance |
| `20261104-independent-audit/server.json` | Read-only SQLite ledger and exhaustive file/hash/probe results |
| `20261104-independent-audit/frames.json` | Per-video first-frame decode results |
| `20261104-independent-audit/comparison.json` | Every collection, identity, membership, receipt and pagination comparison |
| `20261104-independent-audit/ui-order.json` | Exact source/picker board, section and canonical post sequences, including unknown positions |
| `20261104-source-followup/yaay-observed.json` | Fresh complete Yaay native inventory |
| `20261104-source-followup/yaay-media-kinds.json` | Actual transport kind and URL availability per member; no transport URLs |
| `20261104-source-followup/yaay-ui-boards.json` | All 66 rendered boards, 195 sections and 676 membership instances |
| `20261104-source-followup/yaay-ui-saved.json` | All saved canonical identities/order and the unavailable card |
| `20261104-source-followup/post-*.json`, `saved-copy-*.json` | Targeted original metadata and in-memory saved-copy hashes/sizes |

The server evidence SHA-256 is
`7b21e63c7f22c4871b55033c2a11a95655d3ae8d50f4c0d0502b6e936db3911c`;
frames `1153d4ebbb759e0e05b8a02964e28cb5b2a35b6b3bf67a3873bc8d240e21c3ef`;
comparison `75ce6a5c5707618ddb51b1c9ffa5b58b51c95efb70c82e06bdfa75155d0abe55`;
UI order `970b44d81577725ec00a6c3126da893d3e246f26e9f385af7b8020e07240a5d7`.
Credentials, cookies and signed media URLs are not included in these reports or Git.

## Identities, membership and pagination

| Source | Native saved records | Unique canonical posts | Collections | Membership instances |
| --- | ---: | ---: | ---: | ---: |
| Instagram | 1,254 | 1,254 | 28 | 2,522 |
| Yaay | 691 | 685 | 263 | 1,390 |

The union is **1,254 + 685 − 49 = 1,890 unique posts**. The earlier calculation
using 691 Yaay records and 55 overlaps mixed records with unique identities.
Six Yaay keys each have two distinct saved records: `DZWWsStpYJK`, `DYUMse2Tchk`,
`DYxNb-DoiNy`, `DXhaKtbAChF`, `DY9TLI5xesS`, `DVWbv4sDMQm`. These native records
and their membership instances are preserved; they are not six missing posts.

Instagram: 100 API pages across All Posts and 26 named collections, with connected
cursor hashes, explicit terminal pages and no loops. Every one of the 27 grids
matched API post identities and order. The 28th collection is derived Unfiled.
All Posts contains 1,251 posts; `DEZ3KqvMH8d`, `DIOmhyWAnmc`, `DNni3wTvgYs`
occur only in named collections and remain included in the 1,254 unique total.
Fresh native member IDs, member order and media types match stored Instagram
metadata. Receipt member counts, contiguous ordinals and file types match it.

Yaay: one complete board page and seven saved-item pages (600 + 91 records),
with connected cursor hashes and explicit termination. The 263 collections are
66 boards, 195 sections, All saved and Unfiled. There are 691 All saved, 676
board/section and 23 Unfiled membership instances. Every native ID, canonical
identity, collection relationship, membership instance and stored weight matches
fresh source data. Across both sources there are zero new or absent stored items,
missing/stale/reactivated memberships, removed collections or changed native
media metadata. No absent historical membership records were present to test
against a historical source snapshot; this audit establishes the current state.

All 66 Yaay boards and all 195 sections were inspected in the rendered source,
including 15 empty sections. All 676 card instances were accounted for.
Thumbnail identity resolves 194 sections completely to canonical post keys;
four sections with duplicate native candidates resolve because those candidates
share the same canonical key. Photography/Ungrouped retains two opaque
`Not found` positions. Their native membership identities come from the source
API, not from an invented UI identity. The All saved grid reached a stable end:
684 identifiable unique posts in matching order, plus one `Not found` card
after 221 known posts; no extra canonical keys. Unfiled is reconciled from the
complete membership graph.

## Missing Yaay saved variant despite completion

Post `instagram:DXrGxfkGShq`, Yaay saved ID
`019ddb2c-426a-71a0-9ada-4703fffea9da`, belongs to Japan inspiration/Ungrouped
(`g:019dd7be-f667-7aa2-938e-7375f44a4929`) and All saved (ordinal 663).

Yaay retains **20 image members**: the saved ID at ordinal 0 and
`instagram-post-DXrGxfkGShq-1` through `-19`. All 20 were read into memory from
their current source URLs: HTTP 200, JPEG signatures, **3,948,690 bytes total**.
None of their 20 SHA-256 values exists among the server's objects. The exact
ordinal/hash/size list is `saved-copy-a1b7f2ce5a331f17.json`.

The current Instagram original has **two images**, native IDs
`3885228362708900523` and `3885228366014015278`. Native Chrome independently
confirmed the two-image carousel and edited caption. The archive's completed
receipt contains only these two image assets:

| Ordinal | SHA-256 | Bytes |
| --- | --- | ---: |
| 0 | `3b4fd6219a871e9dea99c3113a13030e31556ed917b8903e7daa5ed78ecca5e5` | 1,359,186 |
| 1 | `7207922efe8aef0a3c2a42d006dd648936cb625b4b6e9cbc2584b8cdb62b95d0` | 1,029,166 |

This is an unarchived Yaay saved version, with an 18-member count shortfall
relative to that version. All 20 saved-copy byte sequences are absent; exact
visual equivalence between recompressed copies and the two originals was not
established. It is not evidence that today's two-image Instagram original was
partially downloaded.

The cause is visible in `worker.acquire`: successful Instagram retrieval wins;
Yaay is only a fallback after a download error. `Archive.pending` excludes any
canonical key with a completion receipt. `complete_post` uses `INSERT OR IGNORE`
and validates provided asset links, not source-version completeness. Consequently
daily catch-up and `--finish-backfill` will continue to skip this completed key.

There is **no safe existing command that repairs this defect**. Repair requires
origin/version-specific member bindings and receipt revalidation, followed by
targeted acquisition of the retained Yaay variant. Preserve the two original
assets, their annotations and existing receipt history. Deleting receipts or
overwriting ordinal links is not an acceptable repair command.

## Unavailable Yaay record with an available original

`instagram:Dbl5BhKDB0RpDoZOuAnzgLgEYvzLdR-BuiuX8s0`, Yaay ID
`019fc9f8-a15d-7df1-a5be-5b48ad1098d4`, is explicitly `not_found` in Yaay and has
no downloadable media or thumbnail URL. Its two Photography/Ungrouped
memberships (`g:019de228-bdf5-7762-9e18-48a84fc9ab71`) render as `Not found` at
zero-based section positions 3 and 4; All saved contains its record at ordinal
222. The generic `external_video` placeholder does not establish a video type.

Fresh Instagram original metadata returns **14 members: 13 images and one video
at ordinal 13**, matching the archived receipt's member count/order/types. The
original's files pass the exhaustive checks. This explains the second raw
receipt-count discrepancy in `comparison.json`: it is an unavailable Yaay stub,
not evidence that the complete Instagram original is missing 13 downloads.
The unavailable saved version cannot be independently verified or reacquired
until Yaay exposes its media again. Authentication renewal would not fix a
source record explicitly marked unavailable.

## Source ordering differs from the picker

Matching Yaay weights did not establish UI order: 86 sections contain tied
weights. Rendered source sequences were compared against the actual installed
`obsidian/model.cjs` behavior, including its canonical-key tie breaker.

- The 66-board root sequence differs (the rendered source reverses the API
  inventory sequence).
- **30 boards** have a different section sequence.
- **66 sections across 24 boards** have a different known-post sequence.
- No fully identified section has a canonical-post membership difference.
  Photography/Ungrouped's two unknown positions remain explicitly unverified;
  its identified subsequence still proves an order mismatch.

The boards with section-sequence differences are Photography, Dance, China
inspiration, Cooking, Japan inspiration, Bebe, Top X, Videography, Wedding
Videography, House, Job, Couple Photgraphy, Kids, Style, Guitar, China 2, Design,
Cinematography, Argentijns, Workout, Language learning, Home, Norway, Arab
Peninsula, Use Everything Quisling, Sports, Transformation, Street Photography,
Spain and Germany. Exact board/section IDs and both sequences are in
`ui-order.json`; names preserve source spelling.

For example Japan inspiration/Hiking
(`g:019ee3a1-21da-7b13-a744-73407f2ac94e`) renders
`DZji4SPpOP6, DZuv3g6mPFG, DbFLWCfkf93, DcQxwn9pHYz`; the picker gives
`DbFLWCfkf93, DcQxwn9pHYz, DZji4SPpOP6, DZuv3g6mPFG`.
This requires recording authoritative rendered positions, or verified source
ordering fields, rather than treating tied weights plus alphabetical keys as
source order. A normal refresh of the current collector reproduces the defect;
there is no existing order-repair flag.

## Stored files, receipts and readability

SQLite was opened read-only; `quick_check` returned `ok`. The snapshot contains
3,344 assets, 1,946 source items, 3,348 post/asset links, 1,891 completion receipts,
113 scans, 3,913 memberships and 292 collections, including calibration.

Excluding calibration, exhaustive filesystem checks found **3,343 objects,
1,804 MP4 videos, 1,539 JPEG images, 14,170,134,634 bytes**. Every real object's
SHA-256 matches its content address and basename; size matches the ledger;
paths stay under the object root with no symlinks; files are mode `0444`; JPEG
and MP4 signatures match the recorded kinds. No objects are missing or untracked,
no receipt links are missing, no post/asset links fall outside their receipts,
no real post lacks a receipt, and the incoming area contains no partial files.
Four content objects are shared across post references, giving 3,347 real
receipt-member links rather than 3,343 distinct objects.

All **1,804 real videos** pass FFprobe stream/duration inspection and independently
decode a first frame to 16×16 RGB (768 bytes). Their durations total
68,852.157593 seconds. Existing Jellyfin FFmpeg/FFprobe 8.1.3 in CT112 performed
these checks over stdin; no software, container or media mount was added.
This establishes container/stream and initial-frame readability, **not full-file
frame decoding, every seek point, audio integrity or visual equivalence to
every current source rendition**. Images received hash/size/signature checks,
not an exhaustive pixel decode. Receipt ordinals and media types do not supply
cryptographic native-member-to-file provenance; source-byte hashing was performed
for the disputed 20-member Yaay variant, not for every source rendition.

Grind `18071229254573049` independently has **45 posts, 40 videos, 29 images**,
69 files totaling 488,432,498 bytes and 3,481.521316 video seconds. Native Chrome
accumulated 12, 24, 36 and 45 distinct cards, then three stable non-loading end
observations. Its exact identities/order and carousel metadata match the fresh
collector and server; all hashes, video probes and first frames pass.

The separate calibration video
`469647f59e422610150988ffb1676d4a8f8a195ec0954b9bc7ec0bb699e9838b`
is 2,404,517 bytes and passes hash/probe/frame checks, but remains mode `0600`
(writable). It is excluded from every real total above and left unchanged.
It accounts for the sole `asset_failures: 1` in the server report.

## Installed revisions and daily-fetch health

| Component | Observed revision | Assessment |
| --- | --- | --- |
| Mac collector / LaunchAgent | `1839be6c5fe017425cff05f1c0b9134607247d5a` | Older marker; existing runtime Python files match review branch bytes |
| PVE forced-command archive endpoint | `8cfc162c2cb9e8d864ddd5f69cd385db881844eb` | Active authorized-key command points here; archive/transcribe/transcripts bytes match review branch |
| CT110 checkout marker | `db2f54f33797f0cb63879a1ca7f4a4a5527f230b` | Older infrastructure snapshot; not proof of endpoint implementation drift |
| Installed Obsidian plugin at final check | `97b2585a8b9c540a5dcac6530b5d785e9672245c` | Bundle, CSS and manifest match this review revision |

The branch and installed plugin advanced from `82c1b7d` through `933c3c2` to
`97b2585` through another task during the audit. Those changes were preserved;
the final UI comparison uses the current model. The audit helpers themselves
are new repository tools and were not installed as collector/server releases.
No deployment is justified merely to align revision labels where bytes match.

`media.rafael.reference-collector` is loaded/enabled, RunAtLoad, interval 600
seconds, last exit 0. It is normally idle while `phase` is `waiting for daily
catch-up`. Last attempt: November 4 19:49:47 CET; last success: 19:52:15;
next due: **November 5 19:42:33 CET**. Pending and retry counts are zero; current
issues and retry maps are empty. The audit left these values unchanged and
released its browser/worker lock. The schedule is not overdue, but its success
does not detect the already-completed saved-variant defect.

Historical source failures remain visible: Instagram scans
`a70d9f1d-2b90-4e45-a6e1-67b18ba52ff7` (November 3 09:58:11 CET),
`ac35673d-0803-4546-9a11-66602d070bcc` (10:11:45), and
`91861f90-98de-4015-af8a-a2676747bb2f` (10:23:35) are failed with empty gap arrays;
their causes cannot be recovered from those receipts. Yaay UI-verification
scans `e51e0aac-9dac-4f0e-9bf0-a7239081dd5c` (November 2 14:30:08) and
`7bc59c85-3233-4578-8cef-bf1990f95560` (November 4 09:18:10) are partial.
Later complete scans supersede them. The 113 stored scans comprise Instagram
62 partial/7 complete/3 failed, Yaay 2 partial/38 complete and one calibration
complete scan. Partial pagination checkpoints alone are not fetch failures.

Two audit instrumentation failures were corrected before conclusions: the first
FFprobe pass inherited a buffered file descriptor offset and falsely failed
every probe; a corrected exhaustive pass plus an offset regression test passed.
The first Yaay observer attempted an irrelevant/teardown response body after
inventory completion. Capture was restricted to advancing inventory page
counters, and the clean repeated eight-page Yaay scan has no capture errors.
Neither event is reported as archive corruption or a source-fetch outage.

## Reproduce and resolve

Run from the canonical checkout. These commands create a new private audit
directory, read the authenticated sources, inspect the server, and compare
evidence without submitting inventories or downloads:

```bash
reference_support="$HOME/Library/Application Support/dothomelab-references"
reference_audit="$reference_support/reconciliation/$(date -u +%Y%m%dT%H%M%SZ)-audit"
"$reference_support/venv/bin/python" clients/reference-media/audit-sources.py \
  --support "$reference_support" --output "$reference_audit" --yaay-ui
ssh root@192.168.0.250 -- python3 - --probe-videos \
  < hosts/infra/reference-media/audit.py > "$reference_audit/server.json"
ssh root@192.168.0.250 -- python3 - --decode-first-frames-only \
  < hosts/infra/reference-media/audit.py > "$reference_audit/frames.json"
python3 clients/reference-media/audit-compare.py \
  --server "$reference_audit/server.json" \
  --observed "$reference_audit/instagram-observed.json" \
  --observed "$reference_audit/yaay-observed.json" \
  --pagination "$reference_audit/pagination.json" \
  --yaay-media-kinds "$reference_audit/yaay-media-kinds.json" \
  > "$reference_audit/comparison.json"
node clients/reference-media/audit-ui-order.cjs \
  "$reference_audit/server.json" "$reference_audit/yaay-ui-boards.json" \
  > "$reference_audit/ui-order.json"
```

The server check exits nonzero for findings, including the excluded writable
calibration object; inspect its per-object errors instead of discarding JSON.
To recheck the available saved variant and today's original without storing media:

```bash
"$reference_support/venv/bin/python" clients/reference-media/audit-sources.py \
  --support "$reference_support" \
  --output "$reference_support/reconciliation/$(date -u +%Y%m%dT%H%M%SZ)-variant" \
  --source yaay --hash-yaay-post instagram:DXrGxfkGShq \
  --post https://www.instagram.com/p/DXrGxfkGShq/
launchctl print "gui/$(id -u)/media.rafael.reference-collector"
```

Resolution needs reviewed code changes for variant-aware completion and exact
source ordering, then explicit targeted acquisition and these same checks.
There is no honest one-line repair for either confirmed defect in the installed
implementation. No destructive SQL reset, bulk redownload, permission rewrite
or deployment was performed as a substitute.

## Preservation, validation and remaining limits

The Mac Media SMB mount remains read-only; CT110 Media reports `read only=Yes`,
`oplocks=no`, `level2 oplocks=no`. CT112 retains its read-only shared-media mount
and Jellyfin's Docker media mount is read-only. No playback configuration,
immutable asset or annotation was changed. External-network/sleep-wake playback
and a fresh full Obsidian playback acceptance were not part of these file checks.

Checks passed: 24 server Python tests, 34 client Python tests, 20 Obsidian model/UI
tests. These include regression coverage for cursor termination, misleading
completion receipts, file corruption/path safety, buffered descriptor offsets
and equal-count ordering drift. Audit scripts are repository-owned; private JSON
is evidence, not the only copy of a maintained helper.

No test containers, images or service deployments were created. Observed CT114
build cache is 21.07 GB and CT115 9.7 GB; no unrelated cache or retained release
was pruned. Existing worktrees, dirty documentation and untracked historical
reports were preserved. The old client `download-9yfrwmu6/failure.json` remains
as a pre-existing collector diagnostic, pending its owner's review. Private audit
evidence is retained for repair verification; remove it only after the findings
are resolved and their replacement evidence is accepted. Browser sessions and
the audit lock were closed. No service inventory changed, so no Pulse/Homarr
enrollment was required; this audit does not claim a new fleet monitoring check.
