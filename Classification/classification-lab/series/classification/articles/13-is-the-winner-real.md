---
title: "Is the Winner Real? Uncertainty, Pairs and Other Splits"
description: "One AP number carries about ±0.035 of test-sample uncertainty. Paired comparisons are sharper, multiple comparisons make them weaker, and repeating the whole procedure on other splits shows how much of a ranking is luck."
series: "classification"
order: 13
date: 2026-09-30
updated: 2026-10-04
keywords: ["bootstrap", "paired comparison", "multiple comparisons", "confidence interval", "model selection", "variance"]
readingTime: "11 min read"
figure: "leaderboard-paired.png"
---

The model with the highest average precision on the comparison split scores @@v:uncertainty_single_ap.csv|model=sklearn HistGradientBoosting|ap|.3f@@. The second scores @@v:uncertainty_single_ap.csv|model=LightGBM|ap|.3f@@. Somebody will want to write "wins" on a slide. First ask how much of that ordering would survive a different draw of records, a different training sample or a different random search.

<div class="callout">

**Goal.** Say which differences in the leaderboard are supported by evidence, and be precise about what each analysis varies.

**Work plan.** Bootstrap one model's AP. Compare models in pairs on the same resampled records with simultaneous intervals (because we look at many pairs). Change the resampling scheme as a stress test. Then repeat the whole procedure, search included, on other splits.

</div>

## What kind of uncertainty is this?

| Source | Varied by | Where |
|---|---|---|
| Which comparison records were drawn | Bootstrap of the comparison records | The next two sections |
| Which training records the model saw, and its own randomness | A different split and seed | Final section |
| Which hyperparameters the search picked | A different search | Final section: every split re-tunes from scratch |

The bootstrap of saved predictions **conditions on the fitted models, their settings and thresholds**: it describes test-sample uncertainty for these fits and nothing more.

## One AP is not precise, but pairs are sharper

Resampling the 8,238 comparison records 2,000 times gives each model an interval about 0.07 wide, larger than the range of the top six:

@@table:uncertainty_single_ap.csv|sort=ap|desc|cols=model,ap,ap_lo,ap_hi|fmt=ap:.4f;ap_lo:.4f;ap_hi:.4f|rename=ap_lo:95% low,ap_hi:95% high@@

With 928 subscribers, an AP is known to about ±0.035 *in this evaluation*; that figure belongs to this model, split and prevalence, not to AP in general. The right comparison puts two models on the *same* resamples, so shared noise cancels. Because we look at eleven models at once, the tables give both the marginal 95% interval and a **simultaneous** one (max-t bootstrap), which controls the chance of *any* false exclusion of zero. Endpoints have four decimals so "touches zero" can be judged.

**Against logistic regression.**

@@table:uncertainty_paired_ap.csv|where=resampling==rows|where=reference==Logistic regression|sort=diff|desc|cols=model,diff,ci95_lo,ci95_hi,simultaneous95_lo,simultaneous95_hi|fmt=diff:+.4f;ci95_lo:+.4f;ci95_hi:+.4f;simultaneous95_lo:+.4f;simultaneous95_hi:+.4f|rename=diff:AP difference,ci95_lo:marginal low,ci95_hi:marginal high,simultaneous95_lo:simultaneous low,simultaneous95_hi:simultaneous high@@

**Against the top-scoring model (scikit-learn's histogram booster).**

@@table:uncertainty_paired_ap.csv|where=resampling==rows|where=reference==sklearn HistGradientBoosting|cols=model,diff,ci95_lo,ci95_hi,simultaneous95_lo,simultaneous95_hi,share_resamples_above_zero|fmt=diff:+.4f;ci95_lo:+.4f;ci95_hi:+.4f;simultaneous95_lo:+.4f;simultaneous95_hi:+.4f;share_resamples_above_zero:.3f|rename=diff:AP difference,ci95_lo:marginal low,ci95_hi:marginal high,simultaneous95_lo:simultaneous low,simultaneous95_hi:simultaneous high,share_resamples_above_zero:resamples above zero@@

![Paired AP differences from logistic regression, with marginal (dots, thin bars) and simultaneous (thick gold bars) 95% intervals.](/series/classification/figures/leaderboard-paired.png)
*Figure 1. Gold bars that cross the dashed zero line mean the data do not separate that model from the baseline once the number of comparisons is accounted for.*

- **An interval that includes zero is lack of evidence of a difference, not evidence of equality.** Claiming "not worse" would need a pre-specified margin and an analysis built for it, which we do not have. "Resamples above zero" is an empirical resampling proportion, not the probability that a model is better.
- **Against logistic regression:** scikit-learn's booster, LightGBM and CatBoost lead by about 0.02 to 0.03 AP with simultaneous intervals that exclude zero. The forest and XGBoost lead on marginal intervals only. Extra trees, k-NN, the neural net, the single tree and the SVM are not separated from it.
- **Against the top model:** the other boosters and the forest are within 0.013 of it. Which of those differences are real is not settled by one split. Logistic regression, the SVM, k-NN, the neural net, the single tree and Naive Bayes trail it, with simultaneous intervals that exclude zero.
- **Dependence.** The file is in order and records may be dependent. As a stress test we resampled **blocks of 100 consecutive records** (not calendar-exact: the file has no dates). The booster's interval against logistic regression moves from @@v:uncertainty_paired_ap.csv|resampling=rows|reference=Logistic regression|model=sklearn HistGradientBoosting|ci95_lo|+.4f@@ to @@v:uncertainty_paired_ap.csv|resampling=rows|reference=Logistic regression|model=sklearn HistGradientBoosting|ci95_hi|+.4f@@ (records) to @@v:uncertainty_paired_ap.csv|resampling=blocks of 100|reference=Logistic regression|model=sklearn HistGradientBoosting|ci95_lo|+.4f@@ to @@v:uncertainty_paired_ap.csv|resampling=blocks of 100|reference=Logistic regression|model=sklearn HistGradientBoosting|ci95_hi|+.4f@@ (blocks), so dependence at that scale is not driving the widths. Repeated clients, which neither scheme can see, remain untested.

## What happens on other splits?

To vary the training sample, the seeds and the search too, we repeated the whole procedure on **@@j:stability_notes.json|n_splits@@ other random 80/20 splits** (seeds @@j:stability_notes.json|seed_range@@). On each, every model is re-tuned from scratch (default plus seven random draws, 3-fold CV), refit and scored on that split's comparison part. Nothing chosen on one split is reused on another.

@@table:stability_summary.csv|cols=model,ap_mean,ap_sd,ap_min,ap_max,rank_mean,rank_best,rank_worst|fmt=rank_best:d;rank_worst:d;rank_mean:.1f|rename=ap_mean:mean AP,ap_sd:sd,ap_min:min,ap_max:max,rank_mean:mean rank,rank_best:best rank,rank_worst:worst rank@@

![Mean AP over the other splits, with each split as a dot. Each model is re-tuned on each split.](/series/classification/figures/leaderboard-stability.png)
*Figure 2. The spread across splits is comparable to the gaps among the leading models.*

The leading group stays roughly the same, but positions inside it change from split to split, and a model's own AP moves by about as much as the gaps among the leaders. A handful of splits is too few to estimate those spreads precisely, so read them as an illustration of the size of the effect.

## Statistical and practical significance

A difference can be visible and still not matter, or the reverse. AP is a ranking metric; what operations feel is the number of records contacted and the simulated contribution at a given capacity. Part 14 translates the differences into those units, and notes what AP cannot show: a model a little behind in ranking may be much cheaper to run and explain.

## Analysis and conclusion: what we learned

- **A single AP carries roughly ±0.035 of test-sample uncertainty here**, and the top six models lie within 0.013 of each other.
- **Pairs are sharper, but looking at many weakens them:** several marginal intervals that exclude zero do not survive a simultaneous interval.
- **Supported:** the histogram booster, LightGBM and CatBoost beat logistic regression by about 0.02 to 0.03 AP. **Not supported:** a strict order among the leaders, or equivalence of any two.
- **Other splits move the order**, so "model X is best" describes one sample.

A defensible sentence for a slide: *On this benchmark, gradient-boosted models and a random forest scored about 0.02 to 0.03 average precision above logistic regression, and the evidence separates the three best boosters from it more clearly than the others. The data do not establish an order among the leading models.*

*Further reading.* Efron (1979), [Bootstrap methods: another look at the jackknife](https://doi.org/10.1214/aos/1176344552); Westfall and Young (1993), *Resampling-Based Multiple Testing* (the max-t method used for the simultaneous intervals); Wilson (1927), *Journal of the American Statistical Association* 22, 209-212 (the score interval used for proportions).

[Part 14](/series/classification/14-pricing-the-models/) puts the same frozen scores through an illustrative price list.
