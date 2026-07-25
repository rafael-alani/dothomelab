# Consolidated service routes

Observed again before the observability addition on 2026-07-25: NPM was
healthy, its SQLite database had integrity `ok` with 36 proxy hosts and 6
certificates, and no Prometheus, Loki, Paperless, ImmichFrame, or Wizarr routes
existed. A later same-day preflight also found no Bar Assistant or yt-dlp
routes, and the slskd/DroppedNeedle preflight found neither matching route.
The private Zotero route was live. Audiobookshelf and Kavita rows existed but
targeted stale backends and lacked the managed LAN/Tailscale allow/deny policy.

Nginx Proxy Manager is Compose-owned by `infra-services` and persists at
`/srv/appdata/docker/infra-nginx-proxy-manager`. The route mapping in
`update-consolidated-routes.sql` is the Git-managed recovery definition for
consolidated Infra and Apps routes. It preserves the existing Mealie/Jellystat
targets and creates the private Zotero, Paperless, Prometheus, Loki,
ImmichFrame, Wizarr, three Bar Assistant, yt-dlp, SnapOtter, and Stirling-PDF
routes plus slskd and DroppedNeedle by cloning the wildcard-certificate policy
from Mealie. It also adopts the two existing Audiobookshelf/Kavita rows,
repoints them to Apps ports 13378/5000, and makes them private. These managed
routes include n8n and Pulse on Infra ports 5678/7655. All managed
private routes allow only `192.168.0.0/24` and the Tailscale CGNAT range
`100.64.0.0/10`; keep the final `deny all` because public DNS also resolves
these hostnames. Paperless-GPT and Loki have no native authentication.

The same reconciler keeps the authenticated Jellyfin route
`stream.rafael.ink` public at `192.168.0.112:8096` and creates the separately
authorized public Wizarr route `join-stream.rafael.ink` at
`192.168.0.112:5690`. Both use the existing `rafael.ink` wildcard certificate.
The private `wizarr.rafael.media` route remains limited to LAN/Tailscale.

`apply-consolidated-routes.sh` creates one retained pre-change SQLite
backup, applies the idempotent route definition, asks the installed NPM
backend to render all twenty managed configs, runs `nginx -t`, and reloads
through NPM's own configuration path. Bootstrap runs it after the backends are
healthy.

The SQL is a focused recovery/migration definition, not an export of all 36
live NPM routes, users, certificates, and settings. Full NPM recovery still
depends on the appdata database and certificate directories.

Back up
`/srv/appdata/docker/infra-nginx-proxy-manager/data/database.sqlite`, apply the
SQL with `sqlite3`, verify `PRAGMA integrity_check`, then regenerate the
affected proxy files through NPM. Validate with `nginx -t` before reloading
Nginx.

The original `proxy_data` and `proxy_letsencrypt` named volumes and
`rpool/appdata/docker@pre-infra-migration-20260723` remain rollback assets.
Snapshot `host/afa-appdata/2026-07-24T12:38:45Z` includes the Zotero route and
passed server-side verification, but the targeted restore did not exercise
NPM. Keep the pre-change SQLite copy and rollback assets until a focused NPM or
complete clean-host restore passes.
