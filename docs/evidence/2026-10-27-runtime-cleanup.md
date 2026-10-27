# Runtime cleanup and Production dashboard — 2026-10-27

Rafael requested cleanup of the old tests/restores and retired staging/production
services, monitoring/dashboard enrollment, a separate Production board for the
blog, a storage explanation, and agent rules that prevent recurrence. The exact
cleanup and retained material were explained before mutation. The intervening
[shared observability move](2026-10-27-shared-observability-infra.md) was preserved.

## Delivered

- Removed 23 explicitly inspected, stopped containers: 16 restore-test containers
  and five retired observability containers on CT112, plus the obsolete Blackbox
  container on each of CT114 and CT115. Every Docker guest now has only running
  containers: Servarr 21, Infra 19, Apps 42, Staging 7, Production 2.
- Kept the five active staging applications, public blog, each environment's
  necessary Alloy collector, live `immich_migration_*` services and DroppedNeedle.
  No application release, branch promotion, volume/image prune or data deletion
  was performed. Existing images, mounted data and running container IDs were
  checked before and after cleanup.
- Pruned unused default-builder cache under the staging/production deployment
  locks, with an explicit 5 GB reservation/target. Successive passes reported
  188.073 GB reclaimed on CT114 and 9.234 GB on CT115. Final private cache was
  4.963 GB and 4.645 GB; including image-shared cache, totals were 9.192 GB and
  10.78 GB. All 152 staging and four production images remain. ZFS reported
  about 129 GiB available on the shared SSD pool afterward,
  versus about 57.3 GiB in the preflight. These measurements are not additive;
  Docker logical accounting and ZFS physical allocation differ.
- Created the private [Production board](https://rafael.media/boards/Production)
  with the public Blog tile, its own working favicon, origin health ping, and desktop,
  compact and mobile layouts. Existing boards, rows, home defaults and permissions
  were preserved. Grafana/Umami already had six correct tiles after consolidation;
  their destinations remain `grafana.rafael.media` and `analytics.rafael.media`.
- Fixed recurring Staging dashboard drift: Homarr migrates the obsolete
  `openInNewTab` option to `openIn: newTab` on startup, while the old sync wrote
  the obsolete field back. All managed templates now use the current option;
  the PVE timer's installed release was updated and checked after Homarr restarted.
- Updated [AGENTS](../../AGENTS.md), the [cleanup/enrollment workflow](../operations.md),
  host runbooks and [storage explanation](../../USER_DOC.md#understand-pulses-storage-display).
  Six application restore-test scripts now remove successful stopped test
  containers while retaining data/evidence; failed tests retain and report their
  stopped containers for diagnosis. Future retained artifacts need an owner,
  reason, recovery path and removal condition. No automatic deletion timer was added.

## Verification

Checks beginning at 11:07 UTC, with final follow-ups after cleanup and schema fixes:

- Pulse's authenticated verifier passed for all five Docker agents and all six
  LXCs. The paginated API contained exactly the 91 current containers and none of
  the 23 removed entries; both VMs remain in PVE inventory. Historical telemetry
  was not deleted.
- All five Compose staging applications passed exact accepted-commit, HTTP and
  applicable SQLite checks. Blog remains at `1de2b14aadbf2fa9571a7e2dc498f4c1376f6e82`.
- All 34 shared endpoint probes passed, no scrape was down, all 13 alert rules
  evaluated successfully, and 100 resources had fresh fleet measurements.
  Grafana dashboards/filters and both datasources passed. Umami authenticated
  reads worked; a unique staging 404 arrived in Loki with its query stripped.
- Staging Homarr reconciliation ended with `changed=false`, six apps. One check
  encountered the normal synchronization job's lock and was retried after it
  finished. Intermittent option drift was traced to the schema migration and fixed.
  Before the compatibility fix, all pre-change rows in the seven dashboard tables
  remained present; the final option change preserves their equivalent behavior.
  Home defaults, database integrity and foreign-key checks passed.
- Authenticated browser verification displayed the Production board, Blog link,
  working favicon and green ping. It also confirmed the existing Grafana/Umami
  links. The initial nonexistent CDN icon was replaced with the site's declared
  `/favicon.svg` before completion.
- The public blog URL sometimes returned a Cloudflare 403 to non-browser checks.
  The Homarr tile now checks `http://192.168.0.115:8084` while still opening
  `https://rafael.ink`; separate public HTTPS probes remain active and passing.
- Quiet Infra Compose validation passed. Three focused cleanup tests, two
  Production-board tests, nine Staging-board tests (including the observed Homarr
  migration), the affected shell syntax checks, documentation checks
  and whitespace checks passed. The SQL was also applied twice to a memory-only
  copy of the real Homarr database before live changes, preserving original rows.
  No full database restore test was rerun for this cleanup.

The first cleanup safely stopped after three removals because Docker reordered
the same mount list. The comparison now ignores ordering while still checking
every mount field; regression coverage rejects changed paths, destinations,
permissions and missing mounts. The remaining targets then completed normally.

## Storage interpretation

Pulse v6.6.0 grouped SSD appdata and HDD shared-tree mounts for Apps, Infra and
Servarr, but displayed only the root for Staging and Production. Staging actually
has narrow HDD photo/archive mounts; their omission is an agent reporting limit.
Production intentionally has only SSD root/appdata. No mounts or quotas were
broadened. ZFS quotas are ceilings, not reservations, and shared pool capacity
must not be summed across guests. Pulse's Docker agents also reported physical
host RAM rather than each LXC's configured limit; use PVE/Grafana guest readings.

## Retained material and rollback limits

The homelab operator owns the following retained recovery material. Remove it only
in an explicitly authorized retention task after selecting and verifying the
replacement recovery point and confirming no live consumer still needs it:

| Material | Reason and recovery path |
|---|---|
| Restore-test appdata, anonymous database volumes and private networks | Keep test evidence and restored data; original mounts/volume IDs are in the protected container metadata below. |
| Original observability appdata and `/srv/appdata/docker/observability/rollback-20261027T085235Z` | Preserve pre-consolidation data/history. Follow the shared-observability rollback runbook; do not start an old database against new live data. |
| Current/previous release metadata, release directories and all image IDs | Preserve accepted application rollback choices. Select a matching retained release through the owning deployment workflow; this task did not test rollback. |
| Guest source archives, including `/opt/dothomelab.before-shared-observability-adda1fbfcdb8be340091a9a358dfa68bcfc585b0` | Retain old Compose/configuration and absent read-only mount sources. Recreate a retired container only from the matching source, image and data after checking conflicts. |
| Homarr SQLite backups `db.sqlite.pre-managed-20261027T111006.2944717` and subsequent timestamped backups under `/srv/appdata/docker/homarr` | The first precedes the new board; later copies precede its corrections. Restore only with Homarr stopped and after preserving/comparing intervening dashboard edits. |

Credential-bearing container inspection records remain mode 0600 in canonical
appdata; their checksums and retained mount/image inputs were verified. They must
not be copied into Git, logs or chat:

- CT112: `/srv/appdata/docker/runtime-cleanup/20261027T110731Z-3931225/`
  and `/srv/appdata/docker/runtime-cleanup/20261027T110918Z-3935649/`.
- CT114: `/srv/appdata/docker/staging/runtime-cleanup/20261027T110922Z-719369/`.
- CT115: `/srv/appdata/docker/production/runtime-cleanup/20261027T111014Z-143720/`.

Additional cache-only results are retained in CT114's same directory under
`20261027T111902Z-726073`, `20261027T112009Z-726879` and
`20261027T112123Z-727816`, and CT115's under `20261027T111922Z-144769`.
Their container lists are empty because no further containers were removed.

Removed writable container layers and build cache are not recoverable from those
records. Durable state was mounted and preserved; cache is regenerated by builds.
Routine scheduled backup policy remains unchanged.

The existing Immich machine-learning Docker list/inspect state conflict remains;
the shared exporter marks it unknown. Existing Homarr calendar/download-client
integration widgets also displayed errors; synchronized tiles do not establish
that those integrations work. Notification delivery and independent WAN checks
remain outside this acceptance.

Implementation was committed and pushed on `codex/blog-production-activation`:
`6caff897` adds cleanup, test lifecycle and Production enrollment; `f35bedc9`
fixes mount ordering; `65ea54e0` sets the cache reservation; `ee4e886a` completes
the icon/origin check; `ec5538dd` prevents Homarr option drift. CT110 and the PVE
Staging sync use `ec5538dd`; CT112 uses `f35bedc9`, CT114/115 use `65ea54e0`.
The canonical local checkout retains the
review branch. No temporary worktree was created; unrelated documentation drafts
were left untouched.
