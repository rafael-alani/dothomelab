# Stirling-PDF

The `stirling-pdf` project runs the upstream standard
`stirlingtools/stirling-pdf:latest` image on Apps port 8084. Nginx Proxy
Manager publishes `https://pdf.rafael.media` only to the LAN and Tailscale.

Login and the additional feature set are explicitly enabled. The first
administrator comes from `/root/.env`; Stirling-PDF forces the default
administrator to change its password on first login. Keep the route private
and complete that password change before normal use.

Settings, the embedded account database, custom files, logs, pipelines, and
OCR language data persist below `/srv/appdata/docker/stirling-pdf` and are
covered by the appdata snapshot. The upstream `latest` channel is explicitly
documented as the standard image for most users and is enrolled in the
backup-gated WUD route. After updates, the sequential runner checks the
application status endpoint before continuing.
