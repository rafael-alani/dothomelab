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

## Reverification October 27, 2026

Read-only status/cloud verification from the operator Mac through PVE and
CT110, starting **08:53 CET**. CT110 `DEPLOYED_COMMIT` was
`68cba604cac0f75b4dcf062dfaabaacbf4dfcedc`. No backup was started and no
production configuration, source data, retention state, or cloud object changed.

The latest completed cycle remains **20261017T104109Z**, completed
**October 18 at 05:53:49 CEST**. All four source markers agree; there is no
`current-cycle`. The service's most recent daily due-check exited zero and the
timer is enabled/active. Daily logs October 20–27 show successful not-due exits,
not upload failures. The next due-check is October 28 at 03:48:43 CET. The next
full backup becomes eligible **November 1 at 04:53:49 CET**; because daily
checks run at 03:30 with up to 20 minutes jitter, the expected first eligible
scheduled run is **November 2, 03:30–03:50 CET**, assuming normal uptime.

Fresh Proton authentication and listings succeeded. For every saved generation,
`MANIFEST`, `SHA256SUMS`, and `RESTORE-SAMPLE` downloaded successfully. The
SHA-256 of each downloaded checksum list matched its saved success digest.
Every expected archive-part name was present exactly once, with all three
metadata filenames present. Proton's listed plaintext archive-byte totals were:

| Source | Parts | Archive bytes |
|---|---:|---:|
| Obsidian | 1 | 2,448,401,168 |
| Environment | 1 | 4,363 |
| Immich originals | 2 | 4,759,961,600 |
| Shared photos | 54 | 231,878,379,520 |

Fresh payload checks also passed for the complete environment archive and
Immich `archive.tar.part-00001`: each downloaded SHA-256 matched its expected
entry. Temporary downloads stayed in the private ephemeral container and were
removed when it exited; credential contents were never printed. The photo
232 GB payload and Obsidian payload were **not downloaded again today**. Their
full remote read-back remains the October 18 evidence, not a new byte-level
verification claim. Listing sizes are remote metadata, not fresh content hashes.

Current source inventory: shared photos still contains **43,950 regular files**
and **231,834,301,417 bytes**, with no symlinks; Immich originals contains 867
files and 4,757,258,735 bytes. These totals do not prove every current byte is
unchanged. The prior full photo-content audit result remains `passed`, completed
October 17 at 19:26:12 CEST with unchanged source/archive metadata and no
diagnostics. The live notes folder has 21,763 filesystem files; Syncthing
reports 21,762 local/global indexed files, idle, zero needed files/bytes and
zero pull errors. This is current sync, not proof that later notes are in the
October cloud generation.

**Deployment regression:** current CT110 Compose selects
`dothomelab/proton-drive-cli:0.6.0-backup-v4`, image
`sha256:41a52ad555e8e20350df88a9c0b233b3ec5fb54226a6382ac0d79e2d93cfe9a4`.
The current deployed helper lacks the v5 source-verification code. The v5 image
`sha256:90ccb8532ae6b5c9430616b7338532c62de80df69f9ca585910631e99ad4d706`
still exists, and the implementation remains retrievable at
`origin/codex/proton-source-verification` (`39bd6ee`). Its rollout evidence
records deployment October 17 at `6206c88`; a later repository deployment has
reverted the selected configuration. The existing cloud copy passed the checks
above, but future automatic full-library source verification needs restoration.
This verification request does not deploy that repair.

The earlier follow-up evidence and manual audit helper remain published at
`origin/codex/proton-backup-activation` (`f2d366e`). Consolidating that task's
worktree `/Users/rafael/.codex/worktrees/proton-backup-activation/dothomelab`
is deferred: the canonical checkout is actively changing in another task,
including unrelated edits to `docs/status.md` and the evidence index, untracked
blog reports, and a branch advance during this check. No other worktree or
branch was removed, and no unrelated changes were staged by this verification.
