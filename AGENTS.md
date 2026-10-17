# Working on dothomelab

## Mission and sources

Recreate the managed homelab from Git, clean PVE 9 on `afa`, importable `vault`,
current `/vault/shared`, current appdata at `/srv/appdata/docker`, `/root/.env`,
declared hardware, and the unchanged router. `./bootstrap.sh` must rebuild the
five LXCs without guest-root backups and restore absent HAOS VM104 from its
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
| Edit scripts or run checks | [Development](docs/development.md) |
| Prepare a change for review | [Contributing](CONTRIBUTING.md) |
| Change documentation structure | [Documentation ownership decision](docs/decisions/0001-documentation-ownership.md) |

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

## Completion

Change one service/data class at a time. Keep provisioning, Compose,
`.env.example`, verification, and affected documentation consistent. Read
`prepare.sh`/`verify.sh` before executing them; verifiers can create probes.
Report what changed, what was checked, remaining gaps, and rollback limits.
Guest archives at `/opt/dothomelab` must have the intended `DEPLOYED_COMMIT`.
Completed recovery changes must be committed and retrievable by the clone
path; contain no production secrets; pass relevant checks; and record external
or unverified prerequisites. Documentation drafts can remain local for review.
