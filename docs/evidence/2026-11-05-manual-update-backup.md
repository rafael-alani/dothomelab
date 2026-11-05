# Manual update backup — November 5, 2026

Requested after the [Proton read-back repair](2026-10-17-proton-backup-activation.md#november-5-interrupted-read-back-and-repair),
to provide a fresh recovery point before Rafael updates Immich and other apps.
No application upgrade is part of this task.

## Capture and scope

- Immich remains **3.0.3**, with healthy server, machine learning, Valkey and
  PostgreSQL 14 / VectorChord 0.4.3. Its external `/old-photos` bind is read-only.
- New maintained helper: `hosts/apps/immich/checkpoint.py`, tested revision
  `7f15194b9a55545e56626b425a14f3e71b50aad3` published on
  `origin/codex/reference-media-boards`. The historical v1 restore helper does
  not match the current image/schema. Parser tests, syntax and documentation
  checks passed; actual recovery acceptance is recorded below.
- The checkpoint at
  `/srv/appdata/docker/immich/backups/20261105T040100Z-pre-update-manual`
  contains a **210,548,979-byte custom PostgreSQL dump**, a private recovery-role
  dump, exact runtime image IDs/registry digests/mounts, and counts for **67
  tables** from the same exported database snapshot as the dump.
- The captured database has **27,583 asset rows**, 3 users, 34 albums and 5,343
  album memberships. It already contains 863 offline and 1,040 deleted asset
  records; capturing them does not recover media previously removed or archived.
  The existing focused verifier passed, including ten representative originals.
- The original-file inventory covers **868 files / 4,757,258,748 bytes** across
  managed `upload`, `library`, and `profile` directories, including their marker
  files. This is separate from the much larger external photo tree.
- [Immich's recovery documentation](https://docs.immich.app/administration/backup-and-restore/)
  requires both the database and original files. The helper tests that pairing;
  a dump alone is not a complete photo backup.

## Manual PBS snapshot

`host/afa-appdata/2026-11-05T04:02:54Z` contains **400,818,803,834 logical bytes**.
The backup-only transient unit
`dothomelab-manual-appdata-20261105t040100z.service` began at 05:02:22 CET and
finished successfully at **05:19:38 CET**. It ran the installed appdata backup
script and configured database hooks, briefly froze/unfroze the declared LXCs,
uploaded encrypted appdata plus `recovery-env.conf`, and removed only its own
temporary snapshot `rpool/appdata/docker@pbs-20261105T040222Z`.
Its `OnSuccess` was empty: this manual run did not enqueue a WUD upgrade.
The regular daily timer and its existing update handoff remain configured.

PBS covers application state/databases and Immich's managed upload tree. It does
not include `/vault/shared`, including external photos, Obsidian, reader media,
and archive paths. PBS itself is on the same host/HDD pool; it is a local recovery
point. Proton is the separate cloud copy, whose current photo read-back remains
an independent completion check.

## Verification and retained recovery material

The actual PBS `recovery-env.conf` was decrypted into a process pipe and matched
against the live environment bytes; no restored plaintext environment was written
to disk. The existing operator `secrets/pbs-appdata.key` is mode 0600 and matches
the PVE key. No key/token/environment values were printed or committed.

Selective recovery is into
`/srv/appdata/docker/immich/restore-tests/pbs-20261105T040254Z`, preserving
`immich/backups/<checkpoint>` and the three `immich/upload` source trees.
The restored `checkpoint.json`, `immich.dump` and `roles.sql` independently match
the original checkpoint SHA-256 values. At 07:16 CET the selective restore client
was still traversing the archive, after all selected files had arrived. After the selected content passed all checks, its remaining traversal of unrelated
archive content was intentionally stopped with SIGTERM (client exit -15) to
release the snapshot read lock. This is not represented as a successful full CLI
restore. Acceptance rests on independent exact recovered-file hashes/inventory,
the completed database import/comparisons, and the separate full PBS verification.

The corrected isolated restore passed at **07:08 CET**:

- Exact inventory, byte sizes and SHA-256 hashes for **all 868 managed-original
  files** match, with no missing or extra files.
- The recovered dump restores into the recorded PostgreSQL image, with **all 67
  table counts**, **27,583 asset rows** and **all nine extension versions** matching.
- No network is attached to the test container. Its successful runtime was
  removed, while data remains at
  `/srv/appdata/docker/immich/restore-tests/20261105t060833z`.
- The private result is `restore-test-20261105t060833z.json` inside the recovered
  checkpoint directory. This result was written after the backup; it is not
  claimed to be inside the earlier PBS snapshot.

The production Immich 3.0.3 health/count/extension/original-readability checks
passed again after cleanup. The recovered full application UI was not started;
this acceptance covers the database and original-file restoration. Other apps
are included in appdata but were not individually restore-tested in this task.

The source checkpoint, recovered files and isolated database data are owned by
backup operations and retained for this pre-update rollback. Remove them only
after the intended upgrade is accepted, another usable recovery point exists,
and the cleanup is explicitly authorized. Successful test containers are removed;
failed test containers were stopped for diagnosis and then removed after the
corrected restore passed. Existing production
containers, images, database directories and prior backup generations are retained.

### Restore procedure compatibility findings

The first isolated import recovered all 67 table counts, but the version check
correctly refused success: production's installed pgvector SQL version is 0.8.0,
whereas the identical runtime image creates 0.8.1 by default and contains only
that creation script. An attempt to select 0.8.0 without its definition failed.
The recovery tools now retain the unmodified official
[pgvector 0.8.0 definition](../../hosts/apps/immich/restore-assets/SOURCE.md),
with its permissive license and pinned SHA-256. It is copied only into the
isolated container, leaving production's binary image and database unchanged.

Precreating every extension also conflicted with the dump's `vectors` schema.
The final procedure precreates only pgvector in `public`, lets `pg_restore` order
other extensions and their schemas, then requires every extension version and
all table counts to match. The helper revision is
`7f15194b9a55545e56626b425a14f3e71b50aad3`; its dependency is available from Git,
without a future upstream download. Test output identifies each phase without
printing SQL diagnostics or private row data.

The PBS client initially created the test's top-level directory as PVE root,
mode 0700. After checking `pct config`, mounts, `stat` and `namei`, only that
new directory was assigned host UID/GID 100000 so CT112 root could read it.
Restored child ownership and production permissions were not changed.

Retained diagnostic database directories (not accepted rollback databases):

- `/srv/appdata/docker/immich/restore-tests/20261105t054547z`: default-extension
  import, all counts matching but pgvector 0.8.1 instead of 0.8.0.
- `/srv/appdata/docker/immich/restore-tests/20261105t055113z`: missing-definition
  diagnosis, followed by a successful default-version diagnostic import.
- `/srv/appdata/docker/immich/restore-tests/20261105t060012z`: exact extension
  creation succeeded, but the all-extension precreation caused schema conflict.

Backup operations owns these diagnostics. Retire their data only after the
corrected restore passes and explicit appdata cleanup is authorized. Their three stopped containers were removed with the maintained runtime-cleanup
helper after its inspection-only plan. All running containers, retained images
and bound data were checked unchanged. Private inspection metadata is retained at
`/srv/appdata/docker/runtime-cleanup/20261105T061706Z-692855`, owned by backup
operations until the corresponding diagnostic data can be retired. No production
container was a cleanup target.

## Completion and limits

PBS verify-new completed **TASK OK at 07:24:03 CET**, with zero errors for the
payload archive (`appdata.ppxar.didx`), metadata archive (`appdata.mpxar.didx`)
and `recovery-env.conf.blob`. The payload verification read 272,023.66 MiB over
7,461.36 seconds. Snapshot protection was not yet set: PBS refused its exclusive
lock while the snapshot was in use by the restore reader. The error context corresponds to the snapshot lock in
[Proxmox's implementation](https://lore.proxmox.com/pbs-devel/20261023121152.760779-1-f.gruenbichler%40proxmox.com/).
After the selected-content checks passed, only that task's redundant restore
reader was stopped. The normal PBS client then set **protected=true**, and a
fresh snapshot query confirmed both **verification.state=ok** and **protected=true**.
No lock was bypassed and no datastore file was edited. A private
`pbs-verification.json` receipt is retained inside the recovered checkpoint.
The final listed snapshot size is 400,818,803,954 bytes; verification metadata
added 120 bytes to its initial total.

At 07:26 CET, Proton's independent November 2 photo read-back had verified **35/53 parts**.
Notes, environment and managed Immich archives in that cycle had already passed.
The last fully accepted external-photo cloud generation remains October 17 until
all current parts and the generation completion marker pass. A fresh 07:23 CET
scan found the same **43,087 external photo files**, no new or missing paths, and
no changes in inode, mode, size, modification time or change time against the
November 2 source inventory. This is a metadata comparison, not a new full
226,628,397,040-byte content rehash; the original capture and archive comparison
already have per-file SHA-256 proof.

Pulse verified all declared application containers and Docker agents on CT102,
CT110, CT112, CT114 and CT115. Homarr's staging inventory matched six entries.
Shared probes, scrapes, alert-rule evaluation, Grafana datasource/dashboard
checks and a fresh Loki probe passed. Notification delivery, WAN monitoring and
browser analytics were outside these checks. CT114/115 build caches remain
21.07 GB / 9.7 GB; no builds or cache/image/volume pruning were performed.

Temporary source transports named `immich-checkpoint-30897fe.py`,
`immich-checkpoint-eb36160.py`, `immich-checkpoint-406c49b.tar`, and
`immich-checkpoint-7f15194.tar` were removed from operator `/private/tmp`, PVE
`/tmp` and CT112 `/run`; the two extracted `/run/immich-checkpoint-<revision>`
Git archives were also removed. Maintained helpers and recovery assets are
published in Git. Recovery data, private proof and retained images remain.

## Pre-update live recheck at 12:15 CET

After reconnecting over the existing Tailscale route, the manual snapshot still
reported `verification.state=ok` and `protected=true`. Its checkpoint dump and
role-file hashes remain intact. Immich is healthy on 3.0.3 with all four image IDs
unchanged, the same application counts and nine extension versions, and ten
representative original paths readable. The managed-original inventory is still
868 files, with zero added/missing files or size changes; this inventory check is
not a repeat of the earlier complete content-hash restore test. External photos
remain mounted read-only. Both ZFS pools are healthy; appdata has 49.5 GiB free.

The [Proton cycle completed at 09:37:21 CET](2026-10-17-proton-backup-activation.md#november-5-final-completion-check):
all 53 distinct photo parts passed, all four dataset success markers match
`20261102T023144Z`, and the incomplete-cycle marker is gone. Both backup timers
remain active; no PBS backup/restore tasks remain running. This establishes the
backup/recovery readiness requested before updates. It does not validate an
unspecified future application/database release, and other applications have
not been individually restore-tested. No updates or scheduled follow-ups were
performed in this recheck.
