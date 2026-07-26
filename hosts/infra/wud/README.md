# Central WUD

WUD runs as a separate stack on infra. It watches infra through the local Docker socket and reaches apps (`192.168.0.112`) and servarr (`192.168.0.102`) through mutually authenticated Docker API endpoints on port 2376.

The UI/API is published only as `127.0.0.1:3001` inside LXC 110. The
Proxmox-host updater enters CT110 and executes
`/usr/local/sbin/dothomelab-wud-runner`, which must be installed from
`run-updates.py`; do not expose the unauthenticated UI directly to the LAN.

Observed 2026-07-25 after the Shelfarr and BookOrbit rollout: WUD was healthy.
The current Git-copied runner found 41 watched containers (14 Servarr,
10 Infra, and 17 Apps), all associated with `docker.backupgated`, and no
eligible update. The most recent daily PBS job completed successfully and its
`OnSuccess=` WUD unit also succeeded.

Later on 2026-07-24 the installed runner was refreshed and its SHA-256 matched
the repository copy. It now includes the Infra NPM and all three Portainer/
Agent external checks plus the expanded dry-run discovery report.

## PKI

Bootstrap generates a fresh internal CA and certificates under
`/etc/dothomelab/docker-api-pki`, then installs the two server identities and
Infra client identity. For an explicit manual rotation, generate into a new
ignored directory:

```bash
scripts/generate-docker-api-pki.sh secrets/docker-api-pki
```

Install `ca.pem`, the matching `server-cert.pem`, and matching server `key.pem` as `/etc/docker/tls/{ca.pem,server-cert.pem,server-key.pem}` in apps and servarr. Install `ca.pem`, `client/client-cert.pem`, and `client/key.pem` as `/etc/dothomelab/wud-docker-api/{ca.pem,client-cert.pem,client-key.pem}` in infra. Private keys must be root-owned mode `0400`.

After copying certificates, run the common Docker API installer in each remote LXC with its host-specific systemd drop-in. The installer enables Docker live-restore before restarting dockerd and rolls back the added listener if validation fails.

The CA private key and WUD client key grant root-equivalent Docker access.
Never commit them or expose port 2375. They are rebuild-time state: bootstrap
can rotate all three endpoints together, so an off-host copy is optional.

## Update policy

All Docker watchers use `WATCHBYDEFAULT=false`. Eligible application containers must set:

```yaml
labels:
  wud.watch: "true"
  wud.watch.digest: "true"
  wud.trigger.include: "docker.backupgated"
```

The Docker trigger is `AUTO=false` and `PRUNE=false`. WUD may discover updates
hourly, but only the PBS `OnSuccess=` updater executes mutations. WUD itself,
Immich and its dependencies, Gluetun, and application databases remain
excluded. There are no active legacy Compose stacks.

The declared yt-dlp Web UI, SnapOtter application, Stirling-PDF,
Audiobookshelf, Kavita, Shelfarr/Libation, BookOrbit, Grimmory, Storyteller, and
PinePods, Soularr, Navidrome, and slskd `latest` containers are
eligible and have direct or container-local checks in the sequential runner.
The exact Aurral v2 prerelease is manually updated and excluded from WUD.
The `music-metadata` Beets writer is also manually updated and excluded
because it has narrow write access to canonical music; its exact-release
reconciliation and post-write validation require a focused rollout.
Cleanuparr's exact 2.10.0 digest is also manually updated and excluded from
WUD because its schema-bearing configuration and destructive queue policy
require a focused dry-run and Arr/qBittorrent connection verification.
Before replacing Storyteller, the runner atomically acquires the
reconciler's update guard. A nonempty inbox, held reconciliation lock, or
`QUEUED`/`PROCESSING` readaloud makes the candidate a safe skip; the guard is
released after a healthy replacement. BookOrbit pgvector/PostgreSQL 18,
Grimmory MariaDB 11.4,
PinePods PostgreSQL 18 and Valkey 8, SnapOtter PostgreSQL 17, and Redis 8
remain excluded and major-pinned. All four Bar Assistant containers remain excluded because
the API, Salt Rim, Meilisearch, and Redis must be updated as one manually
verified compatibility cohort.

Before replacing Soularr or slskd, the runner holds Soularr's
`/data/.dothomelab-job.lock` so a cycle cannot start, then queries authenticated
slskd download and upload state. Any non-completed transfer or held Soularr
lock makes the candidate a safe skip. The lock remains held until the new
container and its direct health/path check pass.
The music-metadata writer mounts and acquires that same lock inode per album,
so its active tag/art/ReplayGain pass also makes either replacement a safe
skip.

Use `run-updates.py --dry-run` to force a scan and report every watched
container's `docker.backupgated` association without invoking a mutation.
Retained rollback containers can remain visible in WUD's stored discovery
state; the dry run reports them as `retired=skip`, excludes them from the
active trigger count, and the mutation path denies them before inspecting or
calling a trigger.
Use `--check-storyteller-busy` for a read-only interlock probe; exit `75`
means import or alignment work is active.
Use `--check-music-busy` to acquire and immediately release the combined
Soularr/slskd interlock; exit `75` means a Soularr cycle is active.

The sequential runner also checks Infra Nginx Proxy Manager and the Infra,
Apps, and Servarr Portainer status APIs and Portainer Agent ping endpoints
plus the loopback-only Syncthing health API, yt-dlp Web UI, SnapOtter,
Stirling-PDF, Audiobookshelf, Kavita, Shelfarr/Libation, BookOrbit, Grimmory,
Storyteller, and PinePods after
WUD replaces those containers.
A running container alone is insufficient because an application can keep its
process alive after closing its service listener.
