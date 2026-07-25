# Paperless addition — 2026-07-24/25

## Scope and preflight

The repository adds Paperless-ngx and Paperless-GPT to Apps LXC 112, plus
private NPM routes and Homarr tiles. Read-only live inspection found:

- PVE 9.1.2 with healthy pools;
- CT112 running 27 containers in fifteen Git-managed projects;
- `/srv/appdata/docker` mounted from `rpool/appdata/docker` with 490 GiB free;
- `/data` mounted read-only from `vault/shared`;
- no existing Paperless containers, Compose project, or appdata;
- no collision with the selected Apps ports 8002 and 8003;
- both private NPM rows already present with the correct Apps targets, wildcard
  certificate, WebSockets, LAN/Tailscale allow rules, and `deny all`;
- both managed Homarr applications and all six board items already present;
- Pulse already healthy with command-disabled Docker agents in CT102/110/112
  and complete inventory of every currently running container.

No live service was stopped or changed during preflight.

## Declared end state

Two independent Compose projects own the four containers:

| Project | Containers | Purpose | Update policy |
|---|---|---|---|
| `paperless-ngx` | `paperless-ngx`, `paperless-db`, `paperless-broker` | authenticated document management on Apps port 8002 plus application-local PostgreSQL 18 and Valkey 9 | app latest via backup-gated WUD; database/broker manual |
| `paperless-gpt` | `paperless-gpt` | AI-assisted metadata/OCR UI on Apps port 8003 | backup-gated WUD |

The projects share only the externally prepared `dothomelab-paperless` bridge.
Paperless-ngx has the stable network alias `paperless-ngx`; Paperless-GPT
targets `http://paperless-ngx:8000`. Bootstrap prepares the bridge and deploys
Paperless-ngx before Paperless-GPT. There is no unsupported cross-project
`depends_on`.

All state is under `/srv/appdata/docker/paperless`. Paperless originals are
kept there deliberately so the encrypted appdata backup covers both metadata
and documents. CT112's shared-data mount stays read-only and is not involved.

NPM maps `paperless.rafael.media` to port 8002 and
`paperless-gpt.rafael.media` to port 8003 using the existing wildcard
certificate. Both routes allow only LAN `192.168.0.0/24` and Tailscale
`100.64.0.0/10`, then `deny all`. This restriction is mandatory for
Paperless-GPT because it has no built-in authentication.

Bootstrap idempotently reconciles the NPM/Homarr definitions. The first live
Paperless deployment does not need to rewrite them because their rows already
match the Git contract.

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
isolated restore test documented in `hosts/apps/paperless-ngx/README.md`. The
normal daily PVE job invokes the same logical dump as a pre-hook, then freezes
CT112 before snapshotting appdata and includes `/root/.env`.

Immediate rollback is to stop the two Paperless projects without volumes,
restore the Paperless appdata subtree from the applicable ZFS/PBS recovery
point, and restore prior NPM/Homarr SQLite copies only if their database rows
were changed. Do not delete PostgreSQL data, documents, SQLite rollback
copies, old images, or restore-test directories during rollback.

## Pending live evidence

The 2026-07-25 production `/root/.env` preflight found no Paperless values and
no reusable OpenAI key. `scripts/initialize-paperless-env.py` can create every
Paperless-local password, secret, service identity/token, and model default
without printing them; it deliberately cannot invent the external
`PAPERLESS_GPT_OPENAI_API_KEY`.

Repository validation and an independent Paperless-ngx deployment can proceed
first. Paperless-GPT deployment, both private route checks, Pulse convergence,
logical dump/restore, and the final focused check remain unverified until the
OpenAI key is installed. Do not describe the full live Paperless migration as
complete before that evidence exists; the scheduled appdata job is not a
deployment gate.
