# Operations

Use this guide to choose the right runbook and establish a safe scope. Run
PVE commands on `root@192.168.0.250`; use `pct exec` for LXCs. Read the affected
[service policy](reference/service-policies.md) and service README before a
mutation. [AGENTS.md](../AGENTS.md#permission-and-rollback-boundaries) defines
task-level authorization and rollback requirements.

## Inspect before changing

```bash
# On PVE; read-only
pct list
qm list
zpool status -x
zfs list -o name,used,avail,mountpoint
pct config 112
pct exec 112 -- docker ps --format 'table {{.Names}}\t{{.Status}}'
pct exec 112 -- cat /opt/dothomelab/DEPLOYED_COMMIT
systemctl show dothomelab-appdata-backup.service \
  -p Result -p ExecMainStatus -p InactiveEnterTimestamp
systemctl show dothomelab-wud-update.service \
  -p Result -p ExecMainStatus -p InactiveEnterTimestamp
```

Choose the affected CTID rather than surveying the fleet for every small
change. Use `hostname -I`, `ip route`, `findmnt`, `stat`, and `namei` when the
problem involves networking, mounts, or permissions. Read bounded service
logs privately; sanitize evidence before recording it. Do not dump container
environments, raw `docker inspect`, production dotenv, or expanded Compose.

A running container with no Docker health check is only running. Test the
relevant endpoint and workflow before declaring the application functional.
The current [status](status.md) separates those claims.

## Deploy a production change

1. Establish the affected project, current revision/image, data at risk,
   downtime, rollback, and acceptance checks. Use scheduled backup evidence
   for routine changes. Schema/data mutations need focused rollback first.
2. Implement and validate the change locally following
   [development](development.md). Commit it and make completed recovery changes
   retrievable through the clone path. Check out that intended commit in the
   PVE repository before syncing.
3. Inspect `scripts/sync-guest-repo.sh` before use: it exports `HEAD`, stages
   `/opt/dothomelab.next`, and replaces the one retained
   `/opt/dothomelab.previous`. Preserve an older deployment copy separately if
   the task requires it as rollback. It does not copy uncommitted edits.
4. Sync only the affected guest, then run the service's documented prepare
   step. Those scripts can create directories, mounts, or configuration; they
   are not read-only validation.
5. Use the service's deployment path. The generic `scripts/deploy-compose.sh`
   temporarily copies `/root/.env` to the guest's mode-0600 `/run/dothomelab.env`,
   runs `config --quiet`, pulls images, and runs `up -d`, then removes that env
   copy. **It pulls current tags**, so it is not suitable for an exact-image
   repair without reviewing the update policy. Do not use it for CT114's
   scoped environment or special cohorts that require another runbook.
6. Run focused verification, DNS/TLS checks, and the actual affected user
   journey. Confirm `DEPLOYED_COMMIT`, then record results and outstanding
   limits. A previous code archive cannot reverse a database migration.

Example shape for an already authorized, reviewed production rollout on PVE
(replace the CTID/path with the actual service):

```bash
scripts/sync-guest-repo.sh 112
pct exec 112 -- /opt/dothomelab/hosts/apps/navidrome/prepare.sh
scripts/deploy-compose.sh 112 hosts/apps/navidrome/compose.yaml
pct exec 112 -- /opt/dothomelab/hosts/apps/navidrome/verify.sh
```

Read the chosen verifier first. WebDAV probes write/delete a temporary object;
database restore tests create isolated retained state. Never use `down -v` as
a redeployment shortcut. Deploy Paperless-ngx before Paperless-GPT. Preserve
the shared Gluetun/qBittorrent/NZBGet/Prowlarr namespace as a Compose cohort.

## Update images

Production automatic updates run only after successful appdata backup via
`OnSuccess=dothomelab-wud-update.service`. WUD updates one eligible container at
a time, verifies health, stops on the first failure, and retains old images
(`PRUNE=false`). No independent WUD timer or Watchtower is permitted.

Read [WUD](../hosts/infra/wud/README.md) for discovery versus mutation commands,
retired-container handling, MAC compatibility, and busy-job guards. Read
[service policies](reference/service-policies.md) for manual image channels,
database majors, coupled upgrades, and endpoint acceptance. Do not infer a
successful update from a successful preceding backup. A failed run needs a
focused diagnosis before retry; it does not authorize a fleet restart.

## Diagnose access and user failures

| Symptom | Inspect next | What it does not prove |
|---|---|---|
| Hostname fails | Pi-hole at `192.168.0.100`, client DNS, Tailscale/LAN route | Public DNS resolution does not establish private access |
| TLS/403/502 from a route | NPM certificate, ACL, upstream address, direct service health | An HTTP response does not prove login or data access |
| Healthy service but missing media | Acquisition queue, canonical path, permissions, library scan | Do not move files with a reader to force discovery |
| Desktop music unavailable | SMB mount and native routing; [macOS runbook](../clients/macos-media/README.md) | A TCP 445 probe alone does not prove a usable mount |
| Zotero attachment absent | Native Zotero sync and **Verify Server**, then server-side presence | Metadata sync is distinct from attachment WebDAV sync |
| Stalled managed torrent | Owning Arr and [Cleanuparr policy](../hosts/servarr/cleanuparr/README.md) | Never delete it directly in qBittorrent as stalled-torrent recovery |
| Pulse action unavailable | Guest-local command-enabled agent and inventory | `PVEAuditor` cannot control guest lifecycle |

NPM's [managed route definition](../hosts/infra/proxy/README.md) is a partial
reconciliation policy, not an export of every live route. The existing NPM
database/certificates remain recovery inputs. New public exposure, router
changes, or disruptive DNS changes require separate authorization. Do not
assume all `rafael.media` services have the private ACL; see the dated audit.

## Backup and recovery

| Material | Canonical source | Protection / recovery limit |
|---|---|---|
| Compose, scripts, non-secret declarations | Git | Clone the intended committed revision |
| Application data, native identities, HAOS VMA | `/srv/appdata/docker` | Daily encrypted PBS job; application hooks refresh supported logical/SQLite copies |
| Production environment | PVE `/root/.env` | Included in the encrypted appdata backup; never shell-source it |
| Shared media, episodes, flows, Storyteller assets, Obsidian, photos | `/vault/shared` | Excluded from appdata PBS, including narrow mounts beneath appdata paths |
| Scoped Obsidian/photos/environment off-site copies | Proton runner | Not protection until login, first real cycles, restore checks, and timer enablement are complete |
| Guest roots | PVE guest storage | Rebuildable; not required as LXC recovery inputs |
| VM101 | Outside scope | No recovery claim from this repository |

The daily host job runs hooks, freezes CT102/110/112/114 briefly, snapshots
`rpool/appdata/docker`, resumes them, uploads encrypted appdata and `/root/.env`,
then removes only its temporary snapshot. Its success can enqueue WUD; failure
must not. Retention is 7 last, 14 daily, 8 weekly, and 12 monthly; scheduled
prune, GC, verify-new, and full verification are described in the
[PBS runbook](../backup/pbs/README.md). Do not launch or wait for a manual PBS
cycle for routine work.

PBS lives on `vault` on this physical host. Keep the encryption key off-host:
a copy inside its own encrypted archive cannot unlock it. Native recovery
state includes Samba's `passdb.tdb`, Tailscale's state, account hashes, and the
PBS key. These are sensitive mode-0600 files, never documentation attachments.

For a rebuild, follow [rebuild.md](rebuild.md) in full: supply clean PVE/network,
importable pools, shared files, appdata or a restore source, `/root/.env`, and
declared hardware. Run `./bootstrap.sh --dry-run`, resolve missing inputs, then
choose the normal, `--appdata-source`, or `--restore-latest` path. Bootstrap
retains existing guests and restores VM104 only when absent. Use
[HAOS recovery](haos-vm.md) for VMA/native backup validation.

For an application restore, use its service runbook and matching database
version. Retain current data and restored evidence until identity, records,
files, progress, and representative workflows pass. Never copy PostgreSQL data
directories across majors. A Git revert or retained image is not sufficient
rollback for a migrated schema. Restore tests and cleanup have distinct scopes.

Historical restore evidence and remaining clean-host gaps are linked from
[status](status.md). A successful daily service exit alone does not verify the
archive contents, off-site coverage, or a full restore.

## Staging and desktop operations

Use [staging](../hosts/staging/README.md) for `--staging-only`, app enrollment,
branch polling, health checks, failed-generation holds, and data-aware rollback.
Build cache and root disks are replaceable; accepted bundles, secrets, and data
generations are appdata. Retained generations are not automatic cleanup targets.

Desktop workflows have their own environments: [macOS media](../clients/macos-media/README.md)
installs a user LaunchAgent; [SNOWSKY ECHO](../clients/snowsky-echo/README.md)
works on a mounted physical card. Neither belongs in an LXC bootstrap or proves
device acceptance from a server health check.
