# Reference Boards collection browser — 2026-11-04

## Diagnosis and source reconciliation

The canonical checkout started on `codex/public-blog-tunnel` at `bf8f9f0`, with
five unrelated documentation files changed/untracked. Verified recovery branch
`recovery/reference-picker-before-20261104` (`cf399247e1dcbfa382b60d85b10d4ddfb5cc514e`)
preserves those bytes. Restore a file using `git show <ref>:<path>`; do not reset
the working checkout. The reference review branch was fast-forwarded to retain
the already-published blog work. No task worktree or main promotion was created.

Installed revisions inspected before changes: plugin `8b0c7f4`, Mac collector
`54e118a`, PVE native endpoint `fb5814f`, Infra guest archive `db2f54f`.
Obsidian 1.15.0 was open on the existing Excalidraw example. Its live picker
reproduced independent memberships concatenated as fake hierarchy, fuzzy search
admitting unrelated posts, and repeated carousel files without thumbnails.

The retained Instagram scan completed at **11:56 CET** with 38 current members
of collection `18071229254573049` (Grind). Exactly 32 had archived media: 56 files,
27 MP4s and 29 JPEGs. `instagram:Da83Lq5klTx` was not a Grind member; it was one
cross-source post with ten JPEGs in other collections.

An authenticated Chrome inspection independently accumulated the virtualized
Grind grid through 12, 24, 36 and 45 posts, reaching its non-loading end. A fresh
authenticated browser navigation to the same v1 collection endpoint used by
gallery-dl returned four pages of **12 + 12 + 12 + 9** and explicit terminal
`more_available: false`. Its 45 source keys matched the visible grid in exact
order. Native IDs were preserved as strings, avoiding JavaScript's 64-bit
integer rounding. All 45 media types were checked against the source response.

The seven omissions are the first seven videos, all by `youraveragetechbro`.
They were absent from the entire retained Instagram inventory, not merely from
Grind membership or archived assets. The remaining 38 identities match the
source order exactly. The current source API does return the seven: the available
evidence does **not** establish whether the older collector session received a
transient/session-dependent response or the collection changed during its scan.
It does establish that root enumeration plus terminal API pagination was
insufficient evidence of collection completeness. The old completion flag did
not compare individual collections with the UI; the new collector does.

The collection contains **40 single-video posts, one single-image post and four
image carousels** (7, 5, 9 and 7 members): 45 posts and 69 expected media members.
Source collection order differs from publication order (for example positions
8 and 9 are not newest-publication-first). No saved-at timestamp was observed;
"Source collection order" is intentionally not labeled saved-date chronology.
The plugin's chronological choices use source publication timestamps only.

## Implementation and focused checks

The native Obsidian modal selects exact source and collection IDs, groups by
canonical `source_key`, retains all memberships, and searches only the selected
contents. A separate removed-membership view preserves history. Local thumbnails
lead to a paused native media preview, ordered carousel members, seek controls,
and explicit full-video/excerpt selection. Picker, editor and existing board
players share one playback coordinator. Closing or changing a preview releases
its source. Offline errors keep metadata and thumbnails visible and disable
adding unavailable media. No full-video cache or separate web application exists.

Catalog export adds completion receipts and per-collection audit evidence;
publishing adds pending/partial/retry state without changing immutable asset
IDs, note markers or project files. Existing board annotations and independent
excerpt notes retain their original contract. The collector still uses its
existing ten-minute initial backfill and daily-mode due-time guards.

Tests exercise exact filtering before search, pending and historical posts,
cross-source identity merging, carousel order, genuine hierarchy, publication
ordering, immutable references/annotations, actual Add reference command flow,
thumbnails, paused starts, seeking, single-player coordination, close/switch
cleanup and offline status. Python tests cover source/UI reconciliation and
completion receipt export alongside existing acquisition/scheduling tests.
Live installation and Obsidian acceptance results follow the source ledger.

## Source-order ledger

This is the reconciled source observation, with acquisition at initial inspection.
"Pending" means no archived media was present; it does not assert a deleted or
unavailable original. All URLs are `https://www.instagram.com/p/<code>/`.

| Position | Instagram shortcode | Source media | Archived files | Acquisition |
|---:|---|---|---:|---|
| 1 | `DesEIfyTofn` | video | 0 | Pending |
| 2 | `DeerQcfxN_T` | video | 0 | Pending |
| 3 | `DePGBFXtswr` | video | 0 | Pending |
| 4 | `DeHphfnxfZg` | video | 0 | Pending |
| 5 | `Dd4EU7ORjOK` | video | 0 | Pending |
| 6 | `DdrDDY6Rf4h` | video | 0 | Pending |
| 7 | `Ddjc038x7YX` | video | 0 | Pending |
| 8 | `DcA4Tpgy0V6` | video | 0 | Pending |
| 9 | `DdHF6x-IpfH` | video | 0 | Pending |
| 10 | `DcK8GpMuSNH` | video | 0 | Pending |
| 11 | `DcJiRCrTlG1` | video | 0 | Pending |
| 12 | `DcKmuUnsHPE` | video | 0 | Pending |
| 13 | `DcIBg7IzmVO` | video | 0 | Pending |
| 14 | `DZAMbJIJoBw` | video | 1 | Media present |
| 15 | `DaIyqCvRCq5` | video | 1 | Media present |
| 16 | `DW4gJODCMmA` | video | 1 | Media present |
| 17 | `DYpAgj2t3WJ` | video | 1 | Media present |
| 18 | `DZH-KyfT6oF` | video | 1 | Media present |
| 19 | `DZQjALBBMEK` | video | 1 | Media present |
| 20 | `DZrDwB_PCXv` | video | 1 | Media present |
| 21 | `DWL-z4IkQWr` | video | 1 | Media present |
| 22 | `DZddnLvOmMC` | video | 1 | Media present |
| 23 | `DY1HS5SP83v` | video | 1 | Media present |
| 24 | `DWdtVyHykKh` | video | 1 | Media present |
| 25 | `DZIpQTsyT25` | video | 1 | Media present |
| 26 | `DYi61fzMHK8` | video | 1 | Media present |
| 27 | `DXwGePYDawL` | image | 1 | Media present |
| 28 | `DXmRB9ugf_5` | video | 1 | Media present |
| 29 | `DWoYaIxDWJD` | video | 1 | Media present |
| 30 | `DXPA_9ejgzT` | video | 1 | Media present |
| 31 | `DW1mOfJDaM6` | video | 1 | Media present |
| 32 | `DUPi-Zbja1d` | video | 1 | Media present |
| 33 | `DTrTp5LDsnh` | video | 1 | Media present |
| 34 | `DT_qgP8iKbO` | 7-image carousel | 7 | Media present |
| 35 | `DPqHlRxjVe8` | video | 1 | Media present |
| 36 | `DS0lL7AE6BI` | video | 1 | Media present |
| 37 | `DTJG8XLDPy-` | video | 1 | Media present |
| 38 | `DSiJAQVkfCC` | video | 1 | Media present |
| 39 | `DRa-K1WlYyQ` | video | 1 | Media present |
| 40 | `DSDc-7sDMvx` | video | 1 | Media present |
| 41 | `DQvjMPCCEb5` | 5-image carousel | 5 | Media present |
| 42 | `DS-tKw8CCZZ` | 9-image carousel | 9 | Media present |
| 43 | `DRFcDv4iBeU` | 7-image carousel | 7 | Media present |
| 44 | `DReG_R0ES8K` | video | 1 | Media present |
| 45 | `DQLYYrUCOX_` | video | 1 | Media present |


## Installed workflow acceptance

The tested plugin and collector were installed from committed releases, with
exact bundled JavaScript, stylesheet and Python-byte comparisons. The initial
PVE endpoint `861e502` was subsequently updated by the coordinated agent-context
work to `8cfc162`, preserving these collection changes. Its installed `archive.py`
matches the combined branch. Infra's unrelated guest archive remains
`db2f54f33797f0cb63879a1ca7f4a4a5527f230b`.

Native Obsidian 1.15.0 acceptance used the existing vault, Material Gruvbox theme,
Excalidraw 2.27.3 and Media Extended 4.2.9. Chrome supplied the authenticated source
observation. Checks performed through the actual application:

- Excalidraw → Add reference → Instagram → Grind showed exactly 45 posts in
  source order. The local catalog order equals all 45 observed source keys.
  Searching the samurai shortcode inside Grind returned zero results.
- All Posts showed the samurai once, with ten ordered images. Independent
  Instagram All Posts/Unfiled and Yaay All saved/Photography/Cinematic memberships
  appeared as separate bullets. Grind's `DS-tKw8CCZZ` showed one nine-image post;
  selecting its ninth member displayed that image.
- Thumbnail and detail layout were inspected in screenshots. This exposed and
  fixed Obsidian compressing grid rows; the installed fix renders full-height
  cards with readable captions/status. Pending media had explicit placeholders.
- Video previews started paused, played before selection, and sought using the
  native scrubber. Switching posts started the next preview paused. Full video
  and a separate 3–7 second excerpt of `DY1HS5SP83v` were added to the acceptance
  drawing. Excerpt preview stopped at seven seconds; full-video bounds were
  0–173.914603 seconds. Both cards reference the same immutable original.
- The original board's annotations, full video and independent excerpts rendered
  and played. Starting a second board player paused the first; starting a picker
  preview paused board playback; closing the picker left all players stopped.
  Repeated plugin hot reloads temporarily left Excalidraw embeds blank even with
  Reference Boards disabled. Saving and reloading Obsidian restored the embeds;
  the preceding playback checks then passed. No Excalidraw upgrade was performed.
- Offline acceptance temporarily set only Reference Boards' archive path to a
  nonexistent volume. Thumbnails/metadata stayed visible, the preview reported
  the missing archive, and Choose was disabled. The normal
  `/Volumes/Media/references` setting was restored and playback rechecked.
- Hash comparison against 17 original board/project files found only Waypoint's
  `Projects.md` index changed to list the two new acceptance notes. Original
  boards, cards, annotations and excerpt markers were unchanged. No MP4 files
  exist under vault `References`; local vault/Syncthing paths are unchanged. The
  later SMB playback repair below preserves the same read-only mount.

The retained review artifact is
`References/Board acceptance/Collection browser — November 4.excalidraw.md`, with
its two `Collection browser — November 4.excalidraw — Grind acceptance …` project
notes. Rafael owns these review examples; remove them through Obsidian only when
no longer useful. The baseline hashes and sanitized source observation/report
are retained under the private support directory's `reconciliation/20261104/`.

## Acquisition completion follow-up

Rafael explicitly requested finishing retrieval, then expanded that request to
the entire Instagram/Yaay library. The 13 initially pending Grind posts were
queue entries, not evidence of unavailable originals. A scoped acquisition
selects exact current membership and skips unrelated inventory work without
changing the daily due time. The ordinary background batches had acquired two
more posts before that run; the scoped run completed the rest.

**All 45 Grind posts now have completion receipts: 69 files, including all
40 videos and 29 JPEGs.** Server-side verification read all 69 objects, totaling
488,432,498 bytes, and checked SHA-256 against immutable IDs, stored sizes, safe
paths and non-writable permissions. No mismatch or missing file was found. All 40 MP4s also passed server-side
FFprobe checks for a video stream and positive duration (3,481.5 seconds total).
The Mac command process could not read the mounted volume despite escalation;
verification therefore streamed the objects locally on PVE into the existing
Jellyfin FFprobe over stdin. No software, mount, container or video cache was
created.
The source ledger above intentionally preserves the initial acquisition snapshot;
its former Pending entries have all since been acquired.

Whole-library completion uses an explicit `--finish-backfill` operation. It
finishes source pagination and attempts every pending original once, including
prior failures, while retaining access/rate-error stopping rules and the normal
daily schedule. Failure evidence contains only HTTP codes and expected/actual
file counts, never response bodies, credentials or signed CDN URLs. The completed
run and final acquisition audit follow.


The subsequent full Instagram scan completed 100 API pages and reconciled all
26 named collection grids without API/UI identity disagreement. Grind's automatic
grid audit independently confirmed 45. A later independent Chrome accumulation
of the All Posts grid found **1,251 posts in exactly the API order**, with no
missing or extra identities. That verified audit is now published in the catalog;
future scans require it too. Three additional Instagram posts exist only in named
collections (`DEZ3KqvMH8d`, `DIOmhyWAnmc`, `DNni3wTvgYs`) and were retained.

Original-link API failures returned HTTP 400 with no metadata or files;
authenticated Chrome independently showed `DW_04YyI_ae` unavailable. The worker
previously always chose Instagram for an Instagram-shaped identity, ignoring
Yaay's retained copy. It now falls back to that same identity's Yaay media,
records `via` in the receipt and explains saved-copy provenance in the picker.
Numeric Instagram carousel suffixes are sorted numerically. Missing members
cannot receive a complete-post receipt; rate limiting still stops acquisition.

The final ten failures exposed a second bug: Yaay's CDN sometimes returns valid
media with no Content-Type or `application/octet-stream`. The worker now checks
file signatures, expected media kind and video-stream/duration metadata before
accepting those responses. HTML, thumbnails in place of videos, mismatched types
and invalid MP4s remain rejected. Username-prefixed Instagram links normalize to
the same canonical identity as `/p/<code>/`.

All ten saved copies were then retrieved:

| Instagram identity | Recovered Yaay media |
|---|---:|
| `DW_04YyI_ae` | 1 video |
| `DYeV5VTJAJD` | 1 video |
| `DYjfpICGYyt` | 19 images |
| `DZKNwDQP1o6` | 1 video |
| `DZdQcowBQYr` | 1 video |
| `DajJGs-uVNS` | 1 video |
| `DauwUvinShn` | 6 images |
| `Dbp5Cj_JTGh` | 1 video |
| `DcLx3bTsIIq` | 1 video |
| `DeZrE2phzDx` | 1 video |

Final inventory: **1,890 unique real source posts**, comprising 1,254 Instagram
and 691 Yaay posts with 55 shared identities. Every post has a completion receipt;
there are **zero pending/retry posts and no acquisition issues**. The real library
contains **3,343 files: 1,804 MP4s and 1,539 JPEGs**. The separate calibration post
adds one MP4; totals including it are 1,891 receipts and 3,344 objects.

Server verification read all 3,344 objects (14,172,539,151 bytes), checking SHA-256,
size, safe nonsymlink paths and non-writable permissions. All 1,805 MP4s passed
FFprobe video-stream and positive-duration checks; no failures were found. This
is an exhaustive acquisition/integrity check, not a claim to have watched every
video or decoded every frame. The first newly acquired Grind video was also
fully decoded with FFmpeg without error. The private per-object results are
`reconciliation/20261104/archive-verification-final.json` under the Mac support
directory. The source audits and all completion receipts remain available there
and in the archive catalog; private transport URLs and credentials are not in Git.

## macOS playback repair

New originals initially failed in the picker and native Media Extended while
an older video still played. The first new Grind object is 18,235,681 bytes and
151.2 seconds; server integrity and full decoding passed. macOS logged
`No SMB 2/3 fid found` and `READ failed ... 22` for its SMB handle. Saving and fully
restarting Obsidian, and then a normal unmount/reconnect, did not fix that failure.
Rafael confirmed Obsidian's Network Volumes permission was enabled. Codex's shell
had a separate macOS System Policy file-read denial; that is not evidence of a
missing archive object and remains a limitation on shell-side mount verification.

Setting only Media's `oplocks = No` and `level2 oplocks = No`, validating with
`testparm`, reloading Samba configuration and normally reconnecting the idle
mount restored playback. No guest restart, permission/ownership rewrite, signing
change, credential change or alternate cache was needed. This isolates the
observed failure to SMB handle-caching interoperability; the underlying macOS
implementation defect is not independently established.

Native Obsidian then loaded `DesEIfyTofn` at 151.2 seconds, initially paused,
played and sought through the scrubber before selection. Switching to
`DeerQcfxN_T` stopped it and loaded the next preview paused at 154.4 seconds.
Choose opened the full-video/excerpt editor with the correct bounds. Closing the
editor left board players stopped. Grind displayed **45 with media, 0 awaiting**.
The scoped Cockpit verifier passed; Samba's temporary diagnostic log level was
restored to zero. The existing reconnect LaunchAgent returned zero and the
mount remained read-only SMB 3.1.1 at `/Volumes/Media`.

Disabling opportunistic caching can reduce read performance. Rollback restores
the two previous defaults, validates, reloads configuration, then reconnects
Media only after players stop and the mount is idle:

```bash
ssh root@192.168.0.250 -- pct exec 110 -- net conf delparm Media oplocks
ssh root@192.168.0.250 -- pct exec 110 -- net conf delparm Media 'level2 oplocks'
ssh root@192.168.0.250 -- pct exec 110 -- testparm -s
ssh root@192.168.0.250 -- pct exec 110 -- smbcontrol all reload-config
diskutil unmount /Volumes/Media
launchctl kickstart "gui/$(id -u)/media.rafael.homelab-media"
```

The exact pre-change registry is retained, mode 0600, on CT110 at
`/srv/appdata/docker/infra-samba/reference-playback-before-20261104.conf`.
Do not import the entire snapshot over later unrelated registry edits. Rollback
can reintroduce the observed playback failure. The Git registry and focused
verifier carry the fix for clean rebuilds; no full Infra guest redeployment ran.

## Release checks and retained artifacts

Focused regression results: 30 client Python tests, 21 archive Python tests and
eight Node test cases passed. Coverage includes source completeness, fallback
validation, stable identities, collection filtering, carousel grouping, dates,
playback cleanup and existing-card compatibility. JavaScript syntax, shell
syntax, documentation links and whitespace checks also passed. Fixture results
are separate from the real Chrome/Obsidian acceptance described above.

Final live checks: Pulse reports all PVE guests and command-enabled Docker hosts
102/110/112/114/115; Homarr's six staging entries require no changes; all 35 shared
probes pass. Infra containers are running/healthy. No task container, network or
build was created. Existing unrelated CT114/115 build caches (21.07 GB/9.7 GB)
and current/previous releases were inspected and retained. No mount or storage
policy was changed to alter monitoring metrics.

The coordinated chat's agent-brief/transcription changes remain in the review
branch and installed plugin. Recovery branch
`recovery/reference-context-canonical-20261104` (`c6f1e90d`) retains its canonical
pre-merge snapshot. Neither this task nor its completion promotes to `main`.
Plugin rollback bundles, collector releases/config/plist backups and the Samba
registry snapshot are Rafael-owned rollback artifacts: retain through review
acceptance and until the preceding revision is no longer required. Restore
specific files/releases; do not reset the vault or remove immutable originals.
The reconciliation directory and acceptance drawing are retained evidence.

Duplicate temporary source reports, obsolete picker implementation scratch and
the unchanged `New-video playback check.md` diagnostic note were removed after
verification. This task created no duplicate worktree; the canonical checkout
retains the review candidate. Eight unrelated active/retained Codex worktrees
were inspected and left with their owning chats. Unrelated dirty documentation
and its recovery snapshots were preserved.

Daily fetching remains enabled with its pre-existing due time. There is no
full-video cache in the vault or collector downloads directory. The older
`download-9yfrwmu6/failure.json` (64 bytes, no media) predates this task and is
retained for its original diagnostic owner. Genuine external-network playback
and a sleep/wake cycle remain unverified, as recorded in the November 2 report;
no source/server access is currently blocking retrieval or local playback.
