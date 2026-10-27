---
id: 'blog-<% tp.date.now("YYYYMMDD-HHmmssSSS") %>'
description: ""
publishedAt: '<% tp.date.now("YYYY-MM-DD") %>'
status: draft
kind: article
cover-media: ""
cover-alt: ""
starting-note: ""
tags: []
---

<% tp.file.cursor() %>

%% Write here, or embed an existing note with ![[Note name]].
The title follows this file's name. Keep the ID when renaming or moving.
Description is optional and may stay empty. A grid cover uses:
cover-media: "[[Assets/Photo.jpg]]" (your existing attachments folder works too)
cover-alt: "Describe what the picture shows"
To embed only one section: ![[Note name#Heading]]
For a mind map: ![[Drawing name]]. Optionally set starting-note to a note name
shown in the map (or its full vault path when names repeat). Leave it blank to
start with the whole map. Starting note in the canvas header returns to that note.
Embedded YAML is ignored. The entire selected body, including nested embeds,
will be visible in private staging. See Blog/_Start here for the release rules. %%
