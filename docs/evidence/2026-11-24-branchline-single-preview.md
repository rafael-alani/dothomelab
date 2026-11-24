# One Branchline preview per branch

On 2026-11-24 Rafael requested that a branch could not have multiple preview
runs. The original screenshot showed the same `285-01-track-navigation` commit
under two recipe revisions: one ready, one built and waiting for capacity.

## Released behavior

Branchline `e8d25729904c8336d6fe95f1c2a293f9a3884dd4` is published on its
`staging` branch and installed as both web and native runner on CT114. Repeated
requests reuse the branch's active preview across commit/recipe changes and
while stopping. A changed commit or recipe marks it outdated; **Restart preview**
must finish Stop successfully before queuing its replacement. The deployment's
existing Stop data-reset policy also applies to Restart.

The main list shows the current preview per branch. Historical records and
available logs remain accessible by ID. Runner recovery retires legacy duplicate
runtimes while retaining their data and skipping the operator cleanup helper.
Failed retirement remains visible and blocks additional work for that branch.

The live recipe is newer than the preparation source in CT114's retained
`/opt/dothomelab` archive (`046751571f534285b77e21cb47cbc22ec44264a9`). The standard
web deployer was used, then the exact accepted source was installed as the native
runner without regenerating configuration. This deliberately preserved recipe
`768fcf4b1ea5f2a3539e571f7f409889ad82a086df78a20e873dbf66f4d63f7b` and its
one-build/sixteen-running limits. Align the helper archive with the installed
recipe before using the full recipe-rendering installer in a later release.

## Verification

- All 79 Node tests and all four preview Playwright tests passed; the browser
  bundle built and whitespace checks passed. Regression tests cover recipe-only
  changes, new commits, every active state, concurrent HTTP requests, restart
  ordering, history display, legacy duplicate retirement and cleanup failure.
- Live MCP returned 30 rows for 30 distinct branches, from 33 retained lifecycle
  records. Requesting the two running branches again returned their same IDs
  despite their older recipe. No new run was created.
- The persisted preview state matched exactly as parsed JSON before/after
  rollout. All four running preview container IDs remained identical; both
  preview HTTPS URLs returned 200. Runner configuration bytes were unchanged.
- Web and runner markers both identify the release above. Native runner and
  gateway units were active. The staging verifier passed quiet Compose validation,
  running commit labels and HTTP health. The Staging Homarr check reported no
  changes needed across seven apps. Pulse verified CT114's running application
  containers and command-enabled Docker agent coverage.

The live state changed before deployment: the original pair had become stopped
and failed, and only two other previews remained ready. Fourteen failed preview
starts already existed and were preserved; this release does not diagnose or
retry them. There were no live active duplicates left to migrate, so duplicate
retirement was exercised in isolated fixtures, not against live databases.
No fresh Labrador build, live destructive Restart, database restore or production
deployment was performed.

## Rollback and retained material

CT114 retains protected copies of the old web release record, runner configuration,
preview state and container identities under
`/srv/appdata/docker/staging/branchline/release-checks/single-preview-e8d25729904c/`.
The release log and initial verification log (deployment-lock contention) are
retained there too; the later verifier passed. The previous web
image/source and native runner release were verified available before cutover.
The preview operator owns these records until review and any separate cleanup
authorization; they contain protected runtime configuration and must remain private.

The previous web revision was `1a7e56536fbeec3a2937996d6549994e4b034d8e`; the
native runner was `e6f6e788fed7b98bb9165ef133277cb828af4676`. Prefer reverting
the Branchline change on `staging` and deploying the compatible web/runner pair,
preserving the current recipe. The protected record identifies the original runner
path and web release if exact rollback is required. Do not overwrite preview
state after subsequent user activity. A code rollback restores the old duplicate
behavior and does not restore a preview deleted by a later explicit Stop/Restart.
