# n8n

The `n8n` project runs the upstream
`docker.n8n.io/n8nio/n8n:latest` channel on Infra port 5678. Nginx Proxy
Manager publishes `https://n8n.rafael.media` only to the LAN and Tailscale.
`N8N_PROXY_HOPS=1`, `N8N_EDITOR_BASE_URL`, and `WEBHOOK_URL` preserve correct
HTTPS URLs behind NPM. Public webhook ingress is deliberately not enabled.

The application-local SQLite database, workflows, credentials, settings, and
encryption metadata persist under `/srv/appdata/docker/n8n`. The production
`N8N_ENCRYPTION_KEY` is also retained in Proxmox `/root/.env`; losing either
the appdata or that key can make stored credentials unrecoverable. The
appdata snapshot freezes Infra before capture, so SQLite and its WAL are copied
consistently.

The owner is created idempotently by `configure-owner.py` from the four
`N8N_ADMIN_*` recovery values. The rolling image is enrolled in the
backup-gated WUD route; the sequential runner must pass `/healthz` after a
replacement. Review n8n release notes before accepting a major-version
migration even when the tag remains `latest`.
