# Public blog tunnel

CT110 runs the pinned, manually updated `cloudflare-blog-tunnel` connector.
It replaces inbound port forwarding for **only `rafael.ink`** after the provider
moved the connection behind CGNAT. It has no published ports, persistent volumes,
Docker socket or privileged capabilities. The existing blog publisher is unchanged.

Cloudflare's remotely managed tunnel is declared in [ingress.json](ingress.json):
`rafael.ink` → tunnel → trusted HTTPS NPM `192.168.0.110:443` → existing native
production blog on CT115. Both origin SNI and Host are `rafael.ink`; certificate
verification stays enabled. All unmatched tunnel hostnames return 404. No private
staging or other service hostname is enrolled.

In Cloudflare's `rafael.ink` zone, **SSL/TLS → Edge Certificates → Always Use
HTTPS must be On**. NPM's Force SSL setting alone does not redirect public HTTP:
the connector reaches NPM over HTTPS even when the visitor used HTTP. The edge
redirect preserves the requested path and query string. This zone setting is an
external rebuild prerequisite alongside the remote tunnel and DNS record.

## Credentials and recovery prerequisites

The connector token belongs only in PVE `/root/.env` as
`CLOUDFLARE_BLOG_TUNNEL_TOKEN`. The interactive helper accepts either the token or the copied Windows/Docker
installation command, validates its account/tunnel identity and never echoes or
executes the pasted input. The existing DNS API token remains scoped
to DNS; it cannot create/configure tunnels. Use the authenticated Cloudflare
dashboard to recreate the declared tunnel/ingress if the remote object is lost,
then update its declaration and connector credential through an authorized change.
The dashboard is an external rebuild prerequisite; a restored connector token
cannot recreate a deleted tunnel. Outbound TCP or UDP 7844 must work.

## Deploy and cut over

Run from the PVE Git checkout after fetching the approved revision. This keeps
an immutable source archive on PVE and CT110 without replacing other CT110 code.

```bash
bash hosts/infra/blog-tunnel/deploy.sh <commit> --archive-only
bash /opt/dothomelab-blog-tunnel/releases/<commit>/hosts/infra/blog-tunnel/manage.sh store-token
bash hosts/infra/blog-tunnel/deploy.sh <commit>
bash /opt/dothomelab-blog-tunnel/current/hosts/infra/blog-tunnel/manage.sh prepare-dns
# Configure only the declared ingress in Cloudflare, with TLS verification enabled.
bash /opt/dothomelab-blog-tunnel/current/hosts/infra/blog-tunnel/manage.sh switch-dns
pct exec 110 -- bash /opt/dothomelab-blog-tunnel/current/hosts/infra/blog-tunnel/verify.sh
```

`prepare-dns` retains the old environment and exact apex record, removes only the
apex from `DOMAINS`, validates Compose quietly, then recreates only DDNS using its
current image. It refuses a local tag that differs from the running image and
verifies the recreated container's domain list. Other managed names remain unchanged. `switch-dns` requires a ready
connector and replaces only the saved apex record with the proxied tunnel CNAME.
The dashboard may save ingress while warning that DNS could not be created
because the old A record exists; use `switch-dns` to replace that saved record
rather than deleting it in the dashboard. Check the remote ingress against the
declaration before switching DNS. Helpers
refuse unexpected DNS identities or values rather than overwrite intervening work.

Clean bootstrap deploys the same Compose service from its normal guest archive.
Keep `DOMAINS` free of `rafael.ink`; DDNS must never replace the tunnel CNAME.
The connector has no appdata beyond the operator's rollback directory. Secrets
follow the existing `/root/.env` recovery contract, and the rollback directory is
inside appdata backup coverage. No guest-root backup is required.

## Verification and rollback

Check public HTTPS through public DNS, not the Pi-hole LAN override. Confirm the
home page, an article, media and analytics endpoints. Pulse automatically discovers
the Docker connector through its existing CT110 agent; verify it is healthy.
The blog's existing Homarr Production tile remains the user entry point. A
background connector has no additional dashboard tile. Shared blog probes and
logs remain in the existing observability platform.

Also check an HTTP URL with a path and query, such as
`http://rafael.ink/about?https-check=1`: expect 301 to the exact HTTPS equivalent,
then a trusted HTTPS 200 without a redirect loop. Resolve through public DNS;
a local NPM HTTP redirect does not establish this edge behavior. To undo only
the November 5 redirect change, return **Always Use HTTPS** to its previous
Off value; the connector, DNS and HTTPS route remain intact.

```bash
bash /opt/dothomelab-blog-tunnel/current/hosts/infra/blog-tunnel/manage.sh rollback-dns
```

This restores the saved A record and original DDNS list, preserving unrelated
environment changes. **It restores configuration, not public reachability while
CGNAT remains.** Then stop only `cloudflare-blog-tunnel` if abandoning the tunnel.
Rollback metadata and the root-only environment copy are retained at
`/srv/appdata/docker/cloudflare-blog-tunnel/ingress-before-tunnel-20261104` until
the operator accepts the replacement and authorizes removal. Never commit them.
Connector-image rollback uses the prior Compose release and the same token.

Run focused helper checks with
`python3 -m unittest discover -s hosts/infra/blog-tunnel -p 'test_*.py'`.
These validate credential scope, scoped dotenv edits and DNS guards; they do not
prove a clean rebuild or exercise the live rollback path.

## Media service boundary

Do not treat this public blog tunnel as a complete Jellyfin/Immich ingress
solution. The zone uses the Free Website plan. Cloudflare explicitly applies
its video/large-file restrictions to public Tunnel hostname routes and imposes
a 100 MB request-body limit on Free/Pro proxied domains. Public media needs a
suitable external ingress or restored public home connectivity; private access
can use the existing Tailscale route and appropriate DNS. See
[Cloudflare's Tunnel/media policy](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/delivering-videos-with-cloudflare/)
and [upload limits](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/).
The [November 5 check](../../../docs/evidence/2026-11-05-public-https-follow-up.md)
records which names remain unreachable publicly.
