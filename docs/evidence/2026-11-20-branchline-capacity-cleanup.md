# Branchline capacity, stopped-preview cleanup and reconnect persistence

Date: **2026-11-20**, private staging CT114 on PVE `afa`.
This follows the [initial preview acceptance](2026-11-20-branchline-previews.md).
Rafael authorized a 32 GiB ceiling, eleven running previews and deletion of a
preview and its database when explicitly stopped. Production was not changed.

## Delivered behavior

- Provisioning declares CT114 memory as 32768 MiB; the live cgroup ceiling is
  34359738368 bytes. Its six-CPU allocation is unchanged. Increasing memory
  required no guest or host restart.
- The paired web/native runner release is Branchline
  `6171b7978a8dea232380136f3d80102465036641`, published on `staging` and
  `codex/branchline-v1`. Infrastructure behavior is in `4c7ddf8`, published on
  `codex/branchline-staging` and `codex/branchline-capacity`; this evidence is a
  follow-up on those branches. VM116 received the matching accepted CLI.
- Operator bounds and default limits are one concurrent build and eleven
  running previews. The installed build recipe revision is unchanged, so
  the eleven existing requests retain their environment identities and SHAs.
- Closing a browser, signing out or disconnecting SSH leaves previews running.
  State was already durable; the release adds regression coverage, clearer UI
  text and recovery of interrupted explicit Stop operations.
- Stop removes the project's containers/network, byte-verifies a protected
  cold archive, then deletes its exact live directory (including MySQL and seed
  state), rebuildable outputs and its two application image tags. It does not
  prune shared images, named volumes or the global build cache. Failed cleanup
  retains an unhealthy record and slot for an explicit retry.

The [runbook](../../hosts/staging/branchline/README.md) owns operation and recovery
instructions. The preview list and graph live in canonical staging appdata,
independent of browser sessions and replaceable application releases.

## Stop and recovery acceptance

The test used a separate runner state directory, port 12090 and environment
`7fbd76a192-bd026e35`; it did not stop any of Rafael's eleven environments. It
materialized the accepted final-stack SHA, reused its accepted images and
initialized a new isolated MySQL database. This was a lifecycle test, not a new
source-build acceptance.

The real Compose stack reached healthy status. Before Stop, SQL recorded all
99 non-system table counts and the seed-marker hash. Stop removed its containers,
network, live directory and image tags. The 18,998,128-byte archive was extracted
into a separate private directory and opened with the exact pinned MySQL image,
no network, no published port and `lower_case_table_names=1`. All 99 table counts
and the seed-marker hash matched. The restore container and extracted test copy
were then removed; the verified archive and receipt remain protected.

Evidence on CT114 is under
`/srv/appdata/docker/staging/branchline/acceptance/lifecycle-20261120`:
`environment-id`, `before-stop.json`, `result.json` and `reconnect.json`.
The recovery archive and receipt are in `branchline/preview-recovery`, outside
the active preview tree. They contain scoped credentials and are not in Git.

Local checks passed: **61** Branchline backend/CLI tests, **3** preview browser
tests, **5** cleanup helper tests and **6** existing Labrador preparation tests.
The cleanup tests include archive extraction, unsafe targets/consumers, corrupt
or incomplete recovery copies and retries. Runner tests cover interrupted Stop,
retry after cleanup failure, and ready previews surviving runner/session changes.

## Capacity and reconnect observations

Before the change, a five-minute, 15-second-interval sample with three previews
measured 6.33–6.35 GiB for staging, about 4.93 GiB across the preview containers
and at least 31.12 GiB host memory available. All eight waiting previews had
already built; increasing slots did not trigger another build.

Active capacity was raised **3 → 5 → 8 → 11**, waiting for each group to become
ready. Every step retained the original eleven IDs/SHAs and stayed above 18 GiB
host available memory, with no OOM kills. No preview failed readiness.

A second five-minute sample ran from **11:10:15–11:15:15 CET**, including the
final startup. The final twelve samples, **11:12:30–11:15:15**, all had eleven
ready previews. Their measurements were:

| Measurement | Observed |
|---|---|
| Total staging memory, including cgroup cache/kernel accounting | 18.60–18.66 GiB; mean 18.63 GiB |
| Eleven preview containers combined, Docker working-memory measure | Mean 17.03 GiB; each stack averaged 1.44–1.70 GiB |
| Host memory available | 18.02–18.53 GiB |
| Staging CPU | Mean 0.64 cores; final-startup sample peak 4.20 cores |
| Whole-host CPU, including unrelated workloads | Mean 28.34% during the ready window |
| Shared SSD pool available | 87.27 GiB |
| Staging memory pressure / OOM kills | Zero sampled memory PSI averages and zero OOM events/kills |

Raw observations and the summary are retained in
`branchline/acceptance/capacity-20261120/samples-eleven.jsonl` and
`summary-eleven.json`; `ramp.jsonl` records the stepped activation. CPU samples
average intervals and do not establish instantaneous peaks. No synthetic load
or additional build ran during this measurement.

Two fresh HTTPS sessions authenticated with the existing token returned the same
eleven IDs, commits and URLs after the paired web/runner release. No token was
printed, exported to the operator machine or rotated.

With all eleven ready and no build/start/stop operations in progress, restarting
only the native preview runner preserved all eleven IDs, exact commits and URLs,
the one-build/eleven-running limits, and all 22 running container IDs. Every
preview's private HTTPS URL returned 200. The original three preview stacks were
not restarted by the release or capacity increase. The protected
`capacity-20261120/restart.json` records this acceptance.

## Monitoring, retention and rollback limits

The accepted Branchline deployment verifier and SQLite integrity check pass.
The private Homarr Staging board matches its seven-app registry. The native
runner and gateway systemd units are active. Shared fleet measurements include
fresh CT114 resources; no dedicated Branchline HTTPS probe is currently declared.
Native runner/Codex jobs do not have individual Pulse job monitors.

Pulse's live verifier passed after all eleven stacks were ready: PVE inventories
the guests and its CT114 agent reports the running application containers.
All 35 existing shared endpoint probes passed, with fleet collection under a
minute old. Preview readiness and the eleven HTTPS checks were checked directly;
they are not an ongoing alert notification service.

Staging's Docker build cache was 7.15 GB (2.005 GB reported reclaimable), while
CT115's was zero. Shared pool free space, not CT114's 500 GiB guest quota, is the
relevant disk constraint. No broad cache/image/volume prune was performed.

Protected rollback copies of the original LXC configuration, runner configuration
and preview queue are in `branchline/acceptance/capacity-20261120` on canonical
appdata. The previous paired application release, native runner, immutable recipe
and dated guest source archives are retained. The preview operator owns these
and the test recovery archive until acceptance and separately authorized
retention cleanup. The rollback copies contain private configuration; keep them
outside Git. Do not overwrite the current queue with the earlier three-running
snapshot or lower the guest memory ceiling while eleven previews are active.

The 32 GiB value is a ceiling, not reserved RAM. Eleven preview service limits
sum to 30.25 GiB before builds and other staging services. These observations
do not establish simultaneous heavy-use or build headroom, full application
behavior on every feature branch, notification delivery, a clean-host restore,
or a newly verified PBS backup. Stop deletes the active database; its protected
rollback archive is deliberately retained and is not a running preview.
