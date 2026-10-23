# Blog observability

This candidate provides shared Umami and Grafana services on CT112, with
blog-local collection and probes on CT114. The procedures below describe the candidate implementation;
they do not establish that it is deployed or verified. Read
[status](../../../docs/status.md) for dated deployment evidence. The blog and
infrastructure candidates remain off `main` until accepted and authorized.

## Use and scope

| Private entrypoint | Purpose |
|---|---|
| [Blog](https://blog.staging.rafael.media) | Reader preview on CT114 port 8084 |
| [Umami](https://analytics.staging.rafael.media) | Page traffic, estimated visitors, referrers and explicit interactions; port 8090 |
| [Blog Grafana dashboard](https://grafana.staging.rafael.media/d/blog/blog) | Availability, TLS, monitoring health and request logs; port 8091 |

The two dashboard routes use the existing staging certificate and LAN/Tailscale
policy. No public DNS/application access is added. Collection works only where
the reader can reach the private Umami endpoint. Both dashboards require the
operator account; anonymous Grafana access and sign-up are disabled. Two-factor
authentication is not configured by this stack.

[Apps Compose](../../apps/blog-observability/compose.yaml) pins the exact migrated
images for Umami 3.4.0, its application-local PostgreSQL 17 and Grafana 13.2.4
on CT112. [Collector Compose](compose.yaml) keeps Blackbox Exporter and Alloy
on CT114. Grafana uses existing Prometheus 3.13.1 and Loki 3.7.3 in CT112. All new
containers have `wud.watch=false`; upgrades are manual. PostgreSQL is on an
internal Docker network with no published port. The blog stays a static nginx
application with no runtime secret or writable application volume.

## Configuration and credentials

[website.json](website.json) declares the staging website UUID, name and domain.
The [blog deployment](../blog/compose.yaml) injects its public website ID and
`PUBLIC_UMAMI_SCRIPT_URL` as build arguments. These are browser-visible routing
values, not credentials; changing them requires a blog rebuild. The blog owns
tracking behavior and sanitization, including route pageviews, `map-fit` and
`map-fullscreen-toggle` events. A fullscreen-toggle event counts use of that
control, not browser fullscreen API success.

[initialize.py](initialize.py) parses PVE `/root/.env` as Compose dotenv and
creates missing operator secrets: `BLOG_UMAMI_DB_PASSWORD`,
`BLOG_UMAMI_APP_SECRET`, `BLOG_UMAMI_ADMIN_PASSWORD`, and
`BLOG_GRAFANA_ADMIN_PASSWORD`. It writes only these keys into the stack's
mode-0600 `runtime.env` on CT112, preserves existing values and rejects installed-value
drift. The collector deployment on CT114 receives no operator secrets. Never print either environment file or expanded Compose configuration.

[initialize-umami.py](initialize-umami.py) first tries the configured `admin`
password. Only a rejected login leads to an attempt with the upstream seeded
account; if that succeeds, it changes the password and logs in again before
creating an absent website. An independently changed password or mismatched
website identity fails instead of being reset. The installer secures this
account before adding the private proxy routes. Grafana's initial admin password
comes from its deployment secret; changing an existing Grafana account remains
a separate operation.

Canonical Umami/Grafana state is below `/srv/appdata/docker/blog-observability`
on CT112. CT114 retains only its collector state at
`/srv/appdata/docker/staging/blog-observability/alloy`:

| Path | Owner and recovery role |
|---|---|
| `postgres/` | PostgreSQL 17 native database; guest UID 70 / host UID 100070 |
| `grafana/` | Grafana database and operator state; guest UID 472 / host UID 100472 |
| staging `alloy/` | Collector cursor/state on CT114; guest root / host UID 100000 |
| `runtime.env` | Scoped operator secrets; guest root, mode 0600 |
| `backups/` | Retained logical Umami dumps and checksums |

Existing owners are validated, never recursively repaired. Preserve the matching
PVE secrets with restored appdata. Umami retains analytics indefinitely unless
an explicit cleanup policy is implemented. Loki retains its existing 30-day
configuration; this change does not prove expiration or disk reclamation.
See [Umami retention](https://docs.umami.is/docs/faq) and
[Loki retention](https://grafana.com/docs/loki/latest/operations/storage/retention/).

## Install and recover

For clean-node recovery, follow the prerequisites and appdata selection in the
[rebuild contract](../../../docs/rebuild.md), then run the normal bootstrap.
The source initializes scoped secrets/appdata, deploys both host-specific stacks, reconciles
private routes and installs its PBS pre-hook. Preserve PostgreSQL 17 state and
credentials; do not copy a native data directory into another database major.

For an existing homelab, use a clean, committed PVE checkout of the reviewed
infrastructure candidate. First inspect CT114's `/opt/dothomelab/DEPLOYED_COMMIT`
and reconcile any newer source changes into the candidate. The installer refuses
an unexpected source revision. Set `EXPECTED_STAGING_COMMIT` only to the exact
revision whose changes were reviewed; never use it merely to bypass a mismatch.

```sh
# On PVE, from the clean reviewed checkout; inspect the scripts first.
pct exec 114 -- cat /opt/dothomelab/DEPLOYED_COMMIT
EXPECTED_STAGING_COMMIT='<reviewed-current-full-commit>' \
  bash hosts/staging/blog-observability/install.sh
```

[install.sh](install.sh) initializes only this stack's appdata, archives committed
source under `/opt/dothomelab-blog-observability/releases/<commit>` in CT110,
CT112 and CT114, and records `DEPLOYED_COMMIT` in each retained release. CT110
and CT112 keep their main `/opt/dothomelab` archives; their route/Prometheus
changes use this separate source release. CT114's complete source is replaced
under the poller's lock, retaining
`/opt/dothomelab.before-blog-observability-<commit>`. Its main marker then records
the candidate revision. The installer also retains a consistent NPM SQLite
rollback copy, configures the routes, preserves the Prometheus image/TSDB, adds
the backup hook and deploys/verifies the blog through its existing poller.
Earlier completed steps are retained if a later step fails; this is not an
automatic transactional rollback.

[Collector deploy](deploy.sh) and [Apps deploy](../../apps/blog-observability/deploy.sh)
perform quiet Compose validation before starting their respective services.
On a clean guest it establishes `/var/log/journal` as root:systemd-journal mode
2755 and flushes the journal; an existing directory is left unchanged. The
normal guest journal limit is 100 MiB, shared with other guest logs. Alloy reads
only records tagged `dothomelab-blog` and limits initial history with
`max_age="24h"`. Journal eviction can remove records sooner: this is neither
24-hour guaranteed retention nor a durable queue for a long Loki outage.

## Move an existing CT114 installation

Use the [migration helper](../../apps/blog-observability/migrate-from-staging.py)
from a clean committed PVE checkout of this candidate. Read it first. It requires
CT114 source `35fc0a46de2146bed03f63e70dd44c0f35811bc9`, the three running source
containers and an absent CT112 appdata target; it deliberately refuses to overwrite
a previous attempt. Do not run the ordinary installer first against legacy data.

```sh
python3 hosts/apps/blog-observability/migrate-from-staging.py
```

The helper fetches and verifies the same image digests before downtime, stops
Umami/Grafana, dumps PostgreSQL logically, and restores into a new database.
It compares every public table's row count and the stopped Grafana SQLite table
counts/integrity before starting the target. Authenticated login, dashboard,
datasource and blog monitoring checks precede the route switch. The two existing
URLs, website UUID, accounts and secrets stay unchanged. No blog rebuild,
Prometheus restart or collector restart is needed.

Original databases, Grafana state, scoped environment and earlier dumps move to
`/srv/appdata/docker/blog-observability/rollback-<UTC>/staging-state`, outside
CT114's data mount. The three stopped source containers are removed without
volume deletion. The migration's fresh logical dump, checksums and count manifests
remain alongside that state. Only Alloy's cursor stays under staging.

Failures before route cutover stop the target and restart the original services.
After routing begins, the helper stops on error for explicit recovery: automatically
reverting could discard new events or dashboard edits. Inspect `migration.json`.
For a rollback, first stop target writers, preserve their new data with a logical
dump and stopped Grafana copy, then restore the retained original directories to
their original paths and recreate the original CT114 services from their retained
source releases/images. Repoint only the two dashboard routes to `.114`, validate
nginx and restore the CT114 backup hook. Restore the earlier CT114 source archive
under the staging deployment lock. Do not restore the entire NPM database over
later changes, delete any database, or assume original state contains post-cutover
writes. A failed partial attempt requires inspection before another run.

## Checks and their limits

After deployment, read [verify.py](verify.py), then run it from PVE:

```sh
pct exec 112 -- python3 /opt/dothomelab-blog-observability/current/hosts/staging/blog-observability/verify.py
```

It checks the Umami identity and reports stored path counts, checks Grafana/data
sources, expected probes/scrapes and rule health, then generates one harmless
missing-path request and waits for its sanitized 404 record in Loki. That request
adds a log record; the command does not replace the real-browser acceptance below.

| Check | What it establishes |
|---|---|
| Quiet Compose, container health, Umami heartbeat, Grafana health and Alloy readiness | Configuration/startup readiness; not readership or log delivery |
| Real browser home → article → note → back/forward → reload, followed by authenticated Umami readback | Persisted per-path counts, one initial view and expected SPA transitions; check repeat views, estimated visitors and referrer redaction |
| Fit/fullscreen-toggle activation followed by Umami event readback | Explicit interaction count and source path; mocks alone do not prove collection |
| HTTPS probes of home, about, the Machine and Deep Learning article, and feed | Every 30 seconds: expected 200, trusted TLS, no redirect and a route-specific body marker |
| Direct origin homepage probe | Separates some origin faults from proxy/DNS/TLS faults; no TLS on this internal target |
| Missing-path request during acceptance | Actual 404 behavior; no recurring missing-path probe is configured |
| `up` and `probe_success` | `up` is Prometheus scrape success; only `probe_success` describes the configured endpoint check |
| Fresh harmless request retrieved from Loki and Grafana | Actual nginx → journal → Alloy → Loki delivery with expected labels and sanitized fields |

Browser checks must inspect persisted analytics, query/fragment redaction,
disabled tracking and DNT behavior. Umami visitor IDs are estimates; blocked or
disabled JavaScript is absent. Internal navigation may not make a document
request, so browser pageviews and origin request totals should differ.
See [Umami metrics](https://docs.umami.is/docs/metric-definitions) and
[Prometheus scrape semantics](https://prometheus.io/docs/concepts/jobs_instances/).

[config.alloy](config.alloy) forwards only the access JSON allowlist: timestamp,
method, sanitized path, status, bytes, duration and synthetic-traffic flag. It
drops malformed records and raw nginx error lines, which may contain request
secrets. The dashboard excludes marked health/probe traffic from request totals;
remaining requests can still include assets and bots and are not people. Loki
labels are bounded to source/environment; request paths are parsed fields.
Inspect delivered records, retry/drop counters and query freshness: Alloy's
healthy component state alone does not prove delivery.
Source: [Alloy writer health and metrics](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.write/).

[alerts.yml](alerts.yml) declares failed endpoint/scrape, missing probe,
certificate-expiry and dropped-log rules. Grafana displays firing rules, but no
notification receiver is configured: email/chat/push delivery is not provided.
Probes originate in CT114; there is no external outage vantage, browser-rendering
probe, node exporter or container resource exporter. Grafana panels cover
sampled availability/TLS/duration and received request/status/latency data, not
CPU, RAM, GPU performance or complete internet reachability.

## Backups and rollback

The PVE hook `/etc/dothomelab/backup-pre.d/70-blog-umami-database` enters CT112
and runs [backup-database.sh](backup-database.sh) before the scheduled appdata
snapshot. It creates a PostgreSQL custom-format dump in a new timestamped
`backups/` directory, checks `pg_restore --list`, writes a SHA-256 sidecar and
advances `latest`. Older directories are retained. Archive listing proves that
the table of contents is readable, not that a restore or application recovery
works. The hook is part of [PBS appdata protection](../../../backup/pbs/README.md);
routine dashboard changes do not justify starting another backup job.

Restore testing must use an isolated PostgreSQL 17 instance, import the logical
dump, compare website/event data and exercise a private restored Umami login and
query. The relocation helper performs these checks against the initially empty
CT112 target before routing users to it; a separate disaster-recovery drill is
still outside this procedure. Preserve
current data and dumps throughout recovery; do not run `down -v`, delete volumes
or overwrite live database directories. Major-version updates require their
own logical-dump, isolated-restore and rollback plan.

A blog-only rollback can use the retained prior image or a revert on `staging`;
an older build without tracking leaves existing collector data intact. Rebuild
with analytics disabled to stop collection deliberately. Infrastructure rollback
uses the retained source/configuration and compatible images, after reviewing
database migrations. Reverting code does not undo a schema change. Keep all
source releases, database generations, logical dumps and images until an
explicitly authorized cleanup; restoring the whole NPM database could overwrite
later unrelated route changes and requires separate review.
