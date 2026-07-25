# Media pipeline part 4 evidence — 2026-07-25

## Scope and status

This record covers Storyteller, exact-key pair reconciliation, isolated
staging, alignment, private access, recovery, and update safety. The repository
implementation was committed and pushed before live mutation. The remaining
sections are completed from live acceptance evidence after deployment.

## Upstream and preflight

- Official stable image:
  `registry.gitlab.com/storyteller-platform/storyteller:latest`.
- Official stable release observed: web 2.14.17. The verifier enforces a
  minimum of 2.14.13 because that release fixed quoting of shell
  metacharacters in paths.
- Current documented interfaces used: `/data`-style owned storage split via
  `STORYTELLER_DATA_DIR`, separate `STORYTELLER_DB_DIR` and
  `STORYTELLER_SNAPSHOT_DIR`, `STORYTELLER_SECRET_KEY_FILE`, config-file watch
  rules with `move`, `/api/health`, and the Books `Missing readaloud` bulk
  processing action.
- No documented stable unattended queue API was found. The implementation does
  not write Storyteller SQLite or invoke private web routes to start alignment.
- Preflight found PVE 9.1.2 on 62 GiB RAM with about 20 GiB available, healthy
  pools, about 478 GiB free on appdata, and about 19.8 TiB free on shared
  storage. CT112 had 5 vCPUs, 12 GiB assigned, and about 5.2 GiB available.
  The declared/live limit is safely increased to 16 GiB; Storyteller itself is
  limited to 3 CPUs and 8 GiB with one processing job.
- The latest scheduled appdata backup and its success-only WUD handoff had
  succeeded. No on-demand backup was started.

## Implementation validation before deployment

- Eight reconciler tests cover exact one-time staging, nested multi-file audio
  flattening, ambiguous EPUB rejection, synthetic low-space rejection, changed
  source rejection, unsafe keys, and the WUD marker.
- Three WUD runner tests prove that busy exit 75 never triggers replacement
  and that a successful update acquires and releases the marker.
- Both route SQL definitions were applied twice to temporary copies of the
  live NPM and Homarr databases. Integrity remained `ok`; Storyteller produced
  one private NPM row, one Homarr app, three items, and every declared layout.
- Python compilation, JSON validation, Node syntax, Bash syntax, initializer
  idempotency/mode 0600, and `git diff --check` passed.

## Live deployment

Pending deployment from the committed implementation.

## Pair and alignment acceptance

Pending live acceptance.

## Platform and regression acceptance

Pending live acceptance.

## Recovery and rollback

Storyteller SQLite/config/manifest/secret state and consistent latest/previous
SQLite copies are under `/srv/appdata/docker/storyteller` and are covered by
the encrypted appdata job. Canonical media and the isolated shared
Storyteller inbox/library are outside that job. The inbox is disposable; the
library contains derived but expensive readaloud assets and is not described
as backed up.

Rollback retains appdata, shared Storyteller media, old images, database
copies, and canonical sources. Revert the Git commit, sync the affected
guests, and redeploy the prior Compose state. Rollback does not authorize
deleting any source, readaloud, image, database, or other retained artifact.
