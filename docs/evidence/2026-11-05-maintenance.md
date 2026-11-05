# Homelab maintenance — 2026-11-05

Rafael requested all managed software updates after the successful
backup verification, including the Linux TCP vulnerability disclosed by
Anthropic. He explicitly authorized the PVE reboot and unused Staging/Production
build-cache cleanup. VM101 remains stopped and outside this maintenance scope.

The managed OS/application maintenance and approved reboot are complete. The
explicit remaining exceptions and recovery blockers are listed below; this is
not a claim that every app workflow or clean-host restoration was exercised.

## OS and kernel

PVE and all six managed LXCs completed their APT upgrades successfully, without
removing application data or changing guest ownership. The package plans covered
829 upgrades, plus new dependencies. PVE manager is 9.2.25; PBS is 4.2.9-1.
Docker is 29.9.3 and Compose 5.7.0 on all five Docker hosts. Postboot APT checks
found zero available upgrades on PVE and all six guests.

The running PVE kernel is **7.0.14-28-pve** after the approved reboot.
Proxmox's fix for **CVE-2026-98432**
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
  now 18.6, with VectorChord 1.1.1 and pgvector 0.8.7 after the migrations below.
- Homarr and Stirling-PDF WUD replacements passed their health checks.
  Stirling's download outlasted the runner's 15-minute request timeout but
  completed server-side. Trigger calls now allow one hour; 16 runner tests pass.
- n8n 2.46.6 is healthy. Before migration, a stopped-state copy verified all
  five workflows, one credential, two executions and one user. Private rollback
  state is `/srv/appdata/docker/n8n-backups/20261105-maintenance`. Stable
  version-2 tags replace `latest` for WUD; beta and major upgrades are excluded.
- Home Assistant: Mosquitto 7.1.3 and ICS Calendar 5.2.1 installed. BLE Monitor's
  supported update service eventually completed at 14.4.0 after the calling
  HTTP request timed out; live update state reports complete. Spotify is now
  0.19.0; Core 2026.11.0, OS 18.4, File Editor 6.3.0 and Music Assistant 2.10.9
  also completed. After reboot, no HA update entity reports an available update.

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
`immich_pg18_test_20261105t183928z` was removed after resolving its new-parent
traversal failure; its diagnostic directory `immich/postgres18-rehearsal-20261105` remains;
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

## Cleanup and retained rollback

Approved default-builder cache cleanup reclaimed 16.69 GB on Staging and 3.5 GB
on Production. The helper verified running container IDs, retained images and
mounted data. Metadata remains at:

- `/srv/appdata/docker/staging/runtime-cleanup/20261105T180304Z-2577302`
- `/srv/appdata/docker/production/runtime-cleanup/20261105T180314Z-202587`

The final WUD discovery result is recorded below. Readarr is retired; its
configuration and library data remain. DroppedNeedle remains unchanged under
the existing acceptance requirement.

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
accepts the updates. Rollback after new writes needs reconciliation.

The upstream Immich image bundles pgvector 0.8.5, while [pgvector 0.8.7](https://github.com/pgvector/pgvector/blob/v0.8.7/CHANGELOG.md)
fixes an IVFFlat buffer overflow. Git now declares exact PGDG package
`postgresql-18-pgvector=0.8.7-1.pgdg12+1`; its build and live extension migration
passed. The original PG18 migration evidence above remains the
history of the first cutover.

## Final application cohorts

- Immich's pgvector security patch is live. An in-place test on the prior
  isolated PostgreSQL 18 restoration preserved all 73 table counts and valid
  indexes. Fresh production checkpoint `immich/backups/20261105T194008Z-pre-vector-security`
  and stopped copy `immich/postgres18-before-vector-security-20261105` preceded
  cutover. All 73 live counts matched, followed by full focused verification.
  Current image: `sha256:9e862814dcdb41ec174ba77a188ca889383083457d1863b4cd4c7b5455862996`.
  The original failed rehearsal container was removed after the issue was
  resolved; its data remains. Cleanup metadata is
  `runtime-cleanup/20261105T200215Z-2356103` on Apps.
- Aurral 2.13.0 passed an isolated migration and six durable table comparisons,
  preserving one user, three artist overrides, one playlist job and one request
  history entry. Derived caches changed as expected. Live UID/capability,
  read-only permanent music, shared slskd, private HTTPS and history checks pass.
  Docker now reports capabilities with `CAP_` prefixes; the verifier normalizes
  that representation. Rollback is `aurral/rollback-maintenance-20261105`;
  retained isolated data is `aurral/rehearsal-20261105` and
  `aurral/rehearsal-flows-20261105`. Generated-flow acceptance remains separate;
  DroppedNeedle stays unchanged.
- Beets 2.14.1 updated under both worker and Soularr locks. Its isolated database
  migration preserved item/album counts and SQLite integrity; the live verifier
  passed the existing Lidarr writer policy and read/write boundaries. Rollback:
  `music-metadata-rollback-20261105`; rehearsal data:
  `music-metadata-rehearsal-20261105`. No library retag/reconcile was requested.
- Bar Assistant API 6.10.1, Salt Rim 5.9.0, Meilisearch 1.50.0 and Redis 8.10.3
  passed an isolated upgrade and the final live cutover. Portable full export,
  stopped app/cache copies and logical search dumps are under
  `bar-assistant/rollback-maintenance-20261105`. Both migrations preserved one
  user/bar/membership, 613 cocktails, 286 ingredients, 2,740 ingredient relations,
  890 images, one collection and four bar ingredients; SQLite integrity passed.
  Search dump import preserved both document counts and all API keys. Current
  search state is `bar-assistant/meilisearch-1.50`; the old `meilisearch` directory
  remains. Isolated state is `bar-assistant/rehearsal-20261105`. Test containers
  and networks were removed. Frontend, API, search, Redis and private HTTPS pass.
- Apps Portainer/agent now match the other hosts at 2.45.3. The server database
  was copied while stopped and hash-verified. Rollback:
  `portainer-rollback-maintenance-20261105`. Its API and agent ping pass.
  Mealie was already current at 3.30.0; the recovery declaration now matches.
- Gluetun updated to the October 29 build `ed7af79`, pinned by digest. The first
  DNS/health attempt failed and recovered; all four download clients/indexers
  then passed the shared namespace, VPN interface, port and endpoint checks.
  Private stopped rollback copies are `vpn-rollback-maintenance-20261105`.
  Prowlarr's host-owned operations directory was copied from PVE after guest-root
  access was denied; no ownership was changed. The cross-seed proxy was also
  recreated against the new VPN namespace and current Python 3.13.18. Its
  deterministic definitions were refreshed from the upgraded bundled catalog;
  full cross-seed verification passed at 6.13.9. An unused Portainer agent's
  documented no-client timeout explains its closed HTTP listener before reboot.
- Storyteller's reconciler now uses pinned Python 3.13.18. Nine tests passed;
  the live update acquired and released its interlock and passed health checks.
  Automatic approval initially rejected an unpaired lock acquisition; the
  completed operation paired the lock with bounded exit cleanup and verified
  no marker remained. No Storyteller media/database migration was performed.
- Cloudflared 2026.10.7 and Speaches' current CPU manifest already match upstream.

Fresh WUD discovery now sees 47 watched containers: 46 active/trigger-associated
and retained DroppedNeedle skipped. Readarr has disappeared. No eligible update
remains, but n8n tag discovery is still rate-limited by Docker Hub (429); manual
installation and private HTTPS verification confirm current stable 2.46.6.
The installed CT110 runner now has the one-hour trigger timeout.

## Reboot and final acceptance

PVE reboot began at 21:04 CET and orderly guest startup finished at 21:13.
All six LXCs and VM104 returned automatically; VM101 remains off. Pools are
healthy. Seerr briefly reported unhealthy during startup and recovered unaided.
PBS's newly installed ZFS dependencies tried to manage pools inside the LXC;
the guarded installer now masks its mount/share/event services when running in
LXC without `/dev/zfs`. Both PBS services are active and its failed units cleared.

Home Assistant booted OS 18.4 / kernel 6.18.58-haos from slot A, retaining 18.1
in slot B. The [official OS release notes](https://github.com/home-assistant/operating-system/releases/tag/18.5.rc1)
confirm non-Raspberry-Pi platforms already received CVE-2026-98432's fix in
18.4; 18.5.rc1 is a Pi/Yellow-specific prerelease. Full HA verification passed:
Core configuration, Govee physical inventory/segments/catalogs, saved scenes,
LAN and HTTPS and recovery artifacts. The verifier's old blanket rejection of
`Fireplace` was stale: the lamp now advertises it. Verification checks the live
catalog through the established app API scope; the user's scenes were preserved.
This does not repeat physical visual light-effect acceptance.

The post-upgrade VMA is
`home-assistant/vm/vzdump-qemu-104-2026_11_05-21_20_55.vma.zst` (4.76 GB).
Snapshot backup, full zstd/VMA verification and SHA256 sidecar completed at
21:23 CET. The earlier VMA and protected native backup remain. This verifies
archive integrity, not a destructive VM restore.
The installed `/usr/local/sbin/dothomelab-haos-backup` now byte-matches the
corrected source and passes `--check`. Its prior installed copy is retained at
`/root/dothomelab-maintenance-20261105/haos-backup-installed-before-final-sync.sh`.

Postboot Listenarr authentication/configuration, SQLite integrity and audiobook
integration checks passed. Cleanuparr runtime and API policy checks passed.
Pulse covers all six guests and five Docker agents. Staging Homarr reports no
drift across six apps; Homarr contains zero Readarr apps or integrations.
The full live media-contract verifier passed without write probes, including
canonical ownership/access, narrow consumer mounts and both free-space floors.
Immich's postboot focused checks again matched 27,583 assets, required extension
versions and ten readable sampled originals; n8n's private HTTPS/state checks
also passed.

Loki exposed a capacity issue: above 90% filesystem usage, its WAL refuses
writes with the misleading message `Ingester is shutting down`. At 20:23:50 UTC,
after clearing APT download archives and the remaining approved build cache,
it reported 89.77% and resumed writes. No threshold was weakened. Final
Staging/Production build cache is zero; all images and mounted data were
verified retained. Additional cleanup receipts are
`staging/runtime-cleanup/20261105T202321Z-7400` and
`production/runtime-cleanup/20261105T202339Z-920`.

After Alloy's retry backoff, a new unique HTTPS404 reached Loki with the query
removed and only the permitted fields. Grafana datasource/fleet checks, five
endpoint probes, seven scrapes and five alert rules passed again. One queued
Staging log entry was dropped during the capacity incident; this is not a claim
of uninterrupted log history. No unhealthy Docker containers or failed PVE
units remained. Notification delivery and external-WAN/browser analytics were
not revalidated.

Rafael then explicitly approved removal of the 27 reviewed obsolete staging
blog Docker images. The task removed exactly those IDs under the deployment
and native-build locks, verifying every other image, all running container IDs
and current/previous native HTML hashes afterward. The two newest legacy Docker
images and all source/data remain. Staging image storage fell from 107.9 GB to
17.53 GB; appdata available space increased to **129 GiB**, above the 64 GiB
recovery floor. Private plan/receipt:
`staging/runtime-cleanup/retired-blog-image-plan-20261105.json` and
`staging/runtime-cleanup/retired-blog-images-removed-20261105.json`.

Two unused anonymous volumes created during the database rehearsals also remain
on Apps: `003dadddbd703a9498f89fbdf1d5f06d514ceb1c731ec389205e9cf6df0e6567`
(19:07:16 UTC) and
`03875f5148c7c4e01349f29d6b45081c11f426215fc2b9855f9f860971713241`
(19:31:20 UTC). Homelab maintenance owns this diagnostic retention; volume
deletion was not authorized. Remove only after identifying their mounted role,
accepting the corresponding migrations and receiving explicit cleanup approval.

## Reproducibility and update limits

The fresh actual `bootstrap.sh --dry-run` still fails because it unconditionally
requires `PAPERLESS_GPT_OPENAI_API_KEY`, although GPT is absent. No dummy key or
external document-processing service was introduced. Full disaster recovery is
therefore not proven; this remains a bootstrap policy/secret prerequisite gap.
Contentflow is a live `contentflow:local` container on **CT110 Infra**, outside
the declared Git inventory; its image/build/recovery contract is unestablished.
It was not rebuilt from an unrelated application repository. The README now
explicitly clones the maintenance branch, since default `main` predates these
migrations. Clean bootstrap still depends on external registries/package
repositories and has not been tested on a destroyed/rebuilt host.

OS package installation remains operator-managed. WUD remains tied to successful
scheduled backups, with no separate timer; database/Immich/VPN/bespoke updates
remain manual. Docker Hub's n8n 429 is an unresolved discovery limitation even
though the live application is current. DroppedNeedle remains the deliberate
legacy exception pending generated Aurral-flow acceptance. Staging follows its
review branches; production application-code releases remain manual.

The approved image cleanup restored the free-space floor, but 129 GiB is still
insufficient for a second complete 396 GiB appdata copy on the SSD.
Appdata PBS is on the same physical
host and excludes shared media. Verified scoped Proton copies do not cover all
shared data. These limits prevent a claim of complete disaster recovery.
The protected November 5 PBS snapshot predates these migrations. New logical
checkpoints and the updated HA VMA are currently canonical local appdata and
will enter the next scheduled appdata backup; no second full PBS job was
started. Restoring the older snapshot requires its compatible pre-maintenance
application/database configuration and retained images, not blindly applying
the new PostgreSQL 18 baseline to PostgreSQL 14 data.
All retained rollback/checkpoint/test data in this report is owned by homelab
maintenance and remains until Rafael accepts the corresponding upgrades and
explicitly authorizes removal. Apart from the 27 explicitly approved retired
blog images, rollback images and all volumes were retained.
