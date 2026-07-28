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
ImmichFrame, Wizarr, three Bar Assistant, yt-dlp, SnapOtter, Stirling-PDF,
Storyteller, slskd, and DroppedNeedle routes by cloning the wildcard-certificate policy
from Mealie. It also adopts the two existing Audiobookshelf/Kavita rows,
repoints them to Apps ports 13378/5000, and makes them private. These managed
routes include n8n and Pulse on Infra ports 5678/7655 and the loopback-only
Syncthing GUI at `127.0.0.1:8384`, plus Shelfarr, Listenarr, Cleanuparr, and
Sortarr on CT102 ports 5056/4545/11011/9595, and
BookOrbit on CT112 port 3002, Grimmory on CT112 port 6060, and Storyteller on
CT112 port 8001. All twenty-eight managed
private routes allow only `192.168.0.0/24` and the Tailscale CGNAT range
`100.64.0.0/10`; keep the final `deny all` because public DNS also resolves
these hostnames. Paperless-GPT and Loki have no native authentication.

The same reconciler keeps the authenticated Jellyfin route
`stream.rafael.ink` public at `192.168.0.112:8096` and creates the separately
authorized public Wizarr route `join-stream.rafael.ink` at
`192.168.0.112:5690`. Both use the existing `rafael.ink` wildcard certificate.
The private `wizarr.rafael.media` route remains limited to LAN/Tailscale.

`apply-haos-route.sh` separately adopts the existing public
`ha.rafael.media` row and enforces TLS termination at NPM with a plain HTTP
upstream at `192.168.0.125:8123` plus WebSocket forwarding. It hides Home
Assistant's upstream `X-Frame-Options` header only on this proxy route and
replaces it with `Content-Security-Policy: frame-ancestors 'self'
https://rafael.media`, allowing the authenticated Homarr origin to embed the
Hub dashboard without permitting arbitrary sites to frame Home Assistant.
Direct LAN access retains Home Assistant's default framing protection. The
route keeps its certificate, HSTS, caching, and public exposure policy. Home
Assistant must trust the current Infra address `192.168.0.110`; bootstrap
reconciles that guest configuration through `hosts/haos/configure-proxy.sh`
before NPM renders the route. Both reconcilers retain focused rollback copies.

`apply-consolidated-routes.sh` creates one retained pre-change SQLite
backup, applies the idempotent route definition, asks the installed NPM
backend to render all thirty active managed configs plus the disabled
DroppedNeedle config, runs `nginx -t`, and reloads through NPM's own
configuration path. Bootstrap runs it after the backends are healthy.

The SQL is a focused recovery/migration definition, not an export of all 37
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
