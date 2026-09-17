# Purple Rain manual slskd import — 2026-09-17

The user downloaded the nine-track Prince and The Revolution album directly
in slskd. Its files were complete under
`/vault/shared/media/slskd/complete/(1984) Prince And The Revolution - Purple Rain [FLAC+.cue]`,
but Prince was absent from Lidarr and the permanent music library. Lidarr's
initial manual analysis rejected all nine files because it could not match
an existing album. Navidrome and Aurral therefore had nothing to present.

## Applied recovery

- Retained an independent, SHA-256-verified copy of every source file at
  `/vault/shared/media/slskd/.import-rollback/purple-rain-20260917T213735`.
  `source-sha256.json` records the original bytes. This is on the same pool,
  outside appdata PBS, and is not an independent backup.
- Added only the requested album through Lidarr's supported album API:
  Prince artist ID `162`, Purple Rain album ID `1346`, release-group ID
  `b93a7c47-a6d4-33f2-9034-53fdd991f4ba`. Disabled searches on addition and
  monitoring of new artist releases; did not request a discography download.
- Replaced the automatically selected 35-track edition with the nine-track
  CD release ID `10700`, which Lidarr's analysis matched to all nine files
  without rejections. The prior album resource is retained beside the source
  rollback as `lidarr-album-before-import.json`.
- Held Soularr's shared job lock and used the existing recovery helper's
  `manual_import` function. Supported `ManualImport` command `794992`
  completed in explicit copy mode with replacement disabled.
- Lidarr organized all nine files below
  `/vault/shared/media/music/Prince/Purple Rain (1984)`.
  The existing metadata worker subsequently provided canonical tags/artwork;
  all nine library files have independent, single-link inodes and `cover.jpg`
  is present. Source and rollback hashes still match after processing.
- Requested Navidrome's supported scan through its authenticated Subsonic API.

## Verification and limits

Lidarr reports nine imported files. Aurral's authenticated private-HTTPS album
and track APIs report nine available tracks and 100% completion. Navidrome's
authenticated search and album APIs return the nine-track album, and a raw
stream request through private HTTPS returned HTTP 206 with FLAC audio.
Feishin's native laptop UI displayed Purple Rain after refreshing its search.

Kew is configured for `/Volumes/Media/music`, the mounted read-only Samba
share. The Infra Samba account `afa` can read all nine files. macOS denied
the operator tool access to the mounted directory, including outside the
shell sandbox, so Kew playback was not verified. Its configured `u` binding
updates the local library cache.

No changes were made to automatic acquisition, shared-library permissions,
network exposure, or container images. The manual-download source and the
verified rollback copy remain available. Future direct slskd downloads still
need reviewed import; requesting albums through Aurral uses the existing
managed acquisition/import path.
