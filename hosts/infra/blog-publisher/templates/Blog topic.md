---
id: 'blog-topic-<% tp.date.now("YYYYMMDD-HHmmssSSS") %>'
title: ""
description: ""
order: ""
publishedAt: '<% tp.date.now("YYYY-MM-DD") %>'
lastEditedAt: ""
status: draft
kind: article
view: list
---

%% Give this note the same name as its containing folder: Blog/menu/menu.md or
Blog/menu/topic/topic.md. Keep Waypoint above your ordinary body or gallery.
Use view: cards for child article grids; the folder's own body needs no cover.
Higher order values come first. Blank order falls back to newest publishedAt.
Blank lastEditedAt uses the note's modification date. %%

%% Begin Waypoint %%
%% End Waypoint %%

<% tp.file.cursor() %>
