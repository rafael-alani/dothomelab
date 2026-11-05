# Homelab maintenance — 2026-11-05

In progress. Rafael requested all managed software updates after the successful
backup verification, including the Linux TCP vulnerability disclosed by
Anthropic. He explicitly authorized the PVE reboot and unused Staging/Production
build-cache cleanup. VM101 remains stopped and outside this maintenance scope.

## OS and kernel

PVE and all six managed LXCs completed their APT upgrades successfully, without
removing application data or changing guest ownership. The package plans covered
829 upgrades, plus new dependencies. PVE manager is 9.2.25; PBS is 4.2.9-1.
Docker was upgraded through the configured vendor repositories. Final package
and service verification is still pending.

The installed new PVE kernel is **7.0.14-28-pve**. The running kernel remains
6.17.4-1-pve until the authorized reboot. Proxmox's fix for **CVE-2026-98432**
starts at 7.0.14-25-pve; LXC guests share the host kernel. The old kernel and
initramfs remain on the EFI boot volume as a fallback. References:
[Anthropic disclosure](https://www.anthropic.com/research/discovering-vulnerabilities-with-claude),
[Proxmox security advisories](https://forum.proxmox.com/threads/proxmox-virtual-environment-security-advisories.149331/page-5).

PBS's unlicensed enterprise Deb822 source returned 401. The maintained installer
now disables that exact source before and after package installation; the
configured non-subscription source refreshes successfully. Two focused tests
passed. Host rollback metadata is private under
`/root/dothomelab-maintenance-20261105`; guest package lists/logs are under
`/root/maintenance-20261105` in each guest.

## Completed application changes

- Shared monitoring: Umami 3.4.1, Grafana 13.3.0, Prometheus 3.13.5 (current
  LTS patch), Loki 3.7.9 and all three Alloy collectors 1.21.3. Real candidate
  configuration validation passed. Grafana datasource health, fresh fleet data,
  five endpoint probes, seven scrapes, five rules and unique sanitized HTTPS404
  log ingestion passed. Immutable shared source is retained at
  `/opt/dothomelab-observability/releases/3520d6b2a1eaee6e9b391cceb1b4856fb05b1e50`
  on PVE and CT110; CT114/115 collectors use retained `0cd0bc4d...` source.
- WUD 9.7.0: healthy with mandatory authentication. Its generated operator
  credential stays in PVE dotenv; the derived root-only runner credential is
  provisioned by `initialize-auth.py`, including during bootstrap. Native
  pull-error and generated-MAC handling passed five runtime tests. Live scanning
  proved native LSCR auth still fails, so scoped anonymous-token compatibility
  remains alongside the cross-seed tag guard; four compatibility tests passed.
  Authenticated runner tests passed (16), plus two initializer tests.
- Immich server and ML **3.3.6**, Valkey **9.1.3**. Focused health checks passed:
  3 users, 27,583 assets, 34 albums, 5,343 memberships, 1,605 people, 44,638 faces,
  31 shared links and 10 tags; all ten sampled original paths were readable.
  The 863 offline and 1,040 deleted assets predate this update. PostgreSQL is
  now 18.6, with VectorChord 1.1.1 and pgvector 0.8.5 after the logical migration below.
- Homarr and Stirling-PDF WUD replacements passed their health checks.
  Stirling's download outlasted the runner's 15-minute request timeout but
  completed server-side. Trigger calls now allow one hour; 16 runner tests pass.
- n8n 2.46.6 is healthy. Before migration, a stopped-state copy verified all
  five workflows, one credential, two executions and one user. Private rollback
  state is `/srv/appdata/docker/n8n-backups/20261105-maintenance`. Stable
  version-2 tags replace `latest` for WUD; beta and major upgrades are excluded.
- Home Assistant: Mosquitto 7.1.3 and ICS Calendar 5.2.1 installed. BLE Monitor's
  supported update service eventually completed at 14.4.0 after the calling
  HTTP request timed out; live update state reports complete. Core and OS
  upgrades, remaining apps and full acceptance are pending. Spotify is now 0.19.0.

The retained WUD store is under
`/srv/appdata/docker/wud/rollback-maintenance-20261105`; monitoring's private
runtime metadata and stopped Grafana copy are under
`/srv/appdata/docker/observability/rollback-maintenance-20261105`.
Umami received a fresh logical dump before its update. No rollback data/images
were deleted. An incorrect remote-shell invocation briefly changed PVE's fleet
source link; the corresponding immutable source was installed, the collector's
unchanged source was checked against its previous revision, and collection
passed again.

## Backup and migration evidence

The [earlier protected PBS checkpoint](2026-11-05-manual-update-backup.md) passed
full server verification and actual selective Immich restoration. It is not a
claim of full-host disaster recovery.

Fresh pre-upgrade checkpoint:
`/srv/appdata/docker/immich/backups/20261105T181331Z-pre-3.3.6-upgrade`.
Its isolated restore matched all 67 table counts, nine original extension
versions and all 868 managed-original file hashes. Successful test container
`immich_restore_check_20261105t181613z` was removed; its data and receipt remain
under `immich/restore-tests/20261105t181613z` and the checkpoint directory.
Retain these until the new app/database combination is accepted.

Immich's newest official PostgreSQL/VectorChord image still contains PostgreSQL
18.4. The committed Dockerfile retains its pinned VectorChord 1.1.1/pgvector
0.8.5 bundle and installs PostgreSQL 18.6-1.pgdg12+2. The build succeeded as
`dothomelab/immich-postgres:18.6-vchord1.1.1-pgvector0.8.5`, image
`sha256:5a507693f27992ea469f1f0a278c198d718f5462af2c17106e5957a12f400d0b`.
An isolated restore helper verifies every table, original-file hashes, extensions
and indexes before any live cutover. Rehearsal and final quiesced restore both
passed all 73 tables and 27,583 assets. The live cutover passed health, checksum,
extension, application-count and ten original-path checks. The final checkpoint
is `immich/backups/20261105T184607Z-pre-pg18-cutover`; the new data parent is
`immich/postgres18-production`, with a private migration receipt. PVE's dotenv
path was updated; its previous copy and Compose are private under
`/root/dothomelab-maintenance-20261105/immich-pg18`.

The old `immich/postgres` data and image remain. Initial rehearsal
`immich_pg18_test_20261105t183928z` is stopped with its diagnostic directory
`immich/postgres18-rehearsal-20261105` after a new-parent traversal failure;
the corrected successful rehearsal data is `immich/postgres18-rehearsal-20261105b`.
The helper now distinguishes extension-owned internal objects from external
dependencies and makes only the newly created parent traversable. No existing
data ownership was changed. Retain this rollback/evidence until acceptance;
old-database rollback after new writes requires reconciliation.

Fresh HAOS full snapshot archive:
`/srv/appdata/docker/home-assistant/vm/vzdump-qemu-104-2026_11_05-19_07_58.vma.zst`
with SHA256 sidecar, compressed-stream test and VMA structural verification.
Created from Core 2026.7.4 / OS 18.1 / Supervisor 2026.10.5; 3.23 GB compressed.
The helper no longer passes `--notes-template` with `--dumpdir`, which current
PVE rejects without a storage parameter. Older VM recovery images remain.

## Cleanup and remaining work

Approved default-builder cache cleanup reclaimed 16.69 GB on Staging and 3.5 GB
on Production. The helper verified running container IDs, retained images and
mounted data. Metadata remains at:

- `/srv/appdata/docker/staging/runtime-cleanup/20261105T180304Z-2577302`
- `/srv/appdata/docker/production/runtime-cleanup/20261105T180314Z-202587`

WUD discovery is down from nine errors to two: n8n anonymous registry rate
limiting and Readarr's retired manifest. Docker can download the explicit stable
n8n 2.46.6 image and it is now installed; the fresh discovery check is pending.
Readarr is retired; its configuration and library data remain. DroppedNeedle remains unchanged
under the existing acceptance requirement.

Other manual cohorts, the PVE reboot, final health/monitoring checks and recovery
preflight reconciliation are still outstanding. This document does not assert
that the fleet is fully current or fully reproducible yet.

The initial dirty documentation was preserved in local recovery branch
`codex/recovery-before-maintenance-2026-11-05` at `bb7108b8...`.
Restore selected paths with `git restore --source=<that-branch> -- <path>` only
after comparing later work. Canonical delivery branch is
`codex/homelab-maintenance-2026-11-05`; no duplicate task worktree was created.

## Additional manual updates and retirement

Readarr was retired after Rafael chose retirement. The retained 52 MB app state
contains 196 book records, 60 authors, 28 file records, 22 history rows, 14
indexers, one download client and two root folders. The actual books remain in
shared storage. Its stopped configuration copy is
`/srv/appdata/docker/retired-readarr-20261105` (CT102 sees `/docker`). Cleanuparr
Readarr automation is disabled, Prowlarr application 3 removed, Homarr tile and
integrations removed, and NPM route 16 disabled. Private service configuration,
SQLite backups and container inspection remain in that rollback directory and
CT102 `runtime-cleanup/20261105T190313Z-3265917`. No book files or rollback image
were deleted. Bootstrap no longer enrolls Readarr.

Cleanuparr 2.10.12 passed API checks after removing the obsolete `encryptionKey`
field from its configurator. Its stopped rollback copy is
`cleanuparr-rollback-20261105` on canonical appdata. Listenarr canary 1.5.15 passed
an isolated, network-disabled migration and SQLite integrity/count comparison:
zero audiobooks/downloads, two clients, 19 indexers, one quality profile/root/user.
The live replacement is healthy. Retained rollback, final stopped configuration
and rehearsal receipt are `listenarr-rollback-20261105`; isolated test data is
`listenarr-rehearsal-20261105`. The test container was removed after success.
Sortarr's latest registry manifest resolves to its already-running image; no
replacement was necessary.

Application-local database patches passed real logical restores before cutover:

- PinePods: PostgreSQL 18.6 and Valkey 8.1.11; full application/integration verifier
  passed. Isolated data: `pinepods/restore-tests/20261105T190715Z`.
- Paperless: PostgreSQL 18.6 and Valkey 9.1.3; authenticated API, three users,
  zero documents and private HTTPS checks passed. Test data:
  `paperless/restore-tests/20261105T191000Z`.
- SnapOtter: PostgreSQL 17.11 and Redis 8.10.3; health, schema, one user and HTTPS
  checks passed. Test data: `snapotter/restore-tests/20261105T191317Z`.
- Jellystat: PostgreSQL 18.6; all 14 public table counts matched in an isolated
  restore, then the live health endpoint passed. Checkpoint and receipt:
  `jellystat/checkpoints/20261105T192012Z`.
- BookOrbit: PostgreSQL 18.6 and pgvector 0.8.7; users/libraries/books and all
  extensions matched the expected upgraded state. Read-only library and app
  health verifier passed. Test data: `bookorbit/restore-tests/20261105T193120Z`.
- Grimmory: MariaDB 11.8.9-r0-ls239; all table counts matched its isolated restore.
  A stopped 375-file original configuration copy was hash-verified before the
  live `mariadb-upgrade`; the app is healthy. The verifier's old assumption that
  WUD retains a tag string was corrected to compare actual image identities.
  Test data: `grimmory/restore-tests/20261105T193301Z`.

Each service above retains private evidence under its own
`rollback-maintenance-20261105` directory; successful test containers were
removed. Keep old images, dumps and database/configuration copies until Rafael
accepts the updates. Rollback after new writes needs reconciliation. HA Music
Assistant is now 2.10.9 and started; Core upgrade is running.

The upstream Immich image bundles pgvector 0.8.5, while [pgvector 0.8.7](https://github.com/pgvector/pgvector/blob/v0.8.7/CHANGELOG.md)
fixes an IVFFlat buffer overflow. Git now declares exact PGDG package
`postgresql-18-pgvector=0.8.7-1.pgdg12+1`; its build and live extension migration
are still in progress. The original PG18 migration evidence above remains the
history of the first cutover.
