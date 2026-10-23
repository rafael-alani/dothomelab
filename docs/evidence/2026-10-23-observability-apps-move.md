# Umami and Grafana moved to Apps — 2026-10-23

Rafael requested relocation from CT114 to CT112. Completed on PVE `afa`,
CT110/112/114 and the operator Mac on October 23, 2026, at approximately
08:41 CEST. The [runbook](../../hosts/staging/blog-observability/README.md)
owns the procedure and rollback boundaries.

## Result and source

- Umami 3.4.0, its private PostgreSQL 17 and Grafana 13.2.4 now run on CT112.
  All three are healthy. Their exact existing registry digests are pinned;
  this relocation did not upgrade the applications or database.
- Canonical state and scoped secrets are at
  `/srv/appdata/docker/blog-observability`, outside CT114's bind mount.
- Existing private URLs remain
  `https://analytics.staging.rafael.media` and
  `https://grafana.staging.rafael.media/d/blog/blog`. NPM forwards ports
  8090/8091 to `192.168.0.112`, retaining LAN/Tailscale allow rules and final
  `deny all`. No new public route or credential rotation was introduced.
- The blog, Alloy and Blackbox Exporter stay on CT114. Their observed start
  timestamps and restart counts were identical before and after migration:
  blog `2026-10-22T22:10:52.124079602Z`; Alloy
  `2026-10-22T22:09:17.973452627Z`; Blackbox
  `2026-10-22T22:09:17.852004207Z`; restart counts all zero.
- Implementation `1abc719c968b92bc20a1ff70755f8abc996e40c7` is pushed to
  `origin/codex/move-observability`. CT114's `/opt/dothomelab/DEPLOYED_COMMIT`
  and CT112's `/opt/dothomelab-blog-observability/current/DEPLOYED_COMMIT`
  both match it. All three affected guests retain immutable source releases.
  The main CT110/CT112 archives retain their prior markers; their new targeted
  configurations use the separate release. Nothing was promoted to `main`.

## Data and service checks

The migration stopped only the original Umami/Grafana services, created a
PostgreSQL custom-format logical dump, then stopped the source database. It
restored into an empty CT112 PostgreSQL instance. All **27 public table counts**
matched, including 26 migration records, one operator, one website, one session,
and 20 website events. No PostgreSQL data directory was copied between servers.

A stopped Grafana directory copy preserved numerical ownership. Both SQLite
integrity checks passed and all **92 table counts** matched before target startup,
including one user and two datasources. The provisioned Blog dashboard remained
available from its retained configuration files.

After target startup:

- Existing Umami operator login and exact website identity passed; the API still
  reported the original 16 pageviews and four map-control events in stored data.
- Grafana's Blog dashboard and both Prometheus/Loki datasource health checks
  passed. Authenticated Umami website and Grafana dashboard readback also passed
  through the two existing HTTPS proxy routes.
- Five blog endpoint probes, seven monitoring scrapes and five alert-rule
  evaluations passed. A fresh harmless HTTPS 404 request reached Loki with its
  query string stripped and only the declared log fields.
- Blog, Umami heartbeat and Grafana health URLs each returned HTTPS 200 from the
  operator Mac. Chrome automation separately returned `ERR_ADDRESS_UNREACHABLE`
  for the blog; a new real-browser analytics sequence was therefore not completed.
  Earlier browser acceptance remains documented in the
  [initial rollout evidence](2026-10-23-blog-observability.md).
- Quiet Compose validation passed for the CT112 services before deployment and
  for the resulting CT114 collector definition. NPM `nginx -t` passed.
- The three original CT114 containers were removed without volume deletion;
  its observability appdata directory now contains only `alloy/`.

Local checks passed: 11 credential-preservation tests, three route-boundary tests,
nine existing staging-deployment tests and two SQLite migration-check tests;
Bash/Python/Node syntax, whitespace and documentation-link checks. An independent
script review found a rollback error-handling issue, fixed before live use.

An initial preflight stopped before any service interruption because Docker's
classic and containerd image stores reported different local image IDs. The
corrected check compared matching registry digests. Its unused target directory
was retained at `/srv/appdata/docker/blog-observability-preflight-20261023`.

## Protection and remaining limits

The existing PVE `70-blog-umami-database` pre-backup hook now enters CT112. It ran
successfully, created a fresh logical dump, checked its table of contents and
wrote its checksum. The appdata freeze list remains `102 110 112 114`. The most
recent scheduled PBS job succeeded on October 23 at 02:15:55 CEST; no extra PBS
job or independent full-disaster restore was run for this relocation. The live
migration establishes logical database restore and application readability,
not recovery from a selected PBS archive or a clean PVE rebuild.

Retained rollback:

- `/srv/appdata/docker/blog-observability/rollback-20261023T064038Z` contains the
  migration dump/checksum/count manifests and original PostgreSQL, Grafana,
  runtime environment and earlier dumps under `staging-state/`.
- NPM's consistent SQLite backup is
  `database.sqlite.pre-observability-move-20261023T064038Z` in its canonical
  appdata root. Restore only the affected routes if later unrelated edits exist.
- CT114 retains `/opt/dothomelab.before-observability-move-1abc719c968b92bc20a1ff70755f8abc996e40c7`.
  Original releases and images remain available.

The original rollback database does not contain events or dashboard edits made
after cutover. Preserve new target writes before any rollback. No data, dump,
volume or rollback image cleanup was performed. Alert delivery and independent
external outage monitoring remain unconfigured, as before this migration.
