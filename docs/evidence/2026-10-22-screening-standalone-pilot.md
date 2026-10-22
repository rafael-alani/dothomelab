# Standalone screening pilot — 2026-10-22

This follow-up corrects the scope of the [October 21 preview](2026-10-21-screening-mvp-staging.md):
Film-introspect is a companion for a film playing elsewhere, including a cinema
or a friend's screen. Jellyfin is optional. The pilot catalog contains one real,
openly licensed film, **Sintel (2010)**, with its published English subtitles.
It does not claim lookup coverage for arbitrary commercial films or cuts.

## Source and rights verification

The Blender Foundation's [project page](https://durian.blender.org/about/)
identifies the finished film as 14 minutes 48 seconds (888 seconds), directed by
Colin Levy, released in 2010. The official [Blender Video API](https://video.blender.org/api/v1/videos/0eb052d0-fd51-43e6-aa33-ecdbf77a5d40)
also identifies the full film and reports 888 seconds. This is not its trailer.

The [project sharing policy](https://durian.blender.org/sharing/) licenses the
published project data under CC BY 3.0. Attribution for reused project assets is
Blender Foundation with the project URL; screening the movie retains its full
credits. Logos and trademarks are excluded from the license. The
[official download page](https://durian.blender.org/download/) links Xiph's
Sintel materials. Xiph's [subtitle README](https://media.xiph.org/sintel/subtitles/README.txt)
explicitly identifies these subtitle files as Blender Foundation material under
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), with the same logo and
trademark exclusions. This provides subtitle-specific provenance rather than
assuming that a playable video also licenses an unrelated transcript.

| Asset | Verified source / properties |
|---|---|
| English SRT | [sintel_en.srt](https://media.xiph.org/sintel/subtitles/sintel_en.srt), HTTP 200, 1,514 bytes, UTF-8 |
| Subtitle SHA-256 | `4ed7e1f1bc5ff69fe33606960e4c048ba6766237bf33b132fef76e1a92cb64b2` |
| Subtitle intervals | 26 cues; ordered, positive intervals; first 107.250–110.500 seconds, last 626.200–629.800 seconds |
| Film reference | [Official Blender video](https://video.blender.org/videos/watch/0eb052d0-fd51-43e6-aa33-ecdbf77a5d40) |
| Direct video | [Official 480p MP4](https://video.blender.org/object-storage/web_videos/0eb052d0-fd51-43e6-aa33-ecdbf77a5d40-480.mp4), 119,976,502 bytes |
| Encoding | [Official file metadata](https://video.blender.org/api/v1/videos/0eb052d0-fd51-43e6-aa33-ecdbf77a5d40/metadata/292): H.264, 1126×480, 24 fps, AAC stereo; start time 0; container duration 888.117 seconds, video duration 888.041667 seconds |
| Streaming probe | `GET Range: bytes=0-1023` returned 206, `video/mp4`, `Accept-Ranges: bytes`, correct total size and `Access-Control-Allow-Origin: *` |

The subtitle's first cue, “This blade has a dark past,” is at 1:47.250–1:50.500.
The next starts at 1:51.800. These supply concrete alignment checkpoints for the
real-film browser test. Matching title, release duration and source provenance
support the selected edition; they do not independently prove every cue's
alignment. The final browser checks below distinguish that additional evidence.

The researcher fetched the small subtitle/metadata files and a 1 KiB video
range only. No full movie was downloaded and no full-video checksum is claimed.
The former `download.blender.org/durian/subtitles/sintel_en.srt` URL returned 404;
the original Durian WordPress asset returned 403. The verified Xiph subtitle
copy and current official Blender Video source avoid those unavailable paths.

## Deployment contract

Meta Egg's Docker image bundles its one-film manifest, licensed subtitle and
attribution; `SCREENING_ONLY=true` and `SCREENING_PROVIDER=catalog` are explicit
in the homelab Compose definition. No Jellyfin account, API token, external
catalog service, filesystem mount or runtime subtitle download is required for
searching the pilot and reading its timed text. The reference film remains on
Blender's public video service; playing it needs access to that external host.

Film-introspect reaches Meta Egg through the existing private service endpoint.
The user selects the matching film/cut and starts or aligns a local screening
clock with the separately playing film. Focusing a note holds its timestamp and
subtitle view while that clock advances; saving keeps the original timestamp
and returns the subtitle view to the current clock. A manual clock can drift,
and does not infer an external player's start, pauses, seeks or edition.

Existing Jellyfin environment keys and the restricted-account initializer are
retained only for a deliberate optional integration. No administrator credential
was read, account provisioned, deploy key deleted or existing data removed for
this standalone pilot. Prior direct-Jellyfin and Meta Egg note timelines remain
separate. Existing release generations and private routing remain in place.

## Installed revisions and checks

The operator verified the standalone pilot on October 22 from the operator Mac
and CT114. The private previews are
[Film-introspect](https://film-introspect.staging.rafael.media) and
[Meta Egg](https://meta-egg.staging.rafael.media).

| Component | Verified revision |
|---|---|
| Homelab runtime configuration tested | `71321d1e567af9d6e6bc6a8e4cd5e0ee9b5dd615` |
| Meta Egg | `7b5a53f833939a8d5da9a7d22c1459cc0b992f2a` |
| Film-introspect during the continuous-play test below | `cb2cab9d0a40080d50dbb95b13fdd52e03340d9d` |
| Film-introspect final installed preview | `8b909f0d8f7506c369b7f35e312f26604551fdec` |

The final Film-introspect revision adjusts button wrapping and user-facing
labels. After its deployment, a fresh browser session reopened the same Sintel
cut and retained the note text and its 1:56 timestamp. This report is a subsequent
documentation revision of the tested homelab configuration.

Meta Egg passed 44 tests and two compiled HTTP smoke checks. Film-introspect
passed 18 tests, catalog and Jellyfin provider smoke checks, and its production
build. All five registered staging app verifiers passed and the branch poller
timer remained active. These checks do not constitute a live Jellyfin test.

## Real-film note and catch-up test

The native browser played the official full-film URL listed above and reported
a duration of **888.092993 seconds**. Through Film-introspect's UI, the operator
searched for Sintel, selected its official full-film edition and English track,
and opened a screening. Meta Egg supplied the matching metadata and 26 timed
cues. The operator sought the reference video to **104.553884 seconds**, started
playback and aligned the companion clock through the manual sync control.

| Checkpoint | Reference video clock / state | Film-introspect observation |
|---|---|---|
| Initial running clock | 110.737578 s, playing | 1:50; no active subtitle during the gap after cue 1 |
| Focus Quick note | 116.709002 s, playing | Note captured 1:56 |
| Continue typing | 129.791448 s, playing | Running clock 2:09; note still held at 1:56, with the same cue window (cues 2–4) |
| Save & catch up | 140.397750 s, playing | Clock 2:20; saved note retained 1:56; active cue 9 matched its 138.000–142.200 s interval |
| Continued live following | 153.819515 s, playing | Clock 2:33; active cue matched its 152.950–155.870 s interval |

The active text at save was “Someone very dear? A kindred spirit?” and the later
cue was “I've been alone for as long as I can remember.” The reference video
was neither paused nor sought between the initial anchor and the final
153.819515-second check. The operator stopped it afterward at 172.607471 seconds.
Reloading the film library showed one Sintel note. The earlier direct-Jellyfin
note timeline was retained separately; its pretest live note count was zero.

A separate final-build UI check searched the dialogue for “This blade”, returned
1:47 and started the companion clock at 1:47 when the result was tapped, with
the first cue highlighted. This check did not involve the external video.
Control labels were fully visible at a 1280-pixel viewport; the wrapping fix
was inspected in source, but a narrower post-fix viewport was not verified.

The operator retained local screenshots `sintel-note-held-20261022.png`,
`sintel-note-saved-20261022.png` and `sintel-final-preview-20261022.png`. These
observations establish timestamp capture,
held subtitle view, persistence and catch-up against a real running video's DOM
clock over the tested segment. They do not establish acoustic or frame-perfect
alignment, every cue across the whole film, drift over a full screening, or
behavior after an external pause or seek. No real Jellyfin session was used.

## Remaining scope and rollback

The preview is ready for Rafael to try this one-film workflow. Broader licensed
film/cut coverage and Rafael's acceptance remain open. A manual screening clock
requires a matching edition and initial alignment; it cannot infer changes on
an unrelated screen. Optional Jellyfin device following remains unverified.
No application or homelab candidate was promoted to `main`.

Prior source archives, application release/data generations, deployment keys
and private routes remain available. The implementation adds no database
migration; legacy and Meta Egg note timelines are not merged. Source rollback
is available through the retained releases, but no new backup restore or
clean-host rebuild was performed for this preview.
