# Blog staging log collector

CT114 runs one Alloy collector, with durable journal cursors at
`/srv/appdata/docker/staging/blog-observability/alloy`. It reads only the blog
journal and forwards the sanitized access schema to the shared Loki on CT110.
Project `blog`, environment `staging`, guest `staging`/`114` and service `blog`
identify these records. Production has its own collector/cursors and labels.

Umami, its application-local PostgreSQL, Grafana, Prometheus, Loki and Blackbox
belong to [shared Infra observability](../../infra/observability/README.md).
That runbook owns installation, credentials, retention, migration and backups.
The historical staging dashboard/analytics URLs are compatibility aliases.

[deploy.sh](deploy.sh) quiet-validates and starts only Alloy on CT114. Readiness
is checked externally because the image has no HTTP client. Shared
[verification](../../infra/observability/verify.py) runs on CT110 and sends one
unique harmless 404 request to prove sanitized log delivery. The separate blog
browser acceptance verifies Umami ingestion; health alone is insufficient.

The staging build injects its own website ID and same-origin
`/telemetry/script.js` URL. NPM permits only the tracker script and collection
POST, while keeping the entire staging site private. Production has a different
website ID and its existing public collection-only route. Access logs count
requests, including assets and bots; use Umami for readership.
