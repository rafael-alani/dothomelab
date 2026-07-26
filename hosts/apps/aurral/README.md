# Aurral

Aurral runs the exact upstream v2 prerelease
`ghcr.io/lklynet/aurral:2.0.0-test.7` at the repository-declared digest on
CT112 port 3001.
`https://aurral.rafael.media` is application-authenticated and restricted by
NPM to LAN/Tailscale clients. The prerelease is deliberately excluded from WUD;
upgrade it manually after reviewing migration notes and testing rollback.

Its database, encrypted integration settings, users, sessions, and cache are
under `/srv/appdata/docker/aurral/data`, mounted at v2's `/config`. The
entrypoint migrates the retained v1 database in place. The permanent Lidarr library is
visible only at the identical read-only path `/data/media/music`. Album and
artist requests go to Lidarr at `http://192.168.0.102:8686`; `searchOnAdd`
immediately starts Lidarr's torrent/Usenet search, and v2 records every album
request in its durable Activity history. Aurral never writes the permanent
root.

Flows use `/aurral-flows`, backed by
`/vault/shared/media/aurral-flows` through the persistent host-side narrow bind
at `/srv/appdata/docker/aurral/flows`. This avoids adding an LXC mount and
keeps the flow bytes outside the appdata ZFS snapshot and PBS backup. Navidrome
mounts the same directory read-only.

`scripts/initialize-music-pipeline-env.py` preserves the Aurral administrator,
Lidarr API key, and Navidrome integration credentials in production
`/root/.env`. `configure.py` performs idempotent onboarding without logging
them and configures Aurral to use `http://slskd:5030` with `SLSKD_API_KEY`.
Aurral has no separate Soulseek credentials or identity. It shares the existing
external slskd account for flow and playlist downloads through the private
`slskd-droppedneedle` Docker network and read-only download view.

Current upstream flow generation requires a user-supplied Last.fm API key.
Store `AURRAL_LASTFM_API_KEY` and `AURRAL_LASTFM_USERNAME` only in production
`/root/.env`; the initializer deliberately does not invent external account
credentials. Until both are present, album discovery/request and imported
playlists remain usable, but generated flows are an explicit pending
acceptance item.

Album acquisition first uses Lidarr's Prowlarr/download-client pipeline. If the
album is still missing after the configured grace period, CT102's fail-closed
Soularr wrapper selects only recent album IDs from Aurral's durable history and
uses the same slskd account before handing the completed folder back to Lidarr.
Flow files and Soulseek downloads remain outside PBS.
