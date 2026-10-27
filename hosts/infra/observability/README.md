# Shared observability on Infra

One Umami, Grafana, Prometheus, Loki and Blackbox instance run on CT110. Umami
has its own PostgreSQL 17 database. CT114/CT115 each retain one small Alloy
collector for local sanitized blog journals; these are not duplicate stores.
Prometheus listens on host port 9092 (container port 9090); Cockpit retains host
port 9090. Blackbox uses host networking, bound only to `192.168.0.110:9115`,
so private NPM routes see the Infra LAN address. Images stay at the existing versions and are manually updated.

| Open privately on LAN/Tailscale | Purpose |
|---|---|
| [Umami](https://analytics.rafael.media) | Website readership; select a website/environment |
| [Homelab dashboard](https://grafana.rafael.media/d/homelab/homelab) | Filter resource metrics, endpoint checks and available logs |
| [Blog dashboard](https://grafana.rafael.media/d/blog/blog) | Select staging or production; HTTP availability, latency, errors and logs |
| [Prometheus](https://prometheus.rafael.media) | Inspect targets, rules and numeric queries |
| [Loki readiness](https://loki.rafael.media/ready) | Service health; query logs in Grafana Explore |

The old analytics/grafana `.staging` URLs remain private compatibility aliases.
The production dashboard UID `blog-production` remains a bookmark. No new
public administration route is created. Existing operator credentials are
preserved in PVE `/root/.env` and injected only into the central services through
mode-0600 `runtime.env`; never copy them into application settings or browsers.

## Collection and filters

Pulse already collects PVE, LXC, VM and Docker resource measurements. The PVE
`dothomelab-observability-fleet.timer` exports an allowlist every minute;
[collect-fleet.py](collect-fleet.py) exports CPU, memory, available disk/I/O,
online/health and freshness values. CT110 Alloy reads the textfile every 30s
and sends it to Prometheus. Missing/stale measurements remain absent; freshness
expires after three minutes. Guest metrics use Proxmox's guest measurements,
not the misleading host-wide memory sometimes seen by an in-container agent.

Select **Project → Environment → Guest → Service** in Homelab. Environment is
`infra`, `staging`, or `production`. Labels also include `host`, `guest_id`,
`resource` and `resource_type`. Names come from an explicit allowlist of Compose
metadata; arbitrary container labels, commands, environment and secrets are not
exported. CPU/memory charts are resource usage, not application performance.

Loki receives fleet state changes (`log_type="resource_state"`) and the blog's
sanitized access records (`log_type="access"`). It does not automatically ingest
all applications' raw logs. Blog access records omit IPs, query strings, cookies,
user agents and referrers. Old records retain their original labels; use the
Blog dashboard or `service_name`/`environment` to include pre-migration history.

[targets.json](targets.json) declares shared HTTPS checks. `https_reachable`
accepts successful responses and authentication challenges (401/403); this
establishes reachability, not a working authenticated journey. Blog checks have
stronger page/body/TLS assertions in [blackbox.yml](blackbox.yml). All checks run
inside the homelab and cannot establish external Internet reachability.

Alerts evaluate in Prometheus; **no notification receiver is configured**.
Prometheus retains 30 days or 20 GB, whichever limit is reached first. Loki
retains 30 days; its filesystem has no configured hard size cap. Umami history
is kept until explicitly managed. Monitor free disk space and freshness.

## Add another service

1. Reuse this stack. Give an application an explicit deployment project and
   environment; ordinary Compose resources already appear through Pulse.
2. Add a public/private health URL and the same project/service labels to
   `targets.json`. Select an appropriate shared Blackbox module; verify the
   actual authenticated workflow separately where required.
3. For application logs, declare a narrow source and allowlisted record schema,
   add a local Alloy source with matching labels, then send one test event and
   retrieve it in Loki. Do not ship raw logs containing users' tokens or content.
4. For browser analytics, create a separate Umami website for each application
   and environment. Inject its public ID and a collection URL through the app's
   portable deployment contract. No application gets the Umami administrator key.
5. Validate, deploy the affected configuration, and verify the dashboard filters
   and stored observations. Dashboard selection is a viewing filter, not an
   access-control boundary between untrusted users.

## Deploy and verify

Clean bootstrap initializes the shared state and starts these services on Infra.
The one-time existing CT112 installation uses [migrate-to-infra.py](migrate-to-infra.py),
from a clean committed PVE checkout. It refuses unexpected guest source revisions,
an initialized target, image drift, missing originals and noncanonical mounts.
Do not rerun it after a partial cutover; inspect the recorded migration phase.
For an interruption at `switching-routes`, [finish-cutover.py](finish-cutover.py)
accepts the recorded rollback directory, checks stopped originals/running targets,
and completes routes and source registration without touching migrated data.

For subsequent configuration updates, use a committed retained source archive:

```sh
# CT110, from that archive. Preserve the current activation state.
python3 hosts/production/observability/configure.py --files-only
bash hosts/infra/observability/validate.sh
bash hosts/infra/observability/deploy.sh
python3 hosts/infra/observability/configure-routes.py
python3 hosts/infra/observability/verify.py
```

`deploy.sh` starts the shared Compose project; changed Prometheus/Loki definitions
also need their own quiet-validated Compose deployment. `validate.sh` runs real
promtool, Loki, Alloy and Blackbox configuration checks. `verify.py` reads the
accounts/dashboards/metrics and emits one harmless unique staging 404 request to
prove sanitized log ingestion. Browser analytics acceptance and backend count
verification are separate checks. Reinstall the PVE fleet timer with
`install-source.sh` when its collector changes. It retains an immutable Git
archive independently of an operator checkout.

## Data, backups and rollback

Canonical central state is `/srv/appdata/docker/observability/{postgres,grafana,alloy,fleet}`;
Prometheus and Loki retain their existing sibling directories. Both source and
destination guests use the same unprivileged UID mapping. Never recursively
change owners or run simultaneous writers against a database directory.

The migration stops Umami, takes a logical dump, restores into a fresh isolated
PostgreSQL instance and compares every public table's row count. Grafana is
copied while stopped and checked with SQLite integrity/table counts. Prometheus
and Loki are stopped, copied and compared byte-for-byte before handing the same
canonical directories to CT110. Exact source image digests are checked.

Rollback material lives in `observability/rollback-<UTC>/`; the old Umami/Grafana
data remain under `blog-observability`, and old containers are stopped with
restart disabled. Previous guest source directories and an NPM SQLite backup
plus selected route rows are retained. No original volumes or data are deleted.
Before proxy cutover failure restarts the source. After cutover, first preserve
new writes and reconcile data: simply restarting the old Umami database would
lose new analytics. Never restore the whole NPM database over unrelated later
route edits. Restore only reviewed rows and render/test/reload NPM.

The existing PBS pre-backup hook now dumps `umami-db` on CT110 using
[backup-database.sh](backup-database.sh); its archive listing check is not a
restore test. Scheduled appdata protection covers the canonical stores. The
migration's tested restore does not establish a full disaster-recovery drill.

## Note readership

In Umami, select **The Night Archive — staging**, then Events → Properties.
`map-note-visible` counts a readable note intersecting the actual browser/map
viewport; overview cards and the renderer's offscreen preload margin do not count.
Multiple cards for the same note count once. `map-note-focus`, `map-note-activate`
and `map-note-open` distinguish picker selection, double-click activation and
opening a standalone note. Properties contain the collection and website note URL,
never raw vault paths, note bodies, credentials or persistent reader identifiers.

`map-note-time` records incremental visible/active milliseconds every 15 seconds
and when leaving a note. Active time pauses after 30 seconds without input;
both timers pause when the document is hidden. `map-note-session` records a
completed visible episode. Visibility is sampled once per second; brief exposure
may be missed, and overlapping readable notes can accrue simultaneous time.
These are attention estimates, not proof of reading. DNT and blocked tracking
still apply. Closing/crashing a browser can lose its last interval or completed
episode; historical time cannot be reconstructed.

Run on the operator Mac for combined counts, totals, and mean/median completed
visible episodes (seconds), grouped by readable note URL:

```sh
python3 hosts/infra/observability/note-readership.py --days 7
```

The report uses a read-only SQL transaction through PVE/CT110 and emits CSV.
`--sql` prints the aggregate query; `--website UUID` selects another explicitly
configured website. Umami's Properties UI exposes raw event breakdowns; the
report computes the combined statistics. Existing Grafana operational panels
remain availability/request metrics, not these readership aggregates.
