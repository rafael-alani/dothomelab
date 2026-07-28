# BTSchool qBittorrent tracker-port repair — 2026-07-28

## Scope and observed failure

Two manually added BTSchool television torrents remained at zero progress even
though the tracker website reported seeders and leechers. Read-only
qBittorrent API inspection showed:

- both torrents were private, so DHT, PeX, and LSD were correctly unavailable;
- both had zero connected or tracker-known peers and zero availability;
- `pt.btschool.club` rejected each announce with
  `Port 6881 is blacklisted.`;
- both torrents had an empty qBittorrent category;
- qBittorrent listened on static port 6881, while Gluetun used ProtonVPN over
  WireGuard with VPN port forwarding disabled.

The tracker returned a port-policy error rather than a passkey or
authentication error. BTSchool credentials therefore do not belong in
qBittorrent; the personalized private torrent announce URL remains the
authentication mechanism and must never be logged or committed.

## Rejected Proton forwarding path

An initial repair enabled Gluetun's native ProtonVPN port forwarding and its
qBittorrent synchronization hook. The live NAT-PMP request failed closed with
`connection refused`: the existing WireGuard credential was generated without
Proton's NAT-PMP option. Proton documents that a manual WireGuard connection
needs a P2P configuration generated with NAT-PMP enabled. Generating that
configuration would rotate the production VPN credential, so this task did not
invent, expose, or replace it.

The failed attempt did not change qBittorrent's port or torrent data. Gluetun,
qBittorrent, NZBGet, and Prowlarr returned healthy before the fallback was
applied.

## Reproducible repair

`hosts/servarr/hello/compose.yaml` now:

- sets qBittorrent's VPN-only listening port to high port 52123 instead of
  BTSchool-blacklisted port 6881;
- leaves ProtonVPN port forwarding disabled until the user supplies a
  WireGuard key generated with NAT-PMP;
- keeps qBittorrent bound to `tun0` with random-port selection and UPnP
  disabled;
- removes the obsolete LAN TCP/UDP 6881 publications;
- gives qBittorrent two minutes to persist its large torrent catalogue during
  an intentional stop.

The qBittorrent internal-access reconciler continues to permit
unauthenticated Web UI API calls only from the exact private
`servarr-hello_default` subnet. Localhost and LAN Web UI authentication remain
enabled.

Focused verification rejects port-forwarding settings without the required
credential, a stale 6881 host publication, a LAN publication of 52123, a
different declared or live listening port, a non-`tun0` bind, random-port
selection, UPnP, or disabled localhost authentication.

## Live acceptance

Implementation commit `dd98f1818784b72c2e34aa7b0906d248d0d58b05`
was pushed, synced to CT102, and deployed without pulling unrelated images.
Only Gluetun, qBittorrent, NZBGet, and Prowlarr were recreated. All four
returned healthy, and qBittorrent retained its persisted torrent catalogue.

The qBittorrent internal-access reconciler and Shelfarr verifier passed.
The Servarr verifier passed with its supported
`REQUIRE_AGENT_HTTP=false` mode: the unrelated pre-existing Portainer Agent
container still has no published TCP 9001 endpoint. The in-scope checks proved:

- Gluetun's native health check passed with port forwarding disabled;
- qBittorrent listened on port 52123 and remained bound to `tun0`;
- random-port selection, UPnP, and localhost authentication bypass were off;
- neither port 6881 nor port 52123 was published on the CT102 LAN address;
- qBittorrent, NZBGet, Prowlarr, every Arr, Bazarr, FlareSolverr, and Portainer
  passed their direct service checks;
- canonical appdata and shared download/media mounts remained intact.

Both exact BTSchool torrents were assigned category `tv-sonarr` and only those
two hashes were reannounced. Sanitized final API evidence showed tracker status
`2` (working), no error message, and:

| Torrent | Tracker swarm | Connected result |
|---|---:|---|
| `CCTV8.Who.Is.He.2023.HDTV.1080i.H264-HDCTV` | 98 seeds, 2 leeches | 4 seeds, downloading at 7.6 MiB/s |
| `黑夜告白.Light.to.the.Night.2026.S01.2160p.WEB-DL.HEVC.DTS-ZmWeb` | 68 seeds, 13 leeches | 1 seed, downloading, availability above 1.0 |

No BTSchool account credential, personalized announce URL, passkey, peer IP,
or production environment value was printed or committed.

## Rollback

Revert the Git commit and redeploy the complete Gluetun/qBittorrent/NZBGet/
Prowlarr cohort. The prior qBittorrent application state remains in canonical
appdata. Rolling back restores port 6881, which BTSchool rejects and should be
used only to recover from a wider VPN failure while another allowed port is
prepared.
