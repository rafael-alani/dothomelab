# Durable screening library — 2026-10-22

This follows the [online discovery preview](2026-10-22-screening-online-discovery.md).
The requested end-to-end film is **At Eternity's Gate (2018)**. Jellyfin is only
the Chrome playback source; the application uses Wikidata metadata and
OpenSubtitles timed transcripts. No Jellyfin metadata, token or playback session
was used by the app. The test observed Chrome’s video clock as a manual
alignment reference; no Jellyfin service integration supplied the clock.

## Deployed candidates

| Component | Installed commit |
|---|---|
| Meta Egg | `3d47eaba58ab0141c8bfe53c4219a158e151f3fb` |
| Film-introspect | `29ebf83ded4ae2f4317be0a685c03f6844add67f` |
| Homelab CT114 runtime archive | `c86e422e80cb1461c0127737927479dd4e1b931f` |

The two application `staging` branch heads were verified against these installed
revisions. Homelab configuration is published on `codex/screening-mvp-staging`.
Main branches were not changed. Private previews remain
[Film-introspect](https://film-introspect.staging.rafael.media) and
[Meta Egg](https://meta-egg.staging.rafael.media).

## Initial metadata verification

Selecting a discovered film through Film-introspect saves its metadata in Meta
Egg. Loading a selected subtitle saves that exact release, original cue timing,
provenance and checksums. Each response includes its own `savedAt` only after a
successful durable write. The UI distinguishes metadata and transcript save
confirmations. The private JSON screening library is separate from the inactive
canonical graph. It contains metadata and timed text, not movie video.

On October 22, Chrome searched for the requested film through Film-introspect,
returned **2018 / 110 min**, and selected `wikidata-Q47006131`. The UI then showed
**Saved in Meta Egg**. The actual persistent record's timestamp was
`2026-10-22T08:42:21.122Z` (10:42:21 CEST).

A fresh provider instance inside the deployed container used the mounted
`/data/screening` directory with every network fetch forced to fail. Search and
detail successfully returned this exact film and unchanged saved timestamp.
The directory contained one metadata record and no transcript. After restarting
only the Meta Egg staging container, its HTTP detail endpoint returned the same
saved timestamp and film identity. This proves real requested-film metadata
persistence; it does not prove commercial-film transcript retrieval.

Both staging verifiers passed: accepted commit labels, Compose validation,
HTTP/container health and Film-introspect SQLite integrity. The poller remained
active. Previous and current Film data generations each contained **2 media
items and 1 note**; no new note was created for the blocked screening. Counts do
not prove every existing note field, and no recovery restore was performed.

## Checks and startup correction

Meta Egg passed 61 tests, typecheck, lint, boundaries, formatting, build and two
compiled HTTP smoke tests. New tests cover durable selection, offline restart
retrieval, distinct retained cuts, no duplicate download, corrupt records,
identity mismatch, storage errors and retry. Subtitle persistence tests use
synthetic provider responses, not At Eternity's Gate's transcript.
Film-introspect passed 21 tests, typecheck, build, discovery HTTP/SQLite smoke,
and targeted formatting. Homelab deployment tests (9), scoped environment tests
(3), documentation and diff checks passed.

The initial Meta Egg storage release `661b6c3` failed startup and automatically
rolled back. An isolated credential-free container reproduced package resolution
failure: staging's private checkout umask left workspace directories `0700` and
manifests `0600`, owned by the image's node user. The restricted deployment UID
could not read them without capabilities. Final image `3d47eab` normalizes code
readability during build; application-data permissions are unchanged. Its actual
Docker build, restricted runtime startup and health checks passed. Prior images,
failed-candidate data and accepted release generations remain retained.

## Real-film follow-up: credentials and import

The user subsequently completed Chrome sign-in and provisioned the dedicated
`STAGING_META_EGG_OPENSUBTITLES_API_KEY` in PVE `/root/.env`. The scoped
initializer rendered Meta Egg's environment, and the staging deployer installed
the same `3d47eab` revision with configuration fingerprint `1e566a56ad9f`.
No credential value was printed. No administrator token was read, no account
was created, and no unrelated production credential was reused.

Only an [OpenSubtitles application key](https://www.opensubtitles.com/en/consumers)
was needed; Wikidata needs none. No TMDB or Jellyfin API key was used.
OpenSubtitles documents API-key-only search/download and local subtitle reuse in
its [official tutorial](https://blog.opensubtitles.com/opensubtitles/how-to-build-a-movie-subtitle-finder-cli-with-python-and-the-opensubtitles-api).

Selecting **At.Eternity's.Gate.2018.720p.BluRay.x264-[YTS.AM]** and opening its
screening in Chrome automatically downloaded and persisted **817 cues**.
Film-introspect displayed **Transcript saved in Meta Egg**. The exact record is:

- Movie: `wikidata-Q47006131`.
- Cut: `opensubtitles-9551226-10463961`, track `0`, English, declared 23.976 fps.
- Source: <https://www.opensubtitles.com/en/subtitles/9551226>.
- Saved at: `2026-10-22T08:52:20.384Z`.
- Transcript checksum: `dc957b66d3724cdd8ac920cf60d830876bf56adf9c83a274432b091f1d801d9e`.
- Final cue end: `5958.985` seconds. Chrome's video duration: `6677.712708` seconds.
  These differing lengths are not evidence of a different cut by themselves;
  subtitle tracks can end before silent footage and credits.

A fresh provider process with every network fetch forced to fail returned the
same film, cut, saved timestamp and 817 cues. Restarting only the Meta Egg staging
container then returned the same timestamp and cue count through its HTTP API.
Reopening the screening in Chrome loaded the saved transcript and test note.
No upstream download is required to reuse this stored release.

## Continuous-play note and timing checks

Jellyfin played the movie in Chrome, with its subtitle selection off. The app
used only the independent Meta Egg transcript. The tester read the video's DOM
clock and manually entered an anchor in Film-introspect; the applications do
not share playback state. Playback rate was 1.0. Sequential observations have
interaction delay and Film-introspect displays whole seconds, so these checks
do not measure subsecond acoustic alignment.

| Check | Film-introspect | Chrome video | Result |
|---|---|---|---|
| Initial manual anchor | 1:06 | 66.491417 s, playing | Clocks aligned at display resolution |
| Begin note | Held 1:17 | 78.061755 s, playing | Original note time held |
| Continue writing | Clock 1:41, held 1:17 | 101.721248 s, playing | Movie and companion clock continued |
| Save and catch up | 1:48; saved note 1:17 | 108.660777 s, playing | Live cue window caught up |
| Later checkpoint | 5:30, cue 23 active | 330.933411 s, playing | Within cue interval 329.746–332.079 s |
| Later checkpoint | 5:44, cue 28 active | 344.592976 s, playing | Within cue interval 343.677–348.342 s |

The note body is `E2E screening test: the wish to belong frames the opening.`
A scoped read-only SQLite query found exactly one matching note, at **77 seconds**
on the tested cut; integrity was `ok`. Browser reload and reopening the cut
retained it. This tests the real-film hold/save/catch-up workflow through the
first six minutes, not an uninterrupted full screening. The video was left
paused at `356.846009` seconds after testing. The Film-introspect tab was left
on the saved cut, requiring a new manual anchor before continuing.

The English release omits some French-language passages whose English
translations were visible in the movie image. Subtitle gaps are therefore a
source-coverage limitation, not all silence. A second SDH release,
`opensubtitles-9655125-10566564`, returned the UI's subtitle-retrieval error;
no successful second transcript import or improved coverage is claimed.
The working release and its note remain saved independently.

Manual alignment, correct subtitle-version selection, incomplete language
coverage and provider availability remain constraints. Audio recognition,
acoustic/frame-perfect matching, whole-film drift and the editorial cut's
identity are **unverified**. The checks establish independent import, persistence,
clock-to-cue timing and note catch-up, not automatic synchronization to a cinema.
The imported “script” is timed community subtitles, not a separate screenplay.
Movie video is not copied into Meta Egg.

Both final staging verifiers passed at the deployed app revisions, including
Compose validation, container/HTTP health and Film-introspect SQLite integrity.
The staging branch poller remained active. No main promotion occurred.

## Storage and rollback

Only Meta Egg's independent staging data generation is mounted at `/data`, with
`SCREENING_DATA_DIR=/data/screening`. The service has a read-only root filesystem,
dropped capabilities and no new privileges. Guest-root ownership matches the
staging data-copy mechanism inside the unprivileged LXC. No shared movie mount,
production integration, public route or database engine was added.

The previous guest archive remains at
`/opt/dothomelab.retained-1ed87e0-before-library`; PVE retains the committed setup
at `/root/dothomelab-screening-library-c86e422`. Existing `.previous` archives were
not removed. Rollback must preserve newly saved metadata/transcripts and notes,
not switch blindly to an older data generation. The new records lie within
scheduled appdata backup scope; no new backup, restore or clean-host rebuild
was performed. One Meta Egg process per screening directory is supported.
