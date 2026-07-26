# Cleanuparr

Cleanuparr is the supported stalled-torrent controller for CT102. It uses the
existing qBittorrent and Arr APIs; it does not implement queue deletion in a
local script.

The repository pins the exact Cleanuparr 2.10.0 image digest. The registry did
not expose a usable `v2.10.0` manifest on 2026-07-26, so the Compose reference
uses the documented `latest` name plus the verified immutable digest. The
runtime reports `Cleanuparr v2.10.0`.

`configure.py` reconciles only settings through Cleanuparr's supported HTTP
API:

- qBittorrent at `http://gluetun:8080` on `servarr-hello_default`; the existing
  exact-subnet authentication exception avoids copying the shared qBittorrent
  password into a second application;
- Sonarr v4, Radarr v6, Lidarr v3, and Readarr v0.4 using API keys recovered
  from their canonical `config.xml` files;
- Queue Cleaner every 30 minutes;
- public stalled torrents removed after 12 consecutive strikes (about six
  hours);
- private stalled torrents removed after 48 consecutive strikes (about 24
  hours), reducing false positives and tracker hit-and-run risk;
- strikes reset only after at least 64 MiB of renewed progress;
- qBittorrent metadata stalls removed after 12 strikes;
- failed-import and slow-download rules remain off because the Arrs already
  own failed-download handling and slow rare releases are not necessarily
  dead;
- internet connectivity and download-client presence checks fail closed;
- Seeker replacement searches every five minutes, with proactive library
  searching disabled.

Cleanuparr removes a matched queue item through the owning Arr with blocklisting
enabled and Arr redownload disabled. It then queues the replacement search in
its Seeker. This prevents the same release from being selected again while
keeping replacement searches consistent across Sonarr, Radarr, Lidarr, and
Readarr.

The UI is published only on the Servarr LAN address at
`http://192.168.0.102:11011` and retains username/password authentication. It
has no NPM route and no router exposure.

For a one-off item that should not wait for the automatic grace period, use the
owning Arr's Activity → Queue remove action with all three options selected:
remove from download client, delete files, and blocklist the release. Enable
the replacement search/redownload option. Do not delete the torrent directly
in qBittorrent, because the Arr cannot blocklist a release it did not observe
being removed.

Rollback stops only the `cleanuparr` Compose project without deleting
`/docker/cleanuparr`. Native Arr failed-download handling remains enabled.
