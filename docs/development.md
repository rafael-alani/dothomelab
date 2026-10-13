# Development

This repo contains Bash/Python provisioning and operations scripts, Docker
Compose definitions, service configuration, and macOS client helpers. There is
no single local application server and no repository-wide build command.

## Set up a checkout

Clone normally on the operator machine. Python 3 runs the documentation checker
and the stdlib-based tests below; Bash parses shell scripts, Node runs the WUD
compatibility tests, and Docker Compose validates Compose when installed.
PVE tools (`pct`, `qm`, `zfs`) and production `/root/.env` belong on PVE.

Read [.env.example](../.env.example) for configuration names and
[inventory.env](../provision/inventory.env) for non-secret placement. Do not
copy the production environment to the laptop to run local checks. Do not run
`prepare.sh`, `install.sh`, or bootstrap locally as a development setup step.

## Locate the implementation

| Area | Entry point |
|---|---|
| Public bootstrap wrapper and orchestration | [bootstrap.sh](../bootstrap.sh), [provision/bootstrap.sh](../provision/bootstrap.sh) |
| Guest/network/storage desired state | [inventory.env](../provision/inventory.env) |
| Overall and media verification | [verify.sh](../provision/verify.sh), [verify-media-contract.sh](../provision/verify-media-contract.sh) |
| Service deployment and guest archives | [deploy-compose.sh](../scripts/deploy-compose.sh), [sync-guest-repo.sh](../scripts/sync-guest-repo.sh) |
| Dotenv parsing and Docker base | [hosts/common](../hosts/common) |
| Application implementation | Relevant `hosts/<placement>/<service>/` directory |
| Backup and update handoff | [backup/pbs](../backup/pbs), [WUD](../hosts/infra/wud/README.md) |
| Branch staging and rollback | [staging](../hosts/staging/README.md) |
| Desktop workflows | [macOS media](../clients/macos-media/README.md), [SNOWSKY ECHO](../clients/snowsky-echo/README.md) |

## Choose checks for the change

Run from the repository root. These are separate checks, not a command to run
every suite for every edit:

```bash
# Documentation/navigation; no network or production access
python3 scripts/check-docs.py
git diff --check

# Parse a changed shell script (substitute its actual path)
bash -n scripts/deploy-compose.sh

# Repository-only storage/Compose contract checks; does not need PVE
bash provision/verify-media-contract.sh --repository

# Isolated tests for the relevant subsystem
python3 hosts/staging/test_deploy.py
python3 hosts/infra/wud/test_run_updates.py
node --test hosts/infra/wud/test_compat.cjs
python3 hosts/apps/storyteller/test_reconciler.py
python3 hosts/servarr/soularr/test_request_scoped_soularr.py
python3 hosts/servarr/cross-seed/test_configure.py
python3 clients/snowsky-echo/test_install_hifimule_profile.py
python3 clients/snowsky-echo/test_sync_pinepods_to_echo.py
```

Use a recent Python 3 matching the changed scripts. Bash requirements vary:
inventory-driven scripts use Bash arrays; macOS's system Bash may not support
every production script. Validate production behavior on its declared Debian
or PVE environment. Do not weaken a check just to make a different local
runtime pass.

For Compose, use `docker compose --env-file <safe-env> -f <compose> config
--quiet` with a private, non-production placeholder file when validating
locally. `.env.example` is a reference and may leave required values empty.
Never run `up` with placeholder credentials. Production validation uses the
scoped deployment process in [operations](operations.md#deploy-a-production-change).

## What checks mean

The documentation checker validates repository-local Markdown links and
heading anchors in the documented source directories, required entry pages,
and navigation to historical reports. It deliberately does not fetch external
URLs, execute command examples, validate UI behavior, or certify prose accuracy.

The subsystem unit tests exercise isolated logic and temporary data. Live
`verify.sh` scripts have different effects: for example WebDAV verification
creates and removes test objects, and database restore tests create retained
test containers/data. Read the affected verifier before choosing it. The full
fleet verifier is not the default for a prose change.

## Debug and capture evidence

Start with selected metadata (`docker ps`, service health, relevant systemd
result), then inspect bounded logs privately. Container environments, expanded
Compose, authentication headers, and application responses may contain secrets;
do not paste them into reports. Keep only sanitized observations in Git.

If a change needs production rollout, commit the intended code first: guest
sync exports `HEAD`, ignoring uncommitted edits. Use [operations](operations.md)
for rollout, verify the deployed revision, and update [status](status.md) only
for what was actually checked.
