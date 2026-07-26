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

- Nine reconciler tests cover exact one-time staging, nested multi-file audio
  flattening, ambiguous EPUB rejection, synthetic low-space rejection, changed
  source rejection, unsafe keys, copy/hash failure without publication or
  source mutation, and the WUD marker.
- Three WUD runner tests prove that busy exit 75 never triggers replacement
  and that a successful update acquires and releases the marker.
- Both route SQL definitions were applied twice to temporary copies of the
  live NPM and Homarr databases. Integrity remained `ok`; Storyteller produced
  one private NPM row, one Homarr app, three items, and every declared layout.
- Python compilation, JSON validation, Node syntax, Bash syntax, initializer
  idempotency/mode 0600, and `git diff --check` passed.

## Live deployment

The initial container start imported the Alice pair, but also exposed that
placing partial copies below `inbox/.staging` let the upstream watcher observe
them before publication. Canonical files were read-only and unchanged. The
reconciler now copies below the sibling `/storyteller/.staging` path and uses a
same-filesystem atomic rename into the watched inbox. This pre-acceptance
correction is retained here rather than hiding the failed first attempt.

The corrected reconciler published the exact pair with two files and
80,690,971 bytes. Storyteller imported exactly one book. The second disposable
copy was moved, not deleted, to
`/storyteller/recovery/phase4-initial-watch-race`; its EPUB and M4B sizes remain
189,199 and 80,501,772 bytes. A subsequent reconciliation marked the normal
inbox state consumed and reported the pair unchanged without another copy.

Storyteller 2.14.17 and the reconciler are healthy with zero restarts. CT112 is
live at 5 vCPUs/16 GiB, while Storyteller is limited to 3 CPUs/8 GiB and the
reconciler to 0.5 CPU/256 MiB. At idle they used about 327 MiB and 14 MiB.
The live database has integrity `ok`, one book, one ebook, one audiobook, and
no readaloud or user before first-run setup.

## Pair and alignment acceptance

The canonical public-domain fixture is:

- key: `Lewis Carroll/Alice's Adventures in Wonderland`;
- EPUB: 189,199 bytes,
  SHA-256 `4ac9fc092435338fdb28e96b02989a46bbe075ec310f1789db87a653761cce92`;
- M4B: 80,501,772 bytes,
  SHA-256 `fe522ad254a3dc6ea68fea734f5376897fccff588458dc56e35628c1aec8a3ed`.

Both ending hashes match their pre-deployment fingerprints. Storyteller owns
one imported book with EPUB and audiobook assets under its isolated library.

An intentionally ambiguous two-EPUB fixture was reported as `ambiguous` and
left its isolated inbox empty. A separate synthetic-low-space fixture was
reported as `low-space` and also published nothing. The copy/hash-error unit
test proves partial staging is removed and canonical bytes are unchanged.

Alignment, terminal readaloud validation, and reading/listening position
switching remain pending first-run administrator creation through
`https://storyteller.rafael.media/init`. The environment prevents production
passwords from being transferred through tool output, so the four configured
`STORYTELLER_ADMIN_*` values must be entered directly in that private form.

## Platform and regression acceptance

- Pi-hole resolves `storyteller.rafael.media` exactly to NPM at
  `192.168.0.110`. The private TLS route returns the expected first-run 307 to
  `/init`, uses the valid `*.rafael.media` certificate, targets
  `192.168.0.112:8001`, and has LAN/Tailscale allow rules followed by
  `deny all`.
- NPM integrity and `nginx -t` pass. Homarr is healthy and integrity-clean
  with one Storyteller app, three items, and all seven declared placements.
- The Storyteller, live media-contract, Infra services, Shelfarr, BookOrbit,
  and Audiobookshelf focused verifiers pass.
- The central WUD dry-run discovered 42 watched containers, all associated
  with `docker.backupgated`; Storyteller is present and its idle read-only
  guard passes. The active-job exit-75 replacement check remains paired with
  the pending alignment run.
- The installed backup pre-hook created an online SQLite copy with integrity
  `ok`, a matching SHA-256 and size, mode 0600, and matching table counts. The
  latest scheduled appdata service result remains successful. No on-demand
  PBS backup was run.
- The full production bootstrap dry-run stops at the pre-existing missing
  external `PAPERLESS_GPT_OPENAI_API_KEY`. A second dry-run with a mode-0600
  temporary environment copy and explicit non-production placeholder
  completed and removed the copy.
- `provision/verify.sh` passed pools, media contract, free-space floors, HAOS,
  and all LXC mount/configuration checks, then stopped at the exact known
  pre-existing boundary: `LXC 112 has 34 active containers; expected 37`.
  Live totals are CT102 15, CT110 11, CT112 34, and 60 overall; the three
  absent declared containers remain Paperless-GPT, Prometheus, and Loki.

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
