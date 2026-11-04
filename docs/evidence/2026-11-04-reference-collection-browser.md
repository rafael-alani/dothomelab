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
Live installation and Obsidian acceptance results are recorded below after checks.

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
