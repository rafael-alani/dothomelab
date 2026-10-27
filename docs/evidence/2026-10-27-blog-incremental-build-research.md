# Existing packages for incremental blog publishing

Researched **2026-10-27**, Europe/Amsterdam, against application source, a
read-only staging revision check, official documentation and upstream source.
This is a research draft, not an accepted architecture change or implementation.

**Finding:** existing tools cover substantial parts of the request. For the
current application, `cacache` is a narrow candidate for reusing expensive map
compilation. Content Collections supplies a larger content-processing layer.
Astro has the closest built-in support for reusing complete static pages, but
requires a framework migration and its incremental feature remains experimental.
None is a drop-in replacement for this entire Obsidian-to-React-Router pipeline.

The recommendation is to avoid inventing a general incremental website builder.
Keep the accepted architecture for a bounded map-cache improvement. If selective
rebuilding of ordinary articles is the actual requirement, evaluate Astro before
committing to a custom React Router prerender/cache implementation. These are
different scopes; the first does not complete the second.

## Observed architecture and scope

The local blog and live CT114 staging both identify application revision
`d8b119f5783a19841f9aafe833343c7ce44fd6df`. CT114's accepted content digest is
`05c6874143ff701119fe494905394a8658e8b9d8ccdf4dc5167b8bf32aca33da`, with installed
homelab marker `43768f6659bc5a54963cbcc392d5167480a85dcd`. The local dothomelab
checkout is `9e51706d6f1028baa80838ec044705cb588079c4`. The deployed revision was
read over SSH to PVE using `pct exec`; no service was restarted or deployed.

Source inspection establishes these boundaries:

| Stage | Current behavior | Evidence |
|---|---|---|
| Vault selection/export | Recursively selects notes, drawings and attachments; hashes dependencies; skips an entirely unchanged export; retains checksummed immutable snapshots | [Publisher source](../../hosts/infra/blog-publisher/export.mjs), especially `read`, the unchanged-input check, `collect` and snapshot assembly |
| Map compilation | Deletes generated map output and calls `compileObsidianCollection` for every collection | Blog `scripts/generate-content.ts:722`, loop at line 799 |
| Compiler boundary | Accepts explicit configuration, source paths/bytes and analytics configuration; returns collection metadata and output files without scanning | Blog `scripts/obsidian-content.ts:182` |
| Ordinary articles | Generates eager Markdown/MDX imports and renders those compiled React components | Blog `scripts/generate-content.ts:1018`, `app/content/ContentModuleRenderer.tsx` |
| Article routes | Adds a concrete route for every article/gallery from the generated manifest | Blog `app/routes.ts` |
| Application build | Runs content generation, React Router build and static finalization; React Router is pinned to 8.2.0, Vite to 8.1.4, with `ssr: false` | Blog `package.json`, `react-router.config.ts` and `Dockerfile` |
| Release | Builds a complete candidate before an atomic content-tree switch; content-only updates retain the web container | [Deployment source](../../hosts/staging/deploy.py), [static-tree implementation](../../hosts/staging/static_site.py) |

Blog paths above refer to `/Users/rafael/Repos/blog` at the stated revision.
No application files were edited. Unrelated existing artwork/documentation edits
were preserved. The [publisher runbook](../../hosts/infra/blog-publisher/README.md)
owns the selection and deployment contract.

Two consequences matter. First, most map reading output is already generated
outside React Router: it can be cached without replacing the router. Second,
ordinary articles currently change both the application module graph and, for
new/deleted articles, the route manifest. Replacing their HTML alone is unsafe:
hydration or client navigation could still use an older compiled article.

React Router documents static HTML plus `.data` navigation output. Its
prerender-path selection is not an automatic incremental dependency cache.
The installed 8.2.0 implementation also clears the build directory by default;
no standalone cached-prerender command was found in its CLI. Keeping old output
with `emptyOutDir: false` would not establish correct invalidation or deletion.
[Official prerender contract](https://reactrouter.com/how-to/pre-rendering),
[official CLI](https://reactrouter.com/api/other-api/dev).

## Package comparison

The fit judgments are inferences from the cited APIs and the source above.

| Candidate | What it supplies | Fit and remaining work |
|---|---|---|
| [cacache](https://github.com/npm/cacache/blob/main/README.md) | Persistent result storage with integrity checks, deduplication and concurrent access | Smallest library addition around the existing map compiler; we still define complete input keys and assemble output |
| [Content Collections](https://github.com/sdorra/content-collections/blob/main/docs/transform.mdx) | Content discovery, schemas, generated data and cached expensive transforms | Closest broader content-layer fit; does not make React Router page generation incremental |
| [Astro incremental builds](https://docs.astro.build/en/reference/experimental-flags/incremental-build/) | Reuses complete eligible static pages across build processes | Closest whole-page feature; routing/build migration and experimental feature acceptance required |
| [Turborepo](https://turborepo.dev/docs/crafting-your-repository/caching) / [Nx](https://nx.dev/docs/features/cache-task-results) | Restores outputs of unchanged tasks | Useful after tasks have meaningful boundaries; changing one input to a monolithic build still runs that build |
| [Eleventy](https://www.11ty.dev/docs/usage/incremental/) | Template dependencies and incremental rebuilds | More natural for a template site; documented cold-start/CI incremental reuse still has gaps and the React application needs integration/migration |
| [Quartz](https://github.com/jackyzha0/quartz/blob/v5/quartz/build.ts) | Obsidian-oriented publishing and incremental watcher updates | Relevant digital-garden alternative; a fresh build still clears output and processes all Markdown before watching |
| [Velite](https://velite.js.org/other/roadmap) | Typed content processing and assets | Incremental build remains unchecked on its roadmap; its internal cache is not a supported integration API |
| [Next.js static export](https://nextjs.org/docs/app/guides/static-exports) | Static React pages and navigation payloads | ISR is explicitly unsupported with static export; adopting a regeneration server changes the accepted hosting architecture |

Vite's `build --watch` concerns a continuing bundler process. It is not proof of
persistent, selective website publication across our disposable Docker builds.
[Vite production-build guide](https://vite.dev/guide/build.html#rebuild-on-files-changes).

## Smallest fit: cache the existing compiler

`cacache` was built for npm's local cache. It stores caller-keyed data on disk,
verifies reads, supports streaming and deduplicates content. It does not infer
dependencies or choose the right cache key. That makes it a reusable storage
component rather than another website framework.
[Official API](https://github.com/npm/cacache/blob/main/README.md).

For this application, the natural initial unit is **one map collection**. Its
compiler already receives the complete selected input set. A proposed key covers:

- sorted source paths and content digests, including drawing and attachments;
- collection configuration, current routes and aliases;
- compiler and relevant renderer/plugin versions;
- publication mode, origin and output-affecting analytics configuration.

An unrelated scene-control edit could then reuse every map result. A linked note
shared by two selected collections would change both input sets and invalidate
both. This does not require a new general dependency-graph service. It initially
recompiles the affected collection, not only one note within that collection.

Existing snapshot/checksum utilities should be reused where they already solve
storage and assembly; adding `cacache` is worthwhile only if it removes cache
maintenance code. Do not rewrite scanning, URL ownership or publication policy to
obtain caching. The exporter can still walk/hash inputs on a warm run, so this
does not promise to eliminate all disk I/O or export work.

The cache must survive build containers. Today's Dockerfile copies source and
runs the whole build without a compiler-cache mount. dothomelab would own a
private, environment-scoped persistent cache assignment. Fresh/missing/corrupt
cache must cause recomputation. Construct each candidate from the current
selected outputs, preserving the existing atomic switch; do not mutate retained
hardlinked release files or copy an old output directory wholesale and leave
unpublished files behind. Large attachment payloads should not be needlessly
serialized into giant in-memory JSON cache objects.

Version selection also needs the actual builder runtime: `cacache` 21.0.1 declares
Node `^22.22.2 || ^24.15.0 || >=26.0.0`. The blog declares a Node 24 Docker tag,
which alone does not prove the installed patch meets that requirement.
[Published manifest](https://github.com/npm/cacache/blob/v21.0.1/package.json).

## Content Collections: useful, but a different layer

Content Collections has [Vite](https://github.com/sdorra/content-collections/blob/main/samples/vite/vite.config.ts)
and [Remix/Vite](https://github.com/sdorra/content-collections/blob/main/samples/remix-vite/vite.config.ts)
examples. Its [Vite plugin](https://github.com/sdorra/content-collections/blob/main/packages/vite/src/index.ts)
runs collection generation at build start. This is good architectural alignment,
not verification against this site's pinned React Router version.

Its documentation says the transformation function runs for every document;
`context.cache` skips expensive callbacks. The source persists results under a
cache directory and keys them by configuration checksum, serialized input and an
optional key. Generated content still feeds the application build.
[Transform guide](https://github.com/sdorra/content-collections/blob/main/docs/transform.mdx),
[cache source](https://github.com/sdorra/content-collections/blob/main/packages/core/src/cache.ts),
[builder](https://github.com/sdorra/content-collections/blob/main/packages/core/src/builder.ts).

A significant integration caveat: its `compileMDX` key contains `{content, _meta}`;
additional files are read inside the cached callback. Source inspection therefore
does not support assuming that editing an imported/embedded file invalidates an
unchanged parent. Supply fully expanded content or explicit dependency-aware
invalidation. This is an inference from code, not a reproduced package bug.
[MDX implementation](https://github.com/sdorra/content-collections/blob/main/packages/mdx/src/index.ts).

Choose it if replacing our scanning/schema/generated-data layer would remove
enough code to justify migration. Installing it only for its cache callback is
larger than caching the compiler boundary we already have.

## Closest full-page alternative: Astro

Astro 7.2 introduced experimental incremental static builds on August 6, 2026.
The release explicitly targets the HTML-generation phase, not eliminating the
bundling phase. This is unusually close to the requested behavior, but it should
not be described as skipping every unchanged part of the entire build.
[Release announcement](https://astro.build/blog/astro-720/).

Eligible `getStaticPaths()` entries provide a `cacheKey`. Astro combines it with
code-dependency hashes, restores matching page output from `cacheDir`, and removes
output for paths no longer selected. The data key must cover everything used to
render that page, including shared indexes/menus when relevant. A wrapper's own
timestamp is insufficient for nested Obsidian embeds.
[Feature documentation](https://docs.astro.build/en/reference/experimental-flags/incremental-build/).

Astro supports hydrated React components, and its client router can preserve an
island's state between navigations with `transition:persist`. A persistent React
constellation is consequently plausible. It is not verified for our WebGL canvas,
GSAP interruption behavior, React Router contexts, focus and scroll restoration.
Those integrations would need adaptation and acceptance testing.
[React integration](https://docs.astro.build/en/guides/integrations-guide/react/),
[state persistence](https://docs.astro.build/en/guides/view-transitions/#maintaining-state).

Current documentation still labels incremental builds experimental and identifies
limitations involving middleware invalidation and build concurrency above one.
The reviewed upstream package/changelog identifies 7.4.2. Earlier CSS/Sass cache
bugs are recorded in closed issues, and current source includes compiled-CSS and
client-dependency tracking; those old reports must not be presented as unresolved
current defects. A pinned migration candidate still needs independent tests.
[Feature limits](https://docs.astro.build/en/reference/experimental-flags/incremental-build/#limitations),
[changelog](https://github.com/withastro/astro/blob/main/packages/astro/CHANGELOG.md),
[closed issue](https://github.com/withastro/astro/issues/17974),
[dependency hashing](https://github.com/withastro/astro/blob/main/packages/astro/src/core/build/plugins/plugin-incremental.ts).

Merely moving the shell to Astro would not cache the current custom map compiler.
Its standalone reading pages would need to become Astro-generated pages, or the
existing compiler would still need its own cache. The Obsidian selection/export,
route-history ledger and private/published separation remain application-specific.
Astro is a migration option to compare with building a custom render engine, not
an automatic remedy for every stage.

## Other findings and Waypoint

Eleventy supports `--incremental=filename` outside watch, but its documented
roadmap still distinguishes cold-start and build-server incrementality from warm
updates. Quartz's current `v5` source uses incremental watch behavior; repeating
the old claim that it only has experimental `--fastRebuild` would be inaccurate.
Neither was verified as a drop-in persistent cache for this Docker pipeline.
[Eleventy details](https://www.11ty.dev/docs/usage/incremental/),
[Quartz build](https://github.com/jackyzha0/quartz/blob/v5/quartz/build.ts).

The maintained Contentlayer2 fork advertises incremental content processing, but
its README's framework matrix lists Next.js support and Remix as considering.
That makes its documented adapter fit weaker than Content Collections here;
it does not prove standalone CLI integration impossible.
[Contentlayer2](https://github.com/timlrx/contentlayer2/blob/main/README.md).

Waypoint addresses **selection**, not build caching. It writes real Markdown
links into a folder note and updates them in Obsidian. Following those saved
links can replace a separate inclusion list when the folder note is reachable
from the selected map. The marker alone is not an expanded file list, and edits
outside a running Obsidian plugin can leave it stale. Before removing existing
`map-include` entries, compare selected pages and retained URLs.
[Waypoint documentation](https://github.com/IdreesInc/Waypoint).

## Decision and evidence needed next

For a bounded improvement within the accepted architecture, retain React Router
and cache existing map compilation. Ordinary article edits still run the app
build. For the full requirement—new and edited articles becoming available while
unaffected pages are reused—Astro is the strongest investigated framework
candidate. Research supports testing it before funding a bespoke selective
React Router renderer; it does not yet justify migrating the live site.

Any implementation comparison should measure cold and warm builds separately,
with a fresh process/container and retained cache. Compare output against a clean
build after direct/nested note edits, shared-note edits, drawing/media edits,
new articles, renames, deletions, draft/publication changes, renderer changes and
unrelated UI changes. Check listing/feed/sitemap/redirect updates, absence of
removed private assets, direct no-JavaScript reading, client navigation, and
Canvas continuity. Test cache loss and failure before atomic activation. These
are proposed acceptance cases, not completed tests.

No package was installed and no performance benchmark, migration prototype or
deployment was performed. Exact speedups and compatibility with the complete
reader experience remain unmeasured. This report and its index entry are the
only changes made by this research task.
