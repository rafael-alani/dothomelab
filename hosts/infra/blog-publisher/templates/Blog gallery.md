---
id: 'blog-<% tp.date.now("YYYYMMDD-HHmmssSSS") %>'
title: ""
description: ""
publishedAt: '<% tp.date.now("YYYY-MM-DD") %>'
lastEditedAt: ""
order: ""
status: draft
kind: gallery
tags: []
---

%% Use Blog photo to insert a photo block, or write the blocks yourself:
---
[[Assets/Photo.jpg|Describe what the photo shows]]
An optional description, shown only when the photo is opened.
---
A nonempty title overrides the exact filename. Put this note in a menu or topic,
or use the folder note itself to open the gallery directly.
Photos appear in the order of these blocks. Descriptions can span paragraphs.
The alias after | is optional alternative text, separate from the description.
Original files, orientation and metadata are preserved. %%

<% tp.file.cursor() %>
