# Proton pre-upload source verification — 2026-10-17

Environment: operator Mac, PVE `afa`, CT110 Infra; Europe/Amsterdam.
Implementation: `6206c88458ec80ea558b60ca7a3cd09ddeecf9e3`, pushed on
`codex/proton-source-verification`. It includes the live `ef8bc7f` baseline
and the earlier Proton work; unrelated main-checkout edits were preserved.

## Change

Photos and Immich originals now get an independent SHA-256 inventory before
archive creation. Every archived path, type, size, and regular-file payload is
compared with that inventory before any upload. Repeated or unexpected paths,
missing files, bad hardlinks, incomplete parts, and content mismatches fail.
Source identity/mtime/ctime/size and directory metadata are checked across the
hash/archive window. Nested filesystems, symlinks and special files fail instead
of being silently omitted. This is a guarded live-source read, not a ZFS snapshot.

`SOURCE-FILES.jsonl` and `SOURCE-VERIFIED.json` travel with each photo/original
backup. The receipt binds the source inventory to the part-checksum list; the
upload path rechecks part bytes and that binding. Retained older stages must
pass a complete comparison against current originals before reuse. Existing
remote per-part read-back remains automatic. Retention still runs only after
remote verification. No manual user download is required.

## Validation

- Fifteen Python tests passed on macOS and PVE/Linux, including same-size wrong
  contents, omitted/repeated files, repeated chunks, source changes, truncated
  archives, hidden concatenated archives, hardlinks, and unusual filenames.
- Three complete mock cycles passed on Linux. Invalid source evidence blocked
  upload before any Proton operation. Legacy staged archives were upgraded only
  after full comparison. Corrupt remote bytes prevented retention; successful
  retries reused the remote generation; restored Immich fixture bytes matched.
- Bash syntax, Git whitespace checks, and documentation checks passed.
- Both fixture suites passed inside the final image as UID 1000 with no
  network, a read-only root, and isolated temporary data. Installed checker and
  runner bytes matched the committed sources. The unchanged CLI binary matched
  its pinned SHA-512. A direct CLI version probe without its configured secret
  backend failed; it was not used as a runtime acceptance claim.
- Production Compose validation passed quietly before/after deployment.
  CT110's archive was installed at **19:46:59 CEST** with `DEPLOYED_COMMIT`
  `6206c88458ec80ea558b60ca7a3cd09ddeecf9e3`. Compose selects
  `dothomelab/proton-drive-cli:0.6.0-backup-v5`, image
  `sha256:90ccb8532ae6b5c9430616b7338532c62de80df69f9ca585910631e99ad4d706`.
- Docker's temporary build network had a Debian DNS failure. The final
  reproducible two-stage Dockerfile reused independently cached runtime and
  checksum-verified CLI layers; its final normal Compose build passed. No DNS
  settings were changed. Only superseded build-download processes were stopped.

The separate earlier full-content audit of the current production photo archive
finished at **19:26:12 CEST** with tar/reader exit codes zero, no diagnostic bytes,
and unchanged source/archive metadata. It covered **43,950 files** and
**231,834,301,417 source bytes**. Its private result is
`/srv/appdata/docker/proton-drive/audits/photos-20261017T104109Z-content.json`.
This was the existing one-time audit, not a new generation produced by this
release. The current upload continues in the v4 process; v5 applies to later
staging/retries. Complete photo cloud read-back remains outside this result.

## Rollback and limits

The previous live `ef8bc7f` archive remains at `/opt/dothomelab.previous`;
the older previous archive was retained at
`/opt/dothomelab.previous.pre-source-verification-6206c88`. The v4 image remains
installed, including its unchanged active uploader. Rollback means selecting the
previous committed Compose/helper release for future runs; no data migration
needs reversal. No rollback archive, image, or production generation was deleted.
The PVE release checkout is `/root/proton-source-release-6206c88`; the shared PVE
checkout used by other tasks was left unchanged.

No new production backup, guest restart, source-data mutation, ownership change,
or credential change was performed. The checker proves the configured photo
and Immich-original trees; other locations and Immich database/album recovery
remain separate. Future source churn or unsupported file types can deliberately
fail staging. Existing generations without source inventories retain their older
verification level; they remain restorable. The new production-scale pre-hash
path has not yet run because the current upload predates deployment.
