# Blog analytics and monitoring — 2026-10-23

Verified from the operator Mac and PVE/CT110/112/114 during October 22–23,
Europe/Amsterdam. This is a private staging candidate, not approval to promote
the blog or infrastructure to `main`. [Runbook](../../hosts/staging/blog-observability/README.md).

## Installed source and scope

- Blog preview: https://blog.staging.rafael.media, source
  `eac3c8971ece0847020189c006f55dc02e96fe92` from `rafael-alani/blog:staging`.
  It contains application change `1c36058` and its cited research.
- Infrastructure initial installation: `deb69f8d75eca86fc273734297360c909faf289e`.
  Grafana percentile correction:
  `0e570c3b6b203b570d5bb4f0f8eb3fbb3afa7ace` on `codex/blog-observability`.
  CT114's source archive also receives the final documentation/verifier revision;
  that revision does not change these running service configurations.
- CT114 now runs Umami 3.4.0, its own PostgreSQL 17, Grafana 13.2.4,
  Blackbox Exporter 0.29.1 and Alloy 1.21.1. Existing CT112 Prometheus 3.13.1
  and Loki 3.7.3 are reused; neither image/version nor existing stored data changed.
- The observed CT114 source base was `c86e422`; live registry, deployer and
  environment initializer hashes matched that base before installing. Other
  application definitions and deployments were preserved.
- CT110/112 received separate immutable source releases under
  `/opt/dothomelab-blog-observability/releases/`. Their original
  `/opt/dothomelab` archive markers were not relabeled. Prometheus mounts the
  new declared configuration/rules from the initial release; Grafana mounts
  its corrected dashboard from the second release.

## Readership evidence

The tracker is optional and default-off in portable application builds. Deployment
supplies the staging script origin and public website UUID. React route tracking
has one owner with automatic pageviews disabled: pinned Umami source does not
implement the Back/Forward listener claimed by its SPA guide. Standalone generated
note pages use their own normal document tracker.

Two controlled browser sequences produced these **persisted** counts. The first
sequence recorded all events, then its test locator encountered multiple valid
note headings. The selector was narrowed; a second complete run passed, including
DNT and blocked-tracker contexts. The test-only correction is `1798b11` on the
application feature branch; the deployed product remains `eac3c89`.

| Page | Views | Estimated visitors |
|---|---:|---:|
| `/` | 4 | 1 |
| `/about` | 6 | 1 |
| Machine and Deep Learning article | 2 | 1 |
| Generated note index | 2 | 1 |
| Standalone note `87bdff7efabd3ee7.html` | 2 | 1 |

The authenticated Umami aggregate API reported **16 pageviews, 1 visitor and
1 visit**; its expanded page API matched the table. The ordinary ranked `path`
metric defaults to visitor counts, so the verifier uses `metrics/expanded` to
avoid mislabeling those as views. PostgreSQL independently contained 20 event
rows: 16 views and two each of `map-fit` and `map-fullscreen-toggle`. These are
control uses, not reading completion or successful browser fullscreen API calls.

Each complete sequence exercised initial load, client navigation, Back, Forward,
reload, article, note index and standalone note. The shared Canvas mounted once.
All ten collection requests in the complete sequence returned 2xx, and backend
readback established actual storage rather than relying on HTTP success.
Controlled `example.org` referral metadata appeared in the referrer report.
All captured page/referrer URLs excluded query/fragment components; all 20 stored
events had no nonempty URL query. With DNT enabled, the real tracker loaded but
sent zero collections. With the tracker blocked, reading/navigation still worked
and sent zero collections.

This measures the controlled staging fixture. Visitor estimates are not a count
of unique people; blockers, disabled JavaScript and failed delivery omit traffic.
The fixture's short duration does not establish real readership, engagement time
or browser performance. The [application research](https://github.com/rafael-alani/blog/blob/codex/obsidian-mind-map/docs/research/2026-10-22-blog-observability.md)
contains primary-source citations and version-specific limits.

## Technical checks and logs

- Five live probes passed: HTTPS home, about, article and Atom feed, plus the
  direct HTTP origin homepage. They check status, route-specific content and
  trusted TLS where applicable every 30 seconds; they do not execute browser JS.
- Seven blog monitoring scrapes were up; the existing Prometheus and Loki
  scrapes remained up. `up` means scrape success, while `probe_success` is
  the endpoint result.
- All five alert rules evaluated successfully and were inactive. Unit scenarios
  covered failure, pending/firing/recovery, scrape failure versus endpoint failure,
  removed targets, certificate timing and dropped delivery entries.
- Grafana loaded the Blog dashboard and both exact datasource UIDs. Both datasource
  health checks passed and all 19 panel expressions executed. The p95 query was
  corrected to aggregate parsed fields with `by ()`; the installed panel returned
  one series (about 0.016 seconds in the checked window), not one per timestamp.
- Fresh harmless HTTPS missing paths returned 404 and were retrieved from Loki.
  Original paths survived nginx's internal 404 rewrite; the test query string was
  absent. Records contained only timestamp, method, path, status, bytes,
  request duration and synthetic classification. IPs, cookies, raw agents and
  referrers are not in this access-log schema. Raw nginx error lines are dropped.
- Actual Alloy image tests retained the seven allowed fields and removed an
  extra cookie field and non-JSON errors. The live journal-to-Loki path delivered
  new blog requests; retry/drop counters were zero at inspection. Only blog-tagged
  journal messages are shipped. The read-only mount still exposes the guest
  journal directory to Alloy, not just filtered entries.
- Blog healthchecks and blackbox probes are marked synthetic and excluded from
  ordinary request panels. Other server requests still include assets and bots;
  they are not browser pageviews or human visitors.

No notification receiver is configured: rules appear in Prometheus/Grafana but
do not deliver email/chat/push alerts. Probes run inside CT114; host power/WAN
failure has no independent external observer. No new node/container resource
exporter was installed. No continuous rendered-browser check is claimed.

## Access, storage and recovery limits

Private [Umami](https://analytics.staging.rafael.media) and
[Grafana](https://grafana.staging.rafael.media/d/blog/blog) use the staging TLS
certificate and local DNS. Both route configurations allow LAN/Tailscale then
deny all; DNS and certificate verification passed from PVE, and browser collection
worked from the Mac. External-network denial was inspected in configuration,
not tested from outside the network. Grafana's unauthenticated dashboard API
returned 401. NPM's actual proxy location overwrites `X-Real-IP` from the connecting
client; Umami explicitly uses that header for its visitor estimate.

Umami's seeded password was replaced before the dashboard routes were added.
All operator secrets remain in PVE's protected dotenv and the dedicated scoped
runtime file. The blog receives only public build configuration. Canonical data
is under `/srv/appdata/docker/staging/blog-observability`; only exact newly owned
directories were created. No shared-data mounts or ownership were changed.

Nine initializer tests and nine existing staging-deployer tests passed. Application
typecheck, 24 unit tests, production builds, nine default browser tests, two enabled
tracker contract tests and the complete live smoke passed. Docker Compose, nginx,
Prometheus, Blackbox, Alloy and Grafana provisioning were validated with the relevant
runtime images. The existing JavaScript chunk-size warning remains.

The new logical-backup hook ran successfully against the new Umami database and
its custom-format archive passed `pg_restore --list`; this is not a restore test.
CT114 remains in the scheduled appdata freeze list. The latest observed PBS job
succeeded October 22 at 02:18 CEST, before this addition; no new PBS job, independent
off-host copy or restore drill was performed. Umami keeps data indefinitely unless
separately pruned; existing Loki retention stays at 30 days. The journal is a bounded
runtime buffer and Alloy's 24-hour catch-up setting is not a retention guarantee.

Prior blog images/releases, CT114 source archives, NPM database rollback and all
new database/dump state are retained. Rollback can stop new collection by reverting
the blog without deleting readership history. Source rollback is not database
migration rollback. Main promotion, public collection, cleanup and credential
rotation require their own acceptance/authorization.
