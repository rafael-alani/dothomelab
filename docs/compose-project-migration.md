# Compose project migration runbook

Use this process to move legacy Portainer or ad-hoc containers into a
Git-managed Compose project without changing all services at once. It was
developed during the Servarr migration and is intended for the Infra and Apps
migrations too.

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

## 1. Inventory and baseline

Record:

- `pct config <CTID>`, `findmnt`, numeric ownership, and free space;
- `docker compose ls`, every container's Compose project/service labels, image
  ID, mounts, ports, network mode, restart policy, health, and non-secret
  labels;
- only the names of container environment variables;
- application record counts and service-specific HTTP/API results;
- all named and anonymous Docker volumes.

Do not print `docker inspect` or expanded Compose environment data into task
logs. If a legacy Compose source is missing, capture protected inspect JSON,
compare each container environment with its image defaults, and reconstruct
only intentional overrides. Copy required secret values directly into the
production environment without displaying them.

The pre-migration baseline must use persistent state, not just `docker ps`.
Examples are Arr database row counts, qBittorrent torrent-state count, an
application `/ping` endpoint, and a Portainer status request.

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

For Portainer, stop it briefly before copying `portainer_data`, preserve
ownership with `cp -a` or tar, compare the source and destination database
checksums, then restart the legacy container. Use a host-qualified target such
as `/srv/appdata/docker/servarr-portainer` so three hosts cannot overwrite one
another's state.

Rollback means stopping the replacement, restoring the old container from its
recorded image/settings, and using the retained old appdata or snapshot. A
successful backup upload is not a substitute for knowing this path.

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

## 5. Handle shared network namespaces as a cohort

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
