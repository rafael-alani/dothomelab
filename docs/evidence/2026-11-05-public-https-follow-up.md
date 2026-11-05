# Public HTTPS follow-up — November 5, 2026

The blog's missing HTTP-to-HTTPS redirect is repaired. Public media access is
still unresolved; no claim of full three-domain recovery is made.

## Observed state and cause

Inspected from the operator Mac and PVE/CT110 against repository revision
`2ca65f396ba55116484b9c1074e1fc4ced56463c`. The existing connector remains deployed
at `9234544beeb3fad6469baf76dd217e864d60c1e0` and reports healthy. Its token was
already installed; the earlier hidden-prompt handoff is no longer pending.

| Hostname | Public state before this change | Direct NPM HTTPS |
|---|---|---|
| `rafael.ink` | HTTP 200 and trusted HTTPS 200 through Cloudflare Tunnel | 200 |
| `stream.rafael.ink` | DNS-only A to `168.222.147.138`; TCP 80/443 timeout | 302 to `/web/` |
| `pictures.rafael.ink` | Proxied A to `168.222.147.138`; HTTP/HTTPS response timeout | 200 |

All three NPM routes have Force SSL enabled, valid TLS, and the expected targets:
blog `.115:8084`, Jellyfin `.112:8096`, Immich `.112:2283`. Direct local HTTP
returns 301 for all three. The media applications and proxy certificates are
healthy; their public routes still depend on the connection affected by the
[confirmed CGNAT](2026-11-04-public-blog-ingress-options.md).

Pi-hole `.100` returns the same public answers for these three names. Thus
those names also take the broken public path when used on the LAN. The existing
private `immich.rafael.media` name resolves to `.110`. Infra Tailscale reports
Running with no health warnings; external client routing was not tested.

## Change and verification

Cloudflare dashboard showed **Always Use HTTPS: Off** for the Free Website
zone. It is now **On**, read back in the dashboard. This is a zone-level setting
for proxied hostnames. DNS-only `stream.rafael.ink` does not pass through it.
The tunnel always connects to NPM over HTTPS, explaining why NPM's HTTP redirect
did not cover public HTTP visitors.

Operator `curl --noproxy '*'` requests through public DNS reached Cloudflare
`104.21.36.237`, with no insecure TLS flag:

- `http://rafael.ink/`: 301 to `https://rafael.ink/`.
- `http://rafael.ink/about?https-check=1`: 301 to
  `https://rafael.ink/about?https-check=1`.
- HTTPS `/`, `/about`, `/feed.xml`, `/telemetry/script.js`: all 200, TLS
  verification result zero.

These checks exercise the public Cloudflare edge from the home connection;
they are not a new independent off-site probe or an authenticated media workflow.

All four existing `blog-production-https` probes pass. Pulse reports the blog
connector, Jellyfin and Immich server online. Homarr retains the blog HTTPS tile
and private Immich link. These shared probes do not establish WAN media access
or detect the missing edge redirect by themselves.

## Remaining media decision

Cloudflare's current documentation explicitly says public Tunnel hostname routes
on Free/Pro/Business plans are subject to its video and large-file restrictions.
Free/Pro proxied uploads are limited to 100 MB per request. Merely adding the
media hostnames would not provide reliable unrestricted Jellyfin/Immich access.
[Tunnel/media policy](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/delivering-videos-with-cloudflare/),
[service terms](https://www.cloudflare.com/service-specific-terms-application-services/),
[upload limits](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/).

Public use without a client VPN needs a suitable public ingress outside the
CGNAT connection, or provider-restored public connectivity. Private use can
reuse Tailscale with DNS directed to the local proxy. Rafael was asked which
access model is required. Neither the media DNS records nor their exposure,
credentials, application state or deployment were changed.

## Recovery and retained state

The [tunnel runbook](../../hosts/infra/blog-tunnel/README.md) now records the edge
redirect as an external rebuild prerequisite. Restore the prior behavior by
setting Always Use HTTPS back to Off; this does not alter the tunnel or DNS.
No container, image, data or secret changed and no new backup was necessary.
No temporary runtime or new worktree was created. Existing rollback archives
remain as listed in the [original tunnel report](2026-11-04-public-blog-tunnel.md).
