# Development

This repository contains Bash/Python operations scripts, Compose definitions,
service configuration, and macOS helpers. There is no local app server or
repository-wide build. Clone on the operator machine; use Python 3, Bash, and
Node for the relevant checks, plus Docker Compose for Compose validation.

PVE tools and production `/root/.env` belong on PVE. Do not copy production
secrets to a laptop or run installers/bootstrap as local development setup.
Configuration names live in [.env.example](../.env.example); the source map is
in [architecture](architecture.md#source-map).

## Maintained scripts

Follow the [repository ownership](architecture.md#repository-ownership) boundary.
Write operational tools directly in the owning repository or its Git worktree,
with their checks and owning runbook. Use `hosts/<host>/<service>/` for service
helpers, `backup/` for host backup orchestration, and `scripts/` for shared
operator tools. Existing locations remain authoritative; do not create a second
copy merely because a helper was first developed in a conversation.

Temporary directories may hold exported Git archives, fixtures, diagnostics,
and build output. They are never the maintained source or a required recovery
input. Before completing a task, consolidate useful temporary helpers into
tracked tools, check that the committed revision contains them, and record the
repository, branch, and revision. A pushed feature branch does not mean the
operator's `main` checkout already contains that change. Preserve unrelated
working-tree edits when integrating branches.

Recent temporary helper names map to these maintained entry points:

| Earlier helper / purpose | Repository owner |
|---|---|
| `proton-coverage-audit-20261017.py`, `proton-photo-content-audit-20261017.py`: source coverage and payload comparison | [Source verifier](../hosts/infra/obsidian-sync/source-verification.py), automatically invoked by [Proton backup](../hosts/infra/obsidian-sync/proton-backup.sh); SHA-256 comparison supersedes the earlier path/size and GNU tar audits |
| `create-staging-homarr-board.py`: initial board creation | [Staging Homarr reconciler](../hosts/staging/sync-homarr.py) creates and maintains the board from current inventory |
| `check-ff-route-20261017.py`: one deployment's route inspection | [Staging verification](../hosts/staging/verify.sh) and [route owner](../hosts/staging/configure-routes.py), following the [staging runbook](../hosts/staging/README.md) |
| `deploy-ff-config-20261017.sh`: dated guest archive cutover | [Guest export](../scripts/sync-guest-repo.sh), [staging deployment](../hosts/staging/deploy.py), and their runbooks; inspect rollback handling before use |
| `backup-ff-routes-20261017.py`: one-time fresh NPM/DNS rollback snapshot | [Staging runbook](../hosts/staging/README.md); private snapshots remain appdata recovery assets, not Git source |

The dated deployment/snapshot snippets contain fixed revisions and live-state
assumptions. They are historical execution artifacts, not supported commands
to replay. The route owner retains its initial NPM backup; that is not a fresh
snapshot for every later change. Task-specific rollback still needs current
state inspection. This mapping covers the retained Proton and staging helpers
inspected on 2026-10-17; it is not a claim that every past chat was inventoried.
Symphony and personal-skill helpers were excluded from this homelab audit.

## Choose checks for the change

Run from the repository root; select the relevant checks rather than every
suite. Production scripts target their declared PVE/Debian runtime; macOS's
system Bash may lack required features.

```bash
# Documentation
python3 scripts/check-docs.py
git diff --check

# Shell syntax (substitute the changed file)
bash -n scripts/deploy-compose.sh

# Repository-only media contract; no live access
bash provision/verify-media-contract.sh --repository
```

| Changed subsystem | Isolated check |
|---|---|
| Proton archives (Linux with Bash, jq, GNU tar/coreutils) | `bash hosts/infra/obsidian-sync/tests/test-proton-identifiers.sh`; `bash hosts/infra/obsidian-sync/tests/test-proton-backup.sh` |
| Staging | `python3 hosts/staging/test_deploy.py`; `python3 hosts/staging/test_lifecycle.py`; `python3 hosts/staging/test_sync_homarr.py` |
| Staging dashboard | `python3 hosts/staging/test_sync_homarr.py` |
| Proton source/archive checks | `python3 hosts/infra/obsidian-sync/tests/test_source_verification.py`; Linux: `bash hosts/infra/obsidian-sync/tests/test-proton-backup.sh` |
| WUD | `python3 hosts/infra/wud/test_run_updates.py`; `node --test hosts/infra/wud/test_compat.cjs` |
| Storyteller | `python3 hosts/apps/storyteller/test_reconciler.py` |
| Soularr | `python3 hosts/servarr/soularr/test_request_scoped_soularr.py` |
| Cross-seed | `python3 hosts/servarr/cross-seed/test_configure.py` |
| ECHO profile / podcasts | `python3 clients/snowsky-echo/test_install_hifimule_profile.py`; `python3 clients/snowsky-echo/test_sync_pinepods_to_echo.py` |

Validate Compose with `docker compose --env-file <safe-env> -f <compose> config
--quiet`. Local placeholders must never be deployed; `.env.example` may leave
required values empty. Production validation follows [operations](operations.md#deploy-a-production-change).

## Verification limits

The docs checker covers required pages, local links/heading anchors, and history
navigation. It does not fetch external URLs, execute examples, or validate prose
and UI behavior. Live verifiers can mutate test state: WebDAV writes/deletes
probes and restore tests retain isolated containers/data. Read a verifier before
running it. A prose edit does not need the full fleet verifier.

Guest sync exports committed `HEAD`, not local edits. Record the intended
revision and actual checks; keep secrets out of logs and evidence. See
[CONTRIBUTING](../CONTRIBUTING.md) for completion expectations.
