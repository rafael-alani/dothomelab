# Staging dashboard and test-app retirement

Focused live work on **2026-10-17**, Europe/Amsterdam, through SSH to PVE `afa`
and `pct exec` in CT110/114. Dashboard implementation:
`77ad73f745650529299878dd001e2607b81cdd21`, branch `codex/staging-homarr-sync`.
This is not a fleet-wide review. [Current status](../status.md) retains the other
baseline limits; [the staging runbook](../../hosts/staging/README.md) owns operation.

## Automatic board

The separate private [Staging board](https://rafael.media/boards/Staging) was
explicitly adopted into the PVE-owned reconciler. Both Compose registrations
and enabled Symphony routes contribute tiles. The two-minute timer runs without
Homarr credentials or production mounts in CT114. Failed collection does not
clear the board. Existing board rows and desktop/mobile home defaults remained
unchanged. Its generated grid has desktop, compact, and mobile layouts.

The isolated PVE checkout is `/root/dothomelab-staging-homarr-77ad73f`.
The installed versioned runtime and its `DEPLOYED_COMMIT` match the full revision
above. Existing `/root/dothomelab` and guest archives remain at their prior
`ee1c217` revision; this rollout did not replace them or deploy Compose images.
Future bootstrap runs from the new code install the timer automatically.

Checks: eight disposable SQLite/discovery tests, seven existing staging tests,
shell syntax, documentation links and whitespace checks passed. Live `--check`
reported `changed: false, apps: 1`; the systemd service succeeded. The signed-in
Firefox accessibility tree showed only Film Introspect on the generated board.
Film-introspect's trusted HTTPS URL returned 200 and both containers remained
healthy. No synthetic project was deployed to production staging for this test.

## Removed active test deployments

| Repository | Former private hostname | Result |
|---|---|---|
| `symphony-tests/obsidian-delivery` | `symphony-check.staging.rafael.media` | Stopped; port 10999 closed |
| `rafael-alani/project-49a75765` | `markdown-settings-20261016.staging.rafael.media` | Stopped; port 10003 closed |
| `rafael-alani/symphony-acceptance-20261016-2aea6a7d` | `markdown-only-20261016.staging.rafael.media` | Stopped; port 10002 closed |

The two note projects were already paused with no active idea work; their former
note paths were absent. The fixture had no VM101 vault-project registration.
All three were disabled through the installed receiver protocol. Its allowlist
is empty. Their PVE route-ownership entries, CT114 nginx routes, three NPM hosts,
three exact Pi-hole records, and dashboard tiles were removed. NPM uses its
soft-delete flag and native config-removal/reload path. Nginx and SQLite checks
passed. Film-introspect, the shared router, wildcard certificate, guests, and
production app services were retained.

## Retained rollback and limits

Source archives were checked as readable tar files and SHA-256 values recorded
before retirement. Releases, source archives, logs, and disabled receiver route
reservations remain in canonical appdata. No GitHub repository, note history,
backup generation, volume, or guest was erased.

- PVE router/ownership rollback and archive manifest:
  `/srv/appdata/docker/symphony-staging-control/retired-tests-20261017T102936Z`.
- NPM verified SQLite copy, affected nginx files and prior local DNS list:
  `/srv/appdata/docker/infra-nginx-proxy-manager/retired-staging-tests-20261017`.
- Homarr verified pre-adoption SQLite copy:
  `/srv/appdata/docker/homarr/db.sqlite.pre-staging-sync-20261017`.

Disable `dothomelab-staging-homarr.timer` before reverting its generated board.
Restore only the intended route/board records if later unrelated changes exist;
whole-database rollback would discard those changes. Re-enabling an app also
requires restoring its routing and receiver enrollment, not just a Homarr tile.
The scheduled appdata backup remains the protection path. No new PBS backup,
application restore, physical rebuild, or shared-data recovery was performed.
