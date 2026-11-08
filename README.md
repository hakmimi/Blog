# Blog

My blog, live at https://hakmimi.github.io/Blog/. Built with Astro and the [AstroPaper](https://github.com/satnaing/astro-paper) theme (MIT). Published to GitHub Pages on every push to `main`.

## Write a post

Add a Markdown file in `src/content/posts/` with this frontmatter:

```yaml
---
author: Yitzhak
pubDatetime: 2026-11-08T10:00:00Z
title: My post
tags: [workflows]
description: One line about the post.
---
```

Preview locally:

```powershell
corepack pnpm@11.3.0 install
corepack pnpm@11.3.0 dev      # http://localhost:4321/Blog/
```

## Settings

Site name, author, links and features: `astro-paper.config.ts`.
