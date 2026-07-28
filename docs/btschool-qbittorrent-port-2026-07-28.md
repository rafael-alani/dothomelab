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

Populate this section only after deployment with:

- the Gluetun and qBittorrent health result;
- confirmation that qBittorrent uses port 52123 on `tun0`;
- sanitized BTSchool tracker status after reannounce;
- aggregate peer discovery or transfer-state evidence;
- confirmation that both television torrents use category `tv-sonarr`;
- the deployed Git commit.

## Rollback

Revert the Git commit and redeploy the complete Gluetun/qBittorrent/NZBGet/
Prowlarr cohort. The prior qBittorrent application state remains in canonical
appdata. Rolling back restores port 6881, which BTSchool rejects and should be
used only to recover from a wider VPN failure while another allowed port is
prepared.
