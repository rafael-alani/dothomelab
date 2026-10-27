# Blog folder notes and map lifecycle — 2026-10-27

The candidate implements the requested About body, folder-note migration,
direct gallery pages, exact title fallback, last-edited dates, descending numeric
priority/newest-first ordering, cold map loading, browser-Back panning, and
heading-embed suppression. Production deployment was requested in the task;
preview acceptance is tracked separately below.

## Source migration and behavior

All 34 `_index.md` files in the connected `Blog` vault moved into same-name
folder notes. Waypoint stays above ordinary authored content and is omitted from
the generated site. The application seed and test taxonomy were migrated too;
legacy indices remain readable during transition. Stable IDs and URL histories
are retained. A folder can own an article/gallery and optionally list children.
Photography uses `Blog/creativity/photography/photography.md` directly, with no
extra gallery folder. Its one original photograph loads lazily; the lightbox
retains the caption and original image. About renders only the requested biography.

Nonempty YAML `title` wins; otherwise exact file/folder spelling supplies the
label. Connected URLs continue deriving lowercase hyphenated segments from names.
`lastEditedAt` accepts an explicit date or uses the wrapper's modification date
when blank (legacy `updatedAt` is also accepted). Numeric `order`, including zero
and negative values, puts an entry ahead of all unordered entries; highest comes
first, followed by newest publication dates. Unordered entries use newest dates.
Heading-specific embeds exclude the selected heading while retaining subheadings.

The pinned Excalidraw renderer created zero-size link-icon canvases at the
overview zoom, triggering repeated drawImage errors. A guarded build adaptation
rounds their dimensions up to at least one pixel and fails if the pinned upstream
code changes. The map stylesheet is now owned by the Astro document head and
restored through history navigation. A failed renderer script load is retryable.

## Validation and release

Application: typecheck has zero errors/warnings; 93 unit tests and the static
build pass. The complete authoring assertions pass, including renames, publication
selection, redirects, live editing and malformed-SVG recovery. Local Node 26
prints a Vite shutdown diagnostic after those successful assertions; it is not
claimed as a clean teardown. Exporter/migration: 30 tests pass; vault installer:
4; event runner: 2; production selection/history: 5.

Private staging `3a4d89b17ee3fe998f5afa8abdf4f5fd561ab93d` passed cold client
navigation, full screen, note selection, panning, Read notes, browser Back and
panning again in Chromium and WebKit, with no console/page errors. Both browsers
also render About. The actual Photography page has one lazy original and a working
lightbox; the actual Train Dreams page has no embedded root heading. The final
candidate `ab3dc9dbd4337ab0b8675970571bceda356f835b` adds exact folder spelling
and ordinary folder-page dates. A fresh Chromium run against that deployed
revision also passes both tests. Exporter revision `9c2c154` is installed on CT110;
CT114/115 guest source archives match it.

Pulse verification covers the live PVE guests and declared Docker agents/containers.
Homarr staging reconciliation reports no drift across six tiles. Shared Grafana
datasources/filters, fleet freshness, blog probes/scrapes/rules and a fresh sanitized
staging 404 in Loki pass. Native blog processes have guest coverage and HTTP
probes, not individual Docker process metrics. No monitoring service was added.

Final activation: pending preview acceptance and production promotion. The PVE
`dothomelab-blog-publish.path` dispatch was paused during source migration to keep
the old public parser from consuming the new folder-note layout. The native public
site remains healthy on `ee48d3e`; CT110 export remains active. Resume the path and
run the publisher after the accepted application revision is installed on CT115.

## Rollback material and cleanup

The migration verifies original file bytes before changing any source. Retain:

- Mac vault `.blog-publisher-backups/folder-notes-20261027/`: originals and
  `migration.json` with original/migrated hashes and prior target existence.
- Mac vault `.blog-publisher-backups/20261027T165021773717/`: seven authoring
  files before template refresh.
- Each environment's appdata `blog/folder-migration-before-20261027.json`:
  pre-migration deployed-code/content metadata.
- Native current/previous static sites, immutable editorial inputs, and guest
  `/opt/dothomelab.previous*` archives. Infrastructure owns these retained rollback
  artifacts until recovery is verified and their retirement is authorized.
- Local blog `.cache/folder-migration-20261027` and
  `.cache/fixture-folder-migration-20261027`: source migration copies. The original
  repository versions are also retrievable from `ee48d3e`.

Restore sources only with the exporter/dispatcher paused: verify saved hashes,
restore each original index and prior target from the manifest, remove a generated
target only when the manifest says it did not previously exist, and preserve any
edits after migration. Restore matching code/content metadata and the retained
static site before resuming publication. No live rollback was rehearsed.

Task-owned disposable local export/authoring fixtures are removed after successful
replacement checks. Native builders remove superseded build copies and keep two
complete sites. No temporary Docker containers were created. Shared Docker cache
was inspected: staging 37.55 GB and production 9.7 GB, retained because these native
blog releases do not add to it. Images, volumes and unrelated applications remain.
Canonical local checkouts retain the review revisions; no task worktree was made.
Unrelated Krita evidence and `artwork/scene/picnic2.svg` remain outside these commits.

## Limits

Photography and two prose notes remain drafts unless Rafael changes their source
status. The exporter still reports three pre-existing missing map-note references;
this change does not recreate those source notes. No physical iPhone, independent
WAN uptime check, clean-host recovery or live rollback was tested. Alert delivery
remains an existing unconfigured integration. Neither limit is presented as fixed.
