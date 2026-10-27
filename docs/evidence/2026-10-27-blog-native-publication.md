# Native automatic blog publication — 2026-10-27

The blog now publishes Obsidian content automatically to private staging and
public production without Docker. `status: published` publishes and updates;
`draft` removes the public article while retaining staging. Browser refresh is
manual. The existing domains, TLS routes, private-preview access controls and
separate analytics identities remain.

## Final measured behavior

Measured on 2026-10-27, 14:53:13–14:54:29 UTC, from a completed Mac vault save to
the first matching HTTPS response. `hosts/blog/measure.py` created one temporary
article, polled each actual domain every 0.3 seconds, and required its new body
marker or HTTP 404. Both domains were checked concurrently with a monotonic clock.
This includes Syncthing, export, dispatch, build and HTTP observation. It measures
availability on refresh, not automatic updates to an already-open browser.

| Change | Private staging | Public production | Public result |
|---|---:|---:|---|
| Publish new article | 11.197 s | 11.139 s | 200, new body |
| Edit published text, first | 10.253 s | 10.470 s | 200, changed body |
| Edit published text, second | 10.181 s | 10.259 s | 200, changed body |
| Published → draft | 10.138 s | 10.604 s | 404; staging remains 200 |
| Draft → published | 10.120 s | 10.546 s | 200, new body |
| Delete article | 12.253 s | 12.932 s | 404 in both environments |

Raw observations: [final timings](2026-10-27-blog-native-timings.json).
The probe route was `/art-corner/songs/publication-timing-f65ee983`; its source
note was deleted and both sites returned 404. No timing probe notes remain in
the vault. A [first-pass run](2026-10-27-blog-native-first-pass.json) took about
25 seconds per edit and identified the remaining exporter bottleneck before the
map graph cache was added. Its temporary article was also deleted.

These are warm text/status edits on the actual nine-map library, not a benchmark
of arbitrary new media uploads or cold installation. Changing a map dependency
recompiles that map. Large new files also pay their synchronization time.

## Where the time went

| Stage | Earlier observed path | Final observed path |
|---|---|---|
| Mac file watcher | 10-second batching setting | 1-second batching setting |
| Export scheduling | Minute timer, plus systemd scheduling slack | Syncthing index events, 0.5-second debounce |
| Unchanged export | 88–164 seconds in prior logs | 0.053–0.061 seconds in final event-driven runs |
| Changed export | 219 seconds in the selected prior run | 0.929–1.090 seconds across final changes |
| Exported media/graphs | Reread/reprocess selected library | Nine maps reused; text edits read only 194 changed source bytes |
| Deployment scheduling | Two-minute staging timer plus jitter/slack | PVE path event; both native builders run concurrently |
| Docker work | 1.04 GB context: 14.8 s; COPY: 17.1 s; build command: 29 s | No image/context/copy path for the blog |
| Native build | Not previously available | About 5.2–6.4 seconds per environment |
| Browser/CDN | No forced browser refresh | No forced refresh; `Cache-Control: no-cache`, Cloudflare `DYNAMIC` |

The earlier figures are individual logged stages and configuration, not a measured
save-to-HTTPS trace. They should not be summed into a precise old end-to-end time.
The final end-to-end numbers above are directly measured. Astro's old reported
4.46 seconds was part of the old 29-second build command, not an additional cost.

In the final run, export index work took 45–60 ms, cached rendering 166–242 ms,
and immutable snapshot writes 699–829 ms. Native preparation took 0.15–0.18 s,
generation 1.19–1.56 s, Astro 3.04–3.94 s, and finalization 0.60–1.03 s.
The remaining end-to-end time includes sync, dispatch and HTTP observation.

Cold installation is separate: the first native export populated roughly 951 MB
of source cache in 98 seconds; initial staging setup/build took 205 seconds,
mostly Git acquisition and dependency preparation. These costs are retained
between content edits, not paid for each save.

## Implementation and revisions

- CT110: native Python long-polls Syncthing; native Node exports selected content.
  File deltas avoid full vault scans. Cached map graphs invalidate on changed
  dependencies, configuration or newly available matching note names. Original
  media bytes are hardlinked from an immutable SSD cache, without transformation.
- PVE: `dothomelab-blog-publish.path` immediately fans out completed exports. Only
  the published tree and filtered manifest/history enter production appdata.
- CT114/115: native build workspaces retain Git, npm, Astro and map caches. Entire
  selected content trees replace prior inputs, so deleting/unpublishing cannot
  leave a served article behind. Native nginx serves complete static generations
  through `site/current`; redirects reload only when changed.
- Application Dockerfile and both blog Compose registrations were removed, along
  with the publisher image/timer and the Docker-specific static deployment code.
  Shared observability and other applications retain their own Docker runtimes.
- No deployment polling, manual approval, typecheck, test suite, repeated content
  checksum verification or quiet-sync gate runs in the editorial publication path.
  Content parsing and draft selection remain functional requirements.
- Current URL owners take precedence over obsolete aliases, fixing the earlier
  `A URL already belongs to another identity` failure.

Measured application code: `fa54ef2c8f8ca33d5e40daa11a116fd3c3200769`.
Final application revision: `ee48d3e6d4b1a5b46cc3e90eb810b0fd4dd42e72` on both
remote `staging` and `main`; the difference is authoring/status documentation.
Both native environments were updated to that final revision.

The final exporter is in homelab `366a2af646fd30aefada45fda49fbdd28679d19c`.
Runtime/documentation cleanup is in `f59747c` and the evidence follow-up. Native
output cleanup runs after activation and keeps the current/previous generated
sites. Application code continues to follow its configured branches; editorial
publication never waits for a Git fetch or code-release approval.

Canonical local checkouts remain `/Users/rafael/Repos/dothomelab` on its existing
review branch and `/Users/rafael/Repos/blog` on `staging`. No temporary local
worktree was created. Unrelated Krita authoring work and `artwork/scene/picnic2.svg`
remain outside these commits.

## Verification and operational cleanup

The exporter has 25 passing tests, including current-URL reuse, source/image
invalidation, map graph reuse, added/deleted sources and published-to-draft output.
The application typecheck and all 87 unit tests passed. Native builds completed
on both real hosts. Relevant staging, production, event-runner and Homarr tests
passed; shell/Python syntax and documentation links were checked.

Both native nginx configurations passed as their actual `www-data` user. The
private HTTPS homepage and all six referenced scripts/styles/icons/images loaded.
The real HTTPS timing test verified both publication and removal. Both
staging and production have 5/5 successful Prometheus HTTP probes and fresh
sanitized Loki access records. Native access logs use `dothomelab_blog` as the
syslog identifier, retaining separate environment labels and Umami IDs.

Pulse verifies guest/agent coverage for CT110/114/115. Native nginx no longer has
a Docker process card or individual Docker CPU/memory metrics; HTTP probes and
systemd cover its availability. Both existing Homarr Blog tiles retain their
correct private/public destinations. The scheduled Homarr helper was upgraded
to the native registry description, and repeated reconciliation reported no drift.
Public curl GETs confirmed 200 for home/feed/sitemap and 404 for the existing draft
and deleted probe; neither appears in the public feed/sitemap. A raw Python
default-user-agent request received a Cloudflare 403, while curl and the declared
healthcheck requests passed; no Cloudflare protection rule was changed. Alert delivery and an independent external
WAN observation remain existing monitoring limits; no new claim of either is made.

Removed stopped containers after replacement verification:

- CT114 `staging-blog-web-1`; protected recovery metadata:
  `/srv/appdata/docker/staging/runtime-cleanup/20261027T145254Z-871333`.
- CT115 `production-blog-web-1`; protected recovery metadata:
  `/srv/appdata/docker/production/runtime-cleanup/20261027T145256Z-166339`.

Production Docker build-cache cleanup reported 13.44 GB reclaimed, preserving all
images, bind mounts and volumes. Docker subsequently reported 9.7 GB build cache
remaining; cache accounting/retention does not imply 13.44 GB of physical ZFS
space was freed. Staging's 37.55 GB shared build cache was inspected and retained
because other applications still use it. Native migration caches were initially
9.0 GB on staging and 7.0 GB on production; redundant extraction copies and old
generated site trees were then removed, retaining exactly two sites per
environment. Final native cache totals were 3.1 GB on staging and 3.5 GB on
production. The current native release IDs are
`1793113141284114993-ee48d3e6d4b1` (staging) and
`1793113212266056979-ee48d3e6d4b1` (production).

Rollback material retained by the blog migration:

- Each environment's `docker-before-native-20261027.json`, old Docker image and
  existing release/configuration directory identify the pre-migration runtime.
- Canonical editorial inputs, current/previous metadata and the two native static
  releases preserve the immediately preceding generated site. Git mirrors and
  source remotes permit rebuilding code; guest build caches remain disposable.
- The protected container metadata above identifies the original mounts. Do not
  restore analytics databases to roll back static files. No native clean-guest
  recovery or live rollback was rehearsed; retain the Docker fallback until that
  recovery is verified or the owner explicitly retires it.
- Authoring-guide refresh backup:
  `.blog-publisher-backups/20261027T152617620293` in the Mac vault. It belongs to
  the authoring update and can be retired after accepting the refreshed guide.

Three pre-existing missing map source-note targets still render unavailable-note
cards. The task changes publishing latency and workflow, not those authoring gaps.
