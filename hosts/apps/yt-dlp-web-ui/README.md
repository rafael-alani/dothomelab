# yt-dlp Web UI

The `yt-dlp-web-ui` project runs
`ghcr.io/marcopiovanello/yt-dlp-web-ui:latest` on Apps port 3033.
Nginx Proxy Manager publishes `https://yt-dlp.rafael.media` only to the LAN
and Tailscale, and the application's RPC authentication remains enabled.
`YTDLP_WEBUI_USERNAME`, `YTDLP_WEBUI_PASSWORD`, and
`YTDLP_WEBUI_JWT_SECRET` come from the Proxmox `/root/.env`.

Configuration, the local SQLite database, and session state persist under
`/srv/appdata/docker/yt-dlp-web-ui` and are included in the appdata snapshot.
Downloaded media is intentionally outside appdata: Proxmox bind-mounts only
`/vault/shared/media/yt-dlp` read-write into Apps at `/downloads`, while the
existing broad `/data` mount remains read-only. The downloaded files are not
included in PBS appdata backups and have no independent off-site protection.

The upstream README calls `v4` stable, but on 2026-07-25 both documented
Docker Hub/GHCR `v4` references returned `manifest unknown`; the official GHCR
package published `latest`. This single-container rolling image is enrolled in
the backup-gated WUD route; the sequential runner waits for container health
and the Apps HTTP endpoint before accepting a replacement. Recheck upstream
tags before changing this channel.
