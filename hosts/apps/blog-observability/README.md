# Shared analytics and dashboards

CT112 runs Umami, its private PostgreSQL database and Grafana. Canonical data is
`/srv/appdata/docker/blog-observability`; exact migrated image digests are pinned
in [Compose](compose.yaml), and all three containers remain manually updated.
Existing private URLs and credentials are preserved. No shared media is mounted.

The [observability runbook](../../staging/blog-observability/README.md) owns
installation, migration, verification, backup and rollback. Its blog dashboard
assets stay alongside the CT114 collector configuration, while the applications
and their durable state live here. Use [deploy.sh](deploy.sh) for this host;
CT114's deployment starts only Alloy and Blackbox Exporter.
