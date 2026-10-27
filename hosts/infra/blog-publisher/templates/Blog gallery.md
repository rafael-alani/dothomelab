---
id: 'blog-<% tp.date.now("YYYYMMDD-HHmmssSSS") %>'
description: ""
publishedAt: '<% tp.date.now("YYYY-MM-DD") %>'
status: draft
kind: gallery
tags: []
---

%% Use Blog photo to insert a photo block, or write the blocks yourself:
---
[[Assets/Photo.jpg|Describe what the photo shows]]
An optional description, shown only when the photo is opened.
---
The filename is the gallery title. Put this note inside Blog/menu/topic.
Photos appear in the order of these blocks. Descriptions can span paragraphs.
The alias after | is optional alternative text, separate from the description.
Original files, orientation and metadata are preserved. %%

<% tp.file.cursor() %>
