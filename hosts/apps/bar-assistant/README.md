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
upstream stable-major channels `barassistant/server:v5` and
`barassistant/salt-rim:v4`, the upstream-required non-`latest`
`getmeili/meilisearch:v1.15`, and `redis:8-alpine`. All four containers have
`wud.watch=false`: update this project as one Compose cohort only after a
Bar Assistant export and a review of upstream migration notes. Verify the API,
search, database, and frontend before keeping the new images. Rely on the
scheduled appdata job rather than starting or waiting for a manual PBS run.
