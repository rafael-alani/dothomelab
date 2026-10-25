# Obsidian blog publisher — 2026-10-25

## Scope and revisions

Implemented on `codex/obsidian-blog-publisher` in the canonical dothomelab
checkout. Runtime implementation is `5c348008336e0f22bea2cd23d4961ed4138d8a13`,
followed by the Templater installer/templates and this evidence. Blog runtime
is `634b57da9b2a7244072fe0a130c4608a6017af73` on `staging`; documentation follows
at `340547c`. Neither repository was promoted to main.

CT110 exports from the existing read-only synced vault to canonical staging
appdata. CT114 verifies the immutable export and builds the exact code/content
pair. Existing applications and their release fingerprints remain unaffected.
See the [publisher runbook](../../hosts/infra/blog-publisher/README.md).

## Observed acceptance

- Installed Blog taxonomy, four Templater templates, a draft/published Articles
  base and an author guide into the Mac's existing `obsidian-cloud-retrieval`
  vault. Preserved its `3. Resources/Templates` and attachment locations.
  Templater 2.25.0 was already installed/enabled; its folder was verified in the
  native settings UI. The temporary core Templates activation was undone.
- Original installation/settings backup:
  `.blog-publisher-backups/20261025T202953`. Templater refresh backup:
  `.blog-publisher-backups/20261025T210711044692`. Refresh changed five generated
  authoring files and zero article/source notes.
- Created one draft wrapper referencing the existing Mama’s Boy note. Started
  the installed Mac Syncthing app; the existing pairing transferred the wrapper
  to Infra. The original note was not edited. Actual export contains one draft,
  zero published articles, with digest
  `bdc8e7d3e5f87c9d81300b43e04e0c31d4da3d46c7b1fe84ebb6493da16d5017`.
- CT110 timer is enabled/active. Successful repeated runs produced the same
  digest. Busy synchronization was observed to defer a run while preserving
  the accepted release; the next idle run succeeded. Compose validation passed.
- CT114 accepted code `634b57d`, configuration `b767db8f19d1`, and that digest.
  Deployment verification passed. A real browser loaded the
  [private draft](https://blog.staging.rafael.media/art-corner/songs/mama-s-boy-dominic-fike),
  showing its wrapper title, original embedded prose and “Draft · private
  preview”. Embedded YAML did not render. The seed has no picture.
- Ten exporter tests passed: nested/section embeds, malformed embedded YAML,
  comments, local assets/image edits, published cover requirements, draft/public
  separation, stable addresses, ambiguous/missing refs, cycles, conflicts,
  symlinks and inert MDX/frontmatter. Four editorial-adapter and nine deployment
  tests passed. Blog typecheck, 62 unit tests, production build and two focused
  entry-view browser cases passed. Both image pipelines use Sharp 0.35.5; exporter
  npm audit reported zero vulnerabilities. Documentation checks passed.

## Retained recovery state

Both guests retain their original archive at
`/opt/dothomelab.before-blog-publisher-20261025` and first implementation at
`/opt/dothomelab.before-blog-publisher-fix-e8fa716`; existing `.previous` was not
removed. The Templater archive refresh additionally retains the runtime baseline
at `/opt/dothomelab.before-blog-templater-5c34800`. Staging keeps previous release
bundles/images and the immutable content snapshot; no cleanup was performed.

The PVE source checkout initially held an unrelated detached root-quota change
`7156d76f37bb498ad16f82a50fcff87751ef5076`. It is preserved under
`recovery/pre-blog-publisher-20261025`; after exporting the completed guest
archives, the clean checkout is returned to that revision. To inspect/restore
that source state, use `git -C /root/dothomelab switch --detach
recovery/pre-blog-publisher-20261025` after inspecting local changes. The new job
is retrievable from the published `codex/obsidian-blog-publisher` branch. No
quota, guest sizing or storage change was applied during this task.

Pause the publisher timer to stop new imports. Use the staging rollback command
for a retained release and pin the matching content pointer; do not delete
snapshots to roll back. Compare newer Mac edits before restoring backed-up
settings/templates. User prose stays in the synced vault, never Git.

## Limits

Production has no configured blog destination/route. `status: published` selects
the published-only export for a later approved release; it does not deploy
publicly. Private staging previews both statuses. No new public exposure,
production promotion or independent vault/PBS restore test occurred.

Referenced photo conversion and filtering were fixture-tested; the real draft
has no cover, so live user-photo presentation remains for author acceptance.
Native Templater installation/folder and generated syntax were checked; inserting
a new article through its modal was not exercised. Block-ID and Excalidraw embeds
and arbitrary vault plugin rendering remain unsupported. Syncthing is transport,
not an independent backup; existing backup/versioning gaps are unchanged.
