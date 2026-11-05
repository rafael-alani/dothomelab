# n8n

The `n8n` project runs the upstream
`docker.io/n8nio/n8n:2.46.6` baseline on Infra port 5678. Nginx Proxy
Manager publishes `https://n8n.rafael.media` only to the LAN and Tailscale.
`N8N_PROXY_HOPS=1`, `N8N_EDITOR_BASE_URL`, and `N8N_WEBHOOK_URL` preserve correct
HTTPS URLs behind NPM. Public webhook ingress is deliberately not enabled.

The application-local SQLite database, workflows, credentials, settings, and
encryption metadata persist under `/srv/appdata/docker/n8n`. The production
`N8N_ENCRYPTION_KEY` is also retained in Proxmox `/root/.env`; losing either
the appdata or that key can make stored credentials unrecoverable. The
appdata snapshot freezes Infra before capture, so SQLite and its WAL are copied
consistently.

The owner is created idempotently by `configure-owner.py` from the four
`N8N_ADMIN_*` recovery values. Stable version-2 tags are enrolled in the
backup-gated WUD route; the sequential runner must pass `/healthz` after a
replacement. Major versions require release-note review and an explicit
baseline change; the WUD tag filter excludes beta tags and version 3.

Use Docker Hub directly. On November 5 the `docker.n8n.io` mirror listed tags
but returned HTTP 429 for manifests, while the direct upstream repository
worked. Both references resolved to the identical image digest. Using the
direct reference lets WUD use its native Docker Hub provider for discovery and
pulls. Do not respond to a mirror failure by suppressing discovery errors or
installing an unrelated image. Docker Hub still has its own anonymous quota;
an actual direct-registry limit must remain visible in the WUD audit.
