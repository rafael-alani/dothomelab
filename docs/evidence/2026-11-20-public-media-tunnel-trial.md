# Public Jellyfin and Immich tunnel trial — 2026-11-20

## Scope and retained source

Rafael explicitly requested trying both media hostnames through the existing
Cloudflare Tunnel, using Chrome. This supersedes the previous blog-only scope;
it does not assert that Cloudflare is suitable for unrestricted media hosting.
Work is retained in the canonical checkout on `codex/public-media-tunnel-trial`.
The first published helper revision is `db80948`. Runtime revision
`4f8fd2a593a742c493af0775d60675dbfbd16b8e` includes the final declaration and
record-ID restoration fix. Both PVE and CT110 isolated `current/DEPLOYED_COMMIT`
markers match it. Deployment passed quiet Compose validation and reused the
same healthy pinned container without recreating it. CT110's shared archive
remains `d3d917bcc1ebcef0c5260a95c0ad43af368fbdd5`; later commits on the trial
branch only record these results.

## Observed change

Before the change, both app origins were healthy behind NPM. The tunnel was
healthy with only `rafael.ink`. Both media DNS records pointed to the CGNAT-facing
address `168.222.145.9`; stream was DNS-only and pictures was proxied.

The existing tunnel `28987c47-3311-4503-b688-d6f080468d95` now also has routes for
`stream.rafael.ink` and `pictures.rafael.ink`, each to `https://192.168.0.110:443`,
with its own hostname in the origin SNI and HTTP Host fields. Origin certificate
verification remains enabled. Chrome was used for all Cloudflare mutations:
adding the two routes and converting each A record into a proxied tunnel CNAME.
The existing apex route and Always Use HTTPS setting remain in place.

Before DNS cutover, a guarded helper removed only the two media names from
PVE `/root/.env` and the running DDNS configuration. DDNS now manages only
`join-stream.rafael.ink`. Quiet Compose validation and the current-image check
passed before its scoped recreation. No router, app account, database, media
mount, connector credential or application image was changed.

## Verification

- Public DNS-over-HTTPS resolves both media names to Cloudflare addresses.
  Initial stream checks hit the old local DNS cache; after propagation both
  service login pages rendered in Chrome over their public HTTPS URLs.
- Trusted public TLS and HTTP 200: blog `/`, Jellyfin `/health` and `/web/`,
  Immich `/api/server/ping` and `/auth/login`.
- Unauthenticated Jellyfin `/Users` and Immich `/api/users/me` return HTTP 401.
- All three hostnames redirect HTTP to HTTPS with HTTP 301 while preserving
  `/?tunnel-check=1`. The media origin checks through NPM also pass trusted TLS.
- Connector readiness passes. Pulse reports the connector, DDNS, Jellyfin,
  Immich server and Homarr online. Existing Admin/dashboard tiles remain:
  Jellyfin at `http://jellyfin.rafael.media`, Immich at `https://immich.rafael.media`;
  the blog remains on Production. No additional background-connector tile is needed.
- Shared blog home/about/article/feed/origin probes all report success.
- The standard Pulse verifier passes for CT110/112. Both existing Homarr
  destinations return HTTP 200 (Jellyfin follows its existing HTTPS redirect).
- After deployment, all seven listed public endpoint checks pass again through
  normal DNS without address overrides; all HTTPS certificate checks pass.
- Nine focused helper tests pass, including refusal of DNS/environment drift,
  restoration after dashboard record-ID replacement, and rejection of still-live
  CNAMEs before re-enabling DDNS. Shell syntax passes for the changed verifier.
- The deployed verifier confirms connector readiness, exclusion of all three
  names from DDNS, and trusted HTTPS to all three NPM origins. Documentation
  checks and `git diff --check` pass.

These checks ran from the operator Mac/PVE, not an independent mobile network.
No authenticated media playback, seeking, upload/download, large upload, client
app session, sustained bandwidth trial, clean rebuild or live rollback was tested.
Existing logins remain required; no Cloudflare Access application was introduced.
The [runbook](../../hosts/infra/blog-tunnel/README.md#media-service-limits) records
Cloudflare's media policy and the Free-plan 100 MB request limit.

## Rollback and cleanup

The exact pre-trial DNS bodies and original non-secret DDNS list were saved and
read back on PVE at
`/srv/appdata/docker/cloudflare-blog-tunnel/media-trial-20261120/dns-before.json`
with directory mode 0700 and file mode 0600. The
[runbook](../../hosts/infra/blog-tunnel/README.md#media-trial-and-rollback) restores
DNS in Chrome before the helper restores DDNS, then removes only the media routes.
Rollback restores configuration; it cannot make CGNAT port forwarding work.

The trial owns that snapshot and its immutable source releases; retain them
until acceptance and explicit cleanup authorization. The previous connector
release `9234544beeb3fad6469baf76dd217e864d60c1e0` remains available. No temporary
test containers, application builds or data copies were created. Existing
production `immich_migration_*` containers remain live, not cleanup targets.
The shared CT110 source archive is not replaced by this isolated tunnel release.
The initial helper archive `db80948` is also retained on PVE for trial provenance;
its cleanup condition is the same acceptance and explicit removal authorization.
CT114 build cache was 9.143 GB (3.19 GB reclaimable); CT115 had no build cache.
These pre-existing caches, live preview containers, images and volumes were not
changed by the ingress task. No temporary duplicate Git checkout was created;
the canonical Mac checkout retains the published trial branch.
