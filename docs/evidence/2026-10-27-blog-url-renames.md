# Blog URLs follow names and retain identity redirects

On **2026-10-27**, the renamed Mac and CT110 vault folders were already
`Blog/technical-write-ups/ai`, but their `_index.md` files still contained
`work-and-nerdy` and `ai-technical-write-ups` slugs. The article wrappers also
retained explicit old URLs. HTTPS returned 200 for the old topic and 404 for
`/technical-write-ups/ai`. The active export digest matched staging, ruling out
sync lag. Rafael confirmed that folder and article renames should change URLs
automatically while IDs preserve old links.

## Change and checks

Publisher/importer revision `43768f6659bc5a54963cbcc392d5167480a85dcd` derives
current paths from names and retains former paths by identity. Existing source
slugs and URLs seed aliases; they no longer pin the current address. Folder IDs
join the durable history, and retired paths cannot be reassigned to another ID.
Map article aliases preserve nested reading links. The staging importer matches
Git map fallbacks against historical article URLs as well as current ones, so
renamed draft maps still stay out of the published selection.

The publisher and importer regressions failed before the fix. Local checks pass:
17 publisher tests, three authoring-installer tests, three runner tests, six
editorial-adapter tests, ten deployment tests, and documentation/whitespace
checks. The blog's existing content and Obsidian suites pass all 22 focused tests.
The additional first-export regression covers stale metadata after both parent
and child renames, without relying on an already upgraded history file.

CT110 and CT114 installed that exact source revision. Blog `staging` revision
`d8b119f5783a19841f9aafe833343c7ce44fd6df` records the updated authoring contract.
The Obsidian guide and topic template were updated without changing any article
note, original course note, plugin settings, or publication status.

## Live verification

Staging accepted content digest
`05c6874143ff701119fe494905394a8658e8b9d8ccdf4dc5167b8bf32aca33da`
with blog commit `d8b119f5783a19841f9aafe833343c7ce44fd6df`. The Docker static
build, quiet Compose validation, nginx configuration test and normal read-only
deployment verifier passed. The final content switch gracefully reloaded nginx.

HTTPS checks passed for 29 old-to-new pairs: the parent section, the requested
topic, all nine articles, all nine map indexes and one standalone note from each
map. Every old address returned 301 with the expected destination; all 29 new
addresses returned 200. Query strings survived redirects and an unknown article
returned 404. The original Mac-side curl reproduction now returns 301 to
`/technical-write-ups/ai`, which returns 200.

The in-app browser followed the original topic URL to the new address and showed
all nine article links under it. Clicking Machine and Deep Learning opened its
new route; the interactive map loaded its configured starting note with updated
reading links. The actual export still has ten drafts, zero published maps and
the same three previously documented unavailable source notes. This check did
not repeat every map interaction, all 1,154 reading pages, physical-phone tests,
or analytics-ingestion acceptance.

## Recovery inputs and limits

Both guests retain `/opt/dothomelab.before-url-renames-20261027`. CT110 retains
`dothomelab/blog-publisher:before-url-renames-20261027` and verified copies of
`state.json` and `current.json` in
`/srv/appdata/docker/staging/blog/editorial/rollback-url-renames-20261027/`.
The source/history swap held the appropriate export/deployment lock. Immutable
editorial snapshots, prior static trees, images and releases remain retained.

For a rollback, pause the publisher timer, wait for its active export, retain
the newer source/history, restore the named source and image, and use the saved
editorial pointer with staging's retained release procedure. Restore history
only after comparing later edits/exports; reverting code alone does not rewind
the ledger. No live rollback or PBS restore was performed.

The Mac guide/template originals are verified under
`.blog-publisher-backups/url-renames-20261027T075033/` in the Obsidian vault,
preserving their relative paths. Compare later author edits before copying back.
No temporary code worktree was created. The canonical repositories retain their
published branches; unrelated artwork and documentation edits remain untouched.
Public production and `main` were not promoted or deployed.
