---
title: "When Time Breaks the Model: Train on the Past, Decide on the Future"
description: "Train on the first 80% of the file and score the last 20%, where the share of subscribers jumps from 6.4% to 30.8%. Every choice stays inside the past; we compare corrections that could be applied and one that could not, then describe how to run such a policy for real."
series: "classification"
order: 16
date: 2026-09-30
updated: 2026-10-04
keywords: ["distribution shift", "prior shift", "temporal validation", "concept drift", "monitoring", "deployment"]
readingTime: "14 min read"
figure: "ch16-time-shift.png"
---

Train on the first 80% of the file and 6.4% of the training records are subscribers. Score the last 20% and the share is 30.8%. Under the illustrative prices, contacting *every* record in that last block earns 12,082 units. So the question is not only "which model ranks best on later records?" but "what does a model add to a baseline that is already strong?"

<div class="callout">

**Goal.** Evaluate models the way they would be used, on records that come after their training data.

**Work plan.** Cut the file by row order and keep every choice inside the past. Diagnose what shifted. Compare models and corrections within the future block and against call-everyone. Then describe how to test, monitor and maintain such a policy.

</div>

## The design

The file has no dates, so **row position is a proxy for time**: the first 80% of rows is the *past*, the last 20% the *future*. Settings are chosen with **expanding-window folds** inside the past (train on everything before a block, validate on the next).

| block | first row | last row | records | positives | prevalence |
|---|---|---|---|---|---|
| temporal development (first 80% of rows) | 0 | 32,949 | 32,950 | 2,100 | 0.064 |
| future (last 20% of rows) | 32,950 | 41,187 | 8,238 | 2,540 | 0.308 |
| temporal fold 1: train | 0 | 16,474 | 16,475 | 706 | 0.043 |
| temporal fold 2: train | 0 | 21,910 | 21,911 | 1,028 | 0.047 |
| temporal fold 3: train | 0 | 27,347 | 27,348 | 1,325 | 0.048 |
| temporal fold 1: validate | 16,475 | 21,910 | 5,436 | 322 | 0.059 |
| temporal fold 2: validate | 21,911 | 27,347 | 5,437 | 297 | 0.055 |
| temporal fold 3: validate | 27,348 | 32,949 | 5,602 | 775 | 0.138 |

Prevalence already drifts inside the past (5.9% to 13.8%), so AP is compared *within* a block, never across. Models and search spaces are those of part 12, with candidates scored by mean AP over the three validation blocks, early stopping on a random 10% of the training data (still the past), and one threshold policy chosen on the validation-block predictions. The Platt-scaled SVM is left out because its calibration folds would need an ordered design. The future block is scored once.

![Share of subscribers in each temporal validation block and in the future block, with record counts.](/series/classification/figures/ch16-folds.png)
*Figure 1. The blocks differ in prevalence even inside the past.*

## What shifted?

"The data changed" can mean different things with different remedies. **Prevalence** rose from 6.4% to 30.8%. The **inputs** moved: the macroeconomic columns are several standard deviations from their past values, and a classifier that tells past from future using only the inputs scores an AUC of 0.9999.

| column | future minus past in pooled SDs |
|---|---|
| age | -0.000 |
| pdays | -0.590 |
| previous | 0.790 |
| emp.var.rate | -2.960 |
| cons.price.idx | -1.130 |
| cons.conf.idx | 0.120 |
| euribor3m | -3.500 |
| nr.employed | -3.040 |

The **relationship between inputs and outcome** may also have changed, but we cannot see it, because both moved together. A **prior (label) shift** correction assumes something much narrower: that the *class-conditional* input distributions are stable and only the class proportions move. The near-perfect separability above is evidence against that.

## Ranking within the future block

All comparisons here use the same 8,238 future records. A random ranking scores the prevalence, 0.308. Do not compare these APs with part 12's: AP depends on prevalence, which is now five times higher.

| model | AP | AUC | mean score | ECE |
|---|---|---|---|---|
| Extra trees | 0.547 | 0.748 | 0.151 | 0.157 |
| k-nearest neighbours | 0.538 | 0.706 | 0.168 | 0.141 |
| CatBoost | 0.527 | 0.742 | 0.197 | 0.111 |
| Random forest | 0.514 | 0.735 | 0.144 | 0.164 |
| Gaussian Naive Bayes | 0.499 | 0.714 | 0.757 | 0.455 |
| Small neural net (MLP) | 0.492 | 0.664 | 0.118 | 0.190 |
| Logistic regression | 0.485 | 0.641 | 0.137 | 0.171 |
| sklearn HistGradientBoosting | 0.477 | 0.672 | 0.124 | 0.184 |
| LightGBM | 0.456 | 0.651 | 0.091 | 0.217 |
| Decision tree | 0.444 | 0.630 | 0.107 | 0.201 |
| XGBoost | 0.434 | 0.624 | 0.109 | 0.199 |

![Left: average precision on the future block. Right: simulated contribution at break-even 1/8 for each model with each correction; the dashed line is call-everyone.](/series/classification/figures/ch16-time-shift.png)
*Figure 2. Same models, same future records.*

The ordering is not the random-split one: extra trees, k-NN, CatBoost and the random forest lead on AP; logistic regression is in the middle; and scikit-learn's booster, LightGBM, the single tree and XGBoost come last, with XGBoost, the single tree and logistic regression lowest on AUC. It is one future block with no interval, so do not read differences of a few hundredths as an ordering. The robust point is that **the leaders of a random-split comparison are not guaranteed to lead on later records**, and that mean scores (about 0.09 for LightGBM) sit far below the true rate: the scores belong to the past.

## What a correction can and cannot do

Under an assumed label shift, a model's probabilities can be re-weighted by multiplying the odds by the ratio of new to old prior odds. A monotone correction cannot change AP or AUC; it changes *who crosses the threshold*. We try four priors, three of them available at decision time:

| Correction | Prior used | Available at decision time? |
|---|---|---|
| None | The past prevalence | Yes |
| Last window | Prevalence of the last validation block (13.8%) | Yes: a lagged estimate |
| EM | Estimated from the future block's scores alone (Saerens, Latinne and Decaestecker, 2002) | In principle: no labels needed, but it assumes label shift and calibrated scores |
| Oracle | The future's true prevalence (30.8%) | **No**: a diagnostic only |

Simulated contribution at the break-even threshold 1/8:

| model | none | last window | EM | oracle (not deployable) |
|---|---|---|---|---|
| Logistic regression | 7,665 | 11,802 | 12,082 | 12,088 |
| Gaussian Naive Bayes | 12,092 | 12,120 | 12,082 | 12,107 |
| k-nearest neighbours | 9,369 | 11,637 | 12,094 | 12,045 |
| Small neural net (MLP) | 7,083 | 10,999 | 12,082 | 12,005 |
| Decision tree | 6,722 | 10,037 | 11,965 | 11,025 |
| Random forest | 10,960 | 12,493 | 12,082 | 12,093 |
| Extra trees | 11,538 | 12,392 | 12,082 | 12,084 |
| sklearn HistGradientBoosting | 7,151 | 9,728 | 12,082 | 12,105 |
| XGBoost | 4,753 | 9,260 | 12,082 | 12,033 |
| LightGBM | 5,375 | 9,314 | 12,082 | 11,947 |
| CatBoost | 11,642 | 12,513 | 12,082 | 12,085 |

The yardstick is **call-everyone, 12,082**.

**Try it.** Pick a model, then tell it a base rate with the slider or the buttons (training period, last validation block, the EM estimate, the oracle). The widget shows how many records cross the threshold, the simulated contribution and the gain over call-everyone. Ranking never changes; only who is selected does.

<div class="prior-shift-lab" data-src="/series/classification/artifacts/prior_shift_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/prior-shift-lab.js"></script>

- **Uncorrected, almost every model earns less.** Scores tuned to a 6% world leave most future records below 1/8: LightGBM selects 21% of records and earns 5,375. Naive Bayes is the exception because its inflated probabilities select 93%.
- **The oracle brings most models to about call-everyone**, because with the true prevalence the corrected probabilities of nearly every record exceed 1/8: LightGBM selects 96% of records, logistic regression 100%. A correction that "restores the profit" has turned the policy into "contact (almost) everyone", and its advantage over call-everyone is a few units, not thousands. The first edition of this series reported 12,240 for a corrected LightGBM against 12,082 for call-everyone (+158). Recomputed with past-only development, the oracle-corrected LightGBM earns 11,947.
- **The last-window correction is a deployable middle path.** With a lagged prevalence of 13.8%, the random forest, extra trees and CatBoost earn 12,493, 12,392 and 12,513, about 300 to 430 (2.5% to 3.5%) above call-everyone. Naive Bayes ends within 40 units of it and the other models stay below it. The lagged estimate is itself too low.
- **EM fails here.** For seven of eleven models the iteration drifts to a prevalence near 1 and selects every record. That is what an unmet assumption looks like: the class-conditional input distributions did *not* stay put, so the estimator absorbs the shift in the inputs.

| model | EM prevalence estimate |
|---|---|
| Logistic regression | 1.000 |
| Gaussian Naive Bayes | 1.000 |
| k-nearest neighbours | 0.995 |
| Small neural net (MLP) | 1.000 |
| Decision tree | 0.624 |
| Random forest | 1.000 |
| Extra trees | 1.000 |
| sklearn HistGradientBoosting | 0.831 |
| XGBoost | 0.831 |
| LightGBM | 0.595 |
| CatBoost | 1.000 |

A simpler policy skips the prior correction: choose the contribution-maximising threshold on the past validation blocks and apply it unchanged.

| model | selected | share of records | contribution | gain over call-everyone |
|---|---|---|---|---|
| Extra trees | 5,857 | 71% | 12,687 | +605 |
| Random forest | 4,687 | 57% | 11,985 | -97 |
| Logistic regression | 7,567 | 92% | 11,289 | -793 |
| CatBoost | 3,753 | 46% | 10,823 | -1,259 |
| Gaussian Naive Bayes | 3,563 | 43% | 9,845 | -2,237 |
| LightGBM | 3,589 | 44% | 8,443 | -3,639 |
| k-nearest neighbours | 2,289 | 28% | 7,847 | -4,235 |
| Small neural net (MLP) | 2,594 | 31% | 7,470 | -4,612 |
| XGBoost | 3,235 | 39% | 7,093 | -4,989 |
| sklearn HistGradientBoosting | 2,001 | 24% | 6,879 | -5,203 |
| Decision tree | 2,446 | 30% | 6,722 | -5,360 |

Only extra trees beats call-everyone, by about +605 (5%). With a break-even of 12.5% and a rate of 30.8%, "contact almost everyone" is already a strong policy and a ranking has little left to add.

## Why did the leaders change? Hypotheses and ablations

It is tempting to say boosting failed because it leaned on the macroeconomic columns while logistic regression extrapolates smoothly. The data support less. We refitted three models with their chosen settings under two changes, each using only the past:

| model | variant | AP | AUC | mean score | contribution at 1/8 | selected |
|---|---|---|---|---|---|---|
| Logistic regression | as trained | 0.485 | 0.641 | 0.137 | 7,665 | 3,311 |
| Logistic regression | without the five macro columns | 0.554 | 0.725 | 0.109 | 5,901 | 1,347 |
| Logistic regression | trained on the more recent half of the past | 0.523 | 0.677 | 0.150 | 9,133 | 4,027 |
| LightGBM | as trained | 0.456 | 0.651 | 0.091 | 5,375 | 1,689 |
| LightGBM | without the five macro columns | 0.473 | 0.666 | 0.143 | 7,574 | 2,202 |
| LightGBM | trained on the more recent half of the past | 0.521 | 0.707 | 0.118 | 7,900 | 2,372 |
| Random forest | as trained | 0.514 | 0.735 | 0.144 | 10,960 | 4,088 |
| Random forest | without the five macro columns | 0.454 | 0.672 | 0.143 | 8,485 | 2,707 |
| Random forest | trained on the more recent half of the past | 0.495 | 0.728 | 0.151 | 10,844 | 4,156 |

Removing the macro columns raises the AP and AUC of logistic regression and LightGBM but lowers the forest's, and the contribution at 1/8 moves in different directions (down for logistic regression and the forest, up for LightGBM). Training on the more recent half of the past raises AP for LightGBM and logistic regression and lowers it slightly for the forest. No single column group or training window explains the reordering, so treat the macro-column story as a hypothesis these experiments do not confirm.

One diagnostic separates two kinds of failure. After the oracle prior correction LightGBM's calibration error falls from 0.22 to 0.06: for that model the base rate was the main problem. For logistic regression it barely moves (0.17 to 0.17), which points to a changed input-outcome relationship or to the covariate shift.

## Running this policy for real

None of this is specific to this dataset.

- **Test it prospectively.** Fix the metric before the test and compare the model policy with current practice, call-everyone and a random selection of the same size on a *random split of the planned contacts*. Judge incremental subscriptions net of cost, not AP.
- **Keep an exploration or control sample.** Treat a small random share of planned contacts regardless of score and, where acceptable, leave a small share uncontacted. The first gives unbiased estimates of the base rate and of calibration. The second is the only way to learn what happens *without* a contact, which separates response propensity from uplift (part 14).
- **Expect delayed, selective feedback.** Outcomes arrive late, so recent windows are incomplete. The prevalence among the contacts the model chose is not the prevalence among all candidates: a model that selects well makes its own base rate look high.
- **Monitor four things separately.** Ranking (AP and AUC on recent labelled records against the prevalence), calibration (mean score against observed rate, overall and near the threshold, with counts), policy (records selected and contribution against call-everyone and random) and economics (has the price list changed?). A past-versus-recent classifier on the inputs is a cheap early warning.
- **Recalibrate or retrain.** If ranking holds but mean score and rate diverge, and an updated base rate restores reliability near the threshold (as for LightGBM here), re-weight the prior using the control sample or a recent window. If ranking degrades against the baseline, or a base-rate update does not help (as for logistic regression here), retrain on recent records and rerun the protocol. Recent-half training helped two of three models in this chapter.
- **Capacity changes** change how many records are contacted, not the threshold. Keep the guard: up to capacity, highest scores first, never below the break-even score.
- **Simple model or booster?** Decide on evidence gathered the way you will deploy. In part 12 the boosted models led a random split; here they did not, and a simple baseline plus call-everyone were hard to beat. Keep a simple model in every comparison.
- **Scope.** This series covers binary classification on a table. Multiclass problems produce a vector of class probabilities (softmax, or one-vs-rest) and need per-class metrics and a choice of averaging, as in part 3. Multilabel problems are usually one binary problem per label, each with its own threshold.

## Analysis and conclusion: what we learned

- **Test the way you will deploy.** The leaders of the random split were not the leaders on later records, and the ordering within the future block rests on one sample.
- **Name what shifted.** Prevalence rose, the inputs moved far, and the relationship between them is unknown. A prior correction addresses only the first, and EM's assumptions failed visibly.
- **Compare with call-everyone.** Under these prices it earns 12,082; the best deployable policies beat it by about 2.5% to 5%.
- **Scores fail in different ways.** For LightGBM it was the base rate; for logistic regression it was not.

## Where the series ends up

1. A classifier supports a **decision**: fix the prediction moment, cost assumptions and capacity first (parts 1 and 14).
2. Check eligibility and the file's codes before comparing algorithms (part 2).
3. AP, log loss and simulated contribution answer different questions from accuracy (parts 3, 11, 14).
4. Under one written protocol, boosting and bagging models scored highest on a random split by a modest margin over logistic regression, and their order is not established (parts 12 and 13).
5. A cut-off should come from the economics and be checked, and scores must be calibrated near it to be read as probabilities (part 11).
6. Models can reorder on later records and a simple baseline can be hard to beat. Test the way you will deploy.

Every number in this series is written by a script in `series/classification/scripts` and read back by the article that cites it. If a number does not reproduce, that is a bug.

*Further reading.* Saerens, Latinne and Decaestecker (2002), [Adjusting the outputs of a classifier to new a priori probabilities](https://doi.org/10.1162/089976602753284446).

[Back to the series index](/series/classification/)
