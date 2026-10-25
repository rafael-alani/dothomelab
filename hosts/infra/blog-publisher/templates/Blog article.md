---
id: 'blog-<% tp.date.now("YYYYMMDD-HHmmssSSS") %>'
title: ""
description: ""
publishedAt: '<% tp.date.now("YYYY-MM-DD") %>'
status: draft
kind: article
cover-media: ""
cover-alt: ""
tags: []
---

<% tp.file.cursor() %>

%% Write here, or embed an existing note with ![[Note name]].
Title defaults to this file's name. Keep the ID when renaming or moving.
Fill description before marking published. A grid cover uses:
cover-media: "[[Assets/Photo.jpg]]" (your existing attachments folder works too)
cover-alt: "Describe what the picture shows"
To embed only one section: ![[Note name#Heading]]
Embedded YAML is ignored. The entire selected body, including nested embeds,
will be visible in private staging. See Blog/_Start here for the release rules. %%
