# BTSchool qBittorrent port-forwarding repair — 2026-07-28

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

## Reproducible repair

`hosts/servarr/hello/compose.yaml` now:

- enables ProtonVPN's native Gluetun port forwarding and restricts selection to
  port-forwarding servers;
- uses Gluetun's port-forwarding up/down hooks to apply the leased port to
  qBittorrent over their shared loopback interface;
- binds qBittorrent to `tun0`, disables random-port selection and UPnP, and
  fails closed on loopback with listen port zero when the lease is removed;
- removes the obsolete LAN TCP/UDP 6881 publications;
- omits LinuxServer's `TORRENTING_PORT`, because setting it would overwrite the
  dynamic ProtonVPN port at every qBittorrent start;
- gives qBittorrent two minutes to persist its large torrent catalogue during
  an intentional stop.

The existing qBittorrent internal-access reconciler now permits unauthenticated
Web UI API calls only from localhost and the exact private
`servarr-hello_default` subnet. LAN Web UI authentication remains enabled. The
reconciler reapplies and verifies the current forwarded port after a
qBittorrent restart, covering the first deployment as well as later Gluetun
lease changes.

Focused verification rejects a missing or invalid lease, a static
`TORRENTING_PORT`, a stale 6881 host publication, a non-`tun0` bind, random
port selection, UPnP, or disabled localhost authentication bypass.

## Live acceptance

Populate this section only after deployment with:

- the Gluetun and qBittorrent health result;
- confirmation that the current forwarded port matches qBittorrent without
  recording the ephemeral port as desired state;
- sanitized BTSchool tracker status after reannounce;
- aggregate peer discovery or transfer-state evidence;
- confirmation that both television torrents use category `tv-sonarr`;
- the deployed Git commit.

## Rollback

Revert the Git commit and redeploy the complete Gluetun/qBittorrent/NZBGet/
Prowlarr cohort. The prior qBittorrent application state remains in canonical
appdata. Rolling back restores static port 6881, which is operationally
incompatible with BTSchool and should be used only to recover from a wider VPN
failure while a different allowed port is prepared.
