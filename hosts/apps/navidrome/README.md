# Navidrome

Navidrome runs the official stable `deluan/navidrome:latest` channel on CT112
port 4533. Its SQLite database, cache, and configuration live under
`/srv/appdata/docker/navidrome/data`. The Lidarr library is mounted read-only
at `/music`; the separate Aurral flow library is mounted read-only at
`/aurral-flows`.

`configure.py` idempotently creates the first administrator, the
`Aurral Weekly Flow` library, and a dedicated Aurral integration user.
Navidrome does not expose a narrower role that can trigger library scans and
maintain Aurral's smart playlists, so the dedicated account has administrator
status and access to both libraries. Credentials are generated and retained
only in production `/root/.env`. Subsonic clients use those credentials over
private HTTPS; nothing is committed.

`ND_SCANNER_PURGEMISSING=always` follows Aurral's current guidance so rotated
flow entries leave Navidrome's catalogue. It removes only missing database
records and never writes either read-only library.

`https://navidrome.rafael.media` is application-authenticated and restricted
by NPM to LAN/Tailscale. The rolling image is digest-watched and eligible only
through backup-gated WUD; `/ping` is required after replacement. Navidrome
appdata is in PBS, while both music libraries are outside it.
