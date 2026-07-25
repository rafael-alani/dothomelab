# SnapOtter and Stirling-PDF deployment — 2026-07-25

## Scope and observed baseline

This change declares and deploys production Compose projects for SnapOtter and
Stirling-PDF on Apps LXC 112, private NPM routes, Homarr tiles, focused
verification, and backup-gated update policy.

Read-only live inspection found PVE 9.1.2 with healthy pools, Apps at
`192.168.0.112`, 5 cores, 12 GiB RAM, about 522 GiB free canonical appdata,
and about 50 GiB free on its root disk. Ports 1349 and 8084 were unused.
Neither project, appdata tree, proxy route, nor Homarr application existed.
NPM and Homarr SQLite integrity checks returned `ok`.

Before this rollout the live Apps guest ran 12 containers in five projects
from the older `796d0a4` deployment generation. The repository already
declared other pending Apps projects and their routes/tiles, so the live apply
was intentionally scoped to only these two projects and their two NPM/Homarr
entries. It did not deploy or reconcile unrelated pending projects.

## Verified live deployment

The two projects were prepared from canonical appdata, passed
`docker compose config --quiet`, and were deployed independently:

- `snapotter`: three healthy containers, SnapOtter 2.1.0, PostgreSQL 17, and
  Redis 8;
- `stirling-pdf`: one healthy container running Stirling-PDF 2.14.2.

All four containers had zero restarts after deployment. Apps now runs 16
containers in seven Compose projects. Canonical appdata mounts, mapped
ownership, SnapOtter's health endpoint, and Stirling-PDF's authenticated status
endpoint were verified.

The host backup hook is installed at
`/etc/dothomelab/backup-pre.d/30-snapotter-database`. It produced a current
logical backup in `/srv/appdata/docker/snapotter/backups/latest`. The isolated
restore test completed successfully and retained its stopped test container
and evidence at
`/srv/appdata/docker/snapotter/restore-tests/20260725T062622Z`.

NPM route IDs 37 and 38 forward the two private names to Apps. NPM database
integrity, generated configuration, and `nginx -t` passed. Homarr contains the
two deterministic applications, six tiles, and fourteen layout rows; its
database integrity and container health passed after reconciliation. Pi-hole
resolves both names to NPM, and HTTPS verification passed with a trusted
certificate. SnapOtter returned HTTP 200; Stirling-PDF returned the expected
HTTP 401 before authentication.

The central WUD runner discovers both application containers in its
backup-gated route. SnapOtter PostgreSQL and Redis remain excluded as required.
The guest repositories are synchronized to the exact pushed commit recorded in
their `DEPLOYED_COMMIT` files.

## Declared topology

| Project | Container/image | Apps port | Durable state | Update path |
|---|---|---:|---|---|
| `snapotter` | `snapotter/snapotter:latest` | 1349 | files, AI packs, workspace | backup-gated WUD |
| `snapotter` | `postgres:17-alpine` | private | PostgreSQL plus logical dumps | manual; `wud.watch=false` |
| `snapotter` | `redis:8-alpine` | private | Redis AOF | manual; `wud.watch=false` |
| `stirling-pdf` | `stirlingtools/stirling-pdf:latest` | 8084 | configs/H2 database, custom files, pipelines, OCR data | backup-gated WUD |

SnapOtter follows its upstream production Compose architecture. Its app,
PostgreSQL, and Redis data live below `/srv/appdata/docker/snapotter`.
The daily PVE pre-backup hook writes a PostgreSQL custom-format dump, roles,
counts, checksums status, and SHA-256 manifest before the appdata snapshot.
The restore test creates an isolated, network-disabled PostgreSQL 17 container
and compares restored row counts.

Stirling-PDF uses the upstream standard `latest` image with authentication and
additional features enabled. Its embedded account database and all documented
durable configuration paths live below
`/srv/appdata/docker/stirling-pdf`.

## Proxy and dashboard

NPM maps:

- `snapotter.rafael.media` to `192.168.0.112:1349`;
- `pdf.rafael.media` to `192.168.0.112:8084`.

Both routes allow only `192.168.0.0/24` and `100.64.0.0/10`. SnapOtter's route
also disables response and request buffering, permits 500 MiB requests, and
uses extended timeouts as required for uploads, streamed downloads, and SSE
progress. The reconcilers retain new focused NPM and Homarr SQLite backups
before adding the two routes and six tiles.

## Secrets, recovery, and first use

Production `/root/.env` contains:

- `SNAPOTTER_DB_PASSWORD`;
- `SNAPOTTER_INITIAL_USERNAME`;
- `SNAPOTTER_INITIAL_PASSWORD`;
- `STIRLING_PDF_INITIAL_USERNAME`;
- `STIRLING_PDF_INITIAL_PASSWORD`.

The three generated password values are 64 hexadecimal characters and are not
logged or stored in Git. The initial application passwords seed only the first
administrator. Both applications require the user to change that password on
first login; Stirling-PDF also requires MFA enrollment. Complete these steps
before normal use.

Rollback retains ZFS snapshot
`rpool/appdata/docker@pre-snapotter-stirling-20260725T061343Z`, protected
environment copy
`/root/.env.pre-snapotter-stirling-20260725T061343Z`, the logical dump, prior
guest Git copies, old images, and focused NPM/Homarr SQLite copies. Do not
delete them until post-deployment backup and restore verification succeed.

The latest successful encrypted appdata backup predates this deployment. The
next scheduled run is 2026-07-26 at 02:05 CEST. The current application state
and new recovery variables must not be described as backed up until that run,
or a separately authorized manual run, completes and verifies successfully.

## Update policy

SnapOtter documents `latest` as the latest release and applies pending schema
migrations on startup. Only its application container is enrolled in
backup-gated WUD, with a direct health check before the sequential runner
continues. PostgreSQL and Redis remain on their documented major channels and
must be migrated manually after a current dump and successful isolated restore
test.

Stirling-PDF documents standard `latest` as the normal choice for most users
and documents Compose pull/recreate updates with persisted `/configs`.
It is enrolled in backup-gated WUD with a direct status endpoint check.

Primary upstream references:

- [SnapOtter deployment and NPM guidance](https://docs.snapotter.com/guide/deployment)
- [SnapOtter database backup and restore](https://docs.snapotter.com/guide/database)
- [SnapOtter Docker tags](https://docs.snapotter.com/guide/docker-tags)
- [Stirling-PDF Docker guide](https://docs.stirlingpdf.com/Installation/Docker%20Install/)
- [Stirling-PDF authentication and persistent database](https://docs.stirlingpdf.com/Configuration/System%20and%20Security/)
