# Wizarr

The `wizarr` project runs the upstream `ghcr.io/wizarrrr/wizarr:latest` image
on Apps port 5690 with its database under `/srv/appdata/docker/wizarr`.
Nginx Proxy Manager publishes `https://wizarr.rafael.media` only to the LAN
and Tailscale. The separately authorized
`https://join-stream.rafael.ink` route is public for shareable invitations;
Wizarr's built-in administrator authentication stays enabled.

Wizarr builds a new invitation URL from the origin of the administrator page.
After its Cloudflare record is present, sign in through
`https://join-stream.rafael.ink` when generating public invitations. Existing
invite codes are unchanged and also work after replacing
`https://wizarr.rafael.media` with `https://join-stream.rafael.ink` in the
shared URL.

After first launch, complete Wizarr's setup wizard and connect it to Jellyfin
at `http://192.168.0.112:8096`. Jellyfin credentials and invite policy are
durable Wizarr application state, not Git configuration. Do not commit them.

The rolling application image is enrolled in the backup-gated WUD route.
Wizarr's appdata is included in the existing PVE-controlled PBS snapshot before
WUD is allowed to replace the container.
