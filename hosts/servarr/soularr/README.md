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
also rejects any non-completed slskd transfer. The scheduler defaults on but
`SOULARR_REQUESTS_ONLY=true` makes it fail closed: it reads Aurral v2's SQLite
history read-only and exposes only durable album requests between 10 minutes
and 7 days old to Soularr. A persistent appdata ledger applies a six-hour
per-album retry cooldown after every attempted cycle. This gives Lidarr's
torrent/Usenet search the first attempt, avoids hammering peers for a not-found
release, and prevents the recovered thousand-plus monitored albums from
becoming Soulseek jobs. Broad wanted-list mode requires the explicit,
post-curation override `SOULARR_REQUESTS_ONLY=false`.

`clear-stale-lidarr-queue.py` removes only old terminal `completed` /
`importFailed` queue metadata, with Lidarr instructed not to remove download
client data or blocklist the release. It is a dry run unless `--apply` is used.

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
the API key, and treats Lidarr's `Failed to import` message as a failure even
when the command transport itself completed. If the recovered Lidarr album has
the wrong edition selected, pass both `--album-id` and a reviewed
`--release-id`; the helper changes the selected release through Lidarr's API
and automatically restores the prior selection if the scan fails. It does not
authorize deleting the completed folder, other queued transfers, or failed
candidates.

If the automatic scan reports `Failed to import` but Lidarr's manual analysis
matches every file to the reviewed album with no rejection, first retain a
verified source rollback, then explicitly add `--manual-on-scan-failure`.
That fallback posts only those analyzed items through Lidarr's supported
manual-import API, then invokes Lidarr's `ManualImport` command in explicit
copy mode. It pins files to the reviewed release, disables release switching
for the import, and refuses any path, album, track, or rejection drift.
