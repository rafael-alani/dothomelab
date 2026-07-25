# Bar Assistant and yt-dlp Web UI addition — 2026-07-25

## Scope and live preflight

The repository adds a four-container Bar Assistant project and a
single-container yt-dlp Web UI project to Apps LXC 112, ten private managed NPM
endpoints in total, and two new Homarr applications.

Read-only live inspection found PVE 9.1.2, healthy pools, about 522 GiB free on
appdata, 12 current Apps containers in five projects, NPM and Homarr SQLite
integrity `ok`, 36 proxy hosts, and no listeners on Apps ports 3033 or
8200-8202. The existing `/data` mount in Apps is read-only. No matching
containers, routes, dashboard entries, appdata, or shared download directory
existed. The existing Pi-hole contract already resolves all four new hostnames
to NPM at `192.168.0.110`. Apps deployed commit `796d0a4` and Infra deployed
commit `07939ab` both predate the currently declared but not yet live
Paperless, observability, ImmichFrame, and Wizarr additions.

No live service, mount, route, dashboard, environment, or data was changed
during preflight.

## Declared end state

| Project/container | Image | Apps port | Durable state | Update policy |
|---|---|---:|---|---|
| `bar-assistant` | `barassistant/server:v5` | 8201 | SQLite/media under appdata | manual cohort |
| `bar-assistant-salt-rim` | `barassistant/salt-rim:v4` | 8200 | reproducible frontend | manual cohort |
| `bar-assistant-meilisearch` | `getmeili/meilisearch:v1.15` | 8202 | search index under appdata | manual cohort |
| `bar-assistant-redis` | `redis:8-alpine` | internal | cache/session AOF under appdata | manual cohort |
| `yt-dlp-web-ui` | `ghcr.io/marcopiovanello/yt-dlp-web-ui:latest` | 3033 | config/SQLite/session under appdata | backup-gated WUD |

Bar Assistant follows the upstream production architecture. NPM publishes the
Salt Rim frontend, API, and Meilisearch on `bar.rafael.media`,
`bar-api.rafael.media`, and `bar-search.rafael.media`. The browser client needs
all three routes. yt-dlp Web UI is published at `yt-dlp.rafael.media` with its
native RPC authentication enabled. Every route allows only LAN
`192.168.0.0/24` and Tailscale `100.64.0.0/10`, followed by `deny all`.

Homarr receives one Bar Assistant and one yt-dlp Web UI application plus tiles
on the existing `dashboard`, `Admin`, and `default` boards. Reconciliation is
idempotent and retains focused pre-change NPM and Homarr SQLite backups.

## Storage and recovery

Bar Assistant state and yt-dlp configuration live below
`/srv/appdata/docker`, so the daily guest-freeze/ZFS/PBS flow protects them
together with `/root/.env`.

Downloaded media is application-independent large data. Bootstrap creates
`/vault/shared/media/yt-dlp` with the Apps `1000:1000` mapped ownership and
adds only that directory as a read-write `/downloads` bind. Apps `/data`
remains read-only. PBS does not include the downloads, and the existing Proton
scope does not protect them; loss of `vault` would lose this directory.

Required recovery secrets in `/root/.env` are:

- `BAR_ASSISTANT_MEILI_MASTER_KEY`;
- `YTDLP_WEBUI_USERNAME`;
- `YTDLP_WEBUI_PASSWORD`;
- `YTDLP_WEBUI_JWT_SECRET`.

## Update policy

Bar Assistant explicitly has no `latest` server image and recommends its
stable major channel. Its API, frontend, search schema/index, and session
service form one compatibility cohort, so all four containers use
`wud.watch=false`. Meilisearch also explicitly warns never to use `latest`.
Update the Compose project manually after a Bar Assistant export, review all
upstream migration notes, and verify the API, SQLite database, Meilisearch,
Redis, and frontend before accepting the images. The scheduled appdata job
continues independently and is not a manual update gate.

yt-dlp Web UI documents `v4` as stable, but live registry validation on
2026-07-25 found both documented Docker Hub and GHCR `v4` references absent
with `manifest unknown`; the official GHCR `latest` manifest resolved. The
single rolling container has config protected by the appdata snapshot, so it
is eligible for the backup-gated WUD route. The sequential runner verifies
container health and the direct Apps endpoint. Its downloaded files remain
untouched by image replacement. Recheck upstream registry tags before changing
the channel.

Upstream references:

- [Bar Assistant Docker installation and reverse proxy layout](https://docs.barassistant.app/setup/)
- [Bar Assistant source and image channel policy](https://github.com/karlomikus/bar-assistant)
- [yt-dlp Web UI Docker and stable v4 documentation](https://github.com/marcopiovanello/yt-dlp-web-ui)

## Rollback and live evidence

The live rollout began from empty Bar Assistant and yt-dlp appdata paths, so it
did not overwrite application data. Before adding the four generated recovery
values, it retained the prior production environment as mode 0600 at
`/root/.env.pre-bar-ytdlp-20260725T095708Z`. The NPM routes and Homarr records
had already been created by the consolidated reconciliation and passed
read-only integrity and target checks; this rollout did not rewrite those
databases. Rollback stops only the two new Compose projects without deleting
their data, restores the previous Git archive if required, and retains the new
appdata trees, environment values, and downloads until explicitly reviewed.

Live evidence on 2026-07-25:

- PVE 9.1.2 and both ZFS pools were healthy, with about 511 GiB free on
  appdata and 19.9 TiB free on `vault/shared`;
- bootstrap's declared `mp2` was hot-added without restarting Apps, mapping
  `/vault/shared/media/yt-dlp` to `/downloads` as guest `1000:1000`, mode 0750;
- all four recovery variables were generated on Proxmox, validated with the
  repository dotenv parser, and retained only in `/root/.env`;
- `docker compose config`, pull, and `up -d` completed independently for both
  project files;
- the first Salt Rim health check revealed that its image has `curl` but not
  `wget`; commit `8cda9db` corrected the check, was pushed, synced to CT102,
  CT110, and CT112, and the project was recreated without touching its data;
- all five containers are healthy with zero restarts. Focused verification
  passed Bar Assistant frontend/API/search/Redis/SQLite/storage/HTTPS checks
  and yt-dlp health/authentication/appdata/download-write/HTTPS checks;
- Pi-hole resolves all four names to NPM. The four NPM rows use TLS, the
  correct Apps ports, LAN and Tailscale allow rules, and `deny all`; `nginx -t`
  and NPM SQLite integrity passed;
- Homarr contains both applications with a tile on `dashboard`, `Admin`, and
  `default`, and its SQLite integrity passed;
- Pulse's command-disabled Apps agent converged with all five new containers;
  Bar Assistant remains excluded from WUD while yt-dlp is enrolled in
  `docker.backupgated`;
- the scheduled appdata service's most recent run had `Result=success`; this
  routine rollout did not start or wait for an on-demand PBS backup. The next
  scheduled run protects appdata and `/root/.env`, but not yt-dlp downloads.

Apps now runs 23 containers in eleven projects; the complete declared
generation remains 33 containers in eighteen Apps projects. Create the first
Bar Assistant account and complete one authenticated yt-dlp download before
calling those user workflows verified.
