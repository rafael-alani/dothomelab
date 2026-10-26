# Write for The Night Archive

Open [[Blog/Articles.base|Articles]] to switch between **Drafts**, **Published
selection**, and **All articles**. `published` means selected for the next
approved public release; it does not prove that a production site is live.

1. Create a note in a topic folder under `Blog` (for example
   `Blog/art-corner/songs`). Run **Templater: Open insert template modal** and choose a
   **Blog article**, **Blog poem**, or **Blog project** template.
2. Write directly, or embed an existing note with `![[Note name]]`. Use its full
   vault path if another note has the same name. `![[Note name#Heading]]` includes
   that section through the next heading of the same or higher level. Embedded
   YAML properties are always ignored, even invalid YAML. The wrapper's properties
   control publication. Nested embeds work; ordinary links do not copy notes.
3. Keep `status: draft` while writing. Both statuses appear on the private
   [staging site](https://blog.staging.rafael.media). Publication status stays in Obsidian; the reader interface is the same.
   Allow synchronization, the one-minute export check, and the two-minute build
   poller to finish; reload the page to see the static refresh. Content edits
   need no code deployment or website restart.
4. Set `cover-media` to a local picture link, for example
   `"[[Assets/Photos/canal.jpg]]"`, and fill `cover-alt`. Your current
   `3. Resources/Attachments` folder also works. Paste pictures normally; only
   referenced pictures are exported. Covers are images; YouTube links belong
   in the body. Pictures become web-sized WebP files without source metadata.
5. A topic's `_index` has `view: list` or `view: cards` (grid). Grid articles
   require a cover and meaningful alt text before their status is published;
   drafts can preview without a cover. Add captions and body image alt text
   using ordinary Markdown image syntax.
6. Fill the description and set `status: published` when ready. Review staging
   and explicitly approve its content revision for a production release.
   Production hosting is not yet configured; this setup never promotes code
   to main or exposes drafts publicly. Editing an already-published article
   updates staging; it does not automatically approve the new public version.

## Edit About

Open [[Blog/about/about|About]] to edit your biography. The folder's `_index`
embeds it and supplies the menu properties; keep that embed. Text, headings,
web links and note text embeds work. Local attachments are not supported here.
The site's astronomy credits stay below the editable biography. Changes follow
the same synchronization and private preview build as articles.

## Fields and safe editing

- `starting-note` optionally names a note on an embedded mind map. The map opens
  focused on it; **Starting note** returns there after exploring. Use the exact
  note name or its full vault path if names repeat. Leave it blank for the whole
  map. A missing or ambiguous name falls back to the whole map.
- `id` is generated when inserting the template. Keep it when renaming or
  moving; create a fresh template for a different article. Do not insert the
  template twice or copy another article's ID. Templater fills the date and ID
  and places the cursor in the body. Do not use the core Templates command;
  unprocessed Templater expressions are not valid articles.
- The filename supplies the article title; blank draft descriptions show “Draft preview.”
- `publishedAt` is a display date, not a scheduled publishing trigger. Optional
  `updatedAt` uses the same YYYY-MM-DD format. Dates must be valid.
- The initial URL is retained in the publisher's durable history. An optional
  `url: /menu/topic/my-address` deliberately changes it and reserves the old one.
- Use `kind: article`, `poem`, or `project`. The template supplies the right kind.
- Leave a cover blank when you do not need one in a list. A supplied cover always
  needs `cover-alt`. Do not use a private server URL or a token in an image link.
- Ordinary links to unselected private notes become plain text. To link to a
  blog page, link to its wrapper under Blog. A published wrapper never gets a
  link to a draft wrapper in its public export.
- Note embeds include the selected body. If a body contains private prose,
  choose a safe section instead. Raw HTML is displayed as text; code blocks are
  preserved. Ordinary article block-ID embeds, executable MDX and vault plugins
  are not supported. Embed a whole Excalidraw note to publish its interactive map
  and the complete graph of linked notes/attachments, at any folder depth.
  Original notes need no IDs. The Blog wrapper owns publication selection. Markdown tables, lists and ordinary links work.
- Missing pictures/notes/headings, ambiguous filenames, duplicate IDs, cycles,
  conflicts, or incomplete sync leave the last working preview online. Correct
  the reference or conflict and the next run retries. Source files are never
  rewritten by the server. Syncthing synchronization is not an independent backup.

Templates and this guide are excluded from article publication. The source
notes stay authoritative; exported copies are generated release snapshots.

Rename an article note to change its heading. Rename a menu/topic folder to change
its label. Keep order in `_index` for now; filename numbers do not change ordering.
The nine course-map wrappers are in `Blog/work-and-nerdy/ai-technical-write-ups`.
