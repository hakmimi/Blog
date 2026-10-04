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
