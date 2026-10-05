# Editing the text without rerunning the experiments

**Edit the templates, not the rendered files.**

| What | Where |
|---|---|
| Source text of each part (edit this) | `series/classification/articles/NN-slug.md` (`00-`, `00b-`, `01-` to `16-`) |
| Rendered copy that the site reads (do not edit, it is overwritten) | `src/content/articles/classification/` |
| Numbers, tables and code output | `series/classification/artifacts/` (made by the experiments) |

## The loop for a text change (seconds, no experiments)

1. Edit the prose in a template. Keep `@@...@@` tokens and the fenced `python` and `output` blocks as they are.
2. Render it: `python scripts/build_articles.py 05` (or several: `... 05 06`, or none for all parts).
   Unchanged code snippets are read from `artifacts/snippet_cache.json`, so nothing is recomputed.
3. With `npm run dev` running, the page refreshes by itself.
4. Before you commit: `python scripts/check_series.py` (must say `0 failure(s)`).

## What does and does not trigger real computation

- **Prose, headings, links, front matter:** no computation.
- **A number in the prose:** replace it with a token so it cannot drift, for example `@@j:data_profile.json|prevalence|.1%@@`. Plain typed numbers still work, but the checks cannot protect them.
- **Editing a `python` block:** only that article is re-run (cached blocks before it are replayed quickly). The output block below it is filled in automatically; leave it as `(filled in by the build)` or any text.
- **The big experiments** (`series/classification/scripts/run_all.py`, hours): only needed if you change models, data handling or the protocol. Text edits never need them.

## Other outputs

- Printable white edition: `npm run print` (needs a fresh `npm run build` first).
- Full site check: `npm run build`, then `python scripts/validate_site.py`.
- Change log: `python scripts/build_changelog.py` (text lives in that script).

If you edit a rendered file by mistake, copy the change into the template, because the next render overwrites it.

## Hebrew (right-to-left) copies

- Hebrew templates live in `series/classification/articles/he/` with the same file name as the English part (`00-start-here.md`, `00b-...md`). They have `lang: "he"` in the front matter and the same `order`.
- The `python` blocks must stay **identical** to the English ones (the check enforces this); translate only the prose, headings and table headings. Numbers still come from tokens such as `@@j:...@@`.
- Render with `python scripts/build_articles.py 00b`, which renders the English and the Hebrew copy of that part. Rendered Hebrew goes to `src/content/articles/he/classification/` (do not edit).
- Pages are served at `/he/series/classification/<slug>/`; the English page shows an "עברית" link and the Hebrew page an "English" link.
- Printable Hebrew edition: `python scripts/build_print.py classification --lang he --title "סדרת הסיווג" --out print/classification-he.html`.
- To translate another part: copy its English template into `he/`, add `lang: "he"`, translate, then render. Untranslated parts simply have no Hebrew page.
- The two lab widgets of part 0b take `data-lang="he"` for Hebrew labels; charts and sliders stay left-to-right.
- The Fruit Lab exists as a widget (`public/js/fruit-lab.js`, `data-lang="he"` for Hebrew) and as a Hebrew page at `/he/series/classification/fruit-lab/` (`src/pages/he/series/classification/fruit-lab.astro`).

## Text only: nothing is recomputed

`python scripts/build_articles.py 00` (or `npm run render` for every part) only re-renders the text. It does **not** run the model experiments (`run_all.py`) and it does not fit any model: numbers come from the saved files in `series/classification/artifacts/`, and code snippets are answered from `snippet_cache.json` unless you changed that snippet. While `npm run dev` is running, the page refreshes by itself a few seconds after the render.
