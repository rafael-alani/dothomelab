# Public media ingress without operating a VPS

Research date: 2026-11-05. This is a research draft, not an implemented ingress
change. Prices are the published USD prices checked on that date; taxes,
currency conversion, and unpublished contractual terms are excluded.

## Requirements and method

The requested result is public HTTPS for Jellyfin at `stream.rafael.ink` and
Immich at `pictures.rafael.ink`, reachable through ordinary browsers and native
apps without installing a VPN on those clients. The home connection is behind
CGNAT. Rafael does not want to operate a VPS. Streaming, seeking, WebSockets,
photo downloads, and large video uploads matter; an HTML login page alone is
not a successful acceptance test. The blog at `rafael.ink` can use its separate
ingress.

This report distinguishes a provider-operated public relay from software that
still needs the customer to supply a public server. Findings use provider
documentation, pricing, and terms. Missing published limits are recorded as
unknown, never interpreted as unlimited. No provider account was created,
subscription purchased, support request sent, or public configuration changed
for this research.

## Decision

**A VPS is not required.** A public relay must exist somewhere while the home
connection remains behind CGNAT, but a tunnel provider can operate it. A small
connector at home initiates the connection; visitors use ordinary HTTPS. The
earlier VPS-or-client-VPN framing was incomplete.

The best first paid trial is **Playit Premium HTTPS**. It preserves the two
existing names and Cloudflare DNS, keeps TLS termination at home, and has
positive evidence for media use. **Packetriot Basic** is the alternative with
a clearly published transfer allowance. **Pangolin Cloud Basic** is the strongest
free candidate, conditional on confirming hosted media limits and native-client
authentication behavior. These are research recommendations, not validated
production deployments. Detailed sources and remaining gaps follow.

| Shortlist | Published price | Existing names without moving Cloudflare DNS | Principal tradeoff |
|---|---:|---|---|
| Playit Premium HTTPS | $3/month | Yes, CNAME | Local TLS; informal rather than contractual bandwidth assurance |
| Packetriot Basic / Pro | $5 / $10 monthly | Yes, TXT verification and CNAME | 1 / 2 TB monthly; accounting and quota-exhaustion details need confirmation |
| Pangolin Cloud Basic | Free | Yes, individual CNAMEs | Hosted TLS; media/upload/throughput limits not established |
| OVPN + Public IPv4 | $16/month on monthly billing | Yes, ordinary A records | Provider runs relay; home-side WireGuard and firewall need more configuration |

## Playit Premium HTTPS

The current [HTTPS tunnel guide](https://playit.gg/support/https-tunnel/) supports
normal port-443 URLs on external domains, multiple domains on a gateway, and
CNAME records at the existing DNS provider. Its HTTPS-specific CNAME flow is
newer than the general external-domain instructions that use nameserver
delegation. The guide explicitly leaves TLS termination on the local server.
Reusing the existing valid media certificates is therefore plausible; integration
with NPM remains untested. [Premium is advertised at $3/month](https://playit.gg/).

[Permitted applications](https://playit.gg/support/prohibited-uses/) explicitly
include Immich. Jellyfin is not individually named. In a
[May 2026 operator reply](https://discuss.playit.gg/t/traffic-limits/5574) to a
media/file-server question, Playit describes no fixed traffic ceiling, with
exceptional usage subject to intervention and Europe/North America comparatively
inexpensive to serve. This is useful positive evidence, not an unlimited-bandwidth
contract or a guaranteed bitrate.

No provider HTTP upload-body cap was found. Passing encrypted TLS through the
relay avoids provider-side HTTP body parsing, but does not prove unlimited
connection duration or adequate sustained speed. No native-app or large-file
test has been performed. HTTP port-80 redirect behavior also needs verification;
an HTTPS tunnel alone does not establish it. The
[terms](https://playit.gg/terms/) do not guarantee uninterrupted availability.

**Assessment:** best first paid trial for this homelab. It can preserve TLS at
home and avoid a wholesale DNS move. Confirm both hostname entitlements and
complete the media acceptance checks before calling it restored.

## Packetriot

[Basic costs $5/month with 1 TB/month; Pro $10 with 2 TB](https://packetriot.com/pricing).
Both have enough tunnels for this task. The free plan's 1 GB/month is unsuitable
for media. The provider explicitly documents
[remote Plex hosting](https://packetriot.com/tutorials/posts/setting-up-plex/),
which is positive evidence that media serving is an intended use, although it
does not certify Jellyfin or Immich compatibility.

The [CLI documentation](https://docs.packetriot.com/packetriot_cli/) supports
multiple HTTP services per tunnel, custom-domain TXT verification and ordinary
A/CNAME records. Its custom-domain Let's Encrypt certificates reside at the
home connector, which can terminate TLS. Provider-assigned names have different
certificate behavior; those should not be confused with custom domains.

The inspected documentation does not establish a numeric sustained bitrate,
HTTP upload cap, request/idle timeout, ingress-versus-egress accounting, or the
managed service's precise behavior at quota exhaustion. Documentation for the
self-hosted Spokes product is insufficient to establish those managed-plan
terms. [Service terms](https://packetriot.com/policies/tos) disclaim uninterrupted
availability; the published allowance is not an SLA.

**Assessment:** strong alternative for a predictable monthly transfer budget.
Confirm accounting and large-upload behavior; choose capacity from measured
usage rather than assuming 1 TB is ample.

## Pangolin Cloud

**It really can avoid a VPS.** Pangolin Cloud operates the dashboard, database,
certificates, and globally distributed nodes. Public HTTP resources work through
those hosted nodes. A customer-operated remote node is optional; fully
self-hosted Pangolin and its remote-node mode do require customer-operated
infrastructure. Cloud public raw TCP/UDP listeners also require a remote node,
but Jellyfin and Immich can use HTTP resources instead.
[Cloud versus self-hosted](https://docs.pangolin.net/about/pangolin-cloud-vs-self-hosted)

Public HTTP/HTTPS resources expose a public hostname with an automatically
managed TLS certificate, connect through an outbound site connector behind NAT,
and require no Pangolin client for visitors. Pangolin terminates public HTTPS
before forwarding through the connector, so this puts the hosted proxy inside
the traffic trust boundary.
[HTTP/HTTPS resources](https://docs.pangolin.net/manage/resources/public/http-https)

The current Cloud Basic tier is **free** and lists custom domains, five users,
five sites, five domains, and 15 public resources. Team is **$4/user/month**;
Business is **$9/user/month**. These are the currently published plans; the page
does not publish a bandwidth allowance or per-GB overage price. Older third-party
descriptions of 25 GB plans are insufficient evidence for today's limits.
[Current pricing](https://pangolin.net/pricing)

Each existing hostname can use Pangolin's single-domain CNAME setup. Whole-zone
nameserver delegation is unnecessary for these two hostnames, so choosing
Pangolin need not move the blog or the other records from Cloudflare DNS.
[Domain configuration](https://docs.pangolin.net/manage/domains)

Pangolin authentication is enabled by default and redirects unauthenticated
requests to a browser login. For native media apps, the proposed configuration
must avoid an extra browser-only login barrier and retain the applications'
own authentication. This is an integration requirement inferred from the
documented redirect behavior, not a tested client result.
[Public-resource authentication](https://docs.pangolin.net/manage/resources/public/authentication)

The reviewed hosted-service terms do not contain an express video/media
prohibition. They require compliance with documented limits and allow service
changes. **Neither the terms nor the pricing page establish an unlimited media
service commitment.** No authoritative hosted-node request-body ceiling,
upload/read timeout, sustained throughput guarantee, explicit HTTP Range
guarantee, or WebSocket duration limit was found in the reviewed public pages.
Self-hosted Traefik settings do not prove the settings of Cloud's hosted nodes.
[Terms, modified June 9, 2026](https://pangolin.net/tos),
[pricing](https://pangolin.net/pricing)

**Assessment:** a genuine no-VPS candidate with unusually attractive entry
pricing, but not yet qualified for sustained Jellyfin streaming and large Immich
uploads. Hosted bandwidth/fair-use and request limits remain an explicit gap
before selecting it as the durable solution.

## NetFoundry zrok / myzrok

The NetFoundry-hosted service publishes public HTTPS shares from an outbound
connector; visitors use an ordinary HTTPS URL. It offers automatic certificates.
The current public Free plan is **5 GB/day**, 25 environments, and 50 share
backends. Adding a card removes the browser interstitial. Production workloads
and custom limits are now directed to commercial enquiries; the current pricing
page does not publish a purchasable Pro price or overage rate.
[Current zrok pricing](https://zrok.io/pricing/)

Current version-2 documentation nevertheless says custom domains require a
**myzrok Pro subscription**. This is a pricing/documentation inconsistency:
custom domains exist technically, but their presently available commercial
terms cannot be established from these pages. The documented model appends a
reserved share name to a custom base domain. Using base `rafael.ink` with names
`stream` and `pictures` appears to fit the required names, but exact coexistence
with the existing apex/blog and narrowly scoped DNS must be verified before
cutover.
[Custom domains](https://netfoundry.io/docs/zrok/myzrok/custom-domains/)

The allowance is a **rolling 24-hour window**, not a reset at midnight. Exceeding
it disables running shares and prevents new ones until usage falls below the
limit. Public shares also limit each IP to 2,000 requests per 300 seconds and
each share to 7,500 requests per 300 seconds, with bursts allowed inside those
windows. Inference: the per-IP limit can affect concurrent clients behind one
mobile/carrier NAT, and thumbnail-heavy photo browsing merits testing.
[Hosted service limits](https://netfoundry.io/docs/zrok/myzrok/service-limits/)

For scale, 5 GB permits only approximately **67 minutes at 10 Mbit/s** before
protocol overhead and other traffic. This is arithmetic, not a service speed
claim. A single large backup/upload can also consume the day's allowance.

The provider describes large-upload defenses but does not publish their exact
body-size threshold on its pricing page. A hosted upload cap, streaming timeout,
WebSocket duration limit, and explicit Range-request guarantee were not
established. Therefore the free offer cannot be called a verified Immich ingress.
[Published payload-defense description](https://zrok.io/pricing/)

The similarly named **personalized frontend** is a different arrangement: its
official guide explicitly requires a VPS or container hosting. Hosted public
frontends can log URLs, headers, and other request information; private shares
with a customer frontend conceal that traffic content from the hosted service,
but reintroduce the public frontend infrastructure requirement.
[Personalized frontend and privacy](https://netfoundry.io/docs/zrok/concepts/personalized-frontend/)

**Assessment:** not the leading durable media choice on the verifiable public
offer. Its small hard daily allowance, unresolved paid-domain pricing, and
unpublished large-upload behavior are material gaps. The self-hosted/personalized
frontend routes do not remove the customer's public-server responsibility.

## ngrok

ngrok agents initiate outbound connections to the managed service, which
provides the public endpoint. No client VPN or customer VPS is necessary.
[Agent architecture](https://ngrok.com/docs/gateway/agent)

Using `stream.rafael.ink` and `pictures.rafael.ink` requires **Pay-as-you-go**;
Free and Hobbyist cannot bring those domains. Pay-as-you-go has a **$20/month
minimum with $20 usage credit**. It includes 5 GB, then charges **$0.10/GB** at
the initial tier. It includes 100,000 HTTP requests, then **$1/100,000**, with
volume discounts. The published request-rate limit is 20,000/minute.
[Pricing and limits](https://ngrok.com/docs/pricing-limits)

There are two separate hourly meters: **$0.02 per active endpoint hour** plus
**$0.01 per active custom-domain hour**. An active hour is a clock hour with
traffic, so regular monitoring can make both hostnames active all month. Data
transfer out explicitly includes traffic sent **to the agents**, meaning Immich
uploads count too. Automated certificates are included; the separate expensive
bring-your-own-certificate add-on is not needed for ordinary HTTPS.
[Full pricing table](https://ngrok.com/pricing)

Illustrative 30-day calculation for two continuously active hostnames:
`2 × 720 × ($0.02 + $0.01) = $43.20`. Adding 1,000 GB of billable transfer costs
`(1,000 − 5) × $0.10 = $99.50`: **$142.70 total**, before requests, extras or tax.
The base fee's credit is already accounted for; do not add another $20.
[Meters](https://ngrok.com/pricing),
[base fee and credit](https://ngrok.com/docs/pricing-limits)

ngrok documents **no request-body or response-body size cap**, no total HTTP
round-trip/request/response timeout, and a **five-minute idle timeout**. It
supports WebSockets automatically. Public HTTP endpoints terminate TLS in
ngrok's cloud; forwarding with HTTPS to the origin does not remove that
termination point. Traffic inspection can capture bodies, so a media deployment
should configure inspection deliberately. Its documentation calls the proxy
HTTP-compliant; explicit Jellyfin seeking/Range behavior still needs a real
test. These protocol statements apply to normal HTTP forwarding, not every
optional buffering/WAF action.
[HTTP endpoint behavior and limits](https://ngrok.com/docs/gateway/endpoints/http)

Pay-as-you-go has no interstitial. Edge OAuth/Basic authentication is optional;
the native application login flow should remain responsible for user access.
[Plan features](https://ngrok.com/pricing),
[HTTP authentication](https://ngrok.com/docs/gateway/endpoints/http)

No blanket video-serving prohibition was found in the reviewed acceptable-use
terms; ordinary content/use restrictions still apply. That observation is not
a claim of special media-service approval. ngrok operates a multi-tenant data
plane and a separate US-based control plane.
[Terms](https://ngrok.com/tos),
[security architecture](https://ngrok.com/security)

**Assessment:** technically the clearest documented large-upload/long-stream
candidate among these three, but expensive for continuous media use. Avoid
describing it as simply a $20/month replacement for a VPS.

## Public-IP VPN services: VPN at home, ordinary HTTPS for visitors

This is a distinct no-VPS option: the home gateway makes an outbound VPN
connection to a provider that forwards a public IP/ports back to it. Visitors
need no VPN application. A generic consumer VPN subscription is insufficient;
inbound forwarding on the necessary ports must be supported.

**OVPN Public IPv4** explicitly offers a static dedicated IPv4 with all ports
open, WireGuard/OpenVPN support, and media/web-server use. The add-on is
[$4/month](https://www.ovpn.com/en/features/public-ipv4), on top of the VPN
subscription: [$12/month billed monthly](https://www.ovpn.com/en/pricing),
or $4.99/month equivalent on the currently advertised annual plan. Totals are
$16/month or approximately $8.99/month equivalent respectively, assuming that
add-on rate. Published add-on pricing is for normal consumer usage; commercial
high-bandwidth use requires a separate agreement. A numerical consumer traffic
allowance was not established.

An isolated home connector would forward only the selected web ports to a
restricted public proxy. This preserves local TLS and normal DNS A records,
but requires return routing and firewall work. Attaching an all-ports public IP
directly to a general-purpose Infra interface would be too broad. This is more
network configuration than Playit's application tunnel, although there is no
external operating system to administer.

**GetAStatic** provides another managed WireGuard/public-IP variant. Its
[published plans](https://getastatic.com/) include $4/month for 100 Mbps and
1 TB, $10 for 1 Gbps and 5 TB, and $15 for unlimited transfer at 100 Mbps. Uploads
and downloads both count on capped plans; quota exhaustion pauses the tunnel.
Its listed locations are Kansas City, San Jose and Hong Kong, so this is less
attractive for an Amsterdam homelab than a European relay. These are advertised
ceilings, not tested performance. Provider longevity and operational reliability
were not established. An existing domain can point to the supplied IP; its
optional provider-hostname purchase is not inherently necessary for that.

**Portmap.io** advertises OpenVPN-backed HTTP/HTTPS/TCP/UDP forwarding, own
domains, SSL certificates and unlimited transfer for
[$3.99/month or $29.99/year](https://portmap.io/). Public documentation retrieved
did not establish the exact standard-port/custom-certificate workflow, sustained
throughput, upload timeouts or acceptable sustained media volume. It remains a
plausible reserve option, not a stronger evidenced recommendation than the
shortlist. Its free random-port plan does not meet the requested URLs.

## Other hosted tunnels and excluded alternatives

| Option | Published offer | Why it is not the first choice here |
|---|---|---|
| Pinggy Pro | [$3/month; $2.50/month annually](https://pinggy.io/blog/best_ngrok_alternatives/), advertised unlimited transfer | Technically promising, but the content terms need clarification before private-media use |
| Localtonet PAYG | [About $4/month for two continuously active tunnels](https://localtonet.com/blog/introducing-pay-as-you-go-pricing-for-localtonet) | Explicit media support, but documented custom-domain onboarding moves the root domain's nameservers |
| localhost.run | [$9/month billed annually; five simultaneous tunnels](https://localhost.run/docs/custom-domains) | Custom domains and local TLS supported; media policy, traffic quota and upload limits insufficiently documented |
| Inlets Cloud | [$25/month Personal, up to five tunnels](https://inlets.dev/pricing/) | Real hosted option, but Cloud documentation still describes invitation/beta access and lacks clear managed-media allowances |
| Tailscale Funnel | [Available on all plans](https://tailscale.com/docs/features/tailscale-funnel) | Public visitors need no VPN, but only tailnet `*.ts.net` names are supported and non-configurable bandwidth limits apply |
| PageKite | [Published paid allowances start at 15 GB for $5.99](https://pagekite.net/signup/?more=bw) | Pricing page says new subscriptions cannot currently be processed; quotas are also poor value for media |
| Remote.It | [Business $30/month, $25/month annually](https://www.remote.it/pricing/) | Persistent splash-free public URLs exist, but the required own-domain workflow was not established |

Pinggy can use a [DNS-only CNAME](https://pinggy.io/docs/custom_domain/) and
[multiple hostname routes in one tunnel](https://pinggy.io/docs/http_tunnels/multi_port_forwarding/).
One wildcard configuration appears sufficient for both names, but exact paid-seat
entitlements need checkout verification. It offers
[TLS passthrough](https://pinggy.io/docs/tls_tunnels/) and
[explicit video/unlimited-transfer marketing](https://pinggy.io/compare/pinggy-vs-ngrok/).
However, its [User Content terms](https://pinggy.io/terms_of_service/) use broad
language about non-confidential content, exclusive ownership and a perpetual
content licence. The scope's application to private tunneled media needs written
clarification; this report is not a legal determination. TLS passthrough limits
technical access to plaintext but does not resolve that ambiguity.

Localtonet explicitly promotes
[legitimate Jellyfin streaming and unrestricted HTTP request bodies](https://localtonet.com/blog/cloudflare-tunnel-alternative).
Its [custom-domain guide](https://www.localtonet.com/documents/guides/add-a-custom-domain)
requires the root domain and replacement authoritative nameservers. No supported
CNAME-only exception was found. Moving `rafael.ink` out of Cloudflare would
unnecessarily affect the working blog tunnel and other records. This makes the
documented setup a poor fit despite the low price and positive media evidence.

localhost.run documents [local TLS passthrough](https://localhost.run/docs/tls-passthru-tunnels)
and removes the [free tier's speed restriction](https://localhost.run/docs/forever-free)
on its paid custom-domain plan. That does not establish a guaranteed Mbps rate
or unlimited monthly transfer. Inlets [Cloud documentation](https://docs.inlets.dev/cloud/)
offers hosted London/Virginia endpoints, custom domains and either managed TLS
or TCP passthrough for 80/443; invitation/beta wording and unspecified hosted
traffic terms make it a weaker immediate recommendation.

[ZeroTier's normal setup](https://docs.zerotier.com/start/) requires participating
clients and does not independently supply the desired public web gateway.
[rathole](https://github.com/rathole-org/rathole) and
[boringproxy](https://github.com/boringproxy/boringproxy) are useful relay software,
but still need a public server to run the relay. A free-tier VPS changes cost,
not responsibility for operating it. Bare
[bore public TCP forwarding](https://github.com/ekzhang/bore) does not establish
a supported persistent custom-domain HTTPS media service. Hole punching alone
does not make existing browser/TV/mobile HTTP clients CGNAT-aware.

## ISP public connectivity and IPv6

Obtaining a reachable IPv4 address or a provider-side inbound mapping would
remove the need for a relay. The router's CGNAT address means changing its local
port forwards, DDNS or UPnP alone cannot create that upstream reachability.
The [live follow-up](2026-11-05-public-https-follow-up.md) also found no usable
public IPv6 address/default route on Infra.

ITT Desk's [published FAQ](https://www.ittdesk.nl/veelgesteldevragen/) discusses
shared NAT, a Power-plan SNAT option, and no announced IPv6 rollout in that
document. Its scope is recreational properties, so it cannot establish Rafael's
connection entitlement. SNAT for gaming also does not prove inbound 80/443
hosting. Eligibility, price and current IPv6 availability require the provider
to answer for this specific connection. No provider contact was made.

If available, native IPv6 can serve IPv6-capable visitors directly, but IPv4-only
visitors still require a reachable IPv4 gateway. Thus IPv6 alone is not a
universal replacement for the requested public service.

## Why the existing Cloudflare Tunnel remains blog-only

Cloudflare explicitly applies its media-delivery terms to
[public Tunnel hostname routes on Free, Pro and Business](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/delivering-videos-with-cloudflare/).
The private-network exception does not satisfy the no-client-VPN requirement.
Free/Pro also have a
[100 MB incoming request limit](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/).
Chunking can address a per-request limit only where the application supports it;
it does not settle media policy. Disabling cache does not establish an exception.
Cloudflare Stream stores/transcodes video and is not a drop-in Jellyfin proxy.

Keep Cloudflare as authoritative DNS and keep the working blog tunnel. Route
the media names to the chosen provider with Cloudflare proxying disabled, or
traffic would still pass through Cloudflare's proxy restrictions.

## Transfer budget and architecture

Calculated decimal transfer, excluding protocol overhead:

| Aggregate bitrate | Per hour | At two hours daily for 30 days |
|---|---:|---:|
| 8 Mbit/s | 3.6 GB | 216 GB |
| 20 Mbit/s | 9 GB | 540 GB |
| 50 Mbit/s | 22.5 GB | 1,350 GB |

Simultaneous viewers add together. Immich originals/uploads add more traffic.
Provider accounting may count both directions or relay legs; confirm it rather
than treating the table as an invoice estimate. The home upstream remains a
ceiling for remote playback regardless of provider.

For a Playit trial, the conceptual route is:

```text
Browser / Jellyfin client / Immich app
  -> existing media hostname, HTTPS
  -> provider-operated public relay
  -> outbound connector at home
  -> restricted local TLS proxy
  -> Jellyfin or Immich
```

All storage stays at home. In TLS-passthrough mode the media HTTPS session ends
at home; with a hosted HTTP proxy such as Pangolin, it ends at that provider.
That is a concrete privacy difference, independent of where files are stored.
Local DNS can send LAN clients directly to the home proxy using the same URLs.
No provider login/interstitial should precede application authentication in
native clients.

Before cutover, remove only the migrated media names from DDNS management,
preserve existing DNS/DDNS configuration for rollback, and restrict accepted
hosts at the public proxy. Forwarding into the shared NPM listener must not
accidentally expose unrelated private virtual hosts through a changed Host
header. Record trusted proxy/client-IP handling and keep credentials out of
request logs. Provider selection is not authorization to purchase or deploy.

## Verification still required for any shortlisted service

These are proposed acceptance criteria, not completed tests:

- Public HTTPS and certificate renewal for the exact two hostnames, with no
  VPN on a cellular/external client and HTTP redirected to HTTPS.
- Jellyfin browser and actual mobile/TV client login, playback, long sessions,
  seeking/resume with HTTP Range/206, and WebSocket connections.
- Immich native-app login and background uploads; individual video uploads
  beyond 100 MB, at least 1 GB, and at least the largest normal user file;
  original download, video seeking, and `/.well-known/immich` routing.
- Measure realistic concurrent streaming/upload throughput, and inspect
  provider usage accounting against an explicit monthly budget.
- Retain app authentication, forwarded-host/scheme correctness, and trusted
  proxy/client-IP configuration; verify connector restart recovery and denial
  of unrelated hostnames, including mismatched TLS SNI and HTTP Host.
- Determine the provider's actual bandwidth allowance, cutoff/overage behavior,
  media policy, upload limits, and idle/total timeouts. A missing limit in a
  public page is unresolved evidence, not acceptance.

Immich's [proxy requirements](https://docs.immich.app/administration/reverse-proxy/)
call for large uploads, correct forwarded headers and suitable timeouts; its
Traefik example specifically warns about the default short upload timeout.
Jellyfin's [proxy requirements](https://jellyfin.org/docs/general/post-install/networking/reverse-proxy/)
require WebSockets and trusted-proxy handling and warn about authentication
material in request URLs. These must be tested through the chosen hosted path.

Then verify Pulse, external/shared probes and the appropriate Homarr entries.
The current three-domain task remains incomplete until media acceptance passes.
Research created no runtime, backup, secret or temporary worktree. Existing
rollback artifacts remain owned by their original operational reports.
