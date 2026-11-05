# Aurral

Aurral runs the exact upstream stable release
`ghcr.io/lklynet/aurral:2.13.0` at the repository-declared digest on
CT112 port 3001.
`https://aurral.rafael.media` is application-authenticated and restricted by
NPM to LAN/Tailscale clients. The integration-heavy service is deliberately excluded from WUD;
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
at `/srv/appdata/docker/aurral/flows`. Explicit CT112 `mp7` carries this bridge
into the guest on cold boot. The flow bytes remain outside the appdata ZFS
snapshot and PBS backup. Navidrome mounts the same directory read-only.

`scripts/initialize-music-pipeline-env.py` preserves the Aurral administrator,
Lidarr API key, and Navidrome integration credentials in production
`/root/.env`. `configure.py` performs idempotent onboarding without logging
them and configures Aurral to use `http://slskd:5030` with `SLSKD_API_KEY`.
Aurral has no separate Soulseek credentials or identity. It shares the existing
external slskd account for flow and playlist downloads through the private
`slskd-droppedneedle` Docker network. It has write access only to the narrow
slskd download tree so v2 can validate and transfer its own completed jobs into
the separate flow library; it has no write access to permanent music.

Upstream 2.13 provides flows from library artists, discovery and other templates;
Last.fm is optional for the general flow feature. Preserve existing
`AURRAL_LASTFM_API_KEY` and `AURRAL_LASTFM_USERNAME` only in production
`/root/.env`; the initializer never invents external credentials. User-specific
listening-history templates additionally need an actual linked history source;
a configured global API key is not proof of that connection.

The configurator uses v2.13's top-level `pathMappings`, including Navidrome
`/music` → Aurral `/data/media/music`, and its explicit storage-health POST.
The former nested Navidrome mapping is no longer accepted by the upstream API.
It also queues an idempotent library refresh so the connected Lidarr collection
enters Aurral's library index after rebuild/configuration. Preserve read-only
permanent music access; fixing a mapping never requires widening a mount.

For acceptance, load the deployment dotenv on CT112 and run
`python3 /opt/dothomelab/hosts/apps/aurral/flow-acceptance.py --verify`.
It requires a genuinely generated `Homelab Library Blend` flow and reads an
authenticated 4 KiB audio range from each completed track. `--create` explicitly
creates and generates a bounded three-track flow only when absent, after a
SQLite backup. It leaves the recurring schedule off and never resets an
existing flow. A small library may supply fewer tracks. Default invocation
reports progress without generating or downloading anything. This complements
the ordinary health/mount verifier; user-device audio output remains a separate
check. Flow files are outside PBS, as described above.

Album acquisition first uses Lidarr's Prowlarr/download-client pipeline. If the
album is still missing after the configured grace period, CT102's fail-closed
Soularr wrapper selects only recent album IDs from Aurral's durable history and
uses the same slskd account before handing the completed folder back to Lidarr.
Flow files and Soulseek downloads remain outside PBS.
