# PBS appdata backup

## Scope

The only recurring backup source on the SSD is `rpool/appdata/docker`, mounted at `/srv/appdata/docker`. Guest root disks are intentionally excluded. The production `/root/.env` is added as `recovery-env.conf` whenever it exists and is non-empty.

The PBS datastore is the dedicated HDD dataset `vault/pbs_datastore`, bind-mounted into the PBS LXC at `/mnt/datastore/appdata`. `/vault/shared` is not copied into PBS because it already lives on the same HDD pool.

## Backup mechanics

The daily systemd timer:

1. runs executable hooks under `/etc/dothomelab/backup-pre.d`;
2. briefly cgroup-freezes the configured appdata-writing LXCs without checkpointing or stopping them;
3. flushes pending writes and snapshots `rpool/appdata/docker`;
4. immediately resumes the LXCs and runs post hooks;
5. sends encrypted `appdata.pxar` and optional `recovery-env.conf` archives to PBS;
6. destroys only its own temporary ZFS snapshot.

Database migrations can add logical dump scripts to `backup-pre.d` and cleanup scripts to `backup-post.d`. A failed backup is not successful merely because the ZFS snapshot was created; the PBS client must finish successfully.

## Backup-gated container updates

`dothomelab-appdata-backup.service` starts `dothomelab-wud-update.service` through `OnSuccess=`. There is no independent update timer: failed backups do not enqueue updates, while successful uploads and cleanup are followed by one sequential WUD run.

The Proxmox-host wrapper enters LXC 110 and calls the central WUD API over loopback. WUD scans infra locally and apps/servarr through mutually authenticated Docker TLS endpoints. Only containers labeled for `docker.backupgated` are eligible. The runner records the old image/container IDs, updates one container at a time, waits for its replacement to become healthy, and stops at the first failure. WUD image pruning remains disabled for rollback.

Set `WUD_UPDATE_DRY_RUN=true` in `/etc/dothomelab/wud-update.conf` only while validating discovery; production omits the file or sets it to `false`.

## Retention and maintenance

- backup: daily at 02:00, with up to 15 minutes randomized delay;
- retention: `keep-last=7`, `keep-daily=14`, `keep-weekly=8`, `keep-monthly=12`;
- pruning: daily on PBS;
- garbage collection: weekly;
- verification: new/unverified snapshots daily and every retained snapshot monthly;
- capacity: the PBS dataset has a 2 TiB quota to protect free space on `vault`.

PBS retention tiers are additive. With one scheduled backup per day, `keep-last=7` plus `keep-daily=14` normally keeps roughly three weeks of daily restore points before the weekly and monthly tiers.

## Credentials

The live PVE host stores:

- `/etc/dothomelab/pbs-appdata.conf`: repository and non-secret settings;
- `/etc/dothomelab/pbs-appdata.token`: backup-only API token;
- `/etc/dothomelab/pbs-appdata.key`: client-side encryption key.

All are mode `0600`. Off-host copies are stored as `secrets/pbs-appdata.key` and `secrets/pbs-root-password`; that directory is ignored by Git. Without the encryption key, encrypted backups cannot be restored.

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

After checking ownership, permissions, database dumps, and files, restore into a newly created `rpool/appdata/docker` dataset while applications are stopped. Recreate application LXCs and bind mounts from Git before starting Compose.

When the snapshot contains it, restore the `recovery-env.conf` archive separately to a temporary file, inspect its permissions, and then install it as `/root/.env` with mode `0600`.

If the SSD and PBS LXC are lost but `vault` survives:

1. reinstall PVE and import `vault`;
2. recreate the PBS LXC;
3. bind-mount `/vault/pbs_datastore` at `/mnt/datastore/appdata`;
4. reconnect the existing datastore without initializing or deleting its contents;
5. restore the encryption key from the off-host `secrets/` copy;
6. restore appdata and recreate services from Git.

Never initialize, format, or recursively change ownership on a non-empty recovered datastore without first verifying its contents and UID mapping.

## Verified deployment

On 2026-07-23, two encrypted snapshots completed and verified successfully; the second reused 95.6% of its data. A temporary-path restore recovered 10,018 files, and 200 sampled files matched the live data byte-for-byte with identical UID, GID, and mode. The full verification job, retention simulation, and garbage collection also completed successfully.

The backup gate was tested separately on the same date. A deliberately failed backup did not start the WUD service. A successful encrypted backup completed at 15:28:18 CEST, its temporary ZFS snapshot was removed, and `OnSuccess=` started WUD at 15:28:19. WUD then updated only the disposable Servarr hello container, the replacement became healthy, the sequential runner exited successfully at 15:28:36, and the previous image remained available because pruning is disabled.
