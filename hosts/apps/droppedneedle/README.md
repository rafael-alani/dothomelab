# DroppedNeedle rollback

DroppedNeedle was retired on November 5 after genuine generated Aurral tracks
passed authenticated playback in Aurral and Navidrome, completing the earlier
Soularr/Lidarr import acceptance. Its upstream
`droppedneedle/droppedneedle:latest` image, application state, Compose
definition and image are preserved; its idle container was stopped and removed.
The root-private cleanup receipt is recorded in the
[maintenance follow-up](../../../docs/evidence/2026-11-05-maintenance-automation.md).
It is behind the
`rollback` Compose profile, excluded from WUD, absent from normal bootstrap,
and its former NPM route is disabled.

Configuration, SQLite databases, cover-art/cache data, plugins, and manual
imports remain below `/srv/appdata/docker/droppedneedle`. When explicitly
re-enabled, the existing music library is mounted read-write at `/music` and
slskd completed downloads are mounted at `/slskd-downloads/complete`.

Exact rollback re-enable procedure on CT112 after staging `/root/.env` at
`/run/dothomelab.env`:

```bash
cd /opt/dothomelab
docker compose --env-file /run/dothomelab.env \
  -f hosts/apps/droppedneedle/compose.yaml \
  --profile rollback config --quiet
docker compose --env-file /run/dothomelab.env \
  -f hosts/apps/droppedneedle/compose.yaml \
  --profile rollback up -d --pull never
```

Before that command, stop Soularr and record that restoring a competing
permanent-library writer is intentional. Re-enable the disabled private NPM
route only if the rollback actually needs its web UI. Do not run DroppedNeedle
and Soularr against the permanent library at the same time.

Retirement does not delete appdata, databases, caches, plugins, imports,
images, downloads, or music. Music and completed downloads remain outside PBS
appdata backup.
