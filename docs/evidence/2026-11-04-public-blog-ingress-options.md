# Public blog ingress: confirmed provider NAT and options — November 4, 2026

Research only; no deployment, DNS, router, firewall, credential or service
change. This note complements the [live incident evidence](2026-11-03-public-blog-ingress-outage.md).

## What the evidence establishes

**Follow-up confirmation:** Rafael supplied an Archer AX55 Internet Status
screenshot showing a dynamic WAN IPv4 of `100.64.16.120`. A subsequent PVE
check still reports public outbound IPv4 `168.222.147.138`. The WAN address is
inside RFC 6598 shared space and differs from the public address, confirming
upstream provider NAT on this connection. This resolves the earlier uncertainty
below; any additional provider filtering or stale router forwards remain
uninspected, but ordinary router port forwarding alone cannot establish an
unsolicited route through that upstream NAT.

The existing DDNS updater works: the detected outbound IPv4 and Cloudflare's
stored apex A record both equal `168.222.147.138`. The production origin and
LAN HTTPS proxy return 200, but Cloudflare returns 522 and the observed external
connection attempts do not reach the LAN proxy. The fault is before that proxy;
updater failure and a moved LAN subnet are not supported by the checks.

The upstream `100.64.0.1` and `100.127.11.x` hops fall in the shared address
space reserved for provider NAT. This supports the CGNAT hypothesis, but transit
addresses alone do not establish the router's WAN lease or prove translation
on this subscriber's traffic. [RFC 6598](https://www.rfc-editor.org/info/rfc6598/)

ITT Desk explicitly documents shared IPv4/NAT, no individual IPv4 option and
an on-request SNAT profile on a Power subscription **for its recreation-location
service**. That page is under EuroParcs; it does not establish Rafael's service
policy, student connection configuration, opt-out eligibility, or inbound-port
support. It confirms only that the provider operates such a model.
[ITT Desk recreation FAQ, question 16](https://www.ittdesk.nl/veelgesteldevragen/)

Before the supplied WAN screenshot, provider NAT, provider ingress
filtering/mapping, and router forwarding could not be separated conclusively.
The router's empty public UPnP response did not provide the missing evidence;
the later WAN screenshot does.

## Additional live checks — November 4, 2026

The parent investigation ran only bounded diagnostic probes, with no
configuration, deployment or credential changes:

- Cloudflare's stored apex remains proxied to `168.222.147.138`, matching
  independent outbound discovery. The updater is running without restarts.
  The zone is active; the token cannot read the TLS-mode settings (403), so
  those settings were not verified. The earlier local HTTPS 200/public 522
  checks remain reproducible.
- Independent Globalping TCP tests from the Netherlands and Germany each
  sent three probes to ports 80 and 443: **all 12 attempts timed out**. These
  bypass Cloudflare, establishing that this is not only a Cloudflare-origin
  restriction. Probe networks included DELUXHOST/Oracle in Amsterdam and
  Hetzner in Falkenstein. Results:
  [TCP 80](https://api.globalping.io/v1/measurements/21qWLZ770AOJBjdam00021RGb),
  [TCP 443](https://api.globalping.io/v1/measurements/27jlo6Kh8oDTXcW0D00021RGb).
- TCP-443 traces from LeaseWeb Amsterdam and Hetzner Falkenstein last received
  replies from `141.136.21.162`; subsequent hops and the destination were silent.
  Silence does not locate a specific drop rule or prove CGNAT.
  [External traces](https://api.globalping.io/v1/measurements/2mbim8vYWsvc8cOCy00021RGc)
- A bounded PVE `vmbr0` capture during those tests found no inbound SYN to
  `.110:80/443`. The repeat included sources in `100.64.0.0/10`, removing the
  initial capture's Tailscale-source exclusion. Captures printed headers only;
  no packet file was retained.
- PVE firewall reports disabled. Infra's host input chains accept traffic;
  NPM uses host networking and listens on 443. Tailscale's non-Tailscale
  shared-address source-drop rule has zero packet hits. The checks provide
  no evidence that PVE/Infra are dropping the tested external connections.
- Tailscale's diagnostic reports UDP working, public IPv4
  `168.222.147.138`, no working IPv6, and `MappingVariesByDestIP: true`.
  Destination-dependent NAT is established somewhere along the path, but
  this does not identify which NAT device performs it.
- UPnP reports `IP_Routed`, NAT enabled and physical WAN link up, while the
  external-address field remains empty. Static forwarding and the actual WAN
  lease remain inaccessible through the supported read-only discovery interface.
- Both `region1.v2.argotunnel.com` and `region2.v2.argotunnel.com` resolve on
  Infra. TCP connections to port 7844 on one address in each region succeeded
  in 5–6 ms. This validates the TCP transport prerequisite only: no connector
  was installed, tunnel authenticated, route published or QUIC session tested.

At this stage provider NAT was the leading explanation, with provider filtering
and router forwarding unresolved. Rafael subsequently supplied the WAN screenshot
recorded above. No password, login or settings change was needed to confirm NAT. External
measurement links may expire; the summarized observations above are retained.

## Smallest decisive checks

1. **WAN check completed by the supplied screenshot:** `100.64.16.120` confirms
   upstream NAT. The original diagnostic criterion was to read the router's
   **WAN IPv4**, gateway and static forwarding rules.
   A WAN address in `100.64.0.0/10` or RFC1918 space, while external services see
   `168.222.147.138`, establishes upstream NAT. A matching public WAN address
   would move the investigation toward filtering or forwarding. A provider
   confirmation can supply the same missing fact without dashboard changes.
2. If the router has a public WAN address, observe an external TCP 443 attempt
   at its WAN and LAN sides. Arrival at WAN but not the existing `.110:443`
   forward identifies the router path; no WAN arrival identifies the provider
   path or an incorrect ingress address. An absent LAN SYN alone cannot separate
   those two cases.
3. For an outbound-tunnel option, test DNS and TCP 7844 connectivity to
   Cloudflare's documented tunnel endpoints. A TCP connection is a useful
   read-only prerequisite check; it does not authenticate or prove a tunnel.
   [Cloudflare connectivity checks](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/troubleshoot-tunnels/connectivity-prechecks/)

## Options, in practical order

| Option | Fit for this homelab | Dependency and tradeoff |
|---|---|---|
| Restore provider public ingress | Smallest change if ITT Desk can restore the previous behavior. Existing NPM, DDNS, automatic blog publishing and other public services continue. | Ask whether the migration introduced CGNAT and whether this connection can receive public IPv4 or explicit inbound 80/443 forwarding. Availability and price are unverified. Do not assume the recreation SNAT profile supports hosting. |
| Cloudflare Tunnel for `rafael.ink` | Best contained workaround if public ingress is unavailable. A connector initiates outbound connections, so it does not depend on home inbound port forwarding. Keep the existing blog build/publisher and NPM route. | Needs Cloudflare Tunnel Edit authorization once, a scoped connector credential, outbound 7844, deployment/recovery and monitoring. The present token's failed create request means it cannot currently provision this. Other public hostnames would remain separate work. |
| Public VPS reverse proxy over WireGuard | A controlled public ingress point can forward over a home-initiated VPN connection. Useful if broader services or provider independence justify it. | Adds a rented server, updates, TLS/proxy configuration, scoped routing, monitoring and another failure point. WireGuard keepalive can maintain the NAT mapping; it does not itself supply a public server. More operational work than one blog tunnel. |
| Host the generated static blog externally | Existing generated HTML/assets can be published to an external static host. The last deployed site can remain available during a home outage. | Changes the publication target: automatic Obsidian updates, deletions, draft exclusion, redirects, rollbacks and production analytics must be integrated and tested. A one-time copy would become stale. Home-hosted Umami still needs a reachable collection route or a separately reviewed replacement. |

Cloudflare documents the tunnel's outbound connection model and its separate
account-level Tunnel Edit plus zone DNS Edit authorization. Its API setup also
supports a final 404 ingress rule and a proxied tunnel CNAME.
[Tunnel model](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/),
[API provisioning](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel-api/).
WireGuard documents keepalive for peers behind NAT or stateful firewalls.
[WireGuard quick start](https://www.wireguard.com/quickstart/).
Cloudflare Pages supports uploading prebuilt assets from an existing build
platform. This establishes technical feasibility, not acceptance of a new
hosting platform or publication workflow.
[Pages Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/)

## Conditions for the tunnel option

The proposed public route would be only `rafael.ink` to the existing NPM HTTPS
listener, with `originServerName` and `httpHostHeader` both `rafael.ink`, verified
origin TLS, and a final 404 rule. These settings choose the existing certificate
and virtual host; they would preserve the public route's blog and collection-only
Umami paths. Do not route wildcard private hostnames or the private staging site.
[Cloudflare origin parameters](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/origin-parameters/)

At a later authorized cutover, retain the old apex record and DDNS configuration,
then remove only the apex from DDNS management so it cannot conflict with the
tunnel CNAME. Leave the other DDNS-managed names intact. Keep credentials in
canonical deployment secrets; verify external pages, analytics, private-route
denial, Pulse and Homarr after any eventual deployment. This is a proposed design,
not an installed or accepted change.

## IPv6 is conditional, not a presently available fix

The current checks found no public IPv6 address or IPv6 default route on Infra.
If the provider supplies a routed prefix, an IPv6 origin behind Cloudflare may
avoid IPv4 NAT, but it first needs working addressing, firewall rules and a
reachable HTTPS origin. Public AAAA answers for a proxied hostname can be
Cloudflare's own addresses and do not prove that the home origin has IPv6.
Cloudflare also prefers IPv4 when both origin address families are configured,
so merely adding AAAA beside the broken A record is not an adequate fix.
[Cloudflare IPv6 compatibility](https://developers.cloudflare.com/network/ipv6-compatibility/)

## Recommendation and limits

Provider NAT is now confirmed. Rafael prefers the Cloudflare Tunnel option and
offered Chrome access to Cloudflare and the local router. Router changes are
unnecessary for the proposed outbound tunnel. The current read-only NPM query
confirms `rafael.ink` is enabled and forwards to `http://192.168.0.115:8084`.

The concrete candidate is `dothomelab-public-blog`, with a Compose-managed
connector on CT110 and only `rafael.ink` routed through verified HTTPS to
NPM at `192.168.0.110:443`. NPM retains the existing blog/analytics routing.
Use the Host/SNI and default-deny rules above. Once the connector is verified,
replace only the apex A record with the proxied tunnel CNAME and remove the
apex from the DDNS domain list. Retain the previous DNS/DDNS settings for
rollback; they do not restore reachability while provider NAT remains in place.
Prepare the Git recovery contract and verify external pages, analytics, Pulse
coverage and the existing Homarr Production tile in the same eventual change.

Chrome was not running/connected when offered access, and no dashboard was
opened or changed. The earlier instruction not to implement remains in force
pending explicit implementation/activation authorization. No tunnel or code
was deployed and no credential, DNS, router or firewall configuration changed.
No provider was contacted and no prices or service eligibility were established.
