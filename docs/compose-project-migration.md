# Compose project migration runbook

Use this process to move legacy Portainer or ad-hoc containers into a
Git-managed Compose project without changing all services at once. It was
developed during the Servarr migration and is intended for the Infra and Apps
migrations too.

## How to use this runbook

The numbered process is the reusable procedure. The Servarr and Infra sections
at the end are complete historical records; keep both because they show
different failure modes. Before a new migration, read the reusable process,
the comparison below, and the observations for both completed hosts.

Do not copy a previous Compose file blindly. Carry forward the proven
techniques, then verify the new host's live mounts, data, dependency graph,
images, and application behavior.

## Lessons carried forward

| Finding | Servarr evidence | Infra evidence | Required action for Apps |
|---|---|---|---|
| Legacy metadata is not a source definition | Compose files were absent while labels still referenced them. | The `proxy` file was absent while three containers still had project labels. | Reconstruct from secret-safe live inspection and treat labels only as clues. |
| Mount topology can invalidate an otherwise correct Compose migration | `/data` was an empty root-disk directory because the intended shared mount was missing. | Persistent NPM and Portainer data still lived in root-disk named volumes. | Verify every source and destination with `findmnt`, `stat`, and checks from inside CT112 before copying anything. |
| `running` is not proof of preserved state | Arr row counts and qBittorrent torrent files were the baseline. | NPM row counts, route status codes, and Portainer APIs were the baseline. | Capture application-facing counts and database/file evidence, especially Immich assets, users, albums, and sampled originals. |
| Some services cannot move independently | Gluetun and its network-namespace consumers had to move as a cohort. | NPM needed its database, certificates, Certbot plugin, and external API/route checks. | Map database, cache, service-DNS, network-alias, worker, and application dependencies; move a cohort when an isolated cutover would break connectivity. |
| Ownership migration can accidentally become an upgrade | Radarr's cached `latest` differed from the running image. | DDNS, NPM, and Portainer pulled newer images during migration. | For high-value stateful Apps services, migrate first on the current digest/version; upgrade only after parity, backup, and rollback checks pass. |
| Image health may not equal application readiness | Deunhealth was still in its health-check start period. | NPM had no upstream health check and needed about three minutes to install a Certbot plugin; Portainer Agent could be running with a closed API. | Add realistic start periods and external API/workflow checks; do not use process state alone. |
| Rollback needs multiple independent layers | Old images/volumes, a ZFS snapshot, persistent counts, and PBS were retained. | Root volumes were copied while stopped, byte-compared, snapshotted, and backed up before replacement. | Retain old containers/images/volumes, make logical database dumps, snapshot appdata, protect user data separately, and prove the restore path. |
| Cleanup is not part of cutover | Root cleanup waited until backup and verification and preserved active images/volumes. | Legacy named volumes and snapshots remained after the project/network were removed. | Do not prune images, volumes, databases, or metadata until post-migration backup and restore validation close rollback. |

## Invariants

- Observe the live machine before trusting a saved inventory.
- Keep the old image, appdata, named volumes, and mount configuration until
  post-migration checks and a new backup pass.
- Move one independent service at a time. Stop at the first failed check.
- Never use `docker compose down -v`, delete a named volume, or prune images as
  part of a migration.
- Put secret values in the Proxmox host's `/root/.env`, not Compose or Git.
- Run `docker compose config --quiet` with the production environment before
  stopping the first legacy container.
- Do not combine ownership migration with a database-major or application
  upgrade for high-value stateful services.
- Identify whether each data path is covered by PBS. The appdata job protects
  `/srv/appdata/docker` and `/root/.env`; it does not protect
  `/vault/shared`.

## 1. Inventory and baseline

Record:

- `pct config <CTID>`, `findmnt`, numeric ownership, and free space;
- `docker compose ls`, every container's Compose project/service labels, image
  ID, mounts, ports, network mode, restart policy, health, and non-secret
  labels;
- only the names of container environment variables;
- application record counts and service-specific HTTP/API results;
- all named and anonymous Docker volumes;
- the dependency graph: `depends_on`, service-DNS names, network aliases,
  shared network namespaces, database/cache endpoints, and worker processes;
- every user-data path and whether it is SSD appdata, shared HDD data, guest
  root data, or an external mount.

Do not print `docker inspect` or expanded Compose environment data into task
logs. If a legacy Compose source is missing, capture protected inspect JSON,
compare each container environment with its image defaults, and reconstruct
only intentional overrides. Copy required secret values directly into the
production environment without displaying them.

The pre-migration baseline must use persistent state, not just `docker ps`.
Examples are Arr database row counts, qBittorrent torrent-state count, an
application `/ping` endpoint, and a Portainer status request.

For a database-backed media application, record both sides of the
relationship: application/database counts and evidence that representative
records resolve to readable original files. File counts alone cannot prove
that metadata survived, and database counts alone cannot prove that the media
paths still work.

## 2. Make rollback complete

Before the cutover:

1. Save the guest mount configuration and current container/image IDs.
2. Move or copy root-disk named-volume data into a host-qualified directory
   under the SSD appdata dataset. Keep the original volume unchanged.
3. Preserve any legacy-only secret environment values in `/root/.env`.
4. Run the encrypted appdata PBS job and require a successful upload.
5. Create a named pre-migration ZFS snapshot when an immediate local rollback
   is useful and capacity permits.
6. Confirm the old images still exist; WUD must keep `PRUNE=false`.
7. For every database, create an application-consistent logical dump in a
   backed-up path, record its checksum, and restore it into a disposable
   compatible database before calling the rollback set complete.
8. Protect any irreplaceable data outside `/srv/appdata/docker` by a separate
   verified mechanism; the appdata PBS job does not include `/vault/shared`.

For Portainer, stop it briefly before copying `portainer_data`, preserve
ownership with `cp -a` or tar, compare the source and destination database
checksums, then restart the legacy container. Use a host-qualified target such
as `/srv/appdata/docker/servarr-portainer` so three hosts cannot overwrite one
another's state.

Rollback means stopping the replacement, restoring the old container from its
recorded image/settings, and using the retained old appdata or snapshot. A
successful backup upload is not a substitute for knowing this path.

Filesystem snapshots are valuable but do not replace portable logical
database dumps. A crash-consistent database directory may recover, yet it is a
weaker migration artifact than a tested dump made with compatible tooling.

## 3. Prepare the Git project

- Reproduce the running service before refactoring it.
- Use explicit absolute bind mounts and explicit published host addresses.
- Add a real health check when the image contains suitable tooling.
- Add WUD labels only to services that are safe to replace independently:

```yaml
labels:
  wud.watch: "true"
  wud.watch.digest: "true"
  wud.trigger.include: "docker.backupgated"
```

- Use `wud.watch: "false"` for databases, bespoke upgrades, and dependency
  roots whose independent replacement would break consumers.
- For a high-value stateful service, use the currently running image
  version/digest for the ownership cutover and do not pull a newer image in
  the same step.
- Commit the validated definition before deployment so the live state maps to
  a Git commit.

## 4. Cut over an independent service

The old and new projects cannot own the same `container_name` simultaneously.
For each service:

1. Capture its baseline state and image ID.
2. Stop the old container.
3. Remove only that container; do not remove volumes.
4. Start only the replacement with
   `docker compose up -d --no-deps <service>`.
5. Wait for running/healthy state.
6. Verify HTTP/API behavior, logs, mounts, UID/GID access, and persistent record
   counts against the baseline.
7. Continue only after it passes.

If the replacement fails, remove it, restore the old container with the
recorded image/settings, and investigate before touching another service.

This procedure applies only when the service is actually independent. If it
uses a legacy project network to reach a database, cache, worker, or peer by
service name, either create a temporary shared external transition network or
cut over the dependency cohort together. Do not discover the DNS dependency
after removing the old network.

## 5. Handle dependency cohorts and shared network namespaces

Build a directed dependency map before selecting cutover units. A safe cohort
has a clear start order, health/readiness checks for every dependency, and one
rollback procedure. Keep databases on their existing compatible version during
the ownership migration.

`network_mode: "service:gluetun"` becomes
`NetworkMode=container:<gluetun-id>` at runtime. Docker will not safely replace
or remove Gluetun while qBittorrent, NZBGet, and Prowlarr still reference that
namespace.

For this pattern:

1. Pause container auto-restart helpers such as Deunhealth.
2. Stop and remove only the dependent containers.
3. Stop and remove the old Gluetun container.
4. Start and verify new Gluetun, including its native VPN health check.
5. Start and verify each dependent one at a time.
6. Resume the health helper.

Keep Gluetun out of WUD. Consumers may be WUD-eligible because replacing a
consumer leaves the current Gluetun namespace intact. Update the whole cohort
manually with Compose when Gluetun itself changes.

## 6. Portainer and WUD

Make Portainer Compose-owned with its data bind-mounted from SSD appdata and
the WUD labels above. A WUD Docker trigger can then recreate it on the remote
host through the existing mutually authenticated Docker API.

Portainer images contain no general-purpose HTTP client, so the central update
runner must perform an external status check after replacement or, at minimum,
the migration must check `https://<host>:9443/api/system/status`. Keep the
original named volume until the migrated database and UI are verified.

Treat Portainer Agent as a separate service. An unassociated agent can stop its
API listener after its client-association timeout while leaving the container
running, so `docker ps` alone is not proof that port 9001 works.

Nginx Proxy Manager's `latest` image may have no built-in Docker health check.
Add an explicit check for its admin API. Allow enough startup time for any
configured Certbot plugins to install before declaring the container
unhealthy, and make the central WUD runner check that API after replacement.

## 7. Remove the legacy project

After every service belongs to the new project:

- confirm `docker ps` has no legacy project labels;
- remove the stopped Watchtower container without volumes;
- remove only empty legacy networks;
- verify `docker compose ls` no longer lists the old projects;
- run the complete service verification again;
- confirm WUD discovers the intended containers and trigger association;
- run a post-migration backup.

Do not delete retained named volumes or rollback snapshots during this step.

## 8. Clean the guest root after rollback closes

Treat capacity cleanup as a separate, explicitly approved operation after the
post-migration backup and full verification pass. First attribute usage with
`df`, `du`, `docker system df -v`, `journalctl --disk-usage`, and container-log
sizes.

- Move valuable root-disk archives to a host-qualified SSD appdata rollback
  directory only after checking destination capacity. Compare checksums before
  and after the move.
- `docker image prune -a` preserves images referenced by containers, but it
  removes old image-based rollback points. Run it only after recording that
  those rollback points are no longer required.
- Never use `docker system prune --volumes` or a blanket volume prune during
  cleanup. Map and remove an unused volume individually only when its data and
  rollback value are understood.
- Clean package caches and vacuum journals only after measuring them. Keep a
  useful journal window rather than deleting all logs.
- List the remaining containers, images, and volumes, then repeat the complete
  service and persistent-state verification.

## 9. Apps and Immich preflight

Treat Immich as the highest-risk Apps service because the media files and the
database metadata are one recovery unit. Originals without the database lose
application metadata and relationships; the database without the originals is
also incomplete. Generated thumbnails or caches may be reproducible, but do
not assume a path is disposable until live configuration and restore behavior
prove it.

Before changing any Apps container:

1. Inspect CT112 live state and write a service/dependency map for Immich,
   Jellystat, Mealie, GitLab, their databases/caches/workers, the existing
   `media` project, and standalone Portainer.
2. Locate every Immich original/upload, external-library, thumbnail, encoded
   video, profile, and backup path. Record its host dataset, guest path,
   read/write mode, numeric owner, file count, and size. Do not infer paths
   from a sample Compose file.
3. Record the exact Immich application images, PostgreSQL image and major,
   required extensions, Redis/cache image, environment-variable names,
   network aliases, and health state without printing values.
4. Capture application-facing baseline counts for users, assets, albums, and
   any other important library state available through the supported API/UI.
   Select representative assets from different users/libraries and record
   enough non-secret evidence to verify that originals and metadata still
   resolve after migration.
5. Produce a logical PostgreSQL dump with tools compatible with the live
   server, plus required roles/ownership information. Store it beneath the
   backed-up appdata dataset, checksum it, and restore it into a disposable
   matching PostgreSQL instance. Query baseline counts from the restored copy.
6. Determine whether the Immich media library is under `/vault/shared`.
   Because the PBS appdata job excludes that dataset, define and minimally
   verify a separate protection/restore method before proceeding. A same-pool
   snapshot is useful rollback but is not an independent backup.
7. Run the existing pre-migration appdata PBS job only after the logical dumps
   are present. Require a successful upload and keep a named local snapshot
   when capacity permits.
8. Reproduce the current Immich versions and topology first. Do not consolidate
   its database, change PostgreSQL major/extensions, alter the storage
   template, or update Immich images during the ownership cutover.
9. Keep Immich, its database, and any unsafe dependency roots out of WUD until
   an explicit backup-gated update and rollback test has succeeded.

Do not begin the Immich cutover if any of these gates is missing:

- a tested logical database dump and a documented old-version restore command;
- verified protection for all irreplaceable media paths;
- exact live mount/UID/GID mapping from both host and guest;
- baseline metadata counts plus representative original-file checks;
- enough free SSD/HDD/root space for copies, dumps, snapshots, and old images;
- a dependency-aware cutover order and a timed rollback procedure;
- a way to verify login, timeline/library browsing, several original assets,
  albums/sharing as applicable, background jobs, and database health.

After cutover, repeat the same API/UI counts and representative file checks,
inspect database/application logs for migrations or missing files, run the
post-migration PBS backup, and restore the new logical dump into scratch again.
Only then consider a separate software update or cleanup task.

## Immich observations (2026-07-23)

- The legacy mutable `release` deployment was actually v1.124.2. It was
  recovered first, copied into a separate Git-managed `immich-migration`
  project, and left stopped with its original data as rollback evidence.
- The verified starting baseline was 3 users, 25,780 assets (865 managed and
  24,915 external), 24 albums with 3,339 assets, 1 library, 1,472 people,
  41,277 faces, 26 shared links, 10 tags, and no offline or deleted assets.
- The application advanced through v1.132.3, v1.143.1, and v2.7.5 before the
  final v3.0.3 `release` deployment. Focused checks preserved every baseline
  count and read five managed plus five external database-selected files at
  every checkpoint.
- The v1.143.1 checkpoint moved PostgreSQL 14 from pgvecto.rs to the official
  VectorChord image, Redis to Valkey, and the unchanged host upload directory
  from container path `/usr/src/app/upload` to `/data`. `/old-photos` remained
  mounted read-only and was never rescanned or moved.
- Pre- and post-VectorChord dumps are under
  `/srv/appdata/docker/immich/backups/20260723T211317Z-pre-vectorchord-v1.132.3`
  and `20260723T212250Z-post-vectorchord-v1.143.1`; the final v3 dump is
  `20260723T213250Z-final-v3.0.3`.
- Final vector indexes `clip_index` and `face_index` use `vchordrq`.
  `vectors=0.2.0` remains installed alongside `vchord=0.4.3` and
  `vector=0.8.0`; do not remove an extension without a separate verified task.
- The first final `release` cutover reused the stale local v1.124.2 tag because
  `docker compose up` does not refresh an existing mutable tag. OCI version
  inspection caught it immediately; an explicit pull replaced only the app
  and machine-learning containers with v3.0.3. `deploy-compose.sh` now pulls
  before every `up`.
- Immich and all three dependencies remain `wud.watch=false`. The old v1.124.2
  containers, rollback directories, logical dumps, ZFS snapshots, and PBS
  backups remain retained until manual UI review closes rollback.
- `hosts/apps/immich/verify.sh` is deliberately focused: it checks container
  health, public version, database checksum/extensions/counts, and ten selected
  files without recursively traversing the approximately 212 GiB appdata tree.

## Servarr observations (2026-07-23)

- Both legacy Compose files were already absent, although container labels
  still named `/data/compose/1/docker-compose.yml` and
  `/data/compose/2/docker-compose.yml`.
- CT102 maps host `/srv/appdata/docker` to guest `/docker`; use the observed
  guest path while keeping the host dataset as the backup source.
- CT102 initially lacked its shared-data mount. `/data` was an empty directory
  on the 91%-full guest root disk even though applications referenced
  `/data/media` and `/data/torrents`. The intended writable
  `/vault/shared -> /data` bind had to be restored before migration.
- Portainer and Portainer Agent had no Compose ownership. Portainer used the
  root-disk `portainer_data` volume; it was copied to the host-qualified SSD
  appdata path while the original volume was retained.
- Portainer server was already 2.33.3, while the standalone agent was pinned to
  2.21.5 and its API had timed out because no client associated with it. Both
  moved to 2.39.5; the restarted agent's ping endpoint returned HTTP 204.
- The legacy Radarr container used an older untagged image than the locally
  cached `latest` tag, so its ownership cutover also performed an image update.
- Baseline persistent counts were 25 Prowlarr indexers, 29 Sonarr series, 743
  Radarr movies, 159 Lidarr artists, 60 Readarr authors, and 737 qBittorrent
  torrent records.
- Explicit `192.168.0.102` port bindings are not reachable through
  `127.0.0.1` in CT102. Host-side verification must target the LXC address;
  in-container health checks can continue using loopback.
- The first complete verification ran while a restarted Deunhealth container
  was still in its health-check start period. Wait for `healthy` rather than
  treating `starting` as a failed migration.
- After all 13 services passed the same persistent-state baseline, WUD
  discovered every opted-in Servarr container, excluded Gluetun, and associated
  Portainer, Portainer Agent, and the other services with
  `docker.backupgated` (`AUTO=false`, `PRUNE=false`).
- The legacy `servarr`, `watchtower`, and hello test containers and their empty
  networks were removed. The original named/anonymous volumes and the
  pre-migration snapshot were retained. The encrypted post-migration PBS upload
  completed successfully at 16:19 CEST.
- CT102's 8 GiB root initially remained 92% full because cleanup was deferred
  until the post-migration backup and explicit approval. The later audit found
  4.941 GB of unused images, a 1.75 GB legacy config archive under `/root`,
  178 MB of APT cache, and 211 MB of journals. The archive was moved
  byte-for-byte to `/docker/migration-rollback/servarr-20260723`, unused images
  were pruned, APT was cleaned, and journals were capped at 100 MiB. Root usage
  fell to 34%; all nine volumes and the 13 active images remained, and the
  strict verification passed again.

## Infra observations (2026-07-23)

- The legacy Compose source `/data/compose/1/docker-compose.yml` was already
  absent, although Nginx Proxy Manager, Cloudflare DDNS, and hello still had
  `proxy` project labels. Standalone Portainer and Portainer Agent had no
  Compose ownership.
- NPM used root-disk volumes `proxy_data` and `proxy_letsencrypt`; Portainer
  used `portainer_data`. They were copied while stopped to host-qualified SSD
  appdata paths, byte-compared, backed up to encrypted PBS at 18:14 CEST, and
  retained as rollback volumes. Named pre-migration root and appdata ZFS
  snapshots were also retained.
- The NPM baseline was SQLite integrity `ok`, 35 proxy hosts, 6 certificates,
  and 1 user. Five representative HTTPS routes returned 200, 200, 307, 302,
  and 403 before and after cutover.
- Helloworld, Cloudflare DDNS, and NPM moved one at a time into
  `infra-services`. DDNS's four intentional settings matched by hash and its
  first update check succeeded. Its new image reported that the existing
  `stream.rafael.ink` record is DNS-only while the fallback policy is proxied;
  migration preserved that state rather than changing DNS policy.
- The updated NPM image performed database migrations and spent about three
  minutes installing its persisted Cloudflare Certbot plugin. It shipped
  without the old image's health check, so Compose now checks `/api/` with a
  five-minute startup allowance. Database counts, Nginx config, admin API, and
  representative routes all passed afterward.
- Portainer and Portainer Agent moved from 2.21.5 to 2.39.5 as separate
  cutovers. Portainer retained its database and returned its status API; the
  agent's previously unreachable ping endpoint returned HTTP 204.
- No legacy-labeled container remained, the empty `proxy_default` network was
  removed, and the original three named volumes were retained. The strict
  verifier passed; WUD discovered all five opted-in migrated/Portainer
  containers with `docker.backupgated`; and the encrypted post-migration PBS
  upload completed successfully at 18:51 CEST. Run
  `hosts/infra/services/verify.sh` after future changes.
