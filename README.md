# Blog

My blog, live at https://hakmimi.github.io/Blog/. Built with Astro and the [Fuwari](https://github.com/saicaca/fuwari) theme (MIT). Published to GitHub Pages on every push to `main`.

## Write a post

```powershell
corepack pnpm new-post <file-name>   # creates src/content/posts/<file-name>.md
corepack pnpm dev                    # preview at http://localhost:4321/Blog/
```

Frontmatter: `title, published, description, tags, category, draft`.

## Settings

Site name, profile, links and colors: `src/config.ts`.
