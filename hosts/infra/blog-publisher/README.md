# Obsidian blog publisher

The native CT110 service exports selected vault content as soon as Syncthing
receives an edit. The [native static pipeline](../../blog/README.md) builds private
staging and published production content immediately, with retained dependencies
and caches. No Docker image, deployment poll or manual content release is needed.
Refresh the browser to see new files.

## Authoring

`Blog/` mirrors the blog's menu/topic structure. The Mac installer adds article,
poem, project and topic templates, `Blog/Articles.base` with separate draft and
published views, and `Blog/_Start here.md` with the full author guide. It uses
the installed Templater community plugin and preserves its template folder and
unrelated settings. It registers insert-only **Templater: Insert Blog …** commands
for the current note and enables cursor jumps. Templater generates the permanent
ID/date; photo paths and optional descriptions are edited inline without prompts.
It seeds content only when `Blog/` does not exist. Rerunning it preserves
deleted or renamed folders and articles, including during `--refresh-authoring`. `--refresh-authoring`
backs up and replaces only the Blog templates, guide and Articles base;
it never overwrites article notes or taxonomy. Prior settings and the created-file
list are retained in `.blog-publisher-backups/<timestamp>/` inside the vault.

```sh
python3 hosts/infra/blog-publisher/install-vault.py \
  --vault /Users/rafael/Obsidian/obsidian-cloud-retrieval \
  --blog-repo /Users/rafael/Repos/blog
```

Every menu/topic uses its matching folder note, for example `Blog/about/about.md`
or `Blog/creativity/photography/photography.md`. Its YAML owns navigation; its body
is an ordinary article or gallery at the folder URL. Waypoint stays at the top and
is excluded from publication. Menus can have no submenus. About renders only its
authored biography. Folder bodies use the same draft/published boundary as notes.

Wrappers use `status: draft|published`, a permanent `id`, `kind`,
`description` and `publishedAt`. Nonempty YAML titles override the exact article filename; blank titles fall back to it. URLs still follow filenames. Descriptions are optional in both
drafts and published articles; missing or empty values stay empty. Dates do not schedule release. The exporter's
durable identity/history map follows folder and filename changes while retaining
every former address for redirects. Folder names supply URL segments; article
filenames supply the final segment. Existing `slug` and `url` fields contribute
legacy addresses, not overrides. Keep IDs unchanged when renaming or moving.

`cover-media: "[[Assets/Photos/example.jpg]]"` and `cover-alt` provide card/social
images. The existing `3. Resources/Attachments` folder works too. A topic's
folder note selects `view: cards` or `view: list`. Published grid articles require
a cover; drafts may remain incomplete. Covers are pictures; YouTube links stay in
the body. Photos and covers retain their original bytes, orientation and metadata;
GIF animation is preserved. TIFF cannot be displayed reliably in browsers and is
rejected as a picture (it can still be linked as a download). No external image
service or authenticated URL is fetched.

Whole-note, heading and nested embeds resolve relative to their source note or
an unambiguous vault path/name. Embedded YAML is discarded without parsing or
copying fields, including malformed YAML. Obsidian `%%comments%%` outside code
are removed. Only embeds copy note bodies. Private ordinary note links become
text; selected wrapper links become website links. Published wrappers do not link
to draft wrappers. HTML becomes text and MDX expressions are escaped. Code blocks,
Markdown tables and reference-style image links are supported. Ordinary article block embeds, executable MDX and vault plugins remain unsupported.
A whole Excalidraw embed uses the map pipeline described below.
Waypoint blocks are removed from every rendered body. Empty folder notes remain navigation only.

Missing article/attachment references, unresolved ambiguity, invalid metadata, cycles/deep recursion, symlinks,
path escapes or relevant conflicts leave the last export unchanged. Subsequent
Syncthing events publish concurrent edits without a quiet-window gate. Source notes are never rewritten. An embed selects the entire body or
section, including nested embeds; review the resulting prose before publication.

## Install and operate

The native exporter reads `/vault/shared/media/obsidian` and writes
`/srv/appdata/docker/staging/blog/editorial`. It reads Syncthing's loopback API
credential in memory without logging it. Install and operate it through the
[native runbook](../../blog/README.md#install-and-recover). Bootstrap installs it
with staging. Missing or invalid input leaves the last successfully served files.
Syncthing must be running on the Mac.

Use **Templater: Insert Blog article** (or the desired Blog template command) in
the current note. **Insert Blog photo** adds inline attachment/description cursor
stops; **Jump to next cursor location** advances between them. If the running app
has not noticed the settings, enable Templater under Community plugins or restart
Obsidian. The installer requires an existing Templater installation; it does not
download plugins or change core Templates settings.

Each digest directory holds `preview/` (all selected articles), `published/`
(published articles and only their assets), history, manifest and checksums.
`current.json` changes only after a complete export. The native builder replaces
its entire `content/interests` and `content/obsidian` trees from the selected mode.
Deleted vault folders/articles/maps cannot return from Git seeds. Renames retain
IDs and redirects; a current page may reclaim an obsolete historical address.
Drafts and their assets stay out of published-only inputs. Editorial source is
private appdata and is never committed to Git.

## Production boundary

`status: published` is the publication action. Saves to published notes or their
referenced sources update both sites. Changing back to `draft` removes the public
article and its exclusive assets while keeping it on private staging. A browser
already displaying old content updates only on refresh; previously downloaded
copies cannot be recalled. Application-code releases remain a separate branch
workflow in the [production runbook](../../production/README.md).

## Verify and recover

```sh
npm ci --prefix hosts/infra/blog-publisher
npm test --prefix hosts/infra/blog-publisher
python3 hosts/infra/blog-publisher/test_install_vault.py
python3 hosts/infra/blog-publisher/test_run.py
python3 hosts/staging/test_editorial.py
python3 hosts/staging/test_deploy.py
python3 scripts/check-docs.py
```

Tests cover YAML isolation, comments, nested/section embeds, draft filtering,
covers, image edits, stable URLs, conflicts, symlinks, MDX escaping, checksums,
public/preview separation and existing release rollback. Live acceptance also
needs actual vault sync and rendered content/media through the private URL.

Read `journalctl -u dothomelab-blog-publisher.service` on CT110 for a bounded
validation error or export digest/count. Check `blog/current.json` on CT114 for
accepted code/content. No source YAML or credentials are logged. The private
network ACL protects drafts; noindex and draft metadata do not provide privacy.

Pause the new timer to stop imports, then use staging's retained release/image
rollback and pin the desired editorial `current.json`. Preserve snapshots;
cleanup is a separate authorized operation. Restore Mac settings from the named
backup only after comparing newer changes. Only unedited installer-created files
are uninstall candidates. History and release snapshots are canonical appdata in
scheduled PBS scope; the vault/original photos depend on their separate backup.
Synchronization is not independent backup. This change does not prove a new
vault restore or a clean-host rebuild.

## Live maps and names (111–113)

The Blog article template and existing map wrappers include optional
`starting-note: ""`. Set it to the exact name of a note on the drawing, or its
full vault path when names repeat. Maps open fitted to the drawing, then zoom
to the note; reduced motion and skipped navigation jump directly. Blank, missing
or ambiguous names keep the whole-map view. **Go to Starting note** returns to
the configured card; the button stays disabled when no target resolves. The
publisher validates the field as text and passes it to the portable viewer.

To add the blank field to existing wrappers and the installed article template,
without recreating renamed taxonomy folders or replacing authored content:

```sh
python3 hosts/infra/blog-publisher/install-vault.py \
  --vault /Users/rafael/Obsidian/obsidian-cloud-retrieval \
  --blog-repo /Users/rafael/Repos/blog --add-map-starting-notes
```

This idempotent migration preserves existing choices and verifies prior copies
under `.blog-publisher-backups/starting-notes-<timestamp>/`. To undo, compare
later author edits, then copy the affected file from that backup to its original
relative path. It changes neither original course notes nor publication state.

Embed an existing drawing in a Blog article with `![[full/vault/path/Map]]`.
The exporter follows the scene's local links and all transitive local note links,
embeds and attachments, deduplicating cycles; folder depth has no fixed limit.
It also retains the Embedded Files entries used by visible image elements,
including images without a navigation link and PDF page/rectangle references.
These attachments participate in cache invalidation and the wrapper's publication
selection. Missing image references fail the export before replacing its current
pointer. The blog build resolves their pixels and renders PDF excerpts; the
exporter preserves source bytes and native crop coordinates.
This selects the complete reference graph, so review connected prose before
marking the wrapper published. It strips YAML/comments from ordinary notes and
never writes IDs into source notes. Referenced Jupyter notebooks are downloads,
never executed. Missing map-note targets render an explicit unavailable card and appear in
`warnings.json`; no other note is substituted. Missing attachments, ambiguous
references and invalid scenes fail closed. Short links choose the nearest relative
path; equal-distance ambiguity needs an explicit path. `map-links` on a wrapper
can preserve an explicit source selection without rewriting normal notes.
Optional `map-include: ["[[vault/path/Note]]"]` retains additional reading pages
and their live dependencies even without a drawing element. The wrapper and its
whole map graph share draft/published selection.

`migrate-maps.mjs VAULT BLOG_REPOSITORY` adds the nine course wrappers as drafts,
retaining their article IDs/URLs and legacy collection IDs. It only creates new
files and records their paths in a named `.blog-publisher-backups/maps-*` manifest.
Existing wrappers and original course notes are preserved.
`migrate-map-links.mjs VAULT BLOG_REPOSITORY [SNAPSHOT]` backs up wrappers before
retaining the existing export's PDF edition choices where the vault has duplicate
basenames. With a selected snapshot directory, it also retains formerly exported
reading pages outside the current scene graph through `map-include`, using only
existing original vault files. The publisher ledger
in `state.json` retains readable per-map note routes, matching unchanged source
paths, stable drawing element IDs, then unique content hashes after moves.
An unembedded note renamed and edited simultaneously cannot be identified reliably;
its old route is reserved but automatic rename recovery is not guaranteed.

Map reading URLs are children of their article. Legacy generated indexes/notes
redirect to those addresses. YAML titles override fallback labels. Exact wrapper filenames supply article
headings; exact folder names supply menu labels. The folder note retains
identity, order and view. Renames update canonical URLs; all prior folder, article
and map-reading addresses redirect to their current locations. Current pages take precedence over historical aliases; remaining old addresses redirect. The staging adapter matches
migrated map collections against current and historical article URLs, preserving
draft exclusion even after a rename.

The ten-minute execution budget bounds a stuck exporter; systemd owns its single
process. Metadata identifies unchanged dependencies, SSD caches avoid rereading
large vault media, and immutable snapshot files share hardlinks. Native builds
retain dependencies and map/page caches, produce a complete static tree, and
switch it atomically. See [native publication](../../blog/README.md).

See [note readership](../observability/README.md#note-readership) for metrics.

## Clear descriptions

To clear only description properties under the Mac vault's `Blog/` tree:

```sh
python3 hosts/infra/blog-publisher/install-vault.py \
  --vault /Users/rafael/Obsidian/obsidian-cloud-retrieval \
  --blog-repo /Users/rafael/Repos/blog --clear-descriptions
```

The command verifies a copy of every changed file under
`.blog-publisher-backups/descriptions-<timestamp>/` before changing it. Bodies,
IDs, publication status and image alt text are retained. To restore, compare later
edits and copy only the desired file from that backup to its original relative path.
No changes require no backup. The normal publisher picks up the cleared fields.


### Astro and original-photo galleries

The blog builds with Astro while retaining the persistent React constellation.
`kind: gallery` notes use `---` separators, a `[[photo link]]`, and an optional
multiline description in each block. The publisher exports ordered original
attachments and `gallery.json`; only the selected published mode enters CT115.
Photographs, covers and article images are copied byte-for-byte, including EXIF
orientation and metadata. Descriptions are plain text shown only in the clicked
photo overlay. `Blog gallery.md` and `Blog photo.md` are installed with the existing
vault installer; `--refresh-authoring` preserves replacements in its named backup.
Build caches are disposable and scoped by inputs/configuration; complete immutable
release trees preserve deletions and draft filtering. Published content updates automatically.

### Folder-note migration and dates

`migrate-folder-notes.mjs ROOT` plans the migration; `--apply --backup DIRECTORY`
verifies original index and existing folder-note bytes before changing anything.
It merges metadata, moves Waypoint to the top, retains publication status/identity,
and removes only the backed-up `_index.md` files. Conflicting authored bodies fail
unless `--prefer-folder-body RELATIVE_FOLDER` explicitly selects the existing body.
For the About migration Rafael selected `about/about.md` over the short old index.
The backup's `migration.json` records original and resulting hashes. To roll back,
compare newer edits and restore each recorded original; remove newly created
folder notes only if their hash still matches the recorded migration.

Blank `lastEditedAt` uses the wrapper modification date; a YYYY-MM-DD value overrides
it, with legacy `updatedAt` retained. Lists and menus place explicit `order` values
first, descending (including zero/negative), then sort by newest `publishedAt`.
Heading-specific embeds omit the selected heading while retaining subheadings.
After migrating authoring files, refresh the installed templates and guide with
`install-vault.py --refresh-authoring`. New installations seed folder notes only.
