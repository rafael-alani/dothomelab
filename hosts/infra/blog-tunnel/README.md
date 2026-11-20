# Public ingress tunnel

CT110 runs the pinned, manually updated `cloudflare-blog-tunnel` connector.
It replaces inbound port forwarding for `rafael.ink` after the provider moved
the connection behind CGNAT. The explicitly authorized November 20 trial also
includes `stream.rafael.ink` (Jellyfin) and `pictures.rafael.ink` (Immich). It has no published ports, persistent volumes,
Docker socket or privileged capabilities. The existing blog publisher is unchanged.

Cloudflare's remotely managed tunnel is declared in [ingress.json](ingress.json):
`rafael.ink` → tunnel → trusted HTTPS NPM `192.168.0.110:443` → existing native
production blog on CT115. The two media names use the same NPM HTTPS origin
and their existing CT112 backends. Each route sets origin SNI and Host to its
own public hostname; certificate verification stays enabled. All unmatched
tunnel hostnames return 404. No private staging hostname is enrolled.

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

## Deploy and original blog cutover

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
Keep `DOMAINS` free of all three declared tunnel names; DDNS must never replace
their CNAMEs. The current declared DDNS list contains only `join-stream.rafael.ink`.
The connector has no appdata beyond the operator's rollback directory. Secrets
follow the existing `/root/.env` recovery contract, and the rollback directory is
inside appdata backup coverage. No guest-root backup is required.

## Verification and original blog rollback

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

Restore the media trial first using the procedure below before attempting the
older whole-blog rollback; its DDNS drift guard intentionally rejects the trial
list. Do not stop the shared connector while any tunnel route is still required.

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

## Media trial and rollback

The November 20 trial is live; [evidence](../../../docs/evidence/2026-11-20-public-media-tunnel-trial.md)
distinguishes endpoint/login checks from playback and upload acceptance.
The existing pinned connector is reused, with no additional token or router change.
The tunnel name and container name retain `blog` for operational continuity.

Before the first media cutover, the operator ran on PVE:

```bash
bash /opt/dothomelab-blog-tunnel/current/hosts/infra/blog-tunnel/manage.sh snapshot-media-trial
bash /opt/dothomelab-blog-tunnel/current/hosts/infra/blog-tunnel/manage.sh prepare-media-trial
```

These retain exact media DNS records and the original non-secret DDNS list in
`/srv/appdata/docker/cloudflare-blog-tunnel/media-trial-20261120/dns-before.json`
(mode 0600), verify read-back, and remove only the two media names from DDNS.
Compose is validated quietly; DDNS uses its already-running image. Preparation
refuses DNS/ownership drift and is not rerun after changing the records.

In Chrome, the operator added both declared routes to the existing tunnel,
setting **HTTP Host Header** and **Origin Server Name** to the respective hostname
and leaving **Disable TLS certificate verification** off. Each existing media A
record was changed to a proxied CNAME targeting
`28987c47-3311-4503-b688-d6f080468d95.cfargotunnel.com`. The dashboard replaces
record IDs during this type change. No Cloudflare Access application was added;
the existing app logins protect each service.

To abandon only this trial:

1. In Cloudflare DNS, restore the saved A record bodies. On November 20 both
   pointed to `168.222.145.9`, TTL Auto; `stream` was DNS-only and `pictures`
   was proxied. Compare with the protected snapshot before changing anything.
2. Run `bash /opt/dothomelab-blog-tunnel/current/hosts/infra/blog-tunnel/manage.sh restore-media-ddns`
   on PVE. It verifies the restored bodies, tolerates replacement record IDs,
   refuses intervening DDNS edits, and restores the previous domain list.
3. Remove only the two media routes in the dashboard; leave `rafael.ink`, its
   connector and Always Use HTTPS intact. Revert the two media entries in Git's
   `ingress.json`, `.env.example` and verifier when ending the trial permanently.

This restores prior configuration, **not reachability through CGNAT**. Keep the
root-only snapshot and prior immutable connector release until the operator
accepts the trial and authorizes their removal. The live rollback has not been
executed; guarded restoration is covered by the focused tests.

## Media service limits

This trial does not establish unrestricted or long-term media suitability.
The zone uses the Free Website plan. Cloudflare applies video/large-file
restrictions to public Tunnel hostnames and a 100 MB request-body limit on
Free/Pro proxied domains. Large Immich uploads may fail and a passing Jellyfin
login does not establish sustained playback. See
[Cloudflare's Tunnel/media policy](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/delivering-videos-with-cloudflare/)
and [upload limits](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/).
The [alternatives research](../../../docs/evidence/2026-11-05-public-media-ingress-alternatives.md)
remains relevant if this trial does not meet the user's needs.
