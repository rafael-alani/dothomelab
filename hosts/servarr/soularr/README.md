# Soularr

Soularr runs the official `mrusse08/soularr:latest` channel as its own CT102
Compose project. Its unauthenticated upstream web UI is not published to the
host, LAN, NPM, or internet. State and the rendered credential-bearing
`config.ini` live only under `/docker/soularr`, which is CT102's existing
canonical appdata mount.

Soularr sees only `/data/media/slskd` at `/downloads`; it has no final-library
mount. Its two current upstream path mappings are:

- slskd/Soularr path: `/downloads/complete`
- Lidarr path: `/data/media/slskd/complete`

Both resolve to `/vault/shared/media/slskd/complete`. Soularr tells Lidarr to
perform `DownloadedAlbumsScan`; Lidarr alone imports, renames, and places files
under `/data/media/music`.

`configure-lidarr-download-client.py` also keeps Lidarr's qBittorrent client on
the stable `gluetun` Compose service name and runs Lidarr's built-in client
test. This avoids persisting a transient Docker gateway address across a clean
rebuild.

The repository-managed runner holds `/data/.dothomelab-job.lock` for every
Soularr cycle. WUD acquires the same lock before replacing Soularr or slskd and
also rejects any non-completed slskd transfer. The automatic scheduler defaults
to paused because the recovered Lidarr currently contains more than one
thousand monitored missing releases. An acceptance cycle is run explicitly
against one reviewed authorized release. Set
`SOULARR_SCHEDULER_ENABLED=true` in production `/root/.env` only after Lidarr's
monitoring set is curated; then redeploy this project.

The application image is digest-watched and eligible only through
backup-gated WUD. Its appdata is in PBS; Soulseek downloads and the permanent
music library are outside PBS.

If a bounded Soularr process exits after all files for one reviewed album are
already present in a single completed folder, retain the folder and inspect
the cause first. An operator may then run Lidarr's same supported recovery
scan without granting Soularr a library mount:

```bash
source /opt/dothomelab/hosts/common/load-env.sh
load_dothomelab_env /run/dothomelab.env
/opt/dothomelab/hosts/servarr/soularr/recover-completed-import.py \
  "/data/media/slskd/complete/Album folder"
```

The helper accepts only a child of `/data/media/slskd/complete`, never prints
the API key, and waits for Lidarr's command result. It does not authorize
deleting the completed folder, other queued transfers, or failed candidates.
