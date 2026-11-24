# Branchline preview startup and admin acceptance

On 2026-11-24 the current `285-01-track-navigation`,
`285-02-programme-overview` and `285-03-track-management` previews failed after
successful builds. Their retained container logs show successful Liquibase
migrations and continuing Spring initialization when Docker declared them
unhealthy. No application exception appears in those bounded logs. The recipe
allowed 120 seconds of startup grace plus thirty five-second failures; the
runner's outer deadline was 300 seconds. Concurrent build/start contention is
the likely reason these cold starts exceeded that allowance; it was not replayed
as a controlled load experiment.

## Installed change

Homelab commit `2b190656d8083ab2f6ac7fb85942b4cb6ec34980`, published to
`origin/codex/branchline-startup-timeout`, gives the application 600 seconds of
startup grace and the runner 900 seconds including database initialization.
Successful checks still make previews ready immediately. Health commands,
migrations, application commits, dependency pins and admin seed are unchanged.

PVE retrieved that commit and synced it to CT114; `/opt/dothomelab/DEPLOYED_COMMIT`
identifies it. The standard installer retained the accepted Branchline
web/native revision `f14ce775b095312daff122af8178d6b51c84aafd` and installed recipe
`a0c43d0526834c38c870f77d3c4b76eca8171af693fed6656d867de875873e57`.
Only `recipe` and `healthTimeoutSeconds` changed in the runner configuration.
The active one-build/sixteen-running limits were preserved.

## Verification

- All three exact-commit retries became ready, with no application restart or
  OOM observed. The final current list has eight ready previews, zero failed
  rows and no pending cleanup.
- The five already-running applications retained their original start times,
  zero restarts and healthy status. Their databases already contained enabled
  `admin1` accounts with Core role 5 (ADMIN); no additive repair was needed.
- All three new databases contain exactly one enabled `admin1` with role 5.
  Real HTTPS CSRF login and `/api/auth/authorisation` confirm the admin identity
  and authorization on each repaired preview. Cookies/tokens were not retained.
- Browser login and entering admin mode passed on the existing circuit-transition
  preview and repaired track-navigation preview. The latter displayed **Exit
  admin mode** after the switch. Login uses the documented private fixture
  `admin1` / `admin1`.
- Eight recipe tests, documentation links and whitespace checks passed. All
  three generated Compose configurations validated quietly. The Branchline
  release verifier, Pulse CT114 container coverage and unchanged seven-app
  Homarr staging board passed.

| Branch | New preview | Private URL |
|---|---|---|
| 285-01-track-navigation | `331080b1be-e5d00c4a` | <https://bl-12001.staging.rafael.media> |
| 285-02-programme-overview | `23a0b09398-94efe095` | <https://bl-12002.staging.rafael.media> |
| 285-03-track-management | `ca699971ef-197b8de1` | <https://bl-12003.staging.rafael.media> |

These checks cover fresh starts, fixture identity and admin mode. They do not
prove all feature workflows, worst-case concurrent startup time, a database
restore or production migration compatibility. Teacher-account login was not
retested in this task. Existing ready previews keep their earlier recipe and
may display outdated; this does not require a data-resetting restart.

## Rollback and retained material

The preview operator retains the previous immutable recipe and protected
`release-checks/startup-timeout-2b19065/` under staging Branchline appdata. It
contains `runner-before.json`, `previews-after-install.json` and
`admin-acceptance.json`. Keep these through review and the rollback window.
The standard guest sync also retained the previous helper archive. The original
failed-run recovery archives remain untouched. No new backup or restore is claimed.

To revert the defaults, restore the retained runner configuration while the
queue is idle and restart only the preview runner. Preserve current queue,
graph and database state. Existing previews pin their recipe; reverting defaults
does not modify their databases or generated health checks. The earlier deadline
can reproduce premature startup failures.
