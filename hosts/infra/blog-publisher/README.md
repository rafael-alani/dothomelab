# Obsidian blog publisher

The CT110 job exports selected vault content to immutable appdata snapshots.
CT114's existing branch poller builds the private blog from the exact `staging`
code revision and content digest. The website never receives the vault, Syncthing
credential, production environment or Docker socket.

## Authoring

`Blog/` mirrors the blog's menu/topic structure. The Mac installer adds article,
poem, project and topic templates, `Blog/Articles.base` with separate draft and
published views, and `Blog/_Start here.md` with the full author guide. It enables
Obsidian's core Templates plugin and preserves the existing template folder.
It never overwrites existing author files. Prior settings and the created-file
list are retained in `.blog-publisher-backups/<timestamp>/` inside the vault.

```sh
python3 hosts/infra/blog-publisher/install-vault.py \
  --vault /Users/rafael/Obsidian/obsidian-cloud-retrieval \
  --blog-repo /Users/rafael/Repos/blog
```

Wrappers use `status: draft|published`, a permanent `id`, `kind`, `title`,
`description` and `publishedAt`. Blank draft titles use the filename; blank draft
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
Markdown tables and reference-style image links are supported. Block IDs,
Excalidraw embeds, executable MDX and vault plugins are unsupported in this article
pipeline; the existing registered map collections retain their separate contract.
Folder Notes/Waypoint navigation notes without article metadata are ignored.

Missing/ambiguous references, invalid metadata, cycles/deep recursion, symlinks,
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
Reload the browser after deployment. Syncthing must be running on the Mac.
If the running Obsidian app has not noticed the new settings, enable Templates
under Core plugins or restart Obsidian. No community plugin is installed.

Each digest directory holds `preview/` (all selected articles), `published/`
(published articles and only their assets), history, manifest and checksums.
`current.json` changes only after a complete export. The staging editorial adapter
verifies checksums and rejects extra files before making a separate build context.
It overlays folder metadata but refuses collisions with repository articles.
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

No production blog destination/route is currently configured. This job automates
private staging only and never promotes main or exposes a new public service.
Production hosting and its approval handoff remain an explicit rollout gap.

## Verify and recover

```sh
npm ci --prefix hosts/infra/blog-publisher
npm test --prefix hosts/infra/blog-publisher
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
