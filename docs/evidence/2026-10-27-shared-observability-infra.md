# Shared observability on Infra — 2026-10-27

The existing Umami, its application-local PostgreSQL 17, Grafana, Prometheus,
Loki and Blackbox now run once on CT110. CT114 and CT115 retain only their local
Alloy collectors for sanitized blog access logs. Existing data and website IDs
were retained. The public blog container remains the October 26 release
`8e2fcec638e48a9866a985647188f4cb626bb234`, started at 20:36:55 UTC; only its
existing collection proxy changed upstream.

## Delivery and user workflow

Infrastructure implementation `d3615844` follows `codex/blog-production-activation`
through the retained review branch. The blog integration/documentation follows
`staging`, with `87134da2` providing the checked runtime and `c7641354` recording
acceptance/test updates. No `main` promotion or production application release
was performed. CT110/112 retain source `d3615844`; CT114/115 retain the migration
source `a6f9e2ce`, whose local collector/blog integration files are unchanged by
the later central-only fixes. The PVE fleet timer uses immutable `d3615844`.
A subsequent CT114 archive refresh respected an active application deployment
lock and was not forced; the matching local integration was already installed.
At 09:55 UTC the preview's current release was exactly `c7641354`. Concurrent
blog work subsequently advanced its staging branch separately.

Final checks confirmed all 34 endpoint probes passing, no failed scrapes,
all 13 alert rules healthy/inactive, the unknown-state panel installed and one
explicitly unknown Immich resource. The [shared runbook](../../hosts/infra/observability/README.md)
owns configuration, updates, retention, enrollment and rollback; the
[user manual](../../USER_DOC.md#administer-the-homelab) explains the beginner workflow.

- Private administration uses `analytics.rafael.media` and `grafana.rafael.media`;
  the previous `.staging` aliases remain. Prometheus and Loki retain their names.
- Grafana Homelab has Project, Environment, Guest and Service selectors. Blog
  has an Environment selector; the old production dashboard bookmark remains.
- Umami has separate staging/production websites with the original IDs and
  operator account. The staging build now uses its same-origin telemetry route.
- Grafana and Umami have managed tiles on Homarr's dashboard, Admin and
  HomeAssistant boards. Existing Prometheus/Loki health URLs now point to CT110.
- Pulse supplies allowlisted resource measurements through a one-minute PVE
  exporter and the central Alloy. No extra agent was added to each guest.
  Docker runtime state overrides misleading Pulse discovery status for stopped
  containers; stale/missing resource readings are absent rather than zero.
- Loki receives sanitized blog requests and allowlisted fleet state transitions.
  Other applications' arbitrary raw logs are not collected automatically.

## Verification

Observed between 09:28 and 09:45 UTC through PVE SSH and `pct exec`:

- Umami authenticated API access and expanded page aggregates; Grafana's three
  dashboard UIDs/selectors and both datasource health checks passed.
- Five staging and five production content/status/TLS/origin probes, plus 24
  declared shared endpoint checks, were observed passing. All scrapes were up;
  all 13 alert rules evaluated successfully. Generic 401/403 reachability checks
  do not prove authenticated application workflows.
- A unique staging HTTPS 404 reached Loki with its path intact, its query removed
  and only the seven declared fields. Production logs continued arriving.
- Pre-move Prometheus history still returned the original ten probes at
  Unix time `1793090467`. Pre-move staging and production Loki records remained
  queryable. Umami retained staging history from October 22 and production history
  from October 26.
- Live Chromium staging acceptance passed: eight pageviews (initial, client,
  Back/Forward, reload, article, standalone index and note), two map-button events,
  zero DNT/blocked collections and no query/fragment payloads. Read-only SQL for
  09:33–09:34 UTC confirmed exactly eight pageviews and one of each button event.
- Chromium on the unchanged public blog recorded Home/About collection responses;
  read-only SQL confirmed two production pageviews in 09:35:42–09:35:52 UTC.
- Pulse's verifier passed for PVE, all six LXCs and Docker agents on
  CT102/110/112/114/115. Homarr's two new apps, six tiles and layout placement were
  checked. Reconciliation passed twice against a memory-only database copy
  before applying with a fresh SQLite backup.
- Real promtool configuration and both alert-test suites, Loki validation, three
  Alloy configurations and Blackbox validation passed. Nine focused observability
  unit tests, ten production tests, three route tests and 33 staging tests passed;
  docs/whitespace and applicable PVE shell syntax checks passed.

At 09:38 UTC the seven central containers used about 760 MiB combined. CT110's
cgroup used about 2.96 GiB of its existing 4 GiB allocation including cache and
other workloads. This is a point-in-time observation, not a load test. Prometheus
uses host port 9092 because Cockpit already owns 9090. Blackbox binds only the
Infra LAN address using host networking so NPM's private ACL remains effective.

The cutover exposed two detached Docker bridge interfaces, repaired by restarting
only the affected Umami/fleet containers. Subsequent recreated interfaces and
end-to-end ingestion passed. An obsolete staging article target was updated to
its current canonical path. Old series/alerts remained visible for Prometheus's
lookback window before expiring; their history was not deleted.

One pre-existing Docker API inconsistency remains: CT112's Immich machine-learning
container is listed running/healthy, while inspection of the same ID reports
exited/unhealthy with an October 17 finish. Pulse combines these contradictory
fields. The exporter marks that resource **unknown** and omits untrustworthy
health/usage values; Grafana shows an unknown-state count. No Immich service or
Docker daemon was restarted to address this separate underlying issue.

## Data protection and limits

The migration logically dumped/restored Umami and compared all 27 public tables.
Grafana's stopped SQLite copy passed integrity and counts across 92 tables.
Stopped Prometheus/Loki copies compared byte-for-byte before the original canonical
directories were handed to CT110. No original application data was removed.

Rollback is retained at
`/srv/appdata/docker/observability/rollback-20261027T085235Z`; its journal records
completed cutover. Earlier failed targets were moved into their own retained
rollback directories. Old Umami/Grafana state remains under `blog-observability`.
All five former central CT112 containers and the two former local Blackbox
containers are stopped with restart disabled. They consume retained disk space,
not a second running service allocation.

Guest source archives and the scoped NPM route/SQLite backups remain under their
recorded `before-shared-observability-*` and `observability-route-before-*` paths.
Homarr retains `db.sqlite.pre-managed-20261027T093404.2874645`. The PBS pre-backup
hook now dumps CT110's `umami-db`; its logical archive listing/checksum passed.
No full PBS restore, host rebuild, WAN uptime monitor, notification delivery,
physical-phone check or load test was performed.

Analytics collection was interrupted during cutover and network repair, roughly
08:53–09:28 UTC. The public site's content kept serving. Historical stored events
were verified; browser events that failed during the interruption cannot be
reconstructed. Rollback after cutover must preserve/reconcile new database writes;
simply restarting the old database would discard those newer observations.

## Retained working copies

The canonical repositories keep the delivered review branches. Concurrent work is
preserved in named recovery refs, including
`codex/recovery-observability-20261027-final-consolidation` in dothomelab and
`codex/recovery-observability-20261027-blog-consolidation` in blog. Compare a needed
file with `git show REF:path`, then restore only that reviewed path with
`git restore --source REF -- path`; do not overwrite newer author changes.
Task-owned temporary worktrees are removed after refs, consumers and canonical
copies are verified. Unrelated active worktrees and retained rollback data remain.
