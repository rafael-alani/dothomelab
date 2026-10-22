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

## Verification checkpoint

Source/header/subtitle checks above were performed on October 22 from the
operator Mac. Runtime and real-video browser acceptance are pending at this
draft checkpoint. Final application commits, installed homelab revision and
actual hold/save/catch-up observations will be recorded after the parent
operator completes deployment and verification.
