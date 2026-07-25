# ImmichFrame

The `immichframe` project runs the upstream
`ghcr.io/immichframe/immichframe:latest` image on Apps port 8080. Nginx Proxy
Manager publishes `https://immichframe.rafael.media` only to the LAN and
Tailscale; ImmichFrame upstream explicitly advises against public exposure.

Create a dedicated Immich API key with these read-only permissions and store it
as `IMMICHFRAME_API_KEY` in the PVE host's `/root/.env`:

- `album.read`
- `album.statistics`
- `asset.view`
- `asset.read`
- `asset.statistics`
- `face.read`
- `memory.read`
- `person.read`
- `person.statistics`
- `tag.read`

The service points to the existing Immich server at
`http://192.168.0.112:2283`. Its default settings are environment-driven; the
upstream-recommended `/app/Config` mount persists under
`/srv/appdata/docker/immichframe/config` for optional future overrides.

The rolling application image is enrolled in the backup-gated WUD route.
Appdata and `/root/.env` are covered by the existing PVE-controlled PBS backup
before WUD is allowed to replace the container.
