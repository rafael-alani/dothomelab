# SSD project production scaffold — October 25, 2026

## Delivered state

Observed on PVE `afa` and CT110/112/114/115, Europe/Amsterdam. Infrastructure
implementation `4c2d1e035f0c715121c64a8cad0df422218e2f26` is published on
`origin/codex/production-scaffold`. The final documentation commit follows this
implementation; the canonical Mac/PVE checkouts and installed source archives
are synchronized to that retained review revision.

CT115 `production` is running at `192.168.0.115` with 4 shared CPUs, 4096 MiB
RAM, 512 MiB swap, an unprivileged Debian 12 guest and a 64 GiB `local-zfs`
root quota. `rpool` is on the Samsung SSD 980 NVMe. Canonical production appdata
is `/srv/appdata/docker/production` on `rpool/appdata/docker`, the only guest
bind. Initial SSD free space was approximately 364 GiB; the quota is not a
reservation. The existing CT102/110/112 64/64/192 GiB disk quotas were preserved
from live state and the prior PVE release; no existing guest disk was resized.

Docker and the Pulse host/Docker agent are installed. The final `docker ps` was
empty, with no blog/collector listener or deployment timer. Pulse's readiness
logic now supports deliberately empty guests and checks only the requested
guest's required application containers. No shared `.env`, media, staging
appdata, hardware or remote Docker API reaches CT115.

The apex NPM row remains ID 1, `rafael.ink` → `localhost:8888`, enabled, using
certificate 5. That certificate covers both `*.rafael.ink` and the apex. No
public routing, DNS or router change was made. The blog is **not published**.

## Main and publication gate

The private blog repository has no remote `main`. The existing local historical
`main` lacks a Dockerfile. The production read-only key was registered as
GitHub deploy key `167643488` (`blog-production-ct115-readonly`); authenticated
`ls-remote` succeeded and returned staging `322ab85706237a87e6f204ac281d018bbe067338`
but no main. The production `--prepare` command refused missing main before
building or starting anything; it never used staging as a fallback.

The blog's staging revision above contains the new AGENTS/operations policy
and is deployed privately on CT114. Production promotion remains a separate
acceptance/authorization step. Both repositories' AGENTS and the local
`/Users/rafael/Repos/AGENTS.md` require an explicit production request in the
active prompt, separate environment data/credentials/statistics, and reporting
missing live dependencies. Main pushes do not trigger production deployment.

The final command, **only after an accepted revision exists on origin/main and
publication is wanted**, is:

```sh
ssh root@192.168.0.250 'cd /root/dothomelab && hosts/production/activate.sh blog --publish-rafael-ink'
```

It builds the main revision with the apex origin, production analytics identity
and published-only content, checks origin/container health, starts scoped
collectors and switches the existing apex route. It exposes only the public
Umami script/send paths under `/telemetry`; dashboard/admin access stays private.
That command was not executed during this task.

## Content and telemetry separation

The verified source export belongs to host UID 101000; production release files
belong to guest root, host UID 100000. The helper reads the source as PVE root
and sets the new destination files' ownership individually. Existing staging
and production trees are never recursively repaired. The retained production
content digest is `2be6be95e8cb9160dc894ad79b6dea3e2ee4497035bd46d64beb1808764b2eab`.
It has zero published vault articles, no preview subtree and no draft identities
in its manifest/history. Repository-owned public content is a separate input.
The private staging listening/music mount is not included.

The existing CT112 Umami, Grafana, Prometheus and Loki services are reachable
from CT115. Production has its own Umami website
`88d95afd-ff71-4f64-93ea-e57310dd952b` for `rafael.ink`, while staging retains
`a3417da8-b984-49df-9e5b-88ecb9b2f6da`. Both identities were read back through the
authenticated API. Grafana retains staging UID `blog` and adds `blog-production`;
its Prometheus and Loki datasource health checks both passed.

Production Prometheus jobs, alerts and Loki selectors are separate and include
project/environment identity. Production file-discovery lists are empty, with
no production `up` series or alerts. Nine rules evaluate successfully: five
staging rules and four production rules. No production analytics events or logs
were generated to simulate acceptance.

Three pre-existing staging probes matched obsolete homepage/about copy despite
HTTP 200. Both environments now use their exact canonical URLs for those
checks. Only staging Blackbox was recreated; Alloy and application containers
were not redeployed by that monitoring step. Final observations: five staging
probes and seven staging scrape targets all reported 1. The normal staging
poller separately accepted the blog's documentation-only release.

## Checks and limits

- Nine production regression tests passed: main-only policy, missing/changed
  main, interrupted activation, failed-health rollback, published input filtering,
  telemetry separation, empty Pulse guests, and Umami's null missing-site response.
- Existing staging deployment (9), editorial (4), and environment (3) tests passed.
- Shell syntax, Python compilation, documentation links and whitespace passed.
- PVE production dry-run and live identity/mount/Docker/backup/dependency verifier
  passed. Both production Compose definitions passed quiet validation.
- Prometheus config and production alert tests passed. A staging failure does
  not trigger the production endpoint alert; dormant production has no alert.
- Alloy validation and Blackbox config validation passed in disposable offline
  containers. The candidate telemetry nginx config passed standalone `nginx -t`,
  without reload or public route change.
- Production Git access, separate Umami identities/dashboards, both Grafana
  datasource checks, final staging probe/scrape/rule checks, published content
  checksums and empty production runtime were verified live.

The scheduled appdata backup had succeeded at 02:24:40 CEST before this work.
CT115 now joins its freeze list and production data lies inside the protected
SSD dataset. No backup containing the newly created state was started or
verified; no clean-guest restore was performed. No public production image,
browser journey, log ingestion, analytics event collection or WAN cutover was
verified because publication was deliberately withheld.

Missing capabilities: no notification receiver and no external uptime observer
are configured. Dashboard rule state is not delivered alerting or proof of
Internet reachability. The absent blog main branch blocks activation; all four
declared shared service dependencies exist and respond.

## Retention and rollback

Canonical Mac checkout: `/Users/rafael/Repos/dothomelab`, review branch
`codex/production-scaffold`. Canonical PVE checkout: `/root/dothomelab`, same
branch. No temporary task worktree was created. Existing worktrees belong to
other work and were preserved.

The pre-existing, uncommitted Krita research and its index edit remain unchanged
locally and were also saved at local branch
`recovery/pre-production-scaffold-20261025`. To recover those two files use
`git restore --source recovery/pre-production-scaffold-20261025 -- docs/evidence/README.md docs/evidence/2026-10-25-blog-krita-svg-authoring.md`
after preserving any newer edits. This draft is not included in the production
review commits. PVE has its own same-named recovery branch at
`7156d76f37bb498ad16f82a50fcff87751ef5076`; its older disk-headroom change is also
retained on `origin/codex/lxc-root-headroom`.

Guest helper archives are retained under `/opt/dothomelab-production/releases/`;
CT115's `/opt/dothomelab/DEPLOYED_COMMIT` identifies its installed source. Shared
Prometheus/staging Blackbox use the checked implementation archive; subsequent
documentation-only archive synchronization does not require a service restart.
Prior observability source archives and data remain available. Production
publication will create a focused NPM rollback record; none was needed for a
route change during this scaffold. Empty guest/data removal and rollback-asset
cleanup require a separate authorized task. See the [runbook](../../hosts/production/README.md).

## First production activation — October 26, 2026

Rafael promoted the accepted blog revision
`8e2fcec638e48a9866a985647188f4cb626bb234` to remote `main` and ran the explicit
publication command. It stopped before building because PVE had advanced to
`c58f53148bf0cbdb2c55e46c75f0a7571e97d1ea` for the About publisher, while the
unchanged production archives still recorded `82efd415`.

The repair on `codex/blog-production-activation` compares production runtime
paths and their shared imports against each installed source revision. It permits
unrelated service/documentation commits and still rejects unknown revisions,
committed runtime drift and dirty runtime changes. A fixture Git repository
reproduced the original failure through the extracted guard before the fix;
all ten production tests pass afterward. Shell syntax, whitespace and documentation
checks pass. The first main fetch also exceeded the original two-minute limit;
the fetch now has the same 30-minute allowance as the other build commands.
The blog repository has approximately 858 MiB of packed Git objects locally.

The prior PVE checkout is retained at
`recovery/before-production-activation-20261026`. CT115's original source tree
is retained at `/opt/dothomelab.production-before-82efd415a6b1727259e994be7cb364e8962fc47a`,
alongside its earlier `/opt/dothomelab.previous`. The new `/opt/dothomelab`
symlink and CT110/112 helper symlinks select immutable versioned archives;
all previous archives remain. CT114's application and source were unchanged.
The existing local Krita draft and index changes remain outside these commits.

Preflight confirmed all four declared dependencies, SSD placement/narrow mounts,
336 GiB SSD space and the scheduled appdata backup's successful October 26
02:23:23 CET completion. No on-demand backup or restore was performed.
Cloudflare's public apex returned HTTP 525 before activation: NPM's apex row
existed but its generated `proxy_host/1.conf` was absent, and direct origin TLS
rejected that server name. The normal publication renderer recreates that route;
no Cloudflare record, TLS mode, router or shared credential change is needed.

### Published release and acceptance

Activation completed with platform
`fc039780a6af6789258096a1aba17c71e176b24d`, app revision
`8e2fcec638e48a9866a985647188f4cb626bb234`, release
`1793046895893988368-8e2fcec638e4` and published-only editorial digest
`9f26b518183e7b25ed22d362550142b01f879fcf8a7832b2bbd35717688f0a28`.
CT115 `current.json` and the running container's commit label agree. Image
configuration/health and quiet Compose validation passed, then Alloy/Blackbox
started and the normal NPM renderer published apex row 1 to `192.168.0.115:8084`.
The integrity-checked prior SQLite/route copy is retained at
`/srv/appdata/docker/infra-nginx-proxy-manager/production-route-before-1793047027538929772`.
The previous route had no generated config, so restoring its fields alone would
restore the prior placeholder configuration, not establish a previously healthy
site. No live route rollback or guest restore was attempted.

- Public HTTPS through Cloudflare returned 200 with `x-robots-tag: all`; About's
  canonical URL is `https://rafael.ink/about`. Activation also checked home,
  About, feed, sitemap and the tracker through NPM with normal TLS verification.
- A browser loaded Home and navigated through the menu to the expected
  heading-only About page. Production Umami's authenticated API recorded one
  pageview for each route under its own website ID. This is a focused browser
  smoke check, not a new full interaction suite or physical-phone acceptance.
- Production's five endpoint probes, seven scrapes and four alert rules passed.
  Staging's five probes/seven scrapes remained healthy, with distinct environment
  labels. The production Grafana dashboard and both datasource health checks passed.
- A unique 404 request through NPM reached Loki with only the seven allowed
  fields, its query string removed, and `project=blog,environment=production`.
  The same request was absent from staging's log stream. The initial Python
  request through Cloudflare received 403; direct NPM TLS was used for this
  log-specific probe. Separate public curl and browser checks through Cloudflare
  succeeded, including a missing page returning 404.
- `/listening/manifest.json` and `/telemetry/api/websites` returned public 404.
  Private staging media and Umami administration are not exposed by these paths.

Build output reported 17 npm dependency advisories (6 moderate, 11 high).
Dependencies were not upgraded or audited for runtime exploitability as part of
the scaffold repair; the accepted static application revision was preserved.
Alert notification delivery and an independent external uptime observer remain
unconfigured. No new backup, restore, live rollback, broad UI suite or physical
phone test was claimed. Production remains manually released; pushing main does
not trigger another deployment.
