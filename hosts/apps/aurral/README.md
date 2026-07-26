# Aurral

Aurral runs the official stable `ghcr.io/lklynet/aurral:latest` channel on
CT112 port 3001. `https://aurral.rafael.media` is application-authenticated
and restricted by NPM to LAN/Tailscale clients.

Its database, encrypted integration settings, users, sessions, and cache are
under `/srv/appdata/docker/aurral/data`. The permanent Lidarr library is
visible only at the identical read-only path `/data/media/music`. Album and
artist requests go to Lidarr at `http://192.168.0.102:8686`; Aurral never
writes the permanent root.

Flows use `/aurral-flows`, backed by
`/vault/shared/media/aurral-flows` through the persistent host-side narrow bind
at `/srv/appdata/docker/aurral/flows`. This avoids adding an LXC mount and
keeps the flow bytes outside the appdata ZFS snapshot and PBS backup. Navidrome
mounts the same directory read-only.

`scripts/initialize-music-pipeline-env.py` preserves the Aurral administrator,
distinct Soulseek identity, Lidarr API key, and Navidrome integration
credentials in production `/root/.env`. `configure.py` performs idempotent
onboarding without logging them. Aurral 2.x is not yet the upstream stable
`latest` line as of 2026-07-26; review its external-slskd migration before
accepting that future major change.

Current upstream flow generation requires a user-supplied Last.fm API key.
Store `AURRAL_LASTFM_API_KEY` and `AURRAL_LASTFM_USERNAME` only in production
`/root/.env`; the initializer deliberately does not invent external account
credentials. Until both are present, album discovery/request and imported
playlists remain usable, but generated flows are an explicit pending
acceptance item.

The rolling image has digest watching and is eligible only through the
backup-gated WUD trigger. The sequential runner requires
`/api/health/live` after replacement. Flow files remain outside PBS.
