# Form & Field staging — 2026-10-17

## Scope and revisions

Private staging on PVE `afa`, CT114 `192.168.0.114`, and Infra CT110. Observed
from the operator Mac over PVE SSH and `pct exec`, plus browser/API checks.
This is a focused deployment, not a new fleet-wide baseline or restore test.

- Application branch: `rafael-alani/ff:staging`; accepted revision
  `2ecef28a14c6726db765c441c6438084f5a69bd1`.
- Homelab implementation: `ef8bc7f0f525417d1e8cee8131add3af108916a0` on
  `codex/ff-staging`, based on the observed deployed `2801876` baseline.
- Guest archives CT110 and CT114 carry that exact implementation marker.
  PVE's isolated deployment checkout is `/root/dothomelab-ff-staging-20261017`.
- The application snapshot includes the user's existing shadcn-based Form &
  Field customization. The original Mac checkout and its uncommitted files
  were preserved. The user explicitly approved publishing the staging branches.

## Deployment contract

`https://ff.staging.rafael.media/create` routes through the existing staging
wildcard certificate and private LAN/Tailscale policy to CT114 port 8082.
The normal two-minute branch poller owns updates. The image runs Node 26.9.0,
pnpm 10.33.4, and Bun 1.3.14; build, typecheck and all Form & Field tests are
required during the image build. The full authored source remains available
for export ZIPs. Runtime UID 1000 has a read-only root, temporary caches,
2 GiB memory and 2 CPUs. The app has no database, persistent container mount,
production environment, external API key, or production integration.

The initializer creates only an empty scoped environment for `--app ff`.
The image assigns checkout ownership to the application user because the
staging runner's restrictive umask produces private source files. The pinned
Fumadocs adapter receives `_FUMADOCS_MDX=1` only at runtime to reuse built
metadata instead of trying to regenerate `.source` on the read-only root.

Browser drafts belong to the origin and are outside server backups. Download
presets before clearing browser data or changing origins. Filesystem saves are
intentionally unavailable on the production server.

## Verification

The preflight snapshot passed `ff:build`, `ff:check` and all 37 `ff:test` tests.
The isolated homelab checks passed seven staging deployment/rollback tests,
one lifecycle retirement test, registry validation, and documentation checks.
Compose validation was quiet and used an empty app environment.

Before final acceptance, direct and trusted HTTPS requests returned 200 for
`/create`; the browser rendered the studio, official preview and Advanced
controls. A source export returned a valid 85-file ZIP containing component
source, manual CSS and provenance. `/api/form-field/styles` returned 404.
Pi-hole resolves the exact hostname to `192.168.0.110`; a non-allowed loopback
source inside NPM received HTTPS 403. Nginx configuration validation passed.
Homarr reconciliation included ff alongside the other two active staging apps.
Film-introspect remained healthy throughout.

The final runner accepted `2ecef28a1` at 17:43:44 CEST. The final image again
passed its production build, typecheck and all 37 tests. Post-promotion HTTPS
export returned a valid 85-file ZIP (262,178 bytes); documentation returned 200
and the styles endpoint returned 404. Startup logs were clean, runtime UID was
1000, root was read-only and the memory limit was 2 GiB. The focused live
verifier passed guest identity/isolation, both accepted application commits,
SQLite integrity for Film-introspect, polling, backup-scope inclusion, exact
DNS, trusted HTTPS and Homarr reconciliation. A subsequent ff poll returned
`current` without rebuilding.

Accepted release directory:
`/srv/appdata/docker/staging/ff/releases/1792251246805460205-2ecef28a14c6-fcc66145f9cf`.
Its source bundle, empty scoped environment, Compose and release metadata are
retained. Incomplete/preflight generations and images remain available; no
rollback material was pruned.

## Rollback and limits

The prior complete guest archives are retained as
`/opt/dothomelab.before-ff-20261017` in CT110 and CT114; older
`/opt/dothomelab.previous` directories were preserved. NPM's fresh verified
SQLite backup is
`/srv/appdata/docker/infra-nginx-proxy-manager/database.sqlite.pre-ff-20261017`,
with the prior exact DNS host list in `dns-hosts.pre-ff-20261017.json` beside it.
These contain service recovery state and must remain private.

To roll back only this enrollment, pause the staging timer, stop only the ff
Compose project, restore the previous registry/configuration, and remove only
the ff route/DNS record through their owners. Keep all release/source/image
assets. Restoring the entire NPM database could discard subsequent unrelated
changes, so use the fresh backup for focused comparison/recovery. No volume
or application data deletion is part of rollback.

The retained Git bundle and release configuration are inside canonical staging
appdata and its existing backup scope. No on-demand PBS backup or restore was
run. Base images, package registries and Google Fonts remain external rebuild
dependencies. No external-internet ACL test, exhaustive component/style test,
mobile-browser matrix or independent consumer rebuild was performed here.
