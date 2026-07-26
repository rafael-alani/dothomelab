# Media pipeline phase 6 evidence

Date: 2026-07-26

Scope: deploy Aurral, Soularr, and Navidrome; reconcile slskd to its current
stable channel; exercise both authorized music acquisition paths; and run the
final convergence gate for all six media phases. Production credentials,
tokens, and private peer data are deliberately absent.

## Result

The reproducible core is implemented and live:

- Soularr is a separate CT102 project beside Lidarr and sees only CT102
  appdata plus the shared slskd download tree.
- Aurral and Navidrome are separate CT112 projects. Aurral sees permanent
  music read-only and its flow root read-write; Navidrome sees both read-only.
- slskd is live on the official `latest` channel at 0.26.0 with its prior
  0.25.1 image and task-specific ZFS snapshot retained.
- Lidarr is the only declared permanent-library organizer. A clean bootstrap
  does not start DroppedNeedle, publish its route, add it to Homarr, or enroll
  it in WUD.
- Aurral submitted an authorized Creative Commons request to Lidarr. The
  existing Prowlarr/qBittorrent path completed it, Lidarr imported ten tracks
  exactly once, and Navidrome scanned and streamed them.
- Soularr acquired an authorized 36-track release through slskd. A retained
  upstream remote-queue edge case required the documented reviewed recovery;
  Lidarr then imported the 36 files exactly once in copy mode while both
  source and rollback remained intact.
- Storyteller completed an aligned user-owned readaloud fixture, the original
  Alice pair reconciled idempotently, and an ambiguous fixture was safely
  rejected.
- PinePods repeated subscription, download, web-progress, GPodder, and OPML
  acceptance, then produced a current logical dump and passed an isolated
  PostgreSQL 18 restore/application-readability test.
- Prometheus and Loki were deployed and passed their focused private-route,
  appdata, image, and update-policy checks.

Final convergence is deliberately not claimed. Two external credentials are
absent:

1. Aurral's current upstream flow generation needs
   `AURRAL_LASTFM_API_KEY` and `AURRAL_LASTFM_USERNAME`. No real flow can be
   generated without inventing an external account credential.
2. Paperless-GPT needs `PAPERLESS_GPT_OPENAI_API_KEY`. It was not started with
   a dummy value.

The Aurral-flow gate therefore has not accepted retirement of the live
DroppedNeedle container. It remains running with its existing restart policy
and appdata for rollback, while the repository models it only as a stopped
rollback profile. Numeric CT112 counts match the intended generation because
live DroppedNeedle occupies the one intended Paperless-GPT slot; project
membership does not yet match.

## Upstream revalidation

The implementation was checked against the current primary sources before
rollout:

- [Aurral repository and Docker guidance](https://github.com/lklynet/aurral)
- [Soularr repository and configuration reference](https://github.com/mrusse/soularr)
- [slskd repository, releases, and configuration](https://github.com/slskd/slskd)
- [Lidarr documentation](https://wiki.servarr.com/lidarr)
- [Lidarr manual-import service and command](https://github.com/Lidarr/Lidarr/blob/develop/src/NzbDrone.Core/MediaFiles/TrackImport/Manual/ManualImportService.cs)
- [Navidrome Docker installation](https://www.navidrome.org/docs/installation/docker/)
- [Navidrome configuration options](https://www.navidrome.org/docs/usage/configuration-options/)

The observed compatible choices are:

- `ghcr.io/lklynet/aurral:latest`
- `mrusse08/soularr:latest`
- `slskd/slskd:latest`, live 0.26.0
- `deluan/navidrome:latest`

Aurral's stable `latest` line still uses its current internal Soulseek path and
requires Last.fm for generated flows; its future external-slskd major was not
assumed. slskd 0.26.0's relevant configuration break concerns the old
`permissions.file.mode` setting, which this deployment did not use. Soularr
1.2.2 reached slskd 0.26.0, authenticated, searched, inspected peer
directories, enqueued downloads, and exercised the shared path mapping.

## Pre-change safety and rollback

PVE 9.1.2, both ZFS pools, CT102/110/112/113, VM101, and managed HAOS VM104
were running before the change. Final headroom remained:

```text
rpool/appdata/docker available: 493 GiB
vault/shared available:         19.8 TiB
vault/pbs_datastore available:  1.75 TiB
PVE memory available:           15 GiB
unhealthy Docker containers:    0
```

Retained rollback inputs:

```text
rpool/appdata/docker@pre-music-phase6-20260726T0312Z
slskd/slskd:0.25.1-dothomelab-rollback-20260726
image ID sha256:4037... (full ID remains in Docker)
/root/.env.music-phase6-recovery-20260726 (root:root, 0600)
pre-phase NPM and Homarr SQLite copies
DroppedNeedle Compose, appdata, live container, and image
```

No on-demand backup ran. The most recent scheduled appdata backup and its WUD
handoff both report `Result=success` and exit status zero. No image, volume,
database, appdata, download, media, snapshot, or retained test artifact was
pruned or deleted.

## Placement, storage, and ownership

Live placement is 16 containers/three projects on CT102, 11/five on CT110,
and 41/twenty-three on CT112. No guest or broad guest mount was added.

The path contract is:

```text
host /vault/shared/media/music
  CT102 /data/media/music       Lidarr read/write organizer
  CT112 /data/media/music       Aurral read-only
  CT112 /music                  Navidrome/Jellyfin read-only

host /vault/shared/media/slskd
  CT102 /data/media/slskd       Soularr /downloads read/write
  CT112 /slskd-downloads        slskd read/write

host /vault/shared/media/aurral-flows
  host /srv/appdata/docker/aurral/flows (persistent narrow bind)
  Aurral /aurral-flows          read/write
  Navidrome /aurral-flows       read-only
```

Soularr never mounts the permanent music root. Its upstream mapping is
`/downloads/complete` to Lidarr `/data/media/slskd/complete`; both resolve to
the same host tree. Aurral's main-library requests go through Lidarr. Music,
slskd downloads, and Aurral flow bytes remain under `/vault/shared` and are
outside the encrypted PBS appdata job. App databases, configuration, and
credentials remain under canonical appdata or production `/root/.env`.

The final repository also corrects Lidarr's recovered qBittorrent host from a
stale Docker gateway address to the stable `gluetun` Compose service name and
runs Lidarr's built-in client test. This is now clean-build reproducible.

## Aurral to Lidarr/Prowlarr acceptance

The test used Nine Inch Nails material released under Creative Commons.
Aurral created Lidarr album requests for `Ghosts I–IV` and `The Slip`.
`The Slip` had an authorized indexed result:

```text
release: Nine Inch Nails The Slip Album 24Bit 44 1kHz FLAC Beats
transport: Prowlarr -> qBittorrent
Lidarr album ID: 1302
tracks imported: 10/10
total bytes: 478,593,364
format: 24-bit FLAC
```

Lidarr history recorded exactly one `trackFileImported` event for each of the
ten tracks. The final files are `01.flac` through `10.flac` below
`/data/media/music/Nine Inch Nails`, owned by mapped UID/GID 1000:1000 and
mode 0644. Aurral's permanent-library mount is read-only. The retained
DroppedNeedle log/state did not claim the import; Lidarr history and the
qBittorrent grab identify the writer path.

Navidrome completed a scan with 863 songs/29 folders in the combined
catalogue and indexed all ten new songs. Acceptance responses were:

```text
direct stream:          HTTP 200, 1.67 MiB sampled
private HTTPS range:    HTTP 206, 65,536 bytes
Subsonic ping:          ok
TLS certificate verify: 0
```

Jellyfin's database contains the same music path, its `/data/media` mount is
read-only, and the in-container file hash matches the Lidarr file. An
authenticated Jellyfin playback was not performed because no supported
recovery API credential is declared. Feishin was unavailable. Those are not
reported as passed.

## Soularr and slskd acceptance

The representative authorized target was `Ghosts I–IV` (Lidarr album 1306).
The first bounded cycle:

- searched the exact album and returned 100 Soulseek results;
- matched the selected official Lidarr release;
- enqueued one 36-track FLAC match through slskd;
- proved the CT102/CT112 shared download mapping with live files;
- caused the WUD music guard to return exit 75;
- was stopped after the chosen peer rejected its first track indefinitely.

The working files and diagnostic log were retained. No final Lidarr import was
claimed from that attempt.

An alternate-peer retry temporarily excluded only the rejecting peer, used
the same job lock and album page, and was bounded by an in-container
20-minute timeout. It completed a 36-track, 607,017,632-byte folder and also
retained partial candidates. One unrelated remote queue item remained, so
Soularr stayed in its monitor loop until the outer timeout. The trap restored
`ignored_users`, removed the temporary page state, released the lock, and
left zero manual Soularr processes.

Lidarr's normal `DownloadedAlbumsScan` then reported `Failed to import`
because the recovered album had a combined 108-track release selected. A
committed recovery helper now:

- accepts only a child below `/data/media/slskd/complete`;
- detects Lidarr's failure message even when the command transport completed;
- uses Lidarr's own manual analysis and rejects any path, album, track, or
  rejection drift;
- changes release selection through Lidarr's API with automatic rollback on
  failure;
- invokes Lidarr's official `ManualImport` command in copy mode.

Before that explicit fallback, a 36-file hardlink rollback was retained at
`/vault/shared/media/slskd/recovery/phase6-ghosts-i-iv-20260726T0648`.
Lidarr's no-rejection analyzer chose official US 36-track release 9947. The
result was:

```text
Lidarr album:              1306, Ghosts I–IV
selected release:          9947, official, 36 tracks
imported TrackFiles:       36
unique final paths:        36
import history events:     36
bytes:                     607,017,632
retained source files:     36
retained rollback files:   36
source/library manifest:
  2427374229f6dba5ce482fe1ed07d62d966710867c8e3bc7c2b5a35ce867fc99
```

The final files are `1-01` through `2-18` below the canonical Nine Inch Nails
artist directory. Lidarr alone created the permanent-library records and
paths; Soularr has no library mount. Navidrome indexed all 36 tracks and
streamed a 65,536-byte range directly and through private HTTPS with HTTP 206
and certificate verification result zero.

slskd authentication, server connectivity, 27 shares/819 files, search,
directory inspection, download writes, API ACLs, port 50300 LAN-only listener,
private HTTPS, appdata, and the rollback bridge passed. The accepted runtime
retains the old image and snapshot. The scheduler remains paused because
recovered Lidarr has more than one thousand monitored missing releases. The
one retained remote queue item still causes the WUD music guard to reject a
replacement; it was not cancelled or deleted merely to make the guard idle.

## Aurral flow and DroppedNeedle gate

Production reports `lastfmConfigured=false`. A retained Aurral imported
playlist named `Phase 6 CC Acceptance Playlist` contains one authorized
`The Slip` track reference, but Aurral could not generate/copy playable audio:
the current reuse path did not resolve the Lidarr file and its internal
Soulseek attempt ended at an unavailable peer. The flow directory contains
only playlist/artwork metadata, not a playable media file.

This does not satisfy “create and serve one Aurral flow.” Consequently:

- DroppedNeedle was not stopped;
- its live `unless-stopped` policy was not changed;
- its appdata, image, and download files remain untouched;
- the repository retirement verifier intentionally fails live with
  `true unless-stopped`;
- a clean bootstrap still cannot recreate DroppedNeedle as a competing owner.

After both Last.fm values are supplied, rerun Aurral configuration, generate a
real flow, scan/stream it through Navidrome, prove the permanent root
unchanged, and only then stop DroppedNeedle:

```bash
docker update --restart=no droppedneedle
docker stop droppedneedle
```

Exact rollback re-enable remains:

```bash
cd /opt/dothomelab/hosts/apps/droppedneedle
docker compose --profile rollback up -d
```

Neither command was run during this phase.

## Final cross-phase convergence

The following focused checks passed live:

- CT102: Servarr, Shelfarr, and Soularr prepare/verify.
- CT112: BookOrbit, Audiobookshelf, Storyteller, PinePods, Aurral, Navidrome,
  slskd, Kavita, Jellyfin/media, Portainer, Loki, and Prometheus
  prepare/verify.
- CT110: Infra services, all managed NPM routes, Pi-hole records, Homarr,
  Cockpit/Samba, WUD unit tests, Storyteller guard, and music guard.

Infra observed 60 proxy hosts, 24 managed private endpoints, 22 Homarr
applications, 66 board items, and 154 layout records with SQLite integrity
`ok`. The Aurral and Navidrome names resolved through Pi-hole to NPM;
certificate-validated HTTPS returned 200 with `ssl_verify_result=0`. The NPM
verifier confirms LAN/Tailscale allow rules followed by `deny all`. No public
route was added.

The representative ebook and audiobook were re-scanned through BookOrbit and
Audiobookshelf. Their canonical hashes remained:

```text
ebook:     4ac9fc092435338fdb28e96b02989a46bbe075ec310f1789db87a653761cce92
audiobook: fe522ad254a3dc6ea68fea734f5376897fccff588458dc56e35628c1aec8a3ed
```

Storyteller evidence:

```text
fixture book ID: 4609481329978871
process result: ALIGNED
original Alice reconcile: UNCHANGED
ambiguous fixture: SKIP, ambiguous ebook side: 2 EPUB files
ambiguous inbox files: 0
```

PinePods evidence:

```text
acceptance summary:
  /srv/appdata/docker/pinepods/acceptance/20260726T041055Z/
logical dump checks: all OK
isolated restore:
  /srv/appdata/docker/pinepods/restore-tests/20260726T041105Z
application readability: passed
```

The PinePods repeat exposed a harness defect: it tried to rewind an episode
from its retained 48-second position to 37 seconds. The committed test now
chooses an episode with enough remaining duration and advances from the
existing position. Its corrected rerun passed every stage.

Nine WUD runner unit tests passed. During real jobs the music guard returned
exit 75, while the final idle Storyteller and music checks acquired/released
normally. Application rolling images are digest-watched and backup-gated;
database/cache majors remain pinned with `wud.watch=false`; pruning remains
disabled; the only automatic WUD handoff remains the successful scheduled
appdata service.

## Bootstrap and remaining acceptance

The production `./bootstrap.sh --dry-run` was run. It initialized or preserved
all generated media values without printing them, then stopped safely before
deployment:

```text
ERROR: PAPERLESS_GPT_OPENAI_API_KEY is missing
```

This is an external recovery-input gate, not a dry-run implementation error.
No dummy credential was inserted. `provision/verify.sh` is rerun after the
final evidence commit is synchronized and its exact result is appended here.

Remaining device/account work:

- supply Aurral Last.fm API key and username, then accept a real isolated flow;
- after that acceptance, stop DroppedNeedle and rerun its retirement verifier;
- supply the Paperless-GPT OpenAI key if that content-processing integration
  is desired;
- perform authenticated Jellyfin music playback;
- test Feishin and Kew on macOS when those clients are available;
- client-side KOReader/Kobo and broader Obsidian/Proton steps remain as
  recorded by their phases.

No unperformed device test is called successful.

## Repository generations

The implementation was committed and pushed incrementally:

```text
c427b1d Implement converged music pipeline
e63e792 Fix flow mount verification order
8073553 Harden music pipeline convergence
4d648e3 Make media acceptance repeatable
a3dba2c Reconcile retired media integrations
ce2d265 Add safe Soularr import recovery
5cbccd0 Harden recovered Soularr imports
f5e358b Support reviewed Lidarr manual recovery
c02b4b2 Execute recovered imports through Lidarr
```

The final evidence/current-state commit and final synchronized
`DEPLOYED_COMMIT` values are appended after convergence verification.
