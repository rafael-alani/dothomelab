# Write for the blog

Open [[Blog/Articles.base|Articles]] to switch between **Drafts**, **Published
selection**, and **All articles**. `published` makes the article live at [rafael.ink](https://rafael.ink).
Changing back to `draft` removes it there and keeps it on private staging.

1. Create a note in a topic folder under `Blog` (for example
   `Blog/art-corner/songs`). Run **Templater: Open insert template modal** and choose a
   **Blog article**, **Blog poem**, **Blog project**, or **Blog gallery** template.
2. Write directly, or embed an existing note with `![[Note name]]`. Use its full
   vault path if another note has the same name. `![[Note name#Heading]]` includes
   that section through the next heading of the same or higher level. The selected
   heading is omitted; its subheadings remain. Embedded
   YAML properties are always ignored, even invalid YAML. The wrapper's properties
   control publication. Nested embeds work; ordinary links do not copy notes.
3. Keep `status: draft` while writing. Both statuses appear on the private
   [staging site](https://blog.staging.rafael.media). Publication status stays in Obsidian; the reader interface is the same.
   After synchronization, the native publisher builds immediately; reload the
   page to see the new static files. Content edits
   need no code deployment or website restart.
4. Set `cover-media` to a local picture link, for example
   `"[[Assets/Photos/canal.jpg]]"`, and fill `cover-alt`. Your current
   `3. Resources/Attachments` folder also works. Paste pictures normally; only
   referenced pictures are exported. Covers are images; YouTube links belong
   in the body. Pictures retain their original bytes, orientation and metadata.
5. A topic's folder note has `view: list` or `view: cards` (grid). Grid articles
   require a cover and meaningful alt text before their status is published;
   drafts can preview without a cover. Add captions and body image alt text
   using ordinary Markdown image syntax.
6. Set `status: published` when ready. Descriptions are optional. This publishes
   automatically, and subsequent edits update the public article too. Set it back
   to `draft` to remove it from production while retaining the private preview.

## Photo galleries

Create a note inside `Blog/menu/topic` with **Blog gallery**. Insert **Blog photo**
for each picture; it lets you choose an attachment and optional description. Or
write the blocks after the YAML properties yourself:

```markdown
---
[[Assets/canal.jpg|Canal at dusk]]
An optional description, shown only after clicking the picture.
---

---
[[Assets/portrait.jpg]]
---
```

Photos keep this order. Descriptions may span paragraphs. The optional alias after
`|` is alternative text, separate from the description. The first photo is the
grid preview, so a gallery needs no cover field. Original orientation and metadata
stay in the served file. The large preview closes with ×, Escape, or a click on
the blurred background. Galleries use the same draft/published release workflow.

## Edit About

Open [[Blog/about/about|About]] to edit the biography and its menu properties in
one note. Keep Waypoint at the top; it is excluded from the website. The body
is rendered directly at `/about`, with no separate credits or embedded index.

## Folder pages

Every menu/topic uses its folder note: `Blog/menu/menu.md` or
`Blog/menu/topic/topic.md`. `_index` is retired. Keep the permanent ID when
renaming both the folder and its note. The YAML controls title, order and view;
the body after Waypoint is an ordinary article or a `kind: gallery` photo stream.
A menu can have no submenus. Its own body opens at the menu URL. Photography's
folder note opens directly at `/creativity/photography`, with lazy-loaded images.
Set the folder body to `draft` or `published` just like other notes; its menu
label can remain visible while its private body/photos stay out of production.

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
- A nonempty YAML `title` is displayed as written. Otherwise an article uses
  its exact filename, and a menu uses its readable folder name. Blank descriptions stay empty.
- `publishedAt` is a display date, not a scheduled publishing trigger. A blank or missing
  `lastEditedAt` uses the wrapper’s modification date; set YYYY-MM-DD to override
  it. Legacy `updatedAt` remains readable. Dates must be valid.
- `order` is optional: higher numbers come first, including explicit zero or
  negative values before all unordered notes. Equal priorities and unordered
  notes use `publishedAt`, newest first. Editing does not change publication order.
- Folder names and the article filename determine its current URL. Rename or
  move them normally, keeping the same IDs. Every old URL redirects to the new
  address, including map-reading links. Existing `slug` and `url` properties
  retain legacy addresses; they no longer override names. Do not reuse old
  addresses for a different article or folder.
- Use `kind: article`, `poem`, `project`, or `gallery`. The template supplies the right kind.
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

Rename a note/folder to change its fallback label and URL, or set `title` to
change only its visible label. Keep folder metadata in the folder note.
The nine course-map wrappers are in `Blog/technical-write-ups/ai`.

The Blog folder is the complete website content tree. Delete or move a menu,
topic or article here to remove or move it in the next private preview. Deleted
content is not restored from Git. Keep IDs when moving; old URLs redirect for
moves and return 404 for deletions. Published content updates automatically; application-code releases are separate.
