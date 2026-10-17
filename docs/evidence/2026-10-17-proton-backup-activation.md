# Proton backup activation — 2026-10-17

Environment: operator Mac, PVE `afa`, CT110 Infra and CT112 Apps. Timezone:
Europe/Amsterdam. Implementation starts from repository `963f6ac`; Infra's
initial deployed archive is `ee1c217`. This is a focused backup investigation,
not a new fleet baseline.

## Initial observations

- Proton timer disabled/inactive with no last trigger; no successful-generation
  markers or encrypted login session. No `Backups/dothomelab` directory after
  authentication. The service's default `Result=success` had no run timestamp
  and was not evidence of a successful backup.
- User completed Proton browser login; the CLI exited 0, saved one encrypted
  session, and successfully read `/my-files` through the official CLI.
- Proton UI reported 50.57 GB used of 1039.00 GB before backup upload.
- Infra and Mac both reported 21,140 files, 2,921,162,400 indexed bytes,
  zero needed files/bytes/deletions and zero pull errors. Mac's active Obsidian
  vault is `/Users/rafael/Obsidian/obsidian-cloud-retrieval`; the server path
  remains `/vault/shared/media/obsidian`.
- Folder `mdshx-oxig9` is Send & Receive with no versioning, shared with the Mac
  and Symphony VM101. Both peers were connected; this differs from July's
  Receive Only configuration. VM101 completion was not established here.
- Shared photos: 43,950 files, 231,834,301,417 logical bytes (204 GiB allocated).
  Immich's separate `upload/` had 866 files, 4,757,258,722 bytes; `library/`
  contained only its 13-byte marker. Existing Proton scope missed these
  direct-upload originals. The whole Immich upload tree was 32 GiB including
  regenerable content; only original subtrees are added to Proton.
- Backup UID 1000 could read every Immich original. No ownership changes made.

## Prepared implementation and verification

- Add the independent `Immich` original-file archive with a read-only mount.
- Preserve two dated generations; verify the replacement before retention can
  permanently remove an old one. Never sweep trash by matching filenames.
- Add source-matched sample extraction and remote sample-manifest verification.
  Complete notes and smaller sources before the large shared-photo job.
- Validate Compose quietly in the runner before every backup deployment.
- Isolated Linux tests use the existing pinned CLI image with no network or
  production mounts. Three cycles exercise four sources and two-generation
  retention; a deliberately corrupt download preserves the old photo backups;
  extracted Immich files match the originals and thumbnails are excluded.

The user explicitly approved dated archives, two verified generations with
oldest-generation removal only after replacement verification, and inclusion
of `/root/.env` for recovery. The Proton CLI and browser expose different
address aliases for the same Drive; matching root entries confirmed the
capacity observation applies to the authenticated Drive.

## Live rollout and first cycle

Implementation `9cc756e390e5d17e1886bd21a94ce854178f6748` is pushed to
`origin/codex/proton-backup-activation`, checked out on PVE, and recorded in
CT110 `/opt/dothomelab/DEPLOYED_COMMIT`. The new image is
`dothomelab/proton-drive-cli:0.6.0-backup-v2`, image ID
`sha256:de5dff6f37c4a676ca0a7a1b62b59e3195f433a04193e1eaa3f4eaf50be16868`.
The official CLI 0.6.0 download passed the pinned SHA-512 check. Compose
validated quietly, host units and the guest runner were installed, and no
Syncthing recreation or configuration change was performed.

Cycle `20261017T104109Z` began at **12:41 CEST**. Initial phase: Obsidian
archiving, with the expected temporary Syncthing pause. `tar`, `gzip`, and
`split` were running and Docker reported source reads. The notes archive subsequently completed at
2,448,401,168 bytes with its source-matched extraction test passing, and
Syncthing was confirmed running and unpaused before cloud upload. No real
dataset had finished cloud verification at this checkpoint. The large photo upload and
read-back remain pending; this report does not claim completed protection.

PVE transient unit `dothomelab-proton-first-run-20261017.service` waits for
`dothomelab-proton-backup.service` to succeed, then executes
`backup/proton/install.sh --enable`. The timer remains disabled until every
source has passed full remote part checks and its source-matched archive
extraction test. Failure skips timer activation. Once enabled it checks daily
at 03:30 Europe/Amsterdam (up to 20 minutes randomized delay); complete cycles
are due every 14 days, and an incomplete cycle is retried by the daily check.
The initial transient activation itself is not a persistent retry mechanism
across a host reboot; check its result before assuming scheduling is enabled.

Inspect progress without reading secrets:

```bash
systemctl show dothomelab-proton-backup.service -p ActiveState -p SubState -p Result
systemctl show dothomelab-proton-first-run-20261017.service -p ActiveState -p SubState -p Result
systemctl is-enabled dothomelab-proton-backup.timer
pct exec 110 -- docker compose -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml --profile proton run --rm proton-drive backup status
```

Rollback material is retained:

- PVE installed script, service, timer, and former checkout revision:
  `/root/proton-backup-rollback-20261017T1040Z`.
- CT110 pre-rollout archive: `/opt/dothomelab.previous` (`ee1c217`).
- Previously retained archive: `/opt/dothomelab.previous.pre-proton-20261017T1040Z`
  (`c2661dd`).
- CT110 runner: `/usr/local/sbin/dothomelab-proton-backup-runner.pre-proton-20261017T1040Z`.
- Previous helper image/tag remains present. No images or cloud archives were
  deleted during rollout.

A rollback restores code/scheduling after the current job is safely handled;
it does not remove uploaded generations or the newly authenticated session.
Do not rerun broad preparation over the changed Syncthing folder as a rollback.

## First-cycle failure and repair

At the user's follow-up, inspection established that the service had stopped
with exit 1 at **12:56:21 CEST**. It was not still transferring. Proton had all
four Obsidian generation files: the 2,448,401,168-byte archive fits in one
`part-00000`, plus the manifest, checksums, and restore sample. CLI events showed
upload and download completion; no other real dataset had started.

The retention validator incorrectly allowed only alphanumeric, `_`, and `-`
characters in node UIDs. Real Proton IDs include `~` and `=`. Thus verification
finished but listing validation failed before the success marker, even when no
old generation needed deletion. The original filename-as-UID mock missed this.
The repair accepts the official CLI's long padded and short node-ID forms, and
the mock now emits realistic opaque UIDs. It also corrects permanent deletion:
trash paths resolve by name, so deletion must first verify that exactly one
trash item has that name and its UID matches the selected backup.

Identifier tests reject malformed IDs and ambiguous/wrong-UID trash names.
The isolated three-cycle, four-source test still passes, including corrupted
remote-download refusal and retention of two generations. The runner now saves
root-only per-cycle logs in canonical appdata and reports their location on
failure through the host journal. The helper image tag advances to `backup-v3`.

Live validation passed at **14:54:58 CEST** against CLI 0.6.0 and the actual
Drive: three tiny synthetic photo generations under
`Backups/dothomelab/Verification-20261017T130000Z` each uploaded and downloaded
with matching checksums; the third triggered permanent deletion of only the
oldest fixture. Exactly two remained, and the newest downloaded again through
the restore command. This test used isolated state/work/source paths and did
not mark production datasets successful or delete any production backup. The
two final fixtures remain available.

Repair `1d659c0a077987552d8f87aaa4d000ecab12b0ec` is pushed, checked out on
PVE, and recorded in CT110 `DEPLOYED_COMMIT`. Image
`dothomelab/proton-drive-cli:0.6.0-backup-v3` is
`sha256:8dcd79001372e1fd75e1818fee1185eda3a042adb6719a9f9e831e459b4b0017`.
Compose validated quietly before the build. The installed runner/wrapper match
the new commit. The saved cycle resumed at **14:56:12 CEST**; the transient
first-run gate was recreated after clearing its failed state unloaded it.
The scheduling condition remains full four-source verification.

Additional rollback copies: PVE `/root/proton-backup-rollback-20261017T1258Z`,
CT110 runner suffix `.pre-proton-uidfix-20261017T1258Z`, and pre-activation
archive `/opt/dothomelab.previous.pre-proton-uidfix-20261017T1258Z`.
`/opt/dothomelab.previous` now holds the initial `9cc756e` deployment. Both
older archive copies and helper images remain. The new cycle log was checked
to be mode 0600; no production data or rollback copy was removed.

The first repaired retry entered the CLI's existing-file conflict path and
then showed no advancing transfer bytes (15.5 MB sent; negligible CPU) across
repeated observations. Only that on-demand container was stopped; Syncthing
remained unpaused and the staged source archive was preserved. This does not
establish the underlying CLI defect. A second repair verifies an existing
remote generation against the saved local checksums before attempting another
upload. A matching copy proceeds directly to retention/success bookkeeping.
Per-part download verification now emits progress lines.

This retry path passed the isolated four-source tests, including an assertion
that a failed download verification followed by retry uploads the generation
only once. A live repeat of the final synthetic generation passed at
**15:02:54 CEST**, recording success after full download verification without
another upload. The helper tag advances to `backup-v4`.

## Limits and rollback

No shared data was deleted or permissions changed. Server sync mode and file
versioning were preserved. Mobile sync and Immich client upload were not tested.
Archive recovery covers files, not an independently restored Immich database.
A full photo restore over live storage is not part of this task. Existing
uncommitted work in the main checkout is untouched; implementation is isolated
in the attached worktree.
