# Development

This repository contains Bash/Python operations scripts, Compose definitions,
service configuration, and macOS helpers. There is no local app server or
repository-wide build. Clone on the operator machine; use Python 3, Bash, and
Node for the relevant checks, plus Docker Compose for Compose validation.

PVE tools and production `/root/.env` belong on PVE. Do not copy production
secrets to a laptop or run installers/bootstrap as local development setup.
Configuration names live in [.env.example](../.env.example); the source map is
in [architecture](architecture.md#source-map).

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
| Project production | `python3 hosts/production/test_production.py`; shell syntax, quiet Compose, promtool config and Alloy validation on the declared runtime |
| Staging | `python3 scripts/test_initialize_meta_egg_jellyfin.py`; `python3 hosts/staging/test_initialize_env.py`; `python3 hosts/staging/test_deploy.py`; `python3 hosts/staging/test_lifecycle.py`; `python3 hosts/staging/test_sync_homarr.py` |
| Staging dashboard | `python3 hosts/staging/test_sync_homarr.py` |
| Obsidian blog publisher | `npm ci --prefix hosts/infra/blog-publisher`; `npm test --prefix hosts/infra/blog-publisher`; `python3 hosts/infra/blog-publisher/test_install_vault.py`; `python3 hosts/infra/blog-publisher/test_run.py`; `python3 hosts/staging/test_editorial.py`; `python3 hosts/staging/test_deploy.py` |
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
