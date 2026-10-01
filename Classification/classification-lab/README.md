# Applied ML Notebook

A multi-series, code-first blog about applied machine learning, built with Astro. Every article has a creation date and keywords; keywords generate topic pages (`/topics/`), and each series lives under `/series/<series>/`.

Currently published:

- **Classification** (16 parts): UCI Bank Marketing, 13 classifiers compared head to head, with runnable code and the real output pasted into every post.

## Add a new series

1. Add an entry to `src/data/series.ts`.
2. Put articles in `src/content/articles/<series>/NN-slug.md` with frontmatter: `title, description, series, order, date, keywords[], readingTime, figure`.
3. Put scripts, figures and artifacts in `series/<series>/{scripts,figures,artifacts}`. `npm run sync` copies them to `public/series/<series>/`.

## Build the site

Requirements: Node.js 22+.

```powershell
npm install
npm run build
python scripts\validate_site.py     # frontmatter, word counts, broken links, search index
```

`npm run dev` for authoring, `npm run preview` after a build. Output goes to `dist/`.

## Reproduce the classification series

Requirements: Python 3.13 (tested), then:

```powershell
python -m pip install -r requirements.txt
python series\classification\scripts\download_data.py     # UCI download + checksum
python series\classification\scripts\run_leaderboard.py  # 13-model race (long: tuning + bootstrap)
python series\classification\scripts\chapter_figures.py  # figures for parts 1-11 and 16
python series\classification\examples\ch12.py            # per-chapter example scripts (ch01..ch16)
python scripts\check_snippets.py 01 02 03                # execute the code blocks in the posts
```

The raw CSV is git-ignored. `download_data.py` validates 41,188 rows and 20 input columns.

### Protocol

- Prediction moment: before the call is made. `duration` is leakage and is dropped everywhere.
- Main split: stratified 80/20, seed 42 (32,950 train / 8,238 test).
- Every model gets the same tuning budget: 8 random candidates, 3-fold CV, scored on average precision.
- Cost model: a call costs 1, a subscription is worth 8, so break-even probability is 1/8. Thresholds are chosen on out-of-fold training predictions.
- Part 16 re-runs the race chronologically (first 80% of rows vs last 20%); the ranking changes.

## Data attribution

Moro, S., Rita, P., & Cortez, P. (2014). *Bank Marketing* [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5K306>. Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Project code and original prose/figures are MIT licensed; the dataset retains its CC BY 4.0 terms.
