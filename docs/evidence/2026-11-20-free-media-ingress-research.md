# Free public media ingress research — 2026-11-20

Research draft for Jellyfin and Immich behind CGNAT: public HTTPS, no VPN client
on visitors' devices, no customer-operated VPS, and preferably the existing
`stream.rafael.ink` and `pictures.rafael.ink` names. Provider documentation,
pricing, terms, and public source code were checked on November 20. This is
research, not a provider deployment or a measured performance result. The
[existing Cloudflare trial](2026-11-20-public-media-tunnel-trial.md) is unchanged.

## Decision

Free hosted media relays exist. This research did not verify one offering all
of: a durable zero-price commitment, both existing custom HTTPS domains,
unmodified native clients, large Immich uploads, and reliable sustained media
throughput. Missing documentation is not proof that a feature fails; it is also
not evidence of an unlimited service.

- **Keep the two domains:** NetBird Cloud is the first free experiment to
  benchmark, with the explicit qualification that its proxy is free during beta.
- **Accept provider app addresses and a fixed allowance:** Seawise's ongoing
  free 100 GB/month offer is the clearest media-specific candidate found. Public
  mode may avoid its extra login, but native-client behavior remains untested.
- **Require long-term heavy streaming:** no verified free match emerged.
  Pangolin explicitly throttles hosted traffic; smaller free relays have caps,
  temporary beta offers, or material documentation gaps.

The assessment below updates the [November 5 comparison](2026-11-05-public-media-ingress-alternatives.md),
particularly its unresolved Pangolin limits. It does not authorize changing the
currently working tunnel trial or creating provider accounts.

## Two leading managed candidates

Both Pangolin Cloud and NetBird Cloud can supply the public relay themselves.
Their self-hosted variants are different: free software does not supply the
public server needed outside this home's CGNAT. Neither reviewed managed offer
supports an evidence-backed promise of unrestricted, reliable, free video
streaming and large Immich uploads.

| Question | Pangolin Cloud Basic | NetBird Cloud Reverse Proxy |
|---|---|---|
| Free today | Explicit Basic free plan, no card required | Explicitly no charge during the current beta; future pricing may change |
| Customer VPS / visitor VPN needed for public HTTP | No / no | No / no |
| Custom domain | Included; exact-hostname CNAME mode | Supported on Cloud through custom base domain/CNAME registration |
| Published numeric transfer allowance | No volume cap, but cloud proxy throughput is throttled | No numeric hosted bandwidth/transfer allowance established |
| Evidence for heavy media | Vendor directs streaming/high-bandwidth users to their own remote nodes | Vendor strongly recommends self-hosting for media streaming |
| Free plan capacity | 5 users, 5 sites, 5 domains, 15 public resources | Free account: 5 users and 100 machines; proxy-specific quota unspecified |
| Remaining important unknowns | Actual throttle rate, hosted upload cap/timeouts, sustained performance | Hosted bitrate/body/time limits, future price, sustained performance |

Plan counts are operator/platform identities, not a demonstrated limit on
Jellyfin or Immich application accounts when their own authentication is used.
The table summarizes the sources and qualifications below.

## Pangolin Cloud Basic

The [current pricing page](https://pangolin.net/pricing) explicitly includes
custom domains on free Cloud Basic, with five users/sites/domains, 15 public
resources and five machine clients. It is large enough for one home connector
and two applications. Self-hosted relay nodes are marked unavailable on Basic;
Team starts at $4 per user per month. A paid plan's greater object limits do
not, by themselves, establish faster hosted media throughput.

The important new finding is the [official bandwidth FAQ](https://pangolin.net/faq):
Cloud has no volume cap, but its reverse proxy and relayed connections are
throttled. Direct client-to-site connections escape that throttle because the
provider does not carry their traffic. That exception does not meet the request
for ordinary browser/native-app visitors without a Pangolin client. The FAQ
explicitly directs streaming/high-bandwidth users toward remote nodes on their
own infrastructure. No numeric throttle rate or guaranteed bitrate is published
there. “No bandwidth cap” must not be paraphrased as “unlimited streaming speed.”

[Pangolin's HTTP resource documentation](https://docs.pangolin.net/manage/resources/public/http-https)
provides public HTTPS resources with automatically managed certificates and
backends reached through site connectors. The
[domain guide](https://docs.pangolin.net/manage/domains) offers Cloud Single Domain
(CNAME) mode for an exact hostname, so the two media names can be moved individually
while retaining Cloudflare authoritative DNS and the existing blog route. No
whole-zone nameserver move is necessary for that mode.

The [remote-node guide](https://docs.pangolin.net/manage/remote-node/understanding-nodes)
explains the hybrid architecture: Pangolin Cloud manages identity/configuration,
but the operator runs the traffic termination point. Moving that point to an
external server restores responsibility for public infrastructure. It is not a
free hosted substitute for the requirement being researched.

[Pangolin authentication](https://docs.pangolin.net/manage/resources/public/authentication)
is a separate access layer. For unmodified native media apps, any extra browser
login must be bypassed/disabled for the selected public resource while retaining
Jellyfin/Immich authentication. That is an integration requirement, not proof
that either native app has been tested here.

The reviewed [terms](https://pangolin.net/tos) do not establish an express
blanket media prohibition comparable to Cloudflare's, nor do they promise
unlimited media service. No authoritative numeric hosted request-body ceiling,
read/upload timeout, WebSocket duration, or HTTP Range guarantee was established.
Self-hosted Traefik settings cannot establish those Cloud values.

**Assessment:** genuinely free public HTTPS with a good exact-domain fit, but
the provider's own throttle and streaming guidance weaken it as a durable free
Jellyfin recommendation. A small photo-browsing/low-bitrate trial is plausible;
large uploads and sustained playback remain unqualified.

## NetBird Cloud Reverse Proxy

This is a real managed public-ingress option, distinct from requiring every
visitor to join a mesh VPN. The [current overview](https://docs.netbird.io/manage/reverse-proxy)
says public traffic reaches NetBird's proxy cluster and is forwarded through
an encrypted tunnel to a home peer or routed resource. HTTP mode terminates TLS
at NetBird. The feature is still beta. A home connector is required; an external
customer server is not. The documentation also describes L4 modes, but availability
and port selection depend on cluster capabilities; they should not be assumed
to provide arbitrary free standard-port TLS passthrough.

The [pricing page](https://netbird.io/pricing) lists a €0 Cloud plan with five
users and 100 machines, but omits Reverse Proxy from its plan matrix. The more
specific primary evidence is the
[dashboard source](https://github.com/netbirdio/dashboard/blob/main/src/app/%28dashboard%29/reverse-proxy/services/page.tsx)
(lines 39–43, read directly from the provider's public repository): its
Cloud-only notice says the feature has no charge during beta and warns that
functionality and pricing can change at release. Thus this is **free now during
beta**, not a verified promise of a permanent free production-media tier.

[Custom domains](https://docs.netbird.io/manage/reverse-proxy/custom-domains)
work on Cloud using a base domain and a wildcard CNAME to the selected regional
cluster; no nameserver migration is required. Verification queries
`validation.<base-domain>`. Services append their chosen subdomain. Inference:
registering `rafael.ink` as the base allows `stream` and `pictures`; the existing
explicit media records would need scoped cutover, and the apex/blog can remain
separate. Exact dashboard acceptance has not been tested. Cloud shared clusters
currently use ZeroSSL/Sectigo certificates, so any CAA restriction must permit
that issuer. An EU region appears in the documented domain examples; no specific
Amsterdam placement or geographic routing guarantee is established.

[Authentication configuration](https://docs.netbird.io/manage/reverse-proxy/authentication)
allows a public proxy service with no added provider authentication. The
[official Jellyfin walkthrough](https://netbird.io/knowledge-hub/jellyfin-media-server-setup)
explicitly documents this native-client path and says an extra proxy login
breaks mobile/TV apps. It also **strongly recommends self-hosted NetBird for media
streaming**, particularly large 4K files. This is evidence of Jellyfin
compatibility, not an endorsement of unlimited Cloud streaming.

The [backend configuration guide](https://docs.netbird.io/manage/reverse-proxy/service-configuration)
labels Cloud Reverse Proxy shared and best-effort; sustained/high-volume traffic
may be rate-limited under fair-use rules. The
[terms, section 3.1](https://netbird.io/terms) permit limits on bandwidth,
connections and session duration, endpoint/region changes and suspensions. They
do not promise latency, availability or geographic routing. No blanket lawful
video prohibition was found in that section, but absence of a content ban is
not an unlimited transfer commitment.

No numeric Cloud Mbps rate, monthly GB budget, request-body maximum, HTTP
upload/stream duration or Range guarantee was established from those sources.
Configurable limits in the self-hosted software are not evidence of Cloud's
running configuration. Native client compatibility, WebSocket persistence,
seeking, 1 GB-plus Immich uploads, and throughput from this homelab all require
actual acceptance tests.

**Assessment:** strongest managed free-beta trial candidate if Rafael accepts
its uncertain post-beta price and best-effort throughput. It could be useful for
modest traffic, but research cannot honestly call it a proven long-term free
replacement that works well for sustained media streaming.

## Media-specific providers with free allowances

### Seawise

The [homepage](https://seawise.io/) explicitly welcomes Jellyfin/Plex/music
streaming and lists Immich among supported web apps. A home Docker connector
initiates the connection behind CGNAT; visitors can use an ordinary browser.
The [current pricing](https://seawise.io/pricing) gives the ongoing free plan one
server, 30 apps, one portal with up to 50 guests, and **100 GB per month**.
Incoming and outgoing traffic both count. Apps pause when the monthly allowance
and any purchased reserve are exhausted. Top-ups cost $5 per 100 GB; this report
does not propose buying them.

The [official client README](https://github.com/seawise-io/seawise-client)
describes individual app addresses on `seawise.dev`. The paid Admin plan's
custom **portal** domain is not evidence that an individual app can use
`stream.rafael.ink` or `pictures.rafael.ink`. No supported free mapping for those
exact app domains was established.

Apps are private by default, but [terms section 5.2](https://docs.seawise.io/legal/terms-of-service)
explicitly permits public apps/portals without provider sign-in. It would be
incorrect to claim a portal login is unavoidable. Inference: public mode could
allow native apps to reach their own authentication endpoints; actual Jellyfin
TV/mobile login and Immich background backup still need testing. Section 10
also allows HTTP-header/cookie adjustments for proxy operation.

The [privacy policy](https://docs.seawise.io/legal/privacy-policy) says request
and response bodies are not logged, while operational metadata is recorded.
Private app sessions last eight hours; custom portal sessions last 24 hours.
The relay/gateway provider is Hetzner; actual relay regions were not established.
These are published provider statements, not an independent audit.

No numeric body-size ceiling, long-stream/upload timeout, Range/206 guarantee,
WebSocket duration or measured throughput was established. Publicly linked app
guides could not be retrieved during research. A 100 GB allowance does not prove
that a single 1 GB upload succeeds.

**Assessment:** a real free option explicitly designed for media, especially
browser-based family sharing. It is worth a bounded trial if provider addresses
are acceptable, but it is not yet qualified as a same-domain native-app replacement.

### inrok

The [current product page](https://inrok.in/) advertises **100 GiB per 30 days,
three tunnels and persistent `*.share.inrok.in` URLs**, without a card, free
**during beta**. It also lists custom domains under a planned $8/month Pro tier.
Generic language about receiving the full beta product does not establish free
custom-domain entitlement. Paid plans are planned after beta, so this should not
be described as an ongoing free tier.

Its [terms](https://inrok.in/terms) explicitly allow lawful personal Jellyfin,
Plex, Navidrome, Immich, photo backup and file-sharing use. The service is
best-effort with no beta SLA. [Quota troubleshooting](https://inrok.in/docs/cli/troubleshooting)
says reaching the allowance stops traffic until the next cycle. Its
[HTTP guide](https://inrok.in/blog/expose-localhost-to-internet) supplies managed
HTTPS and an outbound connector; application authentication remains the owner's
responsibility.

The provider's [comparison page](https://inrok.in/blog/ngrok-alternatives)
places its hosted edge in India. That is a less convenient geography for a
Netherlands home and European viewers; no latency or throughput benchmark was
performed. The [privacy policy](https://inrok.in/privacy) says tunnel traffic
does not pass through Cloudflare, payloads are not inspected/stored, and
operational data is retained for 90 days. Audit logs have longer retention with
identifiers redacted upon deletion. These are provider commitments, not audited
facts about an installed connector.

No numeric upload ceiling, stream timeout, explicit Range/206 guarantee,
WebSocket duration, native-app verification or sustained rate was established.
**Assessment:** explicit media permission and a useful testing allowance, but
temporary beta pricing, provider-only names and India hosting make it weaker
for this particular homelab.

## Other free tunnels checked

| Provider | Current free offer / decisive constraint | Assessment for this request |
|---|---|---|
| [Tailscale Funnel](https://tailscale.com/docs/features/tailscale-funnel) | Available on all plans; visitors need no client; only `*.ts.net` names; non-configurable bandwidth limits with no numeric rate established | Credible experiment if different names are acceptable; no evidence of unrestricted media speed |
| [zrok/myzrok](https://zrok.io/pricing/) | 5 GB per rolling 24 hours; custom domains require Pro; a card removes the browser interstitial | Useful small tests, poor fit for sustained video and the two free custom domains |
| [ngrok](https://ngrok.com/docs/pricing-limits/free-plan-limits) | 1 GB/month outgoing transfer; 20,000 HTTP requests/month; assigned dev domain and browser interstitial | Transfer budget is too small; own domains are paid |
| [Packetriot](https://packetriot.com/pricing) | One tunnel and 1 GB/month | Transfer budget is too small; free custom-domain entitlement was not established |
| [Localtonet](https://localtonet.com/pricing) | One tunnel, 1 GB/30 days; free HTTP has no session timeout but has a visitor notice; custom domains paid | Media-capable proxy, inadequate free transfer allowance |
| [Playit](https://playit.gg/) | Game-specific protocols/UDP free; both generic TCP and HTTPS are now Premium | No free generic-TCP workaround; ordinary web media ingress is paid |
| [Pinggy](https://pinggy.io/) | Advertised unlimited transfer, but 60-minute sessions and random changing names | Persistent/custom URLs are paid; session expiry defeats always-on access |
| [localhost.run](https://localhost.run/docs/forever-free) | Free names change regularly; transfers have an unspecified speed limit | Custom stable domains and removal of the speed restriction require payment |
| [LocalXpose](https://localxpose.io/pricing) | Two HTTP/HTTPS tunnels, time limits and an interstitial | Custom domains and 24/7 availability are paid; current numeric free timeout not established |
| [Cruma](https://cruma.io/) | Registered free plan: 3 GiB per UTC day, personal use, no session limit; cap causes HTTP 429 | Custom domains are paid; daily allowance is small for video |
| [tunnelto.me](https://www.tunnelto.me/) | One custom domain free, 500 MB/month, one-hour sessions, 5 Mbps | Has free custom DNS, but too little capacity and only one domain |
| [tunnl.gg](https://tunnl.gg/) | Free provider addresses, two-hour idle timeout and 24-hour session cap | Own domains not established; explicitly positioned for development sharing |
| [Serveo](https://serveo.net/) | Three free tunnels and provider subdomains, with an interstitial | Docs acknowledge lower bandwidth/connection limits; sustained media capacity not established |

Specific qualifications:

- Tailscale Funnel terminates public TLS on the home node. The useful privacy
  property does not establish a numeric upload or throughput guarantee. Ordinary
  Tailscale mesh access remains a different product requiring visitor clients.
- zrok's [service limits](https://netfoundry.io/docs/zrok/myzrok/service-limits/)
  disable shares at quota exhaustion until rolling usage drops. It additionally
  limits each IP to 2,000 requests/300 seconds and each share to 7,500/300 seconds.
  Its [custom-domain guide](https://netfoundry.io/docs/zrok/myzrok/custom-domains/)
  requires Pro; the current pricing page does not publish clear Pro purchasing
  terms. Its payload-defense marketing does not establish a numeric upload cap.
- Localtonet [explicitly supports legitimate media streaming and large bodies](https://localtonet.com/blog/cloudflare-tunnel-alternative),
  but those technical capabilities do not enlarge the free transfer allowance.
- Playit's [HTTPS guide](https://playit.gg/support/https-tunnel/) requires Premium;
  [allowed applications](https://playit.gg/support/prohibited-uses/) include Immich.
  It remains a low-cost paid candidate from the earlier report, not a free one.
- [Serveo's documentation](https://serveo.net/docs/) says paid access increases
  bandwidth and connection limits. Absence of a numeric free cap is not unlimited
  media capacity. Free software such as rathole/boringproxy similarly does not
  supply an external managed relay merely by being free to download.

## An advertised unlimited offer that did not qualify

[21tunnel's pricing](https://www.21tunnel.com/pricing/) now advertises all features,
custom domains and unmetered/unthrottled fair-use transfer for free, plus a browser
interstitial. However, the [homepage](https://www.21tunnel.com/) still lists paid
custom-domain tiers, and its [custom-domain instructions](https://www.21tunnel.com/docs/custom-domains/)
say custom HTTPS certificates are not issued in v1. That guide instead recommends
Cloudflare's proxied Flexible mode in front of its HTTP edge.

That published arrangement would put media back through Cloudflare and leave
the Cloudflare-to-provider leg as HTTP. It does not solve this task's problem.
The conflicting pages may reflect documentation drift, but the working current
entitlement/TLS path was not established. Its [inspection documentation](https://www.21tunnel.com/docs/)
also describes captured headers/bodies with retention. No account was created;
this service is not recommended for the private media trial from the available
evidence.

## Translate allowances into actual use

Calculated using decimal GB, excluding protocol overhead, audio/subtitle changes,
thumbnail traffic, uploads and any provider counting both directions:

| Aggregate video bitrate | Data per hour | Viewing from 100 GB | Two hours daily for 30 days |
|---|---:|---:|---:|
| 5 Mbps | 2.25 GB | 44.4 hours | 135 GB |
| 10 Mbps | 4.5 GB | 22.2 hours | 270 GB |
| 20 Mbps | 9 GB | 11.1 hours | 540 GB |
| 50 Mbps | 22.5 GB | 4.4 hours | 1,350 GB |

At 10 Mbps, 1 GB lasts about 13 minutes, and zrok's 5 GB about 67 minutes.
inrok's 100 **GiB** is about 107.4 decimal GB, or 23.9 hours at 10 Mbps before
overhead. Simultaneous viewers add their bitrates. These are budget calculations,
not measured provider speeds. Immich backups consume the same relay budget;
where both directions are billed, uploads matter as much as viewing.

Cloudflare R2's [10 GB storage allowance and free egress](https://developers.cloudflare.com/r2/pricing/)
are a different architecture: files must be stored in R2, with request/storage
metering. They do not expose the existing Jellyfin and Immich applications behind
CGNAT. Similarly, a free VPS might lower the bill but still leaves a VPS to operate.

## What would establish a useful free trial

For NetBird or another candidate, test with a separate temporary hostname before
moving either existing media name. Preserve application authentication and avoid
an added provider browser login on native-client endpoints. Measure:

1. Actual Jellyfin browser and mobile/TV login, an hour-long playback, seeking
   with HTTP Range/206, resume and WebSocket continuity.
2. Native Immich background backup; individual uploads above 100 MB and at least
   1 GB, then original download and video seeking.
3. Simultaneous playback and upload through an external/mobile network, the
   observed sustained rate, and the provider's transfer counter.
4. Connector restart recovery, correct host/scheme/client-IP forwarding, and
   isolation from unrelated private homelab services.

These checks have **not** been run for any researched alternative. A public
login page alone cannot qualify media performance. The existing Cloudflare
trial remains the only newly activated ingress; this research created no
runtime, account, subscription, backup, secret or temporary worktree and sent
no provider messages. Final findings are retained with this file on the existing
`codex/public-media-tunnel-trial` review branch.
