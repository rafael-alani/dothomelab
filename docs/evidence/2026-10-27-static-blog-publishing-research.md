# Faster static blog publishing

Researched **2026-10-27**, Europe/Amsterdam. All external sources below were
accessed on that date. This is a research draft, not an accepted architecture
change or deployment. It prioritizes the time between an edit and seeing that
edit. Provider capabilities are documented facts; the proposed workflow and fit
judgments are engineering recommendations. No provider deployment was benchmarked.

## Finding

An Astro static site does not require a dedicated application container at
runtime. Astro builds ordinary files, normally into `dist/`; a static host can
publish those files. Docker can provide a build environment, or run a shared web
server, without making a fresh image build part of every content edit.
[Astro deployment guide](https://docs.astro.build/en/guides/deploy/).

The useful distinction is between **author feedback** and **publishing a static
release**. A persistent development server can react to changed files and update
the browser. A static release requires generation, transfer, activation and a
new browser request. Moving the current pipeline to a hosted Git build preserves
much of that work and adds a remote build/deployment dependency; it does not
automatically make editing immediate. Astro documents HMR for `astro dev`,
static output for `astro build`, and `astro preview` as a build-preview command
that is not intended as a production server.
[Astro CLI](https://docs.astro.build/en/reference/cli-reference/).

## What the current installation actually does

Read-only inspection used SSH to PVE and `pct exec` into CT110, CT114 and CT115.
No save probe, build, deployment, benchmark load or source-content mutation was
performed. Logs establish individual stage durations, not a fresh end-to-end
save-to-visible measurement. Times in the table are durations; the recorded
changed export ran **13:45:39–13:49:18 CET** on October 27.

The guest platform markers were `989e052d7ec40159f08b565c53f948b3040d950a`.
Both staging and production recorded blog code
`2f0ec42770fd465d7ff94bd29af7a75ee1a5a428`. Staging content was
`e1ec67f651fae3bda732a7854ac78781faed063035d86b63191cc1f5f2b1755c`;
production content was
`160f93479f63659232b8a7ed48abfc55ab5fe6201c89b3e6bcb07ee4640a7d79`.
Local infrastructure HEAD was `964414727c9e7102439eedbd9f8066fded35ad19`;
SHA-256 comparisons confirmed that the inspected local exporter and staging
deployer matched the live installed files. This checks those files, not every
file represented by a guest marker.

| Stage | Observed fact | Implication |
|---|---|---|
| Syncthing detection | Mac and CT110 folder configurations both enable the watcher with `fsWatcherDelayS=10`. | The sender batches changes before synchronization; removing deployment polls alone does not make remote feedback subsecond. Do not add the receiver's local-watcher setting as another measured inbound delay. |
| Publisher scheduling | `OnUnitInactiveSec=60`, effective `AccuracyUSec=1min`. | The next run is scheduled after the previous run finishes, with additional timer coalescing possible. |
| Export work | Recent unchanged successful runs took 88–164 seconds; the selected changed run took 219 seconds. | Most observed delay precedes Astro. These are logs, not a CPU/I/O profile or a promised normal range. |
| Export scope | Saved state lists 11,244 vault files, 3,489 selected dependencies and ten article wrappers. | A small authored site can still trigger substantial vault and attachment work. |
| Staging scheduling | `OnUnitInactiveSec=2min`, `RandomizedDelaySec=10s`, effective `AccuracyUSec=1min`. | A second wait follows export; a shared staging run can also include other apps. |
| Docker input | The subsequent build transferred a 1.04 GB context in 14.8 seconds; `COPY . .` took 17.1 seconds. | Reusing the running web container does not remove repeated build-input movement. |
| Build command | `npm run build` took 29.0 seconds; Astro reported 21 pages in 4.46 seconds. | The custom content generator and surrounding work deserve more attention than page rendering. These figures are nested, not additive. |
| Final image export | 0.2 seconds in this warm build. | Removing just image export would save little; bypass the whole per-content image/copy path. |

Primary local evidence: installed timer definitions and effective properties,
publisher/staging journals, deployment `current.json` files, and publisher
`state.json`. The implementations are the
[publisher timer](https://github.com/rafael-alani/dothomelab/blob/964414727c9e7102439eedbd9f8066fded35ad19/hosts/infra/blog-publisher/dothomelab-blog-publisher.timer),
[staging timer](../../hosts/staging/dothomelab-staging.timer),
[exporter](../../hosts/infra/blog-publisher/export.mjs),
[importer](../../hosts/staging/editorial.py),
[deployer](../../hosts/staging/deploy.py), and
[static activation helper](https://github.com/rafael-alani/dothomelab/blob/964414727c9e7102439eedbd9f8066fded35ad19/hosts/staging/static_site.py).
The timer behavior follows the
[systemd timer contract](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).

The exporter traverses the vault on every invocation. Even its unchanged path
reads and hashes selected dependencies. Changed exports reread their dependencies
before committing a snapshot. The importer hashes complete snapshots, then
copies selected content into a new build context; snapshot verification occurs
both when selecting the source and when materializing it. Unchanged exported
files already use hardlinks between retained snapshots, but that does not prevent
the later hashing, copying and Docker transfer. The logs do not isolate the cost
of each of these operations.

Content updates currently still call `docker compose build`. The activation
helper creates a temporary container, copies its HTML and redirect configuration
out, removes that temporary container, and switches the static directory symlink.
The existing web container then reloads nginx. Keeping that server running is
already supported; directly supplying its files is the missing optimization.
An unchanged nginx configuration needs no reload merely because file contents
change, but this project's generated redirect rules can change on renames.

The current Docker build invokes content generation and Astro, **not the test
suite or typecheck**. Extensive tests reported in prior release evidence should
not be mistaken for checks performed on every Obsidian edit.
[Inspected blog Dockerfile](https://github.com/rafael-alani/blog/blob/2f0ec42770fd465d7ff94bd29af7a75ee1a5a428/Dockerfile),
[build scripts](https://github.com/rafael-alani/blog/blob/2f0ec42770fd465d7ff94bd29af7a75ee1a5a428/package.json).

Two other findings affect the recommendation:

- The deployed staging output contains **8,344 files totaling 2,100,011,636
  logical bytes** (2.10 GB / 1.96 GiB). Its largest file is 31,958,346 bytes;
  two files exceed 25 MiB. These are the static tree's file sizes, not unique
  compressed transfer bytes, disk allocation or production's size. The full
  private artifact exceeds GitHub Pages' site limit and Cloudflare's individual
  file limit below. A host move needs output deduplication and/or separate large
  asset hosting; preserving original photos need not mean recompressing them.
- Later publisher runs failed with `A URL already belongs to another identity`
  (first observed at 14:05:52 CET; still observed at 14:33:02 CET). Intervening
  runs also reported incomplete sync. These failures retain the old export, so
  waiting longer cannot be assumed to deliver current edits. Their cause was not
  diagnosed or fixed in this research.

## How static hosts publish files

The common pattern separates building from hosting:

1. Generate HTML, CSS, JavaScript and media once, wherever convenient.
2. Upload a deployment's files or a manifest identifying them.
3. Activate the completed deployment at its URL.
4. Serve its files through shared hosting/CDN infrastructure.

GitHub's artifact workflow, Netlify's deploy API and Vercel's prebuilt workflow
all expose this separation. They do not require shipping an application Docker
image. The providers may use containers internally to execute builds; that is a
different concern from a continuously running container for each static site.
[GitHub custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[Netlify deploy API](https://docs.netlify.com/api-and-cli-guides/api-guides/get-started-with-api/),
[Vercel prebuilt deployments](https://vercel.com/docs/cli/deploying-from-cli).

| Option | Documented publishing path | Consequence for this task |
|---|---|---|
| GitHub Pages | A custom Actions workflow uploads static output with `upload-pages-artifact`, then deploys that artifact with `deploy-pages`; it can omit a build when output already exists. | Useful Git-centered hosting, but Git/Actions/deployment remain in the feedback path. [Workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). |
| Cloudflare Pages Direct Upload | `wrangler pages deploy dist` uploads already-built assets; a branch argument selects a preview. | Avoids Cloudflare's Git build for each edit. Requires an upload/activation after local generation. [Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/). |
| Cloudflare Workers Static Assets | An `assets.directory` can point at static output; a pure static site needs no Worker script. Cloudflare recommends this over Pages for new projects. | Current Cloudflare candidate for a new static host, despite the product name suggesting application compute. [Cloudflare guidance](https://developers.cloudflare.com/workers/best-practices/workers-best-practices/). |
| Netlify | `netlify deploy --no-build --dir=dist` uploads prebuilt output; add `--prod` to update the main site. The current CLI otherwise builds by default. | Explicitly skip rebuilding what was already built. The default deploy is a draft. [Current CLI reference](https://cli.netlify.com/commands/deploy/). |
| Vercel | `vercel build` prepares `.vercel/output`; `vercel deploy --prebuilt` uploads it. Static files belong under `.vercel/output/static`. | Avoids Vercel's remote build but uses its output format and deployment service. [Prebuilt workflow](https://vercel.com/docs/cli/deploying-from-cli), [static-file primitive](https://vercel.com/docs/build-output-api/primitives). |
| Existing homelab static server | Build directly into a local release directory, then switch the server's directory pointer. The current staging implementation already supports the directory switch. | Direct build output would replace its current image extraction step. This proposed build path has not been implemented or timed. |

The commands above describe capabilities; none was run against a provider.

## Incremental upload is different from incremental generation

Netlify's API accepts a complete path-to-hash manifest and returns the hashes it
needs uploaded. Existing identical content need not be sent again. After upload,
Netlify processes the deploy and invalidates its CDN; `ready` identifies a live
deployment. Its ZIP path instead sends the whole site.
[Netlify API](https://docs.netlify.com/api-and-cli-guides/api-guides/get-started-with-api/).

Cloudflare Workers Static Assets similarly registers a manifest, requests missing
asset batches, and attaches the completed assets to a Worker version. Recently
uploaded unchanged assets can be omitted from those batches. This is documented
for **Workers Static Assets**; it should not be silently attributed to the Pages
API. [Cloudflare direct-upload protocol](https://developers.cloudflare.com/workers/static-assets/direct-upload/).

These mechanisms reduce transfer. They cannot eliminate a full-vault exporter,
regenerate Markdown themselves, or infer which pages a changed note affects.
Likewise, Vercel cautions that `--archive` can make uploads slower by preventing
reuse of its per-file upload cache; fewer uploaded files is not automatically
faster. [Vercel deploy options](https://vercel.com/docs/cli/deploy).

Astro now has experimental incremental static builds, added in **7.2.0**, disabled
by default. Only `getStaticPaths()` entries with a `cacheKey` qualify. Their data
key and module dependency graph must match. Other pages still render; changes to
configuration/dependencies invalidate the cache. Reuse needs a preserved
`cacheDir`, whose default is `node_modules/.astro/`. The output directory is
emptied and reusable output restored from that cache. A page cache therefore
does not establish an incremental exporter or content compiler.
[Astro incremental-build contract](https://docs.astro.build/en/reference/experimental-flags/incremental-build/).

Recommendation: if the actual Astro stage already takes only a few seconds,
optimize the waits and preceding work first. Do not introduce a custom page
dependency system merely to avoid a cheap build. Preserve the existing framework
cache and measure its hit rate instead.

## What activation and caching do—and do not—guarantee

Netlify explicitly documents atomic deployment: uploads remain inactive until
the full deployment is ready, then the new version becomes current on the CDN.
That is a completion switch, not an approval workflow or test suite.
[Netlify atomic deploys](https://docs.netlify.com/deploy/deploy-overview/).

A comparable local design can populate a new release directory and replace a
pointer only when generation finishes. That recommendation avoids showing an
unfinished tree while imposing little workflow ceremony. Cross-request asset
consistency still needs sensible retention: a browser that already received old
HTML may subsequently request its old asset URLs. Do not treat a directory switch
as a promise that every open browser tab changes versions together.

Cloudflare Pages manages edge caching across deployments and supplies ETags plus
browser revalidation headers. Its documentation warns that extra caching rules
on a custom domain can serve stale assets. Workers Static Assets likewise sends
`Cache-Control: public, max-age=0, must-revalidate` and content-derived ETags.
[Pages serving/caching](https://developers.cloudflare.com/pages/configuration/serving-pages/),
[Workers asset headers](https://developers.cloudflare.com/workers/static-assets/headers/).

For the freshness-first preview, use revalidation for HTML and changing content
URLs; reserve long browser lifetimes for content-addressed assets. `no-cache`
means validate before reuse, not prohibit storage. `no-store` prohibits storage
but does not make an already displayed document update itself. An ordinary static
page needs reload/navigation, or a small explicit reload mechanism, to show a new
release. [HTTP caching semantics](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2).

## What is actually known about delay

GitHub says site changes can take **up to ten minutes** to publish after a push.
This is documented operational guidance, not a promise of instant publication.
Moving here for shorter edit feedback would be an unsupported bet.
[GitHub publication guidance](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

The reviewed Cloudflare, Netlify and Vercel direct-deployment documentation does
not provide a numeric end-to-end edit-to-visible guarantee. Netlify's statement
that a ready version goes live immediately describes activation after upload;
it does not include editor synchronization, export, build, transfer or a browser
refresh. Provider speed must be measured with this site's actual files.

Use separate measurements for:

| Measurement | Why it matters |
|---|---|
| Save → file received on builder | Isolates editor/sync delay. |
| File received → exporter started | Exposes polling/debounce waiting. |
| Export started → content ready | Measures full-vault scanning/conversion. |
| Content ready → build started | Exposes a second queue/poller. |
| Build started → static output ready | Separates content generation from Astro rendering. |
| Output ready → active release | Measures packaging, copying/uploading and activation. |
| Active release → visible browser change | Exposes caches and missing reload/HMR. |

For ideal fixed-interval polling, uniformly distributed edit times yield an
average wait of half the interval. That simplification does not accurately model
these live timers: they wait after completion, allow coalescing, and run work
that can take minutes. Measure the actual timestamps rather than promising a
three-minute maximum from adding the two configured intervals.

## Recommended direction

First simplify the current static publisher: trigger immediately after relevant
synced changes, reuse a warm build workspace and dependencies, and write static
output directly to the existing server. Keep full code-release work separate
from content refreshes. This is the smallest useful architectural change for the
observed installation; removing the long-lived nginx container itself offers
little edit-latency benefit.

For the fastest writing feedback beyond that, use a persistent **private Astro
development preview** connected to a small working content tree. Update that tree
when selected source files change; let Astro's watcher/HMR update the browser.
Astro's loader API supports filesystem-watcher updates in development.
[Loader watcher](https://docs.astro.build/en/reference/content-loader-reference/#loadercontextwatcher).

This only helps once changes reach the files Astro consumes. Keeping the same
slow exporter or timer before the dev server preserves that delay. Start with a
short debounced trigger and an exporter that rewrites only changed outputs; add
more selective dependency tracking only if measured work still justifies it.
Coalesce bursts and keep a single pending newest update while a build runs, so
rapid saves do not produce an ever-growing obsolete build queue.

Syncthing exposes a long-polling event API and `LocalIndexUpdated` events with
changed filenames. Those can trigger a targeted export immediately; a process
watching the exported revision can start the static build without the second
timer. Persistent event position plus a rescan after restart/missed events avoids
making a periodic whole-vault scan the normal edit path. Use a short debounce,
and wait for relevant dependencies rather than making an unrelated large vault
transfer hold every article. This is a proposed implementation, not functionality
already supplied by the publisher.
[Event API](https://docs.syncthing.net/rest/events-get.html),
[LocalIndexUpdated](https://docs.syncthing.net/events/localindexupdated.html),
[watcher delay](https://docs.syncthing.net/users/config.html).

The blog already enables Astro 7.4.2's incremental build, preserves `.cache/astro`
and supplies page cache keys. Its existing development plugin, however, watches
`content/interests`, runs broad content generation, then calls `server.restart()`.
It does not establish complete incremental watching of exported map inputs under
`content/obsidian`. Simply running `npm run dev` behind the same slow exporter is
therefore insufficient. Use a stable selected-content workspace, update only
changed files, cover map/attachment dependencies and reduce broad restarts before
claiming near-instant feedback.
[Astro configuration](https://github.com/rafael-alani/blog/blob/2f0ec42770fd465d7ff94bd29af7a75ee1a5a428/astro.config.ts),
[current development plugin](https://github.com/rafael-alani/blog/blob/2f0ec42770fd465d7ff94bd29af7a75ee1a5a428/scripts/content-dev.ts).

A remote dev preview needs private reachability and a working HMR WebSocket path
through its proxy. It also needs a persistent process and stable watched paths.
Those are implementation requirements to verify, not reasons to rebuild Docker
for every edit. Keep the dev server within the existing private preview access
boundary; publishing its endpoint is not part of this research.

For static publication, use a direct path: **changed content → warm build →
completed static directory → activate**. Reuse installed dependencies and caches.
Keep tests and extensive release checks outside the writing loop, consistent
with the user's priority. A build must still succeed to produce publishable
files; publication selection must still exclude private drafts and unrelated
vault material.

Keep original photos in an immutable asset store scoped separately to private
and published content. Reuse unchanged bytes when captions or ordering change.
Keep collection-level map caching initially; a changed drawing or referenced
note may require recompiling that collection. Renames can legitimately update
navigation, redirects and multiple pages, but should not recopy unrelated media.
SSR or client-fetched content could bypass parts of a static build at the cost
of a different runtime/application design; neither is justified solely to avoid
the measured 4.46-second Astro stage.

Useful **acceptance targets, not measured estimates**: ordinary warm static
updates in tens of seconds after relevant files arrive, with a later goal of
1–3-second local author preview for a small text edit. Remote preview also pays
sync delay; the currently configured ten-second sender debounce must change or
be bypassed for that faster goal. Large new originals and changed map collections
need separate measurements. Check existing text, a rename, caption-only change,
new photo and referenced map-note edit once the pipeline exists.

Production remains manual under the current runbook. For automatic public
content updates, a future policy could make `published` edits automatically
refresh static output using already-approved application code on `main`, while
drafts stay private and code releases remain separate. That is a change in
publication semantics, not an Astro requirement. This research authorizes no
such activation; latency work alone does not change the existing policy.
[Current production contract](../../hosts/production/README.md).

Prefer retaining a suitable existing static server when minimizing this local
feedback path is the only goal. Choose an external static host for its managed
hosting/CDN properties, then use direct artifact deployment. GitHub Pages is
valid static hosting, but its documented publishing delay makes it a weak answer
to this particular latency problem. Cloudflare Workers Static Assets and Netlify
are clearer direct-upload candidates to benchmark if external hosting is wanted.
These rankings are recommendations, not provider performance results.

## Relevant limits and scope

- GitHub Pages: published site at most 1 GB; deployment timeout ten minutes;
  soft limit ten builds/hour, except custom Actions publishing workflows.
  [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
- Cloudflare Pages Direct Upload: Wrangler up to 20,000 files, 25 MiB each;
  dashboard drag/drop up to 1,000 files. A Direct Upload project cannot later
  switch to Git integration in place.
  [Direct Upload limits](https://developers.cloudflare.com/pages/get-started/direct-upload/).
- Cloudflare Workers Static Assets: 20,000 files on Free, 100,000 on Paid;
  25 MiB per file. [Workers limits](https://developers.cloudflare.com/workers/platform/limits/#static-assets).
- Netlify: 54,000 files per directory; ZIP extraction at most 25,000 files.
  The digest-upload path is the better mechanism to investigate for a media-heavy
  incremental publish. [Deploy limit](https://docs.netlify.com/deploy/deploy-overview/),
  [API ZIP limit](https://docs.netlify.com/api-and-cli-guides/api-guides/get-started-with-api/).

Provider plans, custom domains and private-preview access are migration concerns
only if a host move is chosen. No accounts, DNS, credentials, production services,
application source or operational scripts were changed for this research.
