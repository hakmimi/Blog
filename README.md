# Blog

Astro site, published to GitHub Pages on every push to `main`.

## Add a series

1. Add an entry to `src/data/series.ts`.
2. Put posts in `src/content/articles/<series>/NN-slug.md` (frontmatter: `title, description, series, order, date, keywords[], readingTime`).
3. Optional: figures and artifacts in `series/<series>/{figures,artifacts}`.

## Run locally

```powershell
npm install
npm run dev
```

## Credits

Colors and typography adapted from the [Riviera Villa Lite](https://github.com/riviera-themes/riviera-villa-lite) Astro theme (MIT).
