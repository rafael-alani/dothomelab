# SnapOtter and Stirling-PDF addition — 2026-07-25

## Scope and observed baseline

This change declares production Compose projects for SnapOtter and
Stirling-PDF on Apps LXC 112, private NPM routes, Homarr tiles, focused
verification, and backup-gated update policy.

Read-only live inspection found PVE 9.1.2 with healthy pools, Apps at
`192.168.0.112`, 5 cores, 12 GiB RAM, about 522 GiB free canonical appdata,
and about 50 GiB free on its root disk. Ports 1349 and 8084 were unused.
Neither project, appdata tree, proxy route, nor Homarr application existed.
NPM and Homarr SQLite integrity checks returned `ok`.

The live Apps guest still runs 12 containers in five projects from the older
`07939ab` deployment generation. The repository already declares seven other
pending Apps projects and their routes/tiles. This change therefore remains a
committed recovery declaration rather than claiming a complete live rollout.
A complete apply requires all production variables in `.env.example`; it
would deploy the full current Git generation, not only these two projects.

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

Production `/root/.env` must add:

- `SNAPOTTER_DB_PASSWORD`;
- `SNAPOTTER_INITIAL_USERNAME`;
- `SNAPOTTER_INITIAL_PASSWORD`;
- `STIRLING_PDF_INITIAL_USERNAME`;
- `STIRLING_PDF_INITIAL_PASSWORD`.

Generate passwords from a restricted alphabet such as 64 hexadecimal
characters. The initial application passwords seed only the first
administrator. Both applications require the user to change that password on
first login; do this before normal use. Secrets remain outside Git and are
included in the existing encrypted environment backup.

Rollback keeps the retained appdata snapshot, logical dump, prior guest Git
copy, old images, and focused NPM/Homarr SQLite copies. Do not delete any of
them until post-deployment backup and restore verification succeed.

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
