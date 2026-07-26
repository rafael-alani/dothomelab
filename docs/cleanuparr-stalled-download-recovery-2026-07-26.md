# Arr stalled-download recovery — 2026-07-26

## Scope and diagnosis

The live Lidarr queue contained the active download
`Toto - Fahrenheit (2020) [FLAC 24-192]` for album ID `1318`.
qBittorrent hash `4616020FFF65328BFB24CDD2035790DA32F70B52` was in
`stalledDL` with no seed, no download speed, and about 1.63 GB remaining.
Lidarr correctly reported `The download is stalled with no connections`, but
its native failed-download handling did not classify a merely stalled torrent
as failed. Deleting the hash directly in qBittorrent would also prevent Lidarr
from blocklisting the release.

Cleanuparr 2.10.0 is now the purpose-built stalled-download controller. No
repository script decides which queue item to delete. The repository helper
only reconciles Cleanuparr's supported HTTP configuration API.

## Policy

- Queue Cleaner runs every 30 minutes.
- Public torrents need 12 consecutive stalled strikes, approximately six
  hours.
- Private torrents need 48 consecutive stalled strikes, approximately 24
  hours, before client removal is allowed.
- At least 64 MiB of progress resets strikes.
- Metadata stalls need 12 strikes.
- Slow-download and failed-import cleanup remain disabled.
- Connectivity and download-client checks fail closed.
- Cleanuparr removes through the owning Arr with blocklisting enabled; its
  Seeker performs replacement-only searches every five minutes.
- Sonarr, Radarr, Lidarr, and Readarr are connected. Proactive wanted-list
  searching is disabled.

The UI is authenticated and its direct listener is available only on the
Servarr LAN address at `http://192.168.0.102:11011`. A later same-day
dashboard task added private Pi-hole/NPM access at
`https://cleanuparr.rafael.media` for LAN/Tailscale plus Homarr tiles. It
still has no public exposure.

## Deployment and guarded first run

The documented `latest` image resolved to runtime 2.10.0. The registry did not
publish a usable `v2.10.0` manifest, so Compose retains the documented name
with immutable digest
`sha256:9f74fa60bbf84c82b86f69fbef75189dd3e38408f99fd9c1895736185c4620b9`.
Automatic updates are disabled.

Before production configuration, an isolated tmpfs-backed probe:

- connected to the existing qBittorrent, Sonarr, Radarr, Lidarr, and Readarr
  APIs;
- reconciled the intended policy;
- passed the API verifier;
- ran Queue Cleaner in dry-run mode; and
- detected two stalled Radarr items plus Fahrenheit without changing a queue,
  client item, or media file.

The probe container and memory-only database were then removed. Production
configuration again forced dry-run, waited for a completed Queue Cleaner job,
and only then disabled dry-run. The dry-run strikes and events were purged by
Cleanuparr when the real policy was enabled.

## Fahrenheit recovery

The one-off recovery did not wait for the six-hour grace period:

1. Live state was rechecked immediately before removal. Lidarr queue ID
   `1761893697`, album ID `1318`, title, and qBittorrent hash all matched.
2. Lidarr's supported queue-delete API was called with
   `removeFromClient=true`, `blocklist=true`, `skipRedownload=false`, and
   `changeCategory=false`.
3. The old hash disappeared from qBittorrent and the exact source title
   appeared in Lidarr's blocklist.
4. Lidarr `AlbumSearch` command `703963` completed for album `1318` and found
   zero alternative torrent/Usenet reports. The blocklisted release was not
   selected again.
5. A lock-protected, request-only Soularr retry read the existing durable
   Aurral requests. It found 100 Soulseek results for Toto, matched the selected
   10-track CD release to one FLAC folder, and queued that folder through the
   existing slskd account. The Elvis 35-track request had no valid edition
   match and was safely left wanted.
6. All ten Soulseek transfers completed successfully. Soularr handed
   `/data/media/slskd/complete/Toto - Fahrenheit (1986)` to Lidarr.
7. Lidarr `DownloadedAlbumsScan` command `703977` completed with
   `Importing 10 tracks`. Album `1318` now has 10 of 10 track files,
   1,808,033,110 bytes on disk, 100 percent of tracks, and no queue record.

Lidarr remains the only permanent-library writer. The imported files are under
`/data/media/music/Toto`; Soularr has no permanent-library mount.

## Last.fm discovery check

The production Aurral database and authenticated APIs showed:

- Last.fm API key configured;
- default integration username configured;
- the administrator account linked to Last.fm;
- one-month discovery period and a 168-hour automatic refresh interval; and
- an existing Last.fm cache with 200 recommendations.

A supported manual Discover refresh then used 161 library artists and 13 usable
Last.fm history artists, sampled 50 recommendation seeds, and completed with
319 recommendations, 32 trending artists, and 24 genres. The authenticated
Discover API returned the same counts with `isUpdating=false`.

Approximately 50 recent Spotify scrobbles were therefore not the blocker.
Aurral supplements listening history with the Lidarr library, and the live
history already supplied usable artists. A browser retaining the pre-refresh
response may need a normal page reload.

## Verification and rollback

Focused verification passed for:

- repository and live media data contracts;
- Cleanuparr runtime, image digest, appdata, private network, port, health, and
  manual-update policy;
- Cleanuparr API policy and all five external connections;
- Soularr request scoping, job lock, path mapping, and WUD guard;
- slskd authentication, storage, transfer API, peer listener, and WUD guard;
- Aurral v2 history, external slskd, mounts, private HTTPS, and runtime UID;
- Navidrome health, read-only libraries, private HTTPS, and appdata; and
- 69 running containers in 32 active Compose projects.

Rollback stops only the `cleanuparr` Compose project and retains
`/docker/cleanuparr`. Native Arr failed-download handling remains enabled.
Stopping Cleanuparr does not undo the deliberately blocklisted dead Fahrenheit
release or the successful Lidarr import.

## Upstream references

- [Cleanuparr repository](https://github.com/Cleanuparr/Cleanuparr)
- [Cleanuparr Queue Cleaner](https://cleanuparr.github.io/docs/configuration/queue-cleaner/)
- [Cleanuparr Seeker](https://cleanuparr.github.io/docs/configuration/seeker/)
- [Cleanuparr download clients](https://cleanuparr.github.io/docs/configuration/download-client/)
- [Cleanuparr Arr instances](https://cleanuparr.github.io/docs/configuration/arr/)
- [Aurral repository and Discover guidance](https://github.com/lklynet/aurral)
- [Aurral v2 prerelease notes](https://github.com/lklynet/aurral/blob/test/V2.md)
