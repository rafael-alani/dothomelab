# Paperless addition — 2026-07-24

## Scope and preflight

The repository adds Paperless-ngx and Paperless-GPT to Apps LXC 112, plus
private NPM routes and Homarr tiles. Read-only live inspection found:

- PVE 9.1.2 with healthy pools;
- CT112 running 12 containers in five Git-managed projects;
- `/srv/appdata/docker` mounted from `rpool/appdata/docker` with 522 GiB free;
- `/data` mounted read-only from `vault/shared`;
- no existing Paperless containers, Compose project, proxy hosts, or appdata;
- no collision with the selected Apps ports 8002 and 8003;
- NPM SQLite integrity `ok`, 36 live proxy hosts, and 6 certificates;
- Homarr SQLite integrity `ok`, three existing boards, and seven layouts.

No live service was stopped or changed during preflight.

## Declared end state

The `paperless` Compose project owns:

| Container | Purpose | Update policy |
|---|---|---|
| `paperless-ngx` | authenticated document management on Apps port 8002 | backup-gated WUD |
| `paperless-gpt` | AI-assisted metadata/OCR UI on Apps port 8003 | backup-gated WUD |
| `paperless-db` | application-local PostgreSQL 18 with checksums | manual |
| `paperless-broker` | application-local Valkey 9 broker | manual |

All state is under `/srv/appdata/docker/paperless`. Paperless originals are
kept there deliberately so the encrypted appdata backup covers both metadata
and documents. CT112's shared-data mount stays read-only and is not involved.

NPM maps `paperless.rafael.media` to port 8002 and
`paperless-gpt.rafael.media` to port 8003 using the existing wildcard
certificate. Both routes allow only LAN `192.168.0.0/24` and Tailscale
`100.64.0.0/10`, then `deny all`. This restriction is mandatory for
Paperless-GPT because it has no built-in authentication.

Bootstrap creates a retained pre-change SQLite backup for NPM and Homarr,
applies idempotent database definitions, regenerates NPM configs through the
installed NPM backend, runs `nginx -t`, and restarts only Homarr after its
SQLite transaction.

## Recovery and rollback

The canonical recovery inputs remain Git, `/root/.env`,
`/srv/appdata/docker`, and `/vault/shared`. Paperless adds these production
variables:

- PostgreSQL password;
- Paperless secret key and initial administrator credentials;
- dedicated password-disabled Paperless-GPT service superuser and fixed
  40-hex Django REST Framework token;
- OpenAI API key and optional model/language selections.

Before a Paperless schema or database change, run the logical backup and
isolated restore test documented in `hosts/apps/paperless/README.md`. The
normal daily PVE job invokes the same logical dump as a pre-hook, then freezes
CT112 before snapshotting appdata and includes `/root/.env`.

Immediate rollback is to stop only the four Paperless containers, restore the
Paperless appdata subtree from the pre-change ZFS/PBS recovery point, and
restore the prior NPM/Homarr SQLite copies if route/dashboard reconciliation
must also be undone. Do not delete PostgreSQL data, documents, SQLite rollback
copies, old images, or restore-test directories during rollback.

## Pending live evidence

The production `/root/.env` did not contain Paperless variables during the
preflight. Repository validation can complete without production secrets, but
live deployment, route checks, Homarr rendering, logical dump/restore, and a
focused application check remain unverified until those variables are
installed. Do not describe the live Paperless migration as complete before
that evidence exists; the scheduled appdata job is not a deployment gate.
