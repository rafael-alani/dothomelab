# Working on dothomelab

## Mission and sources

Recreate the managed homelab from Git, clean PVE 9 on `afa`, importable `vault`,
current `/vault/shared`, current appdata at `/srv/appdata/docker`, `/root/.env`,
declared hardware, and the unchanged router. `./bootstrap.sh` must rebuild the
six LXCs without guest-root backups and restore absent HAOS VM104 from its
canonical VMA. VM101 and physical disk provisioning are out of scope.

Priority: active user request → observed live state → repository → older
snapshots or external skill inventories. Inspect live state first. A stale
skill must not reintroduce Watchtower, central PostgreSQL, guest-root recovery,
or the former one-service-per-LXC inventory.

## Repository scope

- Keep homelab infrastructure, deployment, backup, recovery, and operational
  scripts in `dothomelab`, including reusable helpers created in earlier chats.
- `openhands-symphony` owns Symphony's documentation, Obsidian task processing,
  and code-generation workflows. Obsidian storage/sync/backup infrastructure
  remains in `dothomelab`; generated applications belong to their own projects.
- Access to another repository is not permission to modify it. Change Symphony,
  n8n, application repositories, or any other project only when the active user
  request explicitly includes that project. Historical authorization does not
  expand a new task's scope. Read related repositories only as needed for context.
- Maintain scripts in the owning Git repository/worktree. `/tmp`, `/private/tmp`,
  and `/run` are for disposable transport, test fixtures, and runtime artifacts;
  they must never be the only copy of a maintained script. Promote reusable
  helpers or consolidate them into existing tracked tools before completion.

## Read for the task

| Task | Required reading |
|---|---|
| Find documentation | [Documentation map](docs/README.md) |
| Establish readiness or investigate drift | [Status](docs/status.md), then the linked evidence |
| Use or change a user workflow | [User manual](USER_DOC.md) |
| Change hosts, storage, networking, data ownership | [Architecture](docs/architecture.md), [media contract](docs/media-data-contract.md) |
| Operate, deploy, update, or recover anything | [Operations](docs/operations.md), [service policies](docs/reference/service-policies.md), affected `hosts/` README |
| Rebuild or change bootstrap | [Rebuild contract](docs/rebuild.md), [HAOS recovery](docs/haos-vm.md), [inventory](provision/inventory.env) |
| Work on staging | [Staging runbook](hosts/staging/README.md) |
| Scaffold, release, publish, or recover project production | [Production runbook](hosts/production/README.md) |
| Edit scripts or run checks | [Development](docs/development.md) |
| Prepare a change for review | [Contributing](CONTRIBUTING.md) |
| Change documentation structure | [Documentation ownership decision](docs/decisions/0001-documentation-ownership.md) |

## Portable applications and staging review

For Rafael's staging previews, connect applications to the required homelab
services through an explicit Docker/Compose deployment contract. The application
repository owns its portable image/build, container paths, configuration keys,
ports, and health checks. `dothomelab` owns the staging assignments: host bind
mounts or named volumes, service endpoints, networks, port mappings, and scoped
environment/secret injection. Keep Rafael-specific paths, addresses, domains,
and service choices in that deployment configuration, not application constants
or defaults that assume another user has this homelab. Other installations must
be able to provide their own values through the same interface.

Declare each integration and its data access explicitly; preserve the media
contract, narrow mounts, read-only access where sufficient, and staging-scoped
credentials. A usable integration preview should exercise its declared services;
report unavailable integrations instead of treating demo mode as their acceptance.
This policy does not itself mount production data or change the current staging
runtime; follow the [staging runbook](hosts/staging/README.md) and task scope.

Publish a candidate to its configured staging/review branch and deploy that exact
revision to a private preview before promoting it to `main`. Give Rafael the
preview URL, deployed commit, checks, and integration gaps so he can use and review
it. Promotion follows his acceptance and authorization; a successful build or
health check alone is not that acceptance. If a delivery path requires publishing
to `main` first or lacks the Docker contract, report the gap and keep the candidate
off `main`; do not work around it with homelab constants in application code.

## Automatic static blog publication

The blog uses the [native static contract](hosts/blog/README.md), without Docker.
Obsidian `status: published` automatically publishes content changes to production;
`draft` removes it there and retains it on private staging. Content edits need no
release approval, Git push, tests, polling delay or browser auto-refresh. This
exception applies to blog content; application code still follows the branch and
production authorization rules below.

## Project production authorization

Agents may deploy a project to production only when the active user prompt
explicitly requests that production deployment. Preparing scaffolding, accepting
a preview, pushing/merging `main`, fixing code, and general historical approval
are not production deployment authorization. When the user asks to leave it off,
complete the scaffold and checks, then hand over the exact activation command.

CT115 production takes application code only from `origin/main`; CT114 follows
its configured review branch. Missing `main` or the applicable portable deployment contract is a
blocker to report, never permission to promote staging or substitute a branch.
Keep production application-code releases manual, with no branch poller, CI deployment or WUD
updates for these images. Review acceptance and production activation are separate.

Before enrollment or release, inspect every declared service dependency in the
live homelab. Reuse available services with explicit production configuration;
notify Rafael about missing/unhealthy services, credentials and permissions.
Do not silently create substitutes, reuse staging credentials or accept demo mode.
Separate appdata, credentials, Umami website IDs, and project/environment labels
in metrics, logs, alerts and dashboards. Production builds use the applicable published
content selection; private staging drafts/media must not enter public artifacts or mounts.

## Application credentials and staging acceptance

Apply this policy to every project deployed through this homelab. Classify
credentials by owner: shared service/operator keys belong in deployment secrets
(PVE `/root/.env`, injected only into the owning service); user-provided server
addresses and tokens belong in that application's authenticated, user-scoped
settings and durable appdata, encrypted at rest where recoverable secrets are
needed. Do not enumerate users' keys as host environment variables. Keep saved
secrets out of responses, browser storage, URLs and logs; provide replace/remove
controls and validate a connection before replacing a working one. A shared
Local viewer profile must be labeled as shared, not claimed as user isolation.

End-user setup uses product settings and server names, without host paths, LXC
IDs or deployment-variable instructions. The deployment owns encryption keys
and recovery procedures; the app owns authorization, credential isolation and
connection validation. For example, Meta Egg's OpenSubtitles key is service-wide;
a Film-introspect user's Jellyfin connection is private application state.

Staging exercises these same ownership and setup flows. Test configured real
integrations and report missing credentials or permissions as gaps; fixtures
only establish fixture behavior. When a connected source has extra capabilities,
show its identity and relevant controls while preserving the standalone flow.
Keep candidates on their configured review branch and private preview until
Rafael accepts and authorizes promotion.

## Essential constraints

- Use SSH to PVE and `pct exec` into LXCs; never depend on guest SSH.
- Never print/store production environment values, tokens, credentials,
  private keys, or native recovery secrets in logs, Git, or task output.
  Never disable SSH host-key checking.
- `/root/.env` is Compose dotenv; use `hosts/common/load-env.sh`, never shell
  `source`. Use `docker compose config --quiet` to validate without rendering
  expanded secrets. Run Compose validation before every deployment.
- Durable application state belongs in canonical appdata; shared media belongs
  on `/vault/shared`. Guest roots contain replaceable runtime state.
- Inspect `pct config`, `findmnt`, `stat`, and `namei` before permission work.
  LXCs are unprivileged: host `101000` maps to guest `1000`; PBS host `100034`
  maps to guest `34`. Map every consumer before any ownership change.
- Keep databases application-local. Never copy PostgreSQL data directories
  between versions/servers. Major/extension changes need logical dumps,
  isolated restore tests, and verified rollback.
- Preserve the sole canonical writers and narrow mounts in the media contract.
  Grimmory must never write audiobooks. Retain live DroppedNeedle unchanged
  until generated Aurral flow acceptance passes; clean bootstrap excludes it.
- Production image updates are backup-gated through WUD. Keep databases, WUD,
  Immich, Gluetun, and bespoke upgrade paths manual. No Watchtower, WUD timer,
  or unauthenticated Docker TCP/2375. CT114 uses its separate branch poller.
- Routine changes use scheduled backups; do not start a backup or wait for PBS
  verification without task-specific durable-data risk. `/vault/shared` is
  outside appdata PBS. Claim recovery only to the extent actually tested.
- Do not start Paperless-GPT with a dummy external API key. Keep staging secrets
  scoped; never supply production integrations implicitly.

## Permission and rollback boundaries

Require explicit task-level authorization and verified rollback before:

- destroying/formatting pools, datasets, partitions, guests, or guest disks;
- `docker compose down -v`, deleting volumes/databases, or pruning volumes;
- recursively deleting/chowning/chmodding appdata or shared data;
- deleting rollback snapshots, dumps, volumes, images, or legacy databases;
- rebooting PVE, stopping guests, disruptive DNS/network/firewall/SSH changes;
- public exposure or shared-credential rotation.

Never use `/`, `~`, `$HOME`, an unresolved variable, or broad glob as a
destructive target. `/vault/backups` and `/vault/data` are never scratch.
Stop when live state contradicts the plan in a way that risks data loss.

## Personal skill synchronization

When a task in this repository changes a personal skill under
`/Users/rafael/.codex/skills` that is already installed in Symphony's VM101
catalog, updating and verifying that VM copy is part of completing the task.
The local skill is authoritative. Follow the
[skill synchronization procedure](docs/operations.md#synchronize-personal-worker-skills)
without asking for separate deployment confirmation, unless the user limits
the task to local changes. Sync only the changed installed skills and their
resources; preserve other catalog entries and retained releases. New skill
installations still need task scope. If access or validation fails, report the
VM copy as unsynchronized. Do not restart services, trigger runs, or rewrite
accepted task snapshots to apply a skill update.

## Useful entry commands

```bash
# Operator machine: read-only host/guest inspection
ssh root@192.168.0.250
ssh root@192.168.0.250 -- pct exec 112 -- docker ps
# Repository checkout: local documentation checks
python3 scripts/check-docs.py
# PVE checkout only: read-only recovery preflight
./bootstrap.sh --dry-run
```

## Worktree completion and cleanup

The canonical local checkout is `/Users/rafael/Repos/dothomelab`. Keep the retained
staging/review version in that original folder; temporary sibling worktrees are
for active isolated work. A completed task must not leave the original folder
on an older version while its delivered work survives only in a task folder.

Before consolidation, inspect the live deployed commit, configured review branch,
remote refs, all worktrees/clones, and local changes. Preserve dirty, untracked,
unpushed and needed ignored files in a verified named recovery snapshot or branch.
Record its ref and restore instructions; retain secrets outside Git. Check local
commands, scheduled jobs and previews for references to a worktree before moving
or removing it, and update and verify those references at the canonical path.

Publish completed changes to their intended integration/review branch after the
required checks. Verify the remote revision and bring the original checkout to
the retained revision, including follow-up documentation. Pending staging
acceptance keeps the candidate on its review branch. Folder cleanup alone does
not authorize promotion to `main`, deployment, or discarding other work.

Once files, refs and consumers are verified, remove the task's inactive duplicate
checkout through its owning lifecycle: Codex archive for managed worktrees,
`git worktree remove` for ordinary linked worktrees. Remove merged local task
branches only after proving their changes are retained remotely. Preserve active
chat/job/preview worktrees and required recovery artifacts. If ownership, access,
local work or review blocks cleanup, report each exact path and reason; never
silently accumulate completed task folders.

## Completion

When adding, moving, renaming, or retiring a service, complete the
[Pulse and Homarr enrollment checks](docs/operations.md#service-monitoring-and-dashboard-enrollment)
in the same change. Verify live Pulse coverage and the appropriate Homarr tile;
report any monitoring or dashboard gap before declaring delivery complete.
After tests, migrations, or releases, follow the
[runtime cleanup procedure](docs/operations.md#runtime-cleanup): remove successful
temporary containers and superseded service runtimes after verifying replacements;
name every retained diagnostic/rollback artifact, its owner, reason and cleanup
condition. Check staging/production build-cache usage and preserve current/previous
releases and durable data. Explain cleanup targets before deleting them. Verify
Pulse, shared monitoring and Homarr against the resulting live inventory; report
storage/metric limitations instead of changing mounts merely to alter a dashboard.

When changing software deployed to VM101, commit and push the completed release
to its configured Git remote and update branch so the VM can pull it. Verify
the remote revision and report the installed revision or the specific deployment
blocker; a local commit, Git bundle, or VM-only source copy is not completion.

Change one service/data class at a time. Keep provisioning, Compose,
`.env.example`, verification, and affected documentation consistent. Read
`prepare.sh`/`verify.sh` before executing them; verifiers can create probes.
Report what changed, what was checked, remaining gaps, and rollback limits.
Guest archives at `/opt/dothomelab` must have the intended `DEPLOYED_COMMIT`.
Completed recovery changes must be committed and retrievable by the clone
path; contain no production secrets; pass relevant checks; and record external
or unverified prerequisites. Documentation drafts can remain local for review.
