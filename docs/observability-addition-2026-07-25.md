# Prometheus and Loki addition — 2026-07-25

## Scope and preflight

The repository adds independent Prometheus and Loki Compose projects to Apps
LXC 112, plus private NPM routes and Homarr tiles. Read-only live inspection
found:

- PVE 9.1.2 with healthy `rpool` and `vault`;
- CT112 running 12 containers in five existing Compose projects;
- `/srv/appdata/docker` mounted from `rpool/appdata/docker` with about 522 GiB
  available;
- no existing Prometheus/Loki containers, projects, appdata, NPM routes, or
  Homarr applications;
- no listeners on the selected Apps ports 9090 and 3100;
- NPM SQLite integrity `ok` with 36 proxy hosts and 6 certificates;
- Homarr SQLite integrity `ok` with three boards and seven layouts.

No live service was stopped or changed during preflight.

## Declared end state

| Project/container | Image | Port | Persistent state | Update policy |
|---|---|---:|---|---|
| `prometheus` | `prom/prometheus:v3.13.1` | 9090 | `/srv/appdata/docker/prometheus` | manual |
| `loki` | `grafana/loki:3.7.3` | 3100 | `/srv/appdata/docker/loki` | manual |

Prometheus 3.13 is the current LTS line through July 2027. It retains 30 days
or 20 GB, whichever limit is reached first, and scrapes itself plus Loki.
Loki uses a single-binary TSDB v13/filesystem configuration with 30-day
Compactor retention. The local filesystem backend is intentionally
single-node and unreplicated.

Prometheus and Loki share only the externally declared
`dothomelab-observability` Docker bridge. Both publish on the Apps LXC address
for NPM and focused verification. NPM maps `prometheus.rafael.media` and
`loki.rafael.media` to those ports using the existing wildcard certificate and
allows only LAN `192.168.0.0/24` plus Tailscale `100.64.0.0/10`. Loki has no
native authentication, so the final `deny all` is mandatory.

Homarr receives Prometheus and Loki applications on the existing `dashboard`,
`Admin`, and `default` boards. The Loki tile opens `/ready` because Loki is an
API backend and does not include its own log-exploration UI.

## Update, backup, and recovery

Both containers use exact release tags and `wud.watch=false`. Prometheus owns
a persistent TSDB, while Loki releases can include configuration and storage
changes; the backup-gated WUD route must not replace either automatically.

For a manual update:

1. complete and verify the normal encrypted appdata backup;
2. review the target release and, for Loki, run its target image with
   `-verify-config=true` against `loki-config.yaml`;
3. update one exact image tag in Git;
4. run `docker compose config`, deploy only that project, and run its focused
   verifier;
5. retain the prior image and appdata recovery point until queries succeed.

The daily PVE guest-freeze/ZFS/PBS flow covers both appdata trees. No logical
database dump is required. Recovery restores appdata, recreates the shared
Docker network in `prepare.sh`, and deploys the exact Git-managed config.

Prometheus and Loki do not add secrets to `/root/.env`. Loki is currently an
empty ingestion/query backend: no Grafana Alloy, Docker logging driver, or
other shipper is declared by this change. Adding collection is a separate
task because it changes host access, cardinality, retention volume, and
verification scope.

Official references:

- [Prometheus 3.13 LTS and release lifecycle](https://prometheus.io/docs/introduction/release-cycle/)
- [Prometheus Docker storage and configuration](https://prometheus.io/docs/prometheus/latest/installation/)
- [Loki installation and authentication warning](https://grafana.com/docs/loki/latest/setup/install/)
- [Loki TSDB/filesystem storage](https://grafana.com/docs/loki/latest/configure/storage/)
- [Loki upgrade configuration checks](https://grafana.com/docs/loki/latest/setup/upgrade/)

## Pending live evidence

Repository validation can complete without production secrets, but live
container readiness, Prometheus target health, Loki config/runtime behavior,
private HTTPS routes, Homarr rendering, and the first post-deployment backup
remain unverified. Do not describe the live addition as complete before those
checks pass.
