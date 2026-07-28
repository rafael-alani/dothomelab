# SNOWSKY ECHO sync decision and acceptance record

Date: 2026-07-28

Status: desktop workflow implemented; physical ECHO/card acceptance pending.

## Decision

Do not deploy HifiMule or EchoList as an Apps Compose project.

HifiMule is a macOS/Windows desktop application whose local daemon, tray UI,
and device discovery operate on an attached mass-storage device. EchoList is a
local GUI that reads a source directory and writes tagged copies to the
mounted player/card. A container in CT112 cannot see a microSD card mounted on
the Mac, and neither upstream application supplies a supported headless
service. Dockerizing either would add remote filesystem/device forwarding and
GUI plumbing without providing a supported sync path.

The repository instead contains:

- a dedicated full-size ECHO HifiMule profile;
- an idempotent, backup-first profile installer;
- a checksum-verifying release downloader that does not execute artifacts;
- tests and an exact two-owner card layout.

No server, Compose, DNS, proxy, secret, shared-media, or durable-data change is
needed.

## Correct ownership model

The proposed pipeline is directionally right but gives Beets too much
authority. The existing homelab contract must remain:

```text
Aurral request
    |
    v
Lidarr ---- Prowlarr ---- qBittorrent / NZBGet
    |
    +------ Soularr ----- slskd
    |
    v
/vault/shared/media/music
    |
    +------ music-metadata/Beets   tag, art, ReplayGain writer only
    +------ Navidrome              read-only client/API source
    +------ Jellyfin               read-only secondary consumer

Mac:
Navidrome --> HifiMule --> microSD /Music/Managed
                                  |
                                  v
                    EchoList reads Managed and writes
                    synthetic copies to /Music/Playlists
```

Lidarr remains the sole organizer, path authority, and selected-release
authority for permanent music. The Beets service may correct approved tags,
artwork, and ReplayGain in place, but it must not import, move, rename, or
delete the canonical library. A second Beets export pipeline is unnecessary
while HifiMule owns the card manifest and prune boundary.

## Capacity policy

The live canonical music tree measured:

```text
bytes:             40,555,624,828
audio tracks:      1,119
FLAC / MP3 / M4A:  820 / 271 / 28
album directories: approximately 100
```

This is roughly 37.8 GiB and fits comfortably on a 256 GB card. Start by
synchronizing the complete library with auto-fill disabled. Reserve at least
10% of the card for filesystem headroom, future acquisitions, and EchoList
copies. The actual EchoList duplication cost must be measured from the chosen
playlists rather than guessed.

A 32–64 GB capsule is not presently justified by storage. If the real player
is unpleasant with about 100 albums, then use auto-fill as a user-interface
policy. Likewise, enable capacity rotation later when Managed plus Playlists
approaches 80% of usable card space. At that point, `70% stable core / 30%
rotation`, album-atomic selection, and a multi-cycle cooldown are sensible
starting values—not permanent truths.

## File and playlist policy

HifiMule 0.13 constructs:

```text
Music/Managed/Album Artist/Album/NN - Track.ext
```

The explicit track prefix gives a deterministic filename fallback. HifiMule
does not currently expose a path template for `YYYY - Album`; promising that
layout would be inaccurate.

Do not depend on HifiMule's M3U output for the ECHO. It is kept in the separate
`HifiMule-M3U` folder so it can be inspected without colliding with EchoList.

EchoList's metadata-copy method is the best available workaround for a player
that ignores M3U, but upstream has tested it specifically with the ECHO MINI,
not the full-size ECHO. It physically duplicates a track for each playlist
membership and may make those copies appear in global browsing. Only FLAC,
MP3, and M4A from the current live library should enter the initial test;
EchoList lists more extensions but its tag-writing implementation is specific
to FLAC, MP3, and MP4-family files.

## Profile rationale

The repository profile directly passes the formats documented for the
full-size ECHO: DSD, WAV, FLAC, APE, MP3, M4A, and OGG. WMA is included because
the current official firmware record explicitly fixes WMA metadata display.
Unsupported source formats request server-side FLAC with a 9,216 kbps ceiling.
The profile's sample-rate and bit-depth fields describe the ECHO's documented
PCM ceiling for Jellyfin-style negotiation; the current Navidrome/Subsonic
transcode path still requires a representative device test.

HifiMule's source-format detection is sometimes container-only, so the direct
rules intentionally use containers without over-constraining codec metadata.
The present library is already entirely FLAC, MP3, and M4A; transcoding, DSD,
APE, OGG, and WMA remain device acceptance cases rather than verified claims.

## First-card acceptance

Update the full ECHO to the current official firmware before testing. As of
this record, FiiO's firmware summary lists v1.8.0; it includes OGG playback,
APE/WMA tag, and MP3 cover fixes. Never install ECHO MINI or ECHO NANO
firmware on the full-size ECHO.

Use a disposable first sample:

1. Initialize the card with HifiMule, but synchronize only two complete albums
   containing FLAC, MP3, and M4A examples.
2. Confirm `NN - Track` order in folder and album browsing before adding
   EchoList output.
3. In EchoList, create two playlists with one track shared by both. Use source
   `Music/Managed`, destination `Music`, folder `Playlists`, and node name
   `* PLAYLISTS *`.
4. Safely eject, refresh the ECHO library, and power-cycle it.
5. Confirm the synthetic node is visible, both playlists are distinct, the
   shared track appears in both, track order survives the power cycle, and
   originals remain under their real artists/albums.
6. Check global browsing for confusing duplicates and measure the exact space
   used by `Music/Playlists`.
7. Delete or offload one test playlist through EchoList, interrupt one later
   disposable sync, and verify its documented recovery path before trusting it
   with the real card.
8. Only then synchronize the full library. Keep HifiMule auto-sync disabled
   until several manual cycles have completed without unexpected pruning.

Failure of the synthetic grouping on the full ECHO is a stop condition for
EchoList, not a reason to mutate canonical tags. HifiMule remains usable for
the ordinary managed library, and the on-device Favorites list is the safe
fallback.

## Evidence and upstream status

- [HifiMule README](https://github.com/HifiMule/HifiMule) documents the
  desktop/server/device workflow and supported server families.
- [HifiMule v0.13.0](https://github.com/HifiMule/HifiMule/releases/tag/v0.13.0)
  is the exact release inspected. The Apple Silicon app archive used here has
  SHA-256
  `d554ba4a0629f17504390a7a2cdaaa46ed384e91e929a4796401d7e532d466d3`.
- [EchoList README](https://github.com/purpleturtle21/echo-list) documents its
  ECHO MINI target, synthetic metadata model, multiple membership, M3U import,
  backup, offload, and recovery behavior.
- [EchoList v0.2.0](https://github.com/purpleturtle21/echo-list/releases/tag/v0.2.0)
  is the exact release inspected. Its Apple Silicon binary has SHA-256
  `19bdff0aca4d211536968911db80b8176f6bd910d2647b1a7b5423873b1abb94`.
- [FiiO's full-size ECHO product page](https://www.fiio.com/echo) documents
  8 GB internal storage, microSD support up to 256 GB, DSD256, PCM
  24-bit/192 kHz, and the supported format family.
- [FiiO's ECHO firmware summary](https://bbs.fiio.com/phoneNote/showNoteContent.do?id=202601301818227421936&tid=16)
  is the authoritative current model-specific firmware/change record.

The two macOS release artifacts inspected are Apple Silicon and ad-hoc signed;
they are not Developer ID notarized. The download helper verifies exact bytes
but deliberately does not install, execute, or remove quarantine attributes.
