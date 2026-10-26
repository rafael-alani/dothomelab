# Obsidian blog publisher

The CT110 job exports selected vault content to immutable appdata snapshots.
CT114's existing branch poller builds the private blog from the exact `staging`
code revision and content digest. Content-only changes atomically switch a retained
static tree and reload nginx configuration without replacing the web container. The website never receives the vault, Syncthing
credential, production environment or Docker socket.

## Authoring

`Blog/` mirrors the blog's menu/topic structure. The Mac installer adds article,
poem, project and topic templates, `Blog/Articles.base` with separate draft and
published views, and `Blog/_Start here.md` with the full author guide. It uses
the installed Templater community plugin and preserves its template folder and
other settings. Templater generates the permanent ID/date and body cursor.
It never overwrites existing author files by default. `--refresh-authoring`
backs up and replaces only the four Blog templates, guide and Articles base;
it never overwrites article notes or taxonomy. Prior settings and the created-file
list are retained in `.blog-publisher-backups/<timestamp>/` inside the vault.

```sh
python3 hosts/infra/blog-publisher/install-vault.py \
  --vault /Users/rafael/Obsidian/obsidian-cloud-retrieval \
  --blog-repo /Users/rafael/Repos/blog
```

For About, edit `Blog/about/about.md`; its body is embedded by
`Blog/about/_index.md` and rendered above the website's retained source credits.
The About folder body is sanitized with the article pipeline and supplied in both
export selections. Text, headings, web links and note text embeds are supported;
local About attachments fail with an explicit error. To migrate the originally
empty About notes, run the installer once with `--seed-about`; it backs up both
files and refuses to replace authored content. It changes no plugin settings.

Wrappers use `status: draft|published`, a permanent `id`, `kind`,
`description` and `publishedAt`. Article titles always use the filename; blank draft
descriptions show a placeholder. Dates do not schedule release. The exporter's
durable identity/history map preserves initial URLs across renames and reserves
retired addresses. Optional `url` deliberately changes a permalink.

`cover-media: "[[Assets/Photos/example.jpg]]"` and `cover-alt` provide card/social
images. The existing `3. Resources/Attachments` folder works too. A topic's
`_index.md` selects `view: cards` or `view: list`. Published grid articles require
a cover; drafts may remain incomplete. Covers are pictures; YouTube links stay in
the body. Images are oriented, bounded to 1600 pixels on each axis, and converted
to WebP without source EXIF/GPS. GIFs become still pictures. No external image
service or authenticated URL is fetched.

Whole-note, heading and nested embeds resolve relative to their source note or
an unambiguous vault path/name. Embedded YAML is discarded without parsing or
copying fields, including malformed YAML. Obsidian `%%comments%%` outside code
are removed. Only embeds copy note bodies. Private ordinary note links become
text; selected wrapper links become website links. Published wrappers do not link
to draft wrappers. HTML becomes text and MDX expressions are escaped. Code blocks,
Markdown tables and reference-style image links are supported. Ordinary article block embeds, executable MDX and vault plugins remain unsupported.
A whole Excalidraw embed uses the map pipeline described below.
Folder Notes/Waypoint navigation notes without article metadata are ignored.

Missing article/attachment references, unresolved ambiguity, invalid metadata, cycles/deep recursion, symlinks,
path escapes, relevant conflicts or changing dependencies leave the last export
unchanged. Source notes are never rewritten. An embed selects the entire body or
section, including nested embeds; review the resulting prose before publication.

## Install and operate

Compose owns the homelab assignments: read-only vault
`/vault/shared/media/obsidian` and writable output
`/srv/appdata/docker/staging/blog/editorial`. The container has no network,
capabilities or writable root. Package versions and the npm lockfile are retained.
The native wrapper checks Syncthing's loopback API without logging its credential.

After publishing and synchronizing the intended dothomelab revision:

```sh
pct exec 110 -- bash /opt/dothomelab/hosts/infra/blog-publisher/install.sh
pct exec 110 -- systemctl start dothomelab-blog-publisher.service
pct exec 110 -- systemctl status dothomelab-blog-publisher.timer
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --app blog
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --app blog --verify
```

Bootstrap installs the job with staging. Missing Blog input leaves the existing
site intact. The one-minute timer waits for idle sync and quiet dependencies;
the existing two-minute staging poller builds changed code/configuration/content.
Reload the browser after the automatic static refresh. No code push or manual
deployment is needed for content edits; the static build still runs automatically. Syncthing must be running on the Mac.
Use **Templater: Open insert template modal** in a new note. If the running app
has not noticed the settings, enable Templater under Community plugins or restart
Obsidian. The installer requires an existing Templater installation; it does not
download plugins or change core Templates settings.

Each digest directory holds `preview/` (all selected articles), `published/`
(published articles and only their assets), history, manifest and checksums.
`current.json` changes only after a complete export. The staging editorial adapter
verifies checksums and rejects extra files before making a separate build context.
It overlays folder metadata and moves renamed folders by their immutable identity.
A wrapper may replace a Git article only with the same ID; all other collisions fail.
Migrated maps follow wrapper publication selection, including removal of their
old Git fallback from published-only build contexts.
Each staging release retains its content snapshot, source bundle, code commit,
content digest and previous release. Nothing from the private vault is committed
to Git. The blog's `CONTENT_PREVIEW=1` build argument renders drafts in private
staging; normal builds default to excluding them.

## Production boundary

`published` means the author's selection for an approved public release, not
proof of live publication or authorization for unattended promotion. Approve an
exact successfully previewed code/content revision. A production builder must
call `editorial.materialize(..., mode='published')` using that retained snapshot,
then `npm run content:prepare` and the blog's normal production build with
`CONTENT_PREVIEW=0` and the production origin. It must never re-read the moving
vault or receive the preview tree. Draft bodies/assets are excluded from the
published build context. The full snapshot is private retained appdata.

This job automates private staging only and never promotes main or releases to
production. The separate [production runbook](../../production/README.md) owns
the main-only, explicitly authorized public release of a retained published
snapshot.

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
full vault path when names repeat, to open centered on that note. Blank, missing
or ambiguous names keep the whole-map opening view. **Starting note** returns to
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
redirect to those addresses. Wrapper filenames supply article headings; folder
names supply menu labels (hyphens/underscores become spaces). `_index` retains
identity, slug, order and view. Renames retain established article permalinks.

The 2 GiB exporter limit and ten-minute execution budget accommodate the selected
PDF-rich course library (about 990 MiB at migration).
The runner skips a still-active export and stops only its named disposable
export container on timeout, preventing overlapping snapshot writers.
Unchanged dependencies skip snapshot generation; identical snapshot files and
retained release inputs are hardlinked, never edited in place. Code/config changes
use normal container deployment. Content-only refresh uses a complete validated
static tree under `blog/static-site/`; its `current` symlink changes atomically.
The web container has 256 MiB for the old/new redirect tables during validation
and graceful reload.
`current.json` records each content digest. A failed cutover restores the previous
release through the existing deployment journal. Retained snapshots/images are
rollback inputs; do not prune them as part of routine editing.

See [note readership](../../apps/blog-observability/README.md#note-readership)
for the event definitions and mean/median report. No production activation is
part of this change.
