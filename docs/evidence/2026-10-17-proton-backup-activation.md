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

Live rollout, the first real backup and timer activation will be recorded
below. Authentication alone is not protection.

## Limits and rollback

No shared data was deleted or permissions changed. Server sync mode and file
versioning were preserved. Mobile sync and Immich client upload were not tested.
Archive recovery covers files, not an independently restored Immich database.
A full photo restore over live storage is not part of this task. Existing
uncommitted work in the main checkout is untouched; implementation is isolated
in the attached worktree.
