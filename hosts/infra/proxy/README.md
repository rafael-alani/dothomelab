# Consolidated service routes

Nginx Proxy Manager is Compose-owned by `infra-services` and persists at
`/srv/appdata/docker/infra-nginx-proxy-manager`. The route mapping in
`update-consolidated-routes.sql` is the Git-managed recovery definition for
consolidated and Apps routes. It preserves the existing Mealie/Jellystat
targets and creates the private `zotero.rafael.media` WebDAV route by cloning
the wildcard-certificate policy from Mealie. The Zotero host allows only
`192.168.0.0/24` and the Tailscale CGNAT range `100.64.0.0/10`; keep the final
`deny all` because public DNS also resolves this hostname.

Back up
`/srv/appdata/docker/infra-nginx-proxy-manager/data/database.sqlite`, apply the
SQL with `sqlite3`, verify `PRAGMA integrity_check`, then regenerate the
affected proxy files through NPM. Validate with `nginx -t` before reloading
Nginx.

The original `proxy_data` and `proxy_letsencrypt` named volumes and
`rpool/appdata/docker@pre-infra-migration-20260723` remain rollback assets.
