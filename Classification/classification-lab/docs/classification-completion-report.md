# Classification series: completion report

Branch `upgrade/publication-quality`. Nothing is pushed. The per-claim list of corrections is in `docs/classification-changelog.md` (36 entries, generated from the artifacts).

## What changed

- **Data contract.** The unit is a record, not a customer. `duration` is excluded because it is unavailable before the contact. `campaign` is excluded from the main feature set because its eligibility cannot be established; a sensitivity run shows its effect on AP is +0.0015 to +0.0018.
- **Protocol.** One module (`protocol.py`) defines a development split (80%) and a comparison split (20%), both stratified with seed 42. Tuning uses shuffled 3-fold CV on development rows only. The temporal study uses the first 80% of rows for development with expanding-window folds, and the last 20% as the future. Every experiment script imports this module.
- **Model comparison.** Twelve models plus a no-model prior baseline. Each model gets its default plus seven random candidates; the measured counts are reported. Defaults are shown as baselines next to the tuned results.
- **Technical corrections.** The ROC-AUC and prevalence argument, the non-converged hand-written logistic regression, class-weight equivalence, out-of-bag explanation, calibration folds and clipping, the CatBoost clone claim, the "thirteen classifiers" wording, and the "statistically tied" claim were all corrected or scoped.
- **Uncertainty.** Paired bootstrap with simultaneous max-t intervals. Stability over three independent re-tuned splits (seeds 100 to 102).
- **Temporal story.** Uncorrected, feasible correction (EM prior estimate) and oracle correction are separated, and all are compared with call-everyone.
- **Interpretation and errors.** Four importance questions are kept apart. Missed subscribers are analysed by policy, with Wilson intervals on segments.
- **Rewrite.** All 16 articles are rewritten in the hybrid format: a Goal/Work-plan callout, run-in labels, and one closing "Analysis and conclusion" section. Objective map, algorithm-family table and operational closure were added. The `ai-engineering` series is unchanged.
- **Reproducibility.** `run_all.py`, `README.md`, `requirements.txt`, `requirements.lock.txt`, `check_series.py`, `check_snippets.py`, and render-time execution of every code snippet.

## What was executed

- All experiment scripts, then `summarise.py`, `export_widgets.py`, `make_figures.py`.
- `build_articles.py` (all 16 parts), `check_series.py` (0 failures), `build_changelog.py`.
- `npm run build` (257 pages) and `validate_site.py` (57 articles, no broken local links).
- Printable editions: `print/classification.html` (16 parts) and `print/ai-engineering.html` (41 parts). `print/` is git-ignored.
- Timing was run alone on an otherwise idle machine.

## Conclusions that changed

- Leader order: the top boosters and the random forest are not separated from each other. Mean AP over three splits is 0.460 to 0.465 for LightGBM, HistGradientBoosting, XGBoost, random forest, CatBoost and extra trees; their rank ranges overlap. Against logistic regression, the simultaneous interval for random forest is [+0.0022, +0.0421], so the gain is small but not zero.
- Default settings are not neutral: random forest 0.385, extra trees 0.300 and decision tree 0.189 AP by default, against about 0.461, 0.460 and 0.433 after tuning (stability means).
- Threshold versus model: the old "threshold is 100% of profit, model about 3%" is now limited to these prices and policies.
- Temporal: the old "corrected model beats call-everyone" (12,240 against 12,082) no longer holds. LightGBM earns 5,375 uncorrected, 12,082 with the feasible EM correction (equal to call-everyone) and 11,947 with the oracle.
- Part 4: the hand-written/library discrepancy was non-convergence, not a flat valley.
- Part 7: the out-of-bag gap is not explained by tree count.

## Remaining limitations

- **Length target not met.** Core prose is about 9% longer than before, not 20 to 30% shorter. Code is folded but is not counted as removed.
- **Added after the first report.** Part 0 (series map) and Part 0b (sigmoid and the apple grid, with the Grid Lab widget and `export_apple_grid.py`). They are numbered 0 and 0b so parts 1 to 16 keep their numbers. Part 0b's apples are synthetic.
- **Temporal.** There is one future block, so those results carry no intervals.
- **Stability.** Three seeds were completed (five were planned). The run was stopped after seed 102 to keep the timing run clean. Part 13 reads the split count from `stability_notes.json`.
- **Thread sensitivity.** XGBoost results depend on the OpenMP thread count; do not run with fewer than 6 threads.
- **Timing.** Numbers are from one machine and one run (environment is recorded in `timing_environment.json`); they are indicative only.
- **Contribution** is a retrospective simulation, not an incremental (uplift) estimate.
- **Browser check.** Widgets and layout were not re-verified in a browser after the final render.
