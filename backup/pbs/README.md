# PBS appdata backup

## Current status

Observed 2026-07-24: PBS 4.2.3 is running in protected unprivileged CT113,
`vault/pbs_datastore` is mounted at `/mnt/datastore/appdata`, and the `appdata`
datastore is online. The PVE timer and success-only WUD handoff are enabled.
The latest successful encrypted snapshot is
`host/afa-appdata/2026-07-24T12:38:45Z` (14:38 CEST). It completed at 14:47,
and its success-only WUD handoff completed without a reported update.
Verify-new finished `OK` at 15:44.

That snapshot includes the final Apps/NPM/Obsidian state and the native
recovery capture. Its catalog contains the Samba/Tailscale state, Infra/PBS
account hashes, and direct-recovery PBS key. A targeted restore of those five
files matched the live bytes and UID/GID/mode, then removed its temporary
directory.

## Scope

The only recurring backup source on the SSD is `rpool/appdata/docker`, mounted at `/srv/appdata/docker`. Guest root disks are intentionally excluded. The production `/root/.env` is added as `recovery-env.conf` whenever it exists and is non-empty.

The PBS datastore is the dedicated HDD dataset `vault/pbs_datastore`, bind-mounted into the PBS LXC at `/mnt/datastore/appdata`. `/vault/shared` is not copied into PBS because it already lives on the same HDD pool.

This is a host-local recovery design, not full off-site protection. Loss of
the `vault` pool would remove both `/vault/shared` and the PBS datastore.

## Backup mechanics

The daily systemd timer:

1. runs executable hooks under `/etc/dothomelab/backup-pre.d`;
2. briefly cgroup-freezes the configured appdata-writing LXCs without checkpointing or stopping them;
3. flushes pending writes and snapshots `rpool/appdata/docker`;
4. immediately resumes the LXCs and runs post hooks;
5. sends encrypted `appdata.pxar` and optional `recovery-env.conf` archives to PBS;
6. destroys only its own temporary ZFS snapshot.

Database migrations can add logical dump scripts to `backup-pre.d` and cleanup
scripts to `backup-post.d`; neither directory contained a hook during the
initial 2026-07-24 audit. The declared Paperless deployment installs
`20-paperless-database`, which creates portable `latest` and `previous`
PostgreSQL dumps before every snapshot. The declared SnapOtter deployment
likewise installs `30-snapotter-database`, with portable dumps and a retained
isolated PostgreSQL 17 restore-test path. Other recurring databases continue
to rely on the brief freeze plus filesystem snapshot, while retained Immich
logical dumps remain migration artifacts. A failed backup is not successful
merely because the ZFS snapshot was created; the PBS client must finish
successfully.

## Backup-gated container updates

`dothomelab-appdata-backup.service` starts `dothomelab-wud-update.service` through `OnSuccess=`. There is no independent update timer: failed backups do not enqueue updates, while successful uploads and cleanup are followed by one sequential WUD run.

The Proxmox-host wrapper enters LXC 110 and calls the central WUD API over loopback. WUD scans infra locally and apps/servarr through mutually authenticated Docker TLS endpoints. Only containers labeled for `docker.backupgated` are eligible. The runner records the old image/container IDs, updates one container at a time, waits for its replacement to become healthy, and stops at the first failure. WUD image pruning remains disabled for rollback.

The declared yt-dlp Web UI, SnapOtter application, Stirling-PDF, and
DroppedNeedle rolling `latest` containers are eligible and receive
post-replacement HTTP checks.
yt-dlp downloaded media is under `/vault/shared` and is outside this backup.
SnapOtter PostgreSQL/Redis and the four-container Bar Assistant project are
excluded from WUD and require their documented manual, backup-first paths.
slskd is pinned to DroppedNeedle's tested 0.25.1 release and is likewise
excluded from WUD. Its music library and completed/incomplete downloads are
under `/vault/shared`, outside this backup; only slskd application state and
DroppedNeedle's configuration/SQLite/cache state are in appdata.

Set `WUD_UPDATE_DRY_RUN=true` in `/etc/dothomelab/wud-update.conf` only while validating discovery; production omits the file or sets it to `false`.

Later on 2026-07-24 the installed
`/usr/local/sbin/dothomelab-wud-runner` was refreshed and its SHA-256 matched
the repository copy. The live runner now includes Infra NPM plus all three
Portainer/Agent external checks.

## Retention and maintenance

- backup: daily at 02:00, with up to 15 minutes randomized delay;
- retention: `keep-last=7`, `keep-daily=14`, `keep-weekly=8`, `keep-monthly=12`;
- pruning: daily on PBS;
- garbage collection: weekly;
- verification: `verify-new=true` checks new uploads, and a monthly job
  reverifies every retained snapshot;
- capacity: the PBS dataset has a 2 TiB quota to protect free space on `vault`.

PBS retention tiers are additive. With one scheduled backup per day, `keep-last=7` plus `keep-daily=14` normally keeps roughly three weeks of daily restore points before the weekly and monthly tiers.

## Credentials

The live PVE host stores:

- `/etc/dothomelab/pbs-appdata.conf`: repository and non-secret settings;
- `/etc/dothomelab/pbs-appdata.token`: backup-only API token;
- `/etc/dothomelab/pbs-appdata.key`: client-side encryption key.

All are mode `0600`. The native recovery capture also placed the key and PBS
root password hash under `/srv/appdata/docker/recovery` for direct appdata
rebuilds. Off-host copies remain mandatory for PBS-only restores: a key inside
its own encrypted appdata archive cannot unlock that archive. The ignored local
`secrets/` directory is one operator copy, not Git.

## Restore

List snapshots:

```bash
source /etc/dothomelab/pbs-appdata.conf
export PBS_REPOSITORY PBS_FINGERPRINT PBS_PASSWORD_FILE
proxmox-backup-client snapshot list
```

Restore appdata to an empty temporary path:

```bash
/usr/local/sbin/dothomelab-restore-appdata \
  host/afa-appdata/<timestamp> \
  /var/tmp/appdata-restore
```

For a full clean-node restore, let bootstrap reconnect PBS and restore the
latest snapshot into a temporary ZFS child before it activates the canonical
dataset and creates application guests:

```bash
./bootstrap.sh --restore-latest
```

Provide `/root/.env` and the off-host encryption key through
`PBS_ENCRYPTION_KEY_FILE` or `PBS_ENCRYPTION_KEY_B64`. The standalone restore
command remains useful for inspection and sampled verification.

If the SSD and PBS LXC are lost but `vault` survives:

1. reinstall PVE as node `afa`, configure `vmbr0`, and import `vault`;
2. clone Git, install `/root/.env`, and provide the off-host PBS key;
3. run `./bootstrap.sh --restore-latest`.

Never initialize, format, or recursively change ownership on a non-empty recovered datastore without first verifying its contents and UID mapping.

## Verification history

On 2026-07-23, two encrypted snapshots completed and verified successfully; the second reused 95.6% of its data. A temporary-path restore recovered 10,018 files, and 200 sampled files matched the live data byte-for-byte with identical UID, GID, and mode. The full verification job, retention simulation, and garbage collection also completed successfully.

The backup gate was tested separately on the same date. A deliberately failed backup did not start the WUD service. A successful encrypted backup completed at 15:28:18 CEST, its temporary ZFS snapshot was removed, and `OnSuccess=` started WUD at 15:28:19. WUD then updated only the disposable Servarr hello container, the replacement became healthy, the sequential runner exited successfully at 15:28:36, and the previous image remained available because pruning is disabled.

On 2026-07-24 the later on-demand job froze CT102, CT110, and CT112, uploaded a
246.784 GiB logical snapshot while reusing 244.444 GiB (99.1%), removed its
temporary ZFS snapshot, and started WUD through `OnSuccess=`. Verify-new
completed successfully. The encrypted catalog contained the five new native
recovery files, and a targeted restore matched each against live bytes and
metadata. This is not a full Apps/NPM restore or complete bare-metal recovery.
