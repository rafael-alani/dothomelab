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

## Credentials and recovery prerequisites

The connector token belongs only in PVE `/root/.env` as
`CLOUDFLARE_BLOG_TUNNEL_TOKEN`. The interactive helper validates its account and
tunnel identity and never echoes it. The existing DNS API token remains scoped
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
current image. Other managed names remain unchanged. `switch-dns` requires a ready
connector and replaces only the saved apex record with the proxied tunnel CNAME.
Check the remote ingress against the declaration before switching DNS. Helpers
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
