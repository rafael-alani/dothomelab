# Branchline verified resource cleanup

Rafael asked for stopped branches to leave no running resources and for this to
be a core invariant covering future runs. The paired web/native runner release
`70c8c395688fe5353603bfdac7df515073183cf0` was deployed on CT114 on 2026-11-24.
Homelab helper archive `e4402921c6b2383441ae46966b5b171cf7de5761` supplies the
matching recipe and resource ownership configuration. Neither repository's
`main` branch was promoted.

After connectivity was restored, Rafael requested all changes from both chats
on staging. Follow-up `f14ce775b095312daff122af8178d6b51c84aafd` is now published
to `origin/staging` and installed in both web and native runner. The helper
archive remains `e440292`; subsequent homelab changes are documentation only.

## Behavior and cause

Previously, failed starts could stop containers without removing their Compose
networks. Fourteen empty failed-preview networks exhausted Docker's available
address pools. Gradle's inherited image volume also left anonymous caches after
container removal. The screenshot's `1e6e05c04b-fb4b4b36` had actually completed
Stop at 09:09:41 CET; its stale row did not indicate a remaining runtime.

Stop, Cancel, build/start failures and interrupted operations now converge on
one verified teardown. The runner journals anonymous-volume identities before
container removal, reaps owned processes and removes owned containers, labelled
builders, networks, reviewed disposable caches and exact preview image tags.
The existing pinned cleanup helper archives and byte-verifies the preview's
database, seed and source before removing its live directory. Unknown data
volumes or foreign consumers block removal rather than silently deleting data.
New runtime Gradle caches use bounded tmpfs.

The runner independently checks absence before declaring a terminal result or
releasing the branch, port and capacity. Failure remains `cleanupPending`,
blocks another run of that branch, and supports retry. Startup reconciles legacy
failures and resumes interrupted cleanup while retaining ready previews. Batch
Stop marks every target before cleanup begins; cleanup is serialized so releasing
a slot cannot start a selected sibling. Late health responses cannot overwrite
cleanup failure. Bounded logs live outside the active workspace.

The coordinated UI release orders the selected range ancestor-first, puts
off-range runs under **Other branches**, and adds **Stop all** in the modal and
canvas plus **Stop selection** in the canvas. Stop all covers the current
repository, including off-range rows. Pending controls prevent double submission;
cleanup failure shows **Retry cleanup**. Stop requests no longer hit the web
client's former 30-second idle timeout.

## Live verification and repair

- The initial audit found no owned containers, networks, image tags or live
  directories for all 17 stopped records.
- Removed exactly 14 empty networks belonging to failed previews, after retaining
  their metadata and rechecking both failed state and absence of endpoints.
- Startup reconciled all 26 old failed records through verified cleanup. Every
  record received `cleanedAt`; no cleanup remained pending at the handoff.
- All 14 ready previews and their exact 28 container IDs survived runner cutover.
  The current one-build/sixteen-running limit was preserved.
- Retried the exact ten address-pool failures only after confirming cleanup,
  unchanged branch SHAs and no active same-branch replacement. The handoff
  snapshot had 14 ready, one building and nine queued retries, with no duplicate
  branch rows. Builds waiting for the sixteen-runtime limit are intentional;
  this does not establish that all retried applications eventually became ready.
- Both live service markers identify `70c8c39`. The served UI bundle matches the
  tested local build byte-for-byte. The scoped staging verifier passed Compose
  validation, commit labels and health; Homarr needed no changes across seven
  apps; Pulse verified CT114 running-container coverage.

The ten retried nodes were `circuit-transition`, `285-01-track-navigation`,
`285-02-programme-overview`, `285-03-track-management`, `285-04-edition-assignment`,
`285-05-programme-graph`, `285-bookmark-schema`, `original-285`,
`try-skill-on-2-2-try-2`, and `programme-backend`.

## Tests

The deployed combined release passed 92 Node tests, eleven preview/workspace
Playwright tests, the bundle build and whitespace checks. The Docker suite is
opt-in and ran separately on CT114 against the exact installed source: ready
Stop, failed builder, failed start, cancellation, interrupted execution/restart,
and retry after verification failure all proved owned-resource and live-directory
absence. Fixtures use random project identities and disposable temporary data,
with no application appdata or published ports. Homelab preparation (eight tests),
cleanup (five tests) and documentation checks passed.

## Remaining work and retained material

The separate `exit-admin-editing` run `6980fdab9d-98c181a1` built successfully but
its skills container became unhealthy. Its archive retained the Compose error,
not the underlying application stdout/stderr, so the application cause remains
unknown. It was not included among the ten network retries.

Follow-up Branchline commit `f14ce77` captures application logs before removing
containers: last 200 lines, 10-second/128-KiB capture limits and at most 64 KiB
retained per container, with known secret environment values redacted. Capture
failure cannot expose raw command errors or prevent cleanup. The pre-fix code
fails the new regression; the follow-up passed the full local suite (93 tests
and one opt-in Docker skip), then all seven focused resource tests after adding
the capture-error case. After reconnection, the real-Docker test passed against
an exact committed-source copy on CT114 (73.4 seconds), including stdout/stderr
retention and credential redaction. The installed resource module's SHA-256
matches the tested source. Existing missing application logs cannot be recovered
retroactively.

The follow-up cutover had no active builds, starts or stops. All sixteen ready
previews retained their exact 32 container IDs. The final authenticated API
snapshot had sixteen ready, eight built/waiting for capacity, five stopped and
the one separate health failure above. There were no duplicate branches or
pending cleanups; one-build/sixteen-running limits and the installed recipe were
unchanged. HTTPS served all requested controls and the tested UI bundle exactly.
Quiet Compose validation, accepted commit labels, both native units, Pulse's
CT114 container coverage and Homarr's unchanged seven-app staging board passed.

The cooperating cleanup chat independently verified all 43 terminal records:
each had `cleanedAt`, no owned runtime resources or live directory, and a retained
recovery receipt with matching archive SHA-256. This establishes archive integrity,
not a new MySQL restore. Both disposable test-source transports under `/run` were
removed after successful acceptance; maintained source remains in Branchline Git.

Twenty unused anonymous Gradle caches (2,052,540 file bytes) remain pending
deletion. The cooperating cleanup chat rechecked the exact volumes and created
private `legacy-gradle-caches.tar.gz` (520,208 bytes) and
`legacy-gradle-caches.json` under `release-checks/resource-invariant/`. Extracted
file hashes, ownership and modes match all twenty original volumes. Automatic
approval review rejected deletion because [AGENTS](../../AGENTS.md) requires
separate explicit volume-deletion authorization. That chat has requested the
exact approval; no volume deletion is claimed. Fourteen other anonymous volumes
are still used by original ready previews and are outside this deletion request.

The preview operator retains these deliberate recovery or shared resources:

| Material | Reason and cleanup condition |
|---|---|
| `preview-recovery/<id>.tar.gz` and checksum receipts | Protected cold preview recovery; remove only with separate authorization |
| `release-checks/resource-invariant/` | Private before-state/config/container identities, empty-network metadata, retry receipt and release logs; retain through acceptance and rollback window |
| `release-checks/diagnostics-f14ce77/` | Follow-up web/config/queue and ready-container snapshots, deploy log and verification; retain through acceptance and rollback window |
| Historical `recipe-proof` and `recipe-proof-ci` resources | Two proof networks, four image tags and diagnostic data outside lifecycle records; retain until the owner releases the proof/rollback evidence |
| Historical `58d68c9ce1-cb11a7d6` and `0a24487d6a-71c5032e` directories | Earlier cancelled source/log evidence; retain until historical acceptance evidence is no longer needed |
| Shared base images and Docker build cache (about 15.2 GB at initial audit) | Shared reproducible inputs; managed separately by bounded host maintenance |

These protected diagnostic directories together occupied about 1.15 GB at the
initial audit. They are not a claim of leaked active previews. Private archives
contain scoped credentials and must not enter Git or task output. No global
prune, production data mutation, fleet restart or new PBS backup was performed.

## Rollback and continuation

CT114's private `release-checks/resource-invariant/` holds `web-before.json`,
`runner-before.json`, `previews-before.json`, `previews-before-runner.json`,
`ready-before-runner.json`, `network-failures.json` and `network-retries.json`.
Retained web/native releases and the previous runner configuration support a
paired code rollback. Preserve current queue/graph/database state; restoring old
state wholesale would discard subsequent activity. A code rollback restores the
old cleanup defects and cannot restore deleted live databases.

The cleanup helper remains pinned to
`9c83a5862375419339ea70bc65cd372fbc1cf173dbcf8f5d175fc50347eeff11`.
Its archive byte verification is not a new database restore test. The earlier
[cold MySQL restore](2026-11-20-branchline-capacity-cleanup.md) remains the tested
recovery evidence; a clean-host restore and simultaneous heavy-load capacity are
still unverified. Resume through the
[paired release runbook](../../hosts/staging/branchline/README.md#install-or-release-the-paired-services),
after active builds/starts finish, and recheck original ready-container identities.
