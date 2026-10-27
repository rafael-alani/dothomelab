# Native static blog publication

Obsidian saves trigger publication without a Git commit, Docker build, test gate,
manual approval or deployment poll. Refresh the browser to see the new files.
`published` updates the public site and preview; `draft` removes the article and
its assets from public output and retains the private preview.

## Flow and ownership

1. Syncthing receives the Mac edit on CT110. A native Python service long-polls
   its local index events, debounces 0.5 seconds, then runs the Node exporter.
2. The exporter uses Syncthing file deltas, cached source text and hardlinked SSD
   media. Unchanged map dependency graphs are reused; editing a selected source
   or adding a matching missing note invalidates its graph. Restarts reconcile the full index once; warm runs inspect changed paths.
   Completed exports atomically replace staging `editorial/current.json`.
3. PVE's `dothomelab-blog-publish.path` immediately invokes `publish.py`. It
   hardlinks only the published tree and filtered history/manifest into production
   appdata, then builds both environments concurrently. New exports during a build
   are picked up before the worker exits.
4. Native builders retain installed code, dependencies and Astro/map caches. They
   replace imported content completely, generate once, build Astro and switch a
   symlink. Native nginx serves files on the existing guest port 8084. Only changed
   redirects require nginx reload. HTML/assets revalidate on browser refresh.

The blog application owns its portable static build and optional
`STATIC_OUTPUT_DIR`. This directory owns host assignments in `environments.json`,
nginx, native toolchain, triggering and publication. The website has no vault
mount, database or runtime secret. CT115 never receives preview content or the
private listening media. Existing proxy access controls, TLS and separate
analytics identities remain in place.

Content refreshes use the installed code revision. Staging's existing branch
poller updates code from `origin/staging`; explicitly requested production code
releases update `origin/main`. Content publication does not wait for either.

## Install and recover

After synchronizing the committed repository into the guests, run on PVE:

```sh
pct exec 114 -- bash /opt/dothomelab/hosts/blog/install-web.sh
pct exec 115 -- bash /opt/dothomelab/hosts/blog/install-web.sh
pct exec 110 -- bash /opt/dothomelab/hosts/infra/blog-publisher/install.sh
bash hosts/blog/install-publisher.sh
```

On the Mac, reduce the vault watcher delay from ten seconds to one with
`python3 hosts/blog/configure-client.py --vault /path/to/vault`. It updates only
that folder's watcher settings through the local authenticated API. Refresh the
installed authoring guide with the publisher's `install-vault.py --refresh-authoring`.

`measure.py --vault /path/to/vault --output /path/to/results.json` creates one
explicitly temporary article, measures HTTPS publication/edit/draft/republish/delete
and removes its own note. Run only when public timing probes are in task scope.

The installers retain dependencies between runs. The web installer enables but
never starts the listener before a build. During the one-time Docker migration,
build first, stop only the corresponding old blog web container and start
`dothomelab-blog-web.service`; other Docker services remain independent.
`publish.py` starts the native listener after a successful build. A production
`current.json` enrolls an already activated site; a new scaffold stays private
until its initial explicit activation. Full recovery reuses retained code/content
metadata and rebuilds replaceable guest-root files; npm/Git access is required if
those caches were lost.

Native state:

- `/srv/appdata/docker/<environment>/blog/editorial`: immutable editorial inputs.
- `blog/current.json` and `previous.json`: code/content revisions and stage timings.
- `/var/lib/dothomelab-blog`: disposable Git mirror, installed workspace, caches
  and `site/<release>/client`. `site/current` selects the served release.
- `/var/lib/dothomelab-blog-publisher`: native exporter dependencies on CT110.

Read `journalctl -u dothomelab-blog-publisher` on CT110 and
`journalctl -u dothomelab-blog-publish` on PVE for export/build timings. A failed
export/build leaves the last served files; correcting the source triggers another
attempt. To retry immediately, restart the exporter service or start the PVE
publication service. These are operational diagnostics, not edit-time gates.

For a stateless rollback, pause the PVE path and CT110 publisher, point
`site/current` at the retained previous complete release and reload native nginx.
Restore the matching `current.json` before resuming, or the next content event
will build from the newer recorded code. Keep the last Docker images/release
metadata from migration until native rollback/rebuild is verified. Analytics
state is separate and must not be rewound with website files.

## Monitoring

Native nginx emits sanitized JSON to journald with
`SYSLOG_IDENTIFIER=dothomelab_blog`. Existing scoped Alloy collectors label
staging and production separately. Existing Prometheus HTTP probes cover the
native origins and HTTPS routes; Pulse covers the guests, while the web server
is now a systemd service rather than a Docker container. Existing Homarr URLs
remain unchanged. See the [production runbook](../production/README.md) and
[shared observability](../infra/observability/README.md).
