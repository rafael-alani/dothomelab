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
`http://192.168.0.112:2283`. Since v1.0.38, settings live in SQLite under
`/srv/appdata/docker/immichframe/config`; this directory must be writable by
container UID 1000 (host UID 101000). `prepare.sh` sets ownership on that
directory only, with mode 0700, before deployment.

The Compose entrypoint writes the recovery API key to a private mode-0600 file
in the container's replaceable `/tmp` and seeds `Settings.json` only if no
settings file exists. Upstream imports this file into SQLite on the first
configured start. The seed references the key file, so the database does not
need to contain the API key. Restored database settings take precedence; never
delete the database to change configuration. Existing settings files are
preserved. Admin editing is disabled by upstream when an imported configuration
has no admin password; the private slideshow works without admin onboarding.

Restore the entire config directory with its numeric ownership, including
SQLite state. Bootstrap recreates the key file from `IMMICHFRAME_API_KEY` at
every start. The supported file import is deprecated upstream, so a future
release that removes it requires a reviewed replacement for first-start setup.

The rolling application image is enrolled in the backup-gated WUD route.
Appdata and `/root/.env` are covered by the existing PVE-controlled PBS backup
before WUD is allowed to replace the container.

Photo links and QR codes go directly to `https://pictures.rafael.ink/photos/…`.
Upstream v1.0.40 hard-codes `my.immich.app` in its browser bundle, with no
external-link setting. `patch-photo-links.sh` rewrites that prefix at every
container start, regenerates gzip and removes the stale Brotli sibling from
the replaceable container filesystem. A one-off edit inside the container
would disappear at the next WUD replacement. If upstream changes the link
builder or bundle permissions, startup fails for review; replace this workaround
with an upstream setting when available. Existing browser tabs need a refresh
(a hard refresh if they cached the original bundle).

Run `python3 hosts/apps/immichframe/test_photo_links.py` locally for the
replacement, compressed-file and restart checks. To roll back the workaround,
revert its Git change and recreate only ImmichFrame using the retained image;
the saved SQLite settings and photos are unaffected.

Run `verify.sh` inside CT112 after deployment. It checks SQLite integrity,
configured accounts, slideshow asset discovery and image delivery in addition
to the UI, API key, storage and update-policy checks. It also checks the served
photo-link bundle with identity, gzip and Brotli requests.
