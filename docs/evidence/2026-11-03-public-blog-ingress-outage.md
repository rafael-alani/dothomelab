# Public blog ingress outage — November 3, 2026

Public access is **not restored**. Read-only checks on PVE, CT110, CT114 and
CT115 locate the failure before the existing HTTPS proxy. Rafael reports that
the provider changed infrastructure during an Internet outage today.

## Observed state

- Local checkout: `5529318`, branch `codex/reference-media-boards`. Existing
  unrelated local documentation changes were preserved.
- CT110 archive: `db2f54f33797f0cb63879a1ca7f4a4a5527f230b`; CT115 archive:
  `9c2c15414382082ffb787fb4e912002564cbc902`. No archive was deployed.
- All six LXCs are running. Native blog listeners on CT114/115, the CT110
  exporter and the PVE publication path unit are active.
- `http://192.168.0.115:8084/` returns 200. A trusted HTTPS request to
  `https://rafael.ink/` with `--resolve rafael.ink:443:192.168.0.110` returns 200
  from both PVE and the operator Mac. Private `blog.staging.rafael.media`
  returns 200 from the Mac.
- Normal public `https://rafael.ink/` repeatedly returns Cloudflare 522.
  During a corresponding request, a bounded PVE capture observed no non-LAN,
  non-Tailscale inbound HTTPS SYN packets to `192.168.0.110` on `vmbr0`.
- PVE remains `192.168.0.250/24`, Infra remains `192.168.0.110/24` with
  Pi-hole secondary `192.168.0.100`. The default gateway is `192.168.0.1`,
  responding to both pings. `192.168.1.1` does not answer ping or HTTP;
  its trace follows the existing default route. There is no evidence of a
  LAN subnet migration.
- At **10:29:56 CET**, DDNS detected a change from `80.114.140.44` to
  `168.222.147.138` and updated the four existing public A records. The
  Cloudflare API confirms the new address; PVE, Infra and the Mac report the
  same outbound IPv4. The apex remains proxied; stream remains DNS-only.
- RIPE identifies the current prefix as `168.222.144.0/20`, ITT Desk B.V.,
  AS42383. The upstream trace is `192.168.0.1 → 100.64.0.1 → 100.127.11.1 →
  100.127.11.201/202`. Infra has no public IPv6 address or IPv6 default route.
- Router discovery identifies an Archer AX55. Its read-only UPnP status says
  connected, but the WAN-address response is empty. NAT-PMP WAN-address lookup
  returns network failure and `0.0.0.0`. UPnP has no dynamic mappings for
  TCP 80/443; that does **not** establish whether static forwarding rules exist.

## Diagnosis and remaining dependency

The site and LAN proxy are healthy, and DDNS matches the observed outbound IP.
Shared-address upstream hops and missing ingress after the provider change
suggest provider NAT or inbound filtering. Traceroute alone does not prove
CGNAT: the router's actual WAN lease and the provider's ingress policy remain
unverified. No router, firewall, guest IP or DNS change is justified by the
current evidence.

The existing Cloudflare API token can enumerate tunnels, but creation of an
inactive `dothomelab-public-blog` tunnel was denied with HTTP 403. No tunnel,
DNS change, connector, credential or runtime was created. Rafael declined the
Cloudflare sign-in request; the tunnel route was not pursued further.

To retain the current ingress arrangement, ask the provider to check whether
today's migration removed inbound TCP 80/443 or put this connection behind
shared NAT, and restore a reachable public IPv4/forwarding path. Include the
old/new addresses and change time above. Router WAN status would distinguish
the cases if available. Do not blindly reset DNS to the former address.

An alternative, if separately selected and authorized, is a named Cloudflare
tunnel exposing only `rafael.ink`, forwarded over verified TLS to the existing
NPM route with `originServerName` and `httpHostHeader` set to `rafael.ink`, plus
a final `http_status:404` rule. This needs Cloudflare Tunnel Edit authorization,
a scoped connector credential, Git-managed deployment/recovery, and removal
of the apex from DDNS only at verified cutover. Retain the existing DNS record
and DDNS configuration for rollback. The private staging hostname must not be
included. No such configuration is installed or accepted by this investigation.

References: [Cloudflare API tunnel setup](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel-api/),
[RIPE prefix data](https://stat.ripe.net/data/prefix-overview/data.json?resource=168.222.147.138),
[ITT Desk support](https://www.ittdesk.nl/ondersteuning/).

## Limits and cleanup

No service restart, backup, restore, application release, network mutation or
credential rotation ran. No persistent diagnostic container, packet capture,
script or remote file was created. Existing services and rollback material were
left intact. The router login tab was closed; Chrome became unavailable when
closing the Cloudflare login tab, so its closure is unverified. The existing
Pulse/Homarr enrollment was not changed or audited, and public browser journeys
remain blocked. Other public services may share the same ingress failure but
were not repaired or independently accepted. This local evidence draft is not
a completed recovery release.
