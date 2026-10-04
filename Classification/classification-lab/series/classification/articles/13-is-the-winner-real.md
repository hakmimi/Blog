---
title: "Is the Winner Real? Uncertainty, Pairs and Other Splits"
description: "One AP number carries about ±0.035 of test-sample uncertainty. Paired comparisons are sharper, multiple comparisons make them weaker, and repeating the whole procedure on other splits shows how much of a ranking is luck."
series: "classification"
order: 13
date: 2026-09-30
updated: 2026-10-04
keywords: ["bootstrap", "paired comparison", "multiple comparisons", "confidence interval", "model selection", "variance"]
readingTime: "13 min read"
figure: "leaderboard-paired.png"
---

The model with the highest average precision on the comparison split scores @@v:uncertainty_single_ap.csv|model=sklearn HistGradientBoosting|ap|.3f@@. The model in second place scores @@v:uncertainty_single_ap.csv|model=LightGBM|ap|.3f@@. Somebody will want to write "wins" on a slide. Before they do, we should ask how much of that ordering would survive a different draw of records, a different training sample, or a different random search.

<div class="callout">

**Goal.** Say which differences in the leaderboard are supported by evidence and which are not, and be precise about what each analysis varies.

**Work plan.** Bootstrap one model's AP. Compare models in pairs on the same resampled records, with simultaneous intervals because we look at many pairs. Check how the result changes with a different resampling scheme. Repeat the whole procedure, search included, on five other splits.

**You will leave with** a vocabulary for what an interval does and does not show, and a defensible way to describe the leaderboard.

</div>

## What kind of uncertainty is this?

Four different things can move a model's score, and each analysis below varies only some of them.

| Source | Varied by | Where it appears here |
|---|---|---|
| Which comparison records you drew | Bootstrap of the comparison records | The intervals in the next two sections |
| Which training records the model saw | A different split | Final section |
| The model's own randomness (seeds, early-stopping slices) | A different fitting seed | Final section (it changes with the split) |
| Which hyperparameters the search happened to pick | A different search | Final section: every split re-tunes from scratch |

The bootstrap of saved predictions **conditions on the fitted models, their settings and their thresholds**. It resamples the 8,238 comparison records and recomputes each metric, so it describes test-sample uncertainty for these particular fits and nothing more.

## One AP is not precise

Resample the comparison records with replacement 2,000 times and recompute AP for every model on the same resamples:

@@table:uncertainty_single_ap.csv|sort=ap|desc|cols=model,ap,ap_lo,ap_hi,width|fmt=ap:.4f;ap_lo:.4f;ap_hi:.4f;width:.4f|rename=ap_lo:95% low,ap_hi:95% high@@

Each interval is about 0.07 wide, which is larger than the range of the top six models. With only 928 subscribers in the comparison split, an AP is not known better than roughly ±0.035 in this evaluation. That figure belongs to this model, this split and this prevalence, not to AP in general.

## Pairs are sharper

The wrong comparison puts two intervals side by side. The right one compares the two models on the *same* resampled records, so whatever makes a sample hard for one model (an unusual cluster of subscribers) usually makes it hard for the other, and the shared noise cancels. Below, each model is compared with the top-scoring one (scikit-learn's histogram booster) and with the logistic regression baseline.

We look at eleven models at once, so some intervals will exclude zero by chance. The tables give two intervals: the usual **marginal** 95% interval, and a **simultaneous** 95% interval from the max-t bootstrap, which controls the chance of *any* false exclusion among the eleven. Endpoints are given to four decimals so that "touches zero" can be judged.

**Against the top-scoring model.**

@@table:uncertainty_paired_ap.csv|where=resampling==rows|where=reference==sklearn HistGradientBoosting|cols=model,diff,ci95_lo,ci95_hi,simultaneous95_lo,simultaneous95_hi,share_resamples_above_zero|fmt=diff:+.4f;ci95_lo:+.4f;ci95_hi:+.4f;simultaneous95_lo:+.4f;simultaneous95_hi:+.4f;share_resamples_above_zero:.3f|rename=diff:AP difference,ci95_lo:marginal low,ci95_hi:marginal high,simultaneous95_lo:simultaneous low,simultaneous95_hi:simultaneous high,share_resamples_above_zero:resamples above zero@@

**Against logistic regression.**

@@table:uncertainty_paired_ap.csv|where=resampling==rows|where=reference==Logistic regression|sort=diff|desc|cols=model,diff,ci95_lo,ci95_hi,simultaneous95_lo,simultaneous95_hi|fmt=diff:+.4f;ci95_lo:+.4f;ci95_hi:+.4f;simultaneous95_lo:+.4f;simultaneous95_hi:+.4f|rename=diff:AP difference,ci95_lo:marginal low,ci95_hi:marginal high,simultaneous95_lo:simultaneous low,simultaneous95_hi:simultaneous high@@

![Paired AP differences from logistic regression, with marginal (dots, thin bars) and simultaneous (thick gold bars) 95% intervals.](/series/classification/figures/leaderboard-paired.png)
*Figure 1. Gold bars that cross the dashed zero line mean the data do not separate that model from the baseline once the number of comparisons is accounted for.*

How to read them, carefully.

- **An interval that includes zero is lack of evidence of a difference, not evidence of equality.** Nothing here shows that two models are equivalent. Claiming that a model is "not worse" would need a pre-specified margin and an analysis designed for it, which we do not have.
- **The column "resamples above zero" is an empirical resampling proportion**, the share of bootstrap resamples in which the model scored higher. It is not the probability that the model is better.
- **Against the top-scoring model:** the other boosters and the forest sit within 0.013 of it. Some marginal intervals exclude zero and the simultaneous ones are wider, so which of these differences are real is not settled by one comparison split. Models outside that group are separated from it: logistic regression, the SVM, k-NN, the neural net, the single tree and Naive Bayes all trail it, with simultaneous intervals that exclude zero.
- **Against logistic regression:** scikit-learn's booster, LightGBM and CatBoost beat it by about 0.02 to 0.03 AP, and their simultaneous intervals exclude zero. The random forest and XGBoost beat it on marginal intervals, but not once the eleven comparisons are accounted for. Extra trees, k-NN, the neural net, the single tree and the SVM are not separated from it.

The data are in file order and may be dependent (campaigns run in waves, and a client could be in several records). Resampling single records ignores that. As a stress test we resampled **blocks of 100 consecutive records** instead. This is not a calendar-exact analysis, because the file has no dates, only an order. The paired intervals against logistic regression change by only a few thousandths (for the top booster, @@v:uncertainty_paired_ap.csv|resampling=blocks of 100|reference=Logistic regression|model=sklearn HistGradientBoosting|ci95_lo|+.4f@@ to @@v:uncertainty_paired_ap.csv|resampling=blocks of 100|reference=Logistic regression|model=sklearn HistGradientBoosting|ci95_hi|+.4f@@ against @@v:uncertainty_paired_ap.csv|resampling=rows|reference=Logistic regression|model=sklearn HistGradientBoosting|ci95_lo|+.4f@@ to @@v:uncertainty_paired_ap.csv|resampling=rows|reference=Logistic regression|model=sklearn HistGradientBoosting|ci95_hi|+.4f@@ for single records), so dependence at that scale is not what drives the widths. Dependence we cannot see, such as the same client appearing repeatedly, is not tested by either scheme.

## What happens on other splits?

The bootstrap leaves the fitted models fixed. To vary the training sample, the seeds and the search as well, we repeated the whole procedure on **five other random 80/20 splits** (seeds 100 to 104). On each split every model is re-tuned from scratch on that split's development part with the same protocol (default plus seven random draws, 3-fold cross-validation), refit, and scored on that split's comparison part. Nothing chosen on one split is reused on another, so no split's comparison part helped choose anything for itself.

@@table:stability_summary.csv|cols=model,ap_mean,ap_sd,ap_min,ap_max,rank_mean,rank_best,rank_worst|fmt=rank_best:d;rank_worst:d;rank_mean:.1f|rename=ap_mean:mean AP,ap_sd:sd,ap_min:min,ap_max:max,rank_mean:mean rank,rank_best:best rank,rank_worst:worst rank@@

![Mean AP over five other splits, with each split as a dot. Each model is re-tuned on each split.](/series/classification/figures/leaderboard-stability.png)
*Figure 2. The spread across splits is larger than the gaps among the leading models.*

On these splits the models keep roughly the same grouping, but positions inside the leading group change from split to split, and a model's own AP moves by about as much as the gaps among the leaders. Five splits are too few to estimate those spreads precisely, so read them as an illustration of the size of the effect and not as a measurement of it.

## Statistical and practical significance

A difference can be statistically visible and still not matter, or the reverse. AP is a ranking metric; what a manager feels is the number of records to contact and the simulated contribution at a given capacity. Part 14 translates the differences into those units, and it also shows the cost side that AP cannot: a simple model that is a little behind in ranking can be much cheaper to run and explain.

## Analysis and conclusion: what we learned

- **A single AP has roughly ±0.035 of test-sample uncertainty here.** The top six models are within 0.013 of each other.
- **Pairs are sharper, but looking at many pairs weakens them.** Several marginal intervals that exclude zero do not survive a simultaneous interval.
- **Supported:** the three best-scoring boosters (the histogram booster, LightGBM and CatBoost) beat logistic regression by about 0.02 to 0.03 AP, with simultaneous intervals that exclude zero. **Not supported:** a strict ordering of the leading models, or a statement that any two of them are equivalent.
- **Other splits show the order moves.** The leaders change places from split to split, so "model X is best" describes one sample.
- **Dependence is a limit.** Row and block resampling gave similar widths, but neither can see repeated clients.

A defensible sentence for a slide: *On this benchmark, gradient-boosted models and a random forest scored about 0.02 to 0.03 average precision above logistic regression, and the evidence separates the three best boosters from it more clearly than the others. The data do not establish an order among the leading models.*

[Part 14](/series/classification/14-pricing-the-models/) puts the same frozen scores through an illustrative price list.
