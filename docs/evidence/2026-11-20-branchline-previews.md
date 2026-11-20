# Branchline previews and independent SSH development

Rafael requested private staging hosting, existing application Compose files,
previews for one/selected/all graph branches, configurable capacity and a fresh
SSH development VM without Symphony. Application changes are in the private
[Branchline staging branch](https://github.com/rafael-alani/branchline/tree/staging);
infrastructure is on `codex/branchline-staging` in the canonical homelab checkout.
No application feature branch needs an infrastructure commit.

## Delivered contracts

- Graph selection supports drag rectangles, Shift additions and Command/Control
  toggles. The node context menu provides Preview, inspection, comparison,
  descendant selection and copy actions. Selected and visible-range requests
  capture the displayed branch tips and refuse stale graph submissions.
- The web app uses a Unix-socket client. A separate native runner snapshots the
  selected commit, prepares the registered recipe, validates merged Compose and
  queues bounded builds/runtimes. Defaults are one build and three live previews;
  operator bounds can be raised after reviewing the host's capacity.
- The Labrador recipe consumes the source `end_to_end/compose.yml` and existing
  Dockerfiles. It retains their combined LabraCore/Skill Circuits image and a
  separate private MySQL container. Preparation compiles exact Skill Circuits
  sources with pinned local LabraCore/dependency inputs, without GitLab access.
- The CLI exchanges Git bundles over authenticated HTTPS. Checkout is isolated;
  submit requires committed work and the expected server tip; fetch preserves
  working files. Stopping a preview retains its database, source and logs.
- VM116 `codex-dev` has Debian 13, four CPUs, 8 GiB RAM, Java 21, Node 24.22.3,
  Chromium and Codex CLI 0.143.0. Its `/workspace` is canonical appdata through
  virtiofs. VM101 stays stopped and unchanged. The SSH VM has no Docker socket,
  PVE private key or production environment.

## Verification record

Live acceptance completed on November 20. Codex account authentication and
desktop remote-chat/handoff remain user setup and unverified respectively.

| Component | Accepted identity / location |
|---|---|
| Web, native runner and VM CLI | `b00f1a239d38d38e71357afad7e0fe2fd6f02e13` |
| Recipe | `d26171f4d636a6331fa41af7c9b2a152322c41fadfcaa58e7894ac0d25b62e57` |
| Application | https://branchline.staging.rafael.media |
| Final stack | `7fbd76a192-16451060`, https://bl-12000.staging.rafael.media |
| Partial stack | `050feb8bea-28196691`, https://bl-12001.staging.rafael.media |

Both preview URLs are private and use the existing E2E fixture login
(`cseteacher1` / `cseteacher1`), with isolated fixture databases.

- Branchline's 56 backend/CLI tests passed; browser tests exercised selection,
  context actions, capacity controls, logs, stop, unchanged editor state and the
  existing editor/range/propagation flows. The initial sandboxed test attempt
  could not inspect process identities; the unchanged run with that permission
  passed.
- Homelab deploy/environment/route, gateway HTTP, recipe and VM client tests
  passed. Documentation links and whitespace checks passed.
- Staging accepted the paired Branchline release above.
  HTTPS health and the registered deployer verification passed. Java,
  TypeScript, Svelte and JSON language services passed in the actual non-root
  web container; Java completion used the installed JDT LS. Its archive required
  `--no-same-owner` because upstream file ownership exceeds the LXC UID mapping.
  A rejected-session check used bounded polling for asynchronous WebSocket close
  delivery in the disposable Linux test copy; production code was unchanged.
- Actual staging browser checks passed for the 48-node final range, 25-node
  partial range, zoomed drag selection, Shift/Command selection and context menu.
  These checks used the imported Git catalog without mocked API responses.
- The real Linux recipe compiled Java and frontend assets, built the existing
  image structure and started isolated MySQL and the application healthy.
  Both final and partial URLs passed real browser login, Core identity and API
  authorization, local fonts and JavaScript checks. The seeded Reasoning and
  Logic course appears in the final preview. Core applied 254 migrations and
  Skills applied 226. After a validated Compose stop/start, all 99 table counts
  and the seed marker timestamp matched the settled baseline exactly. An earlier
  API-only baseline preceded the browser's lazy creation of one Skills edition;
  a second restart verified the settled application state without that race.
- A single SSH preview request built the final stack. Real UI Command-selection
  and **Preview 2 branches** reused that environment and queued the partial stack.
  At a running limit of one, final became ready while partial remained built,
  waiting for capacity. **Preview graph** queued all 48 visible nodes with exact
  expected SHAs; the 46 new test environments were cancelled, exercising one UI
  Cancel and the batch API. The two examples were preserved. UI capacity controls
  restored one build/three running previews and partial then started successfully.
- A scoped runner restart preserved both ready environments, limits, the socket
  directory inode and the continuously running gateway. The release-symlink
  entrypoint and boot/process identity lock are covered by real child-process
  regression tests. Startup now establishes the native socket group and verifies
  both service endpoints rather than accepting only systemd's start-job result.
- Private exact/wildcard TLS routes were installed with a verified focused NPM
  SQLite rollback copy. CT110's shared archive remains unchanged; the isolated
  helper is pinned to `366759d6d4a80f5d2e95ae03405c276b07d0bddd`.
- VM116 cloud-init completed; SSH, versions and the `/workspace` mount passed.
  Its authorized public key is retained for rebuilding. Codex account sign-in
  is a user step and has not yet been verified.
- The real VM116 CLI checkout/commit/submit/fetch round trip passed. The server
  immediately showed the submitted commit, fetch preserved an uncommitted file,
  and compare-and-swap restoration returned every one of the 50 catalog tips to
  its exact original value. The empty acceptance commit is retained at
  `refs/branchline/verification/ssh-20261120`; no application files changed.
  `/workspace/repos/skill-circuits` is left clean at the final stack tip.
- VM116's headless Chromium rendered the real Branchline HTTPS page. This proves
  remote browser execution, not authenticated Codex operation or desktop handoff.
- Homarr shows Branchline on the private Staging board. Pulse enrollment covers
  VM116, the web container and the managed preview containers. This does not
  monitor native Codex/runner jobs individually.

## Runtime and recovery limits

Historical Skill Circuits migrations mix table-name case. A fresh Linux MySQL
database with default case-sensitive names failed on `BOOKMARK_LIST`; the recipe
uses `lower_case_table_names=1` from initial database creation. Application source
is unchanged. This does not establish compatibility with case-sensitive
production MySQL, and the setting must never be applied to initialized data.

Skills' existing TINYINT boolean migration also conflicts with Hibernate's BIT
validation. All three relevant JDBC boolean-metadata options still returned
TINYINT in a read-only probe. Only generated Skills preview configuration sets
`ddl-auto=none`; Core retains validation and Liquibase still applies both apps'
migrations. These settings do not establish production migration compatibility.

The task operator owns the retained acceptance material:

- `staging/previews/recipe-proof` and `recipe-proof-ci`: original diagnostic
  databases, sources and exported container logs. Their four stopped containers
  were removed with the canonical scoped cleanup helper after managed acceptance.
  Images and mounted data remain. Protected recovery metadata is under
  `staging/runtime-cleanup/20261120T014247Z-896534`.
- `staging/branchline/acceptance/20261120/previews-before-history-archive.json`:
  verified complete state before archiving the 46 cancelled test records. The
  live UI now contains only the two ready examples. Their cancelled build data
  and logs remain; no volumes or databases were deleted.
- `staging/branchline-artifacts/labrador/artifacts`: verified offline dependencies
  and Core source. Manifest SHA-256 is
  `44515a25b9423d6e112db8af8d8d639fc1dade8ecbd865bde3773b4653222328`.
  The retained rebuild archive SHA-256 is
  `28b74849215fcc747ca84edae02fe0836bb22ccce601eb2ef7a7331d1b0b7ef7`.

These paths are relative to `/srv/appdata/docker`. Remove retained diagnostic
data/images only after user acceptance and a separately authorized cleanup;
preserve the artifact bundle, live preview data and Git recovery references.
At final acceptance the SSD pool had about 97 GiB available. One idle combined
application used about 1.06 GiB plus 492 MiB for MySQL; hard limits remain
2 GiB/768 MiB per application/database. This measurement is not a peak-load test.

Stable Git/queue state, artifact manifests, per-preview databases/seed markers
and the VM workspace reside under canonical appdata. Scheduled backup inclusion
does not prove a MySQL, VM116 or clean-host restore. Previous app releases,
configuration copies and NPM rollback material remain retained. The paired web,
runner and recipe release is manual; no production activation or Symphony
service is introduced. See the [preview runbook](../../hosts/staging/branchline/README.md)
and [SSH runbook](../../hosts/codex-dev/README.md) for exact install/recovery paths.
