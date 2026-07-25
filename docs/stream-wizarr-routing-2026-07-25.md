# Jellyfin stream repair and public Wizarr invitations — 2026-07-25

## Scope

Repair the public Jellyfin hostname `stream.rafael.ink` and add the explicitly
authorized public Wizarr invitation hostname `join-stream.rafael.ink`. The user
retains responsibility for adding the new Cloudflare DNS/proxy record with the
same policy as the existing public hostnames.

No Docker image, Compose project, application database, credential, shared
media, or appdata path changes for this task. The private
`wizarr.rafael.media` NPM route remains limited to LAN/Tailscale.

## Observed cause and desired state

Read-only inspection found healthy Jellyfin and Wizarr containers on Apps LXC
112. Both backends returned HTTP 302 at `192.168.0.112:8096` and
`192.168.0.112:5690`. NPM's `stream.rafael.ink` row still targeted retired
address `192.168.0.151:8096`, which reproduced HTTP 502 through NPM.

The Git-managed NPM reconciler now enforces:

- public `stream.rafael.ink` to `http://192.168.0.112:8096`;
- public `join-stream.rafael.ink` to `http://192.168.0.112:5690`;
- private `wizarr.rafael.media` to `http://192.168.0.112:5690`;
- TLS and WebSockets on all three routes, with the existing `rafael.ink`
  wildcard certificate on the two public hostnames.

Wizarr derives an invitation URL from the origin used by its administrator
page. Generate shareable invitations while signed in at
`https://join-stream.rafael.ink`. Existing invite codes remain valid when the
hostname in a link is changed from `wizarr.rafael.media` to
`join-stream.rafael.ink`.

## Live rollout and verification

Commit `4a54c66` was pushed to `origin/main`, imported into the clean detached
PVE clone without changing its rollback-bundle remote, and synced to Infra LXC
110. The route reconciler created NPM proxy-host ID 53 for `join-stream` and
updated existing proxy-host ID 2 for `stream`.

Post-change evidence:

- the complete Infra verifier passed, including all containers, NPM SQLite
  integrity, 53 proxy hosts, six certificates, all eighteen private managed
  routes, both public routes, Homarr, and canonical appdata placement;
- the focused pre-change database is owned by root, mode 0600, and has SQLite
  integrity `ok`;
- NPM configuration validation passed after all twenty managed configs were
  regenerated;
- direct trusted TLS checks returned HTTP 302 for both public roots, and an
  invalid `join-stream` `/j/` probe reached Wizarr's invitation page with HTTP
  200;
- `wizarr.rafael.media` returned HTTP 403 for a non-LAN/non-Tailscale source,
  while `join-stream.rafael.ink` returned HTTP 302 for the same source;
- `stream.rafael.ink` returned trusted HTTP 302 through its public DNS/router
  path, replacing the reproduced pre-change HTTP 502.

Public DNS for `join-stream.rafael.ink` was still absent immediately after the
NPM rollout. The user later created a Cloudflare-proxied A record for the
current dynamic WAN IPv4 address. Infra's Cloudflare DDNS scope includes the
hostname so future ISP address changes update its origin alongside
`rafael.ink`, `pictures.rafael.ink`, and `stream.rafael.ink`. The updater
preserves each existing record's dashboard-selected proxy status:
`join-stream`, `pictures`, and the apex are proxied, while `stream` remains
DNS-only.

The DDNS completion used focused rollback
`/root/.env.pre-join-stream-ddns-20260725`, changed only the production
`DOMAINS` entry, and recreated only the `cloudflare-ddns` container. Both
dotenv files remained root-owned mode 0600. On its first API reconciliation,
the updater detected WAN IPv4 `80.114.140.44`, enumerated all four declared
domains, and reported every A record already current. The strengthened Infra
verifier passed, authoritative DNS returned Cloudflare proxy addresses for
`join-stream`, trusted external HTTPS returned HTTP 302 at the root, and an
invalid invitation probe reached Wizarr with HTTP 200.

## Rollback

The route reconciler retains the focused mode-0600 NPM SQLite backup
`/srv/appdata/docker/infra-nginx-proxy-manager/database.sqlite.pre-stream-wizarr`.
If rollback is required, stop NPM, retain a copy of the failed database,
restore the focused backup, start NPM, regenerate the affected proxy configs,
and require both SQLite `PRAGMA integrity_check` and `nginx -t` to pass.

Removing the new Cloudflare record only removes external discovery; it does
not roll back the NPM row. Do not remove either authenticated public route
without a separate availability review.
