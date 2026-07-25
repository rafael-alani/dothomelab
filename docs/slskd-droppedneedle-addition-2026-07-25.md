# slskd and DroppedNeedle addition — 2026-07-25

## Scope and live preflight

This change declares separate `slskd` and `droppedneedle` Compose projects on
Apps LXC 112, a private shared Docker network, narrow shared-data mounts,
private NPM routes, Homarr applications, focused verification, recovery
secrets, and explicit update policy.

Read-only live inspection found:

- PVE 9.1.2 with healthy `rpool` and `vault` pools;
- about 521 GiB free on canonical appdata and 19.9 TiB free on
  `vault/shared`;
- Apps at `192.168.0.112` with no listeners on 5030, 50300, or 8688;
- no slskd/DroppedNeedle containers, Compose projects, appdata trees, proxy
  rows, or exact Homarr applications;
- NPM and Homarr SQLite integrity `ok`;
- the existing `/vault/shared/media/music` directory on `vault/shared`, owned
  by the Apps-mapped UID 1000 with owner write permission;
- no `/vault/shared/media/slskd` directory or new LXC mounts;
- none of the six slskd production variables in `/root/.env`.

The live Apps guest remains on the older five-project, 12-container
generation. Several earlier declared projects also await their production
secrets. This change is therefore a committed recovery declaration, not a
claim that either new service is live.

## Declared topology

| Project | Image | Apps ports | Durable state | Update path |
|---|---|---:|---|---|
| `slskd` | `slskd/slskd:0.25.1` | 5030 web; 50300 Soulseek peer | app config/databases/logs/share index | manual; `wud.watch=false` |
| `droppedneedle` | `droppedneedle/droppedneedle:latest` | 8688 | config, SQLite/cache, plugins, import staging | backup-gated WUD |

The projects share the external Docker network `slskd-droppedneedle`, so the
DroppedNeedle download-client URL is `http://slskd:5030`. slskd's primary API
key has Administrator role and is restricted to Docker bridge CIDRs. Web
authentication stays enabled, remote configuration and remote file deletion
stay disabled, and NPM terminates HTTPS.

## Storage and recovery

Bootstrap adds two exact Apps bind mounts:

- `/vault/shared/media/music` -> `/music`, read-write at the LXC boundary;
- `/vault/shared/media/slskd` -> `/slskd-downloads`, read-write.

slskd mounts `/music` read-only for sharing and writes only to
`/slskd-downloads/{complete,incomplete}`. DroppedNeedle mounts both paths
read-write so it can import into the library. Both host directories are on the
same `vault/shared` ZFS filesystem, and prepare/verify scripts check the source,
device, mapped UID permissions, and container mount modes.

The directories remain separate narrow container mounts. Current DroppedNeedle
documents a safe copy-and-remove fallback across mount boundaries; an import
can therefore briefly need space for both copies. This is preferred to giving
the container write access to all of `/vault/shared/media`, which also holds
photos, movies, series, books, and other unrelated data.

slskd state and DroppedNeedle's configuration/SQLite/cache state live under
`/srv/appdata/docker` and are included in the encrypted PBS appdata flow.
Music and downloads are under `/vault/shared` and are not included in that
backup or the scoped Proton jobs. Loss of `vault` would lose them.

Production `/root/.env` must add:

- `SLSKD_SOULSEEK_USERNAME`;
- `SLSKD_SOULSEEK_PASSWORD`;
- `SLSKD_WEB_USERNAME`;
- `SLSKD_WEB_PASSWORD`;
- `SLSKD_API_KEY`;
- `SLSKD_JWT_KEY`.

DroppedNeedle creates its first administrator through the private web UI.
After login, configure `/music`, `http://slskd:5030`, and the dedicated API
key, then run a library scan and a legally permitted end-to-end import.

## Proxy, dashboard, and network boundary

NPM maps:

- `slskd.rafael.media` to `192.168.0.112:5030`;
- `droppedneedle.rafael.media` to `192.168.0.112:8688`.

Both routes allow only `192.168.0.0/24` and `100.64.0.0/10`, followed by
`deny all`. WebSocket/SSE support, disabled proxy buffering, request streaming,
and extended timeouts are declared. Homarr receives both applications and one
tile per existing `dashboard`, `Admin`, and `default` board. The NPM and Homarr
reconcilers retain new focused SQLite backups before their idempotent changes.

The Compose project publishes TCP 50300 only on the Apps LAN address. The
repository does not alter the router's public 80/443-only forwarding contract.
slskd documents that lack of an inbound peer forward can reduce connectivity.
Adding that forward is a separate public-network change requiring explicit
authorization and verification.

## Update policy

DroppedNeedle requires slskd 0.25.0 or newer and explicitly documents 0.25.1
as its tested version. slskd is therefore pinned to `0.25.1`, not `latest`,
and excluded from WUD. Update it manually only after configuration-migration
review and confirmation that DroppedNeedle supports the target. Verify login,
Soulseek connection, shares, search/download, API access, and import before
accepting it. The scheduled appdata job is not a manual update gate.

DroppedNeedle documents `latest` as its production image. Its default startup
upgrade path backs up settings and SQLite state, upgrades a working copy,
validates it before starting background workers, and retains upgrade backups.
It is enrolled in backup-gated WUD; the sequential runner additionally checks
`/health` after replacement. Old images remain available because pruning is
disabled.

Primary upstream references:

- [DroppedNeedle deployment and upgrade behavior](https://github.com/DroppedNeedle/DroppedNeedle)
- [DroppedNeedle slskd requirements](https://droppedneedle.com/docs/slskd-setup)
- [DroppedNeedle configuration and persistent paths](https://droppedneedle.com/docs/configuration)
- [slskd Docker deployment](https://github.com/slskd/slskd/blob/master/docs/docker.md)
- [slskd configuration and security options](https://github.com/slskd/slskd/blob/master/docs/config.md)
- [slskd Nginx reverse-proxy requirements](https://github.com/slskd/slskd/blob/master/docs/reverse_proxy.md)

## Repository validation

- Both new Compose files passed the Apps guest's installed Docker Compose
  parser with synthetic credentials.
- All changed shell scripts passed `bash -n`; the WUD runner passed Python
  bytecode compilation and the NPM reconciler passed Node syntax validation.
- Both SQLite reconcilers ran twice against temporary copies of the live
  databases. Integrity remained `ok`; the final copies contained exactly 14
  managed private NPM routes, 12 managed Homarr applications, 36 managed
  items, and all expected board placements.
- A complete `./bootstrap.sh --dry-run` against the live PVE state passed with
  a synthetic validation environment. A dry-run with production `/root/.env`
  correctly stopped at an earlier-generation missing required variable,
  confirming that an apply must wait for the complete current secret set.

No production dataset, mount, guest, container, NPM row, Homarr row, or
environment file was changed during this validation.

## Rollback and pending live evidence

Before deployment, retain an appdata ZFS snapshot and the focused NPM/Homarr
SQLite backups. Rollback restores the prior guest Git copy and old images,
stops only the two new projects without deleting data, and restores or removes
only the two managed routes/apps. Keep both appdata trees and shared downloads
until focused application checks pass and rollback is no longer needed.

Live evidence still required:

1. all production variables for the complete current Git generation;
2. additive LXC mounts and mapped-user permission checks;
3. both projects healthy with exact images and WUD labels;
4. slskd Soulseek login/share connectivity and DroppedNeedle API pairing;
5. one authorized search, download, and import with file/metadata verification;
6. private HTTPS and Homarr rendering on all managed boards.
