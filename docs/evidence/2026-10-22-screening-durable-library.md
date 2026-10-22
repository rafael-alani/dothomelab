# Durable screening library — 2026-10-22

This follows the [online discovery preview](2026-10-22-screening-online-discovery.md).
The requested end-to-end film is **At Eternity's Gate (2018)**. Jellyfin is only
the proposed Chrome playback source; the application uses Wikidata metadata and
OpenSubtitles timed transcripts. No Jellyfin metadata, token or playback session
was used by the app or this import check.

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

## Behavior and live evidence

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

## Remaining end-to-end blocker

The dedicated `STAGING_META_EGG_OPENSUBTITLES_API_KEY` was absent on PVE; only its
presence was printed. The UI truthfully reports missing subtitle setup and keeps
Open screening unavailable. Chrome's Jellyfin tab is at sign-in. The user was
asked to provision the key in PVE `/root/.env` and sign in directly in Chrome.
No administrator token was read, no account was created, and no unrelated
production credential was reused.

Only an [OpenSubtitles application key](https://www.opensubtitles.com/en/consumers)
is needed for this discovery path; Wikidata needs none. OpenSubtitles documents
API-key-only search/download and local subtitle reuse in its
[official tutorial](https://blog.opensubtitles.com/opensubtitles/how-to-build-a-movie-subtitle-finder-cli-with-python-and-the-opensubtitles-api).
Provider quota and actual matching-release availability still need a live test.
No TMDB or Jellyfin API key is required.

After the key is installed, render Meta Egg's scoped environment and redeploy via
the [staging runbook](../../hosts/staging/README.md#meta-egg-screening-api). Then
select a matching release, verify transcript persistence, align using dialogue
while Jellyfin plays separately, compare later dialogue checkpoints, hold a note
while playback continues, save and verify timestamp/catch-up. **This movie's
subtitle alignment, continuous-play note test and full-screening drift remain
unverified.** No fixture success substitutes for that acceptance.

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
