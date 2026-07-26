# DroppedNeedle rollback

DroppedNeedle is retained as a rollback-only project after the phase-6
Aurral/Soularr/Lidarr path was accepted. Its upstream
`droppedneedle/droppedneedle:latest` image, application state, Compose
definition, and prior container/image are preserved. It is behind the
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
  --profile rollback up -d --pull never
```

Before that command, stop Soularr and record that restoring a competing
permanent-library writer is intentional. Re-enable the disabled private NPM
route only if the rollback actually needs its web UI. Do not run DroppedNeedle
and Soularr against the permanent library at the same time.

Retirement does not delete appdata, databases, caches, plugins, imports,
images, downloads, or music. Music and completed downloads remain outside PBS
appdata backup.
