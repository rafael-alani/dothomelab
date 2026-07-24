# Consolidated service routes

Observed before the Paperless addition on 2026-07-24: NPM was healthy,
`nginx -t` passed, and its SQLite database had integrity `ok`, 36 proxy hosts,
and 6 certificates. The private Zotero route was live. No Syncthing route
existed yet.

Nginx Proxy Manager is Compose-owned by `infra-services` and persists at
`/srv/appdata/docker/infra-nginx-proxy-manager`. The route mapping in
`update-consolidated-routes.sql` is the Git-managed recovery definition for
consolidated and Apps routes. It preserves the existing Mealie/Jellystat
targets and creates the private Zotero and Paperless routes by cloning the
wildcard-certificate policy from Mealie. Zotero, Paperless-ngx, and
Paperless-GPT allow only `192.168.0.0/24` and the Tailscale CGNAT range
`100.64.0.0/10`; keep the final `deny all` because public DNS also resolves
these hostnames. Paperless-GPT has no native authentication.

`apply-consolidated-routes.sh` creates one retained pre-Paperless SQLite
backup, applies the idempotent route definition, asks the installed NPM
backend to render both new proxy configs, runs `nginx -t`, and reloads through
NPM's own configuration path. Bootstrap runs it after the Apps backends are
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
