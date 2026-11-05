# Bar Assistant

The `bar-assistant` project follows the upstream production layout:
Bar Assistant API, Salt Rim, Meilisearch, and Redis. Nginx Proxy Manager
publishes three private LAN/Tailscale routes:

- `https://bar.rafael.media` -> Salt Rim on Apps port 8200;
- `https://bar-api.rafael.media` -> Bar Assistant on Apps port 8201;
- `https://bar-search.rafael.media` -> Meilisearch on Apps port 8202.

The API database, Meilisearch index, and Redis state persist below
`/srv/appdata/docker/bar-assistant` and are included in the appdata snapshot.
The Meilisearch master key is supplied by `BAR_ASSISTANT_MEILI_MASTER_KEY` in
the Proxmox `/root/.env`; never commit the production key.

Before a manual update, create the upstream portable backup inside the mounted
storage:

```bash
docker exec bar-assistant php artisan bar:full-backup --no-interaction
```

Bar Assistant does not publish a `latest` server image. The stack uses the
upstream stable-major channels `barassistant/server:v6` and
`barassistant/salt-rim:v5`, the upstream-required non-`latest`
`getmeili/meilisearch:v1.50`, and `redis:8-alpine`. All four containers have
`wud.watch=false`: update this project as one Compose cohort only after a
Bar Assistant export and a review of upstream migration notes. Verify the API,
search, database, and frontend before keeping the new images. Rely on the
scheduled appdata job rather than starting or waiting for a manual PBS run.

The accepted November baseline is API 6.10.1, Salt Rim 5.9.0, Meilisearch
1.50.0 and Redis 8.10.3. Search data uses `meilisearch-1.50`; the preceding
`meilisearch` directory remains for rollback. Upgrade search through a logical
dump imported into an absent directory, preserving API keys and comparing both
index counts. Rehearse the API migration on a copied SQLite database with an
isolated search/cache network; compare users, bars, recipes, ingredients and
relationships before cutover. The API must be stopped for the final checkpoint.
Retain the old images, SQLite/appdata copy and search directory until acceptance.
