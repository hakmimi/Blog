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

The model with the highest average precision on the comparison split scores 0.492. The second scores 0.491. Somebody will want to write "wins" on a slide. First ask how much of that ordering would survive a different draw of records, a different training sample or a different random search.

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

| model | ap | 95% low | 95% high |
|---|---|---|---|
| sklearn HistGradientBoosting | 0.4917 | 0.4580 | 0.5283 |
| LightGBM | 0.4909 | 0.4567 | 0.5278 |
| Random forest | 0.4863 | 0.4524 | 0.5231 |
| CatBoost | 0.4844 | 0.4495 | 0.5212 |
| Extra trees | 0.4821 | 0.4484 | 0.5181 |
| XGBoost | 0.4795 | 0.4451 | 0.5182 |
| Small neural net (MLP) | 0.4696 | 0.4339 | 0.5067 |
| Decision tree | 0.4650 | 0.4306 | 0.5014 |
| Logistic regression | 0.4642 | 0.4289 | 0.5003 |
| Linear SVM (Platt scaled) | 0.4608 | 0.4244 | 0.4963 |
| k-nearest neighbours | 0.4547 | 0.4205 | 0.4910 |
| Gaussian Naive Bayes | 0.4048 | 0.3719 | 0.4394 |

With 928 subscribers, an AP is known to about ±0.035 *in this evaluation*; that figure belongs to this model, split and prevalence, not to AP in general. The right comparison puts two models on the *same* resamples, so shared noise cancels. Because we look at eleven models at once, the tables give both the marginal 95% interval and a **simultaneous** one (max-t bootstrap), which controls the chance of *any* false exclusion of zero. Endpoints have four decimals so "touches zero" can be judged.

**Against logistic regression.**

| model | AP difference | marginal low | marginal high | simultaneous low | simultaneous high |
|---|---|---|---|---|---|
| sklearn HistGradientBoosting | +0.0275 | +0.0140 | +0.0415 | +0.0088 | +0.0463 |
| LightGBM | +0.0267 | +0.0143 | +0.0403 | +0.0089 | +0.0445 |
| Random forest | +0.0221 | +0.0085 | +0.0379 | +0.0022 | +0.0421 |
| CatBoost | +0.0202 | +0.0078 | +0.0338 | +0.0025 | +0.0379 |
| Extra trees | +0.0178 | +0.0043 | +0.0316 | -0.0009 | +0.0366 |
| XGBoost | +0.0152 | +0.0047 | +0.0282 | -0.0008 | +0.0312 |
| Small neural net (MLP) | +0.0054 | -0.0029 | +0.0153 | -0.0071 | +0.0178 |
| Decision tree | +0.0008 | -0.0152 | +0.0165 | -0.0207 | +0.0222 |
| Linear SVM (Platt scaled) | -0.0034 | -0.0085 | +0.0018 | -0.0105 | +0.0036 |
| k-nearest neighbours | -0.0095 | -0.0225 | +0.0039 | -0.0274 | +0.0084 |
| Gaussian Naive Bayes | -0.0594 | -0.0780 | -0.0427 | -0.0837 | -0.0352 |

**Against the top-scoring model (scikit-learn's histogram booster).**

| model | AP difference | marginal low | marginal high | simultaneous low | simultaneous high | resamples above zero |
|---|---|---|---|---|---|---|
| Logistic regression | -0.0275 | -0.0415 | -0.0140 | -0.0467 | -0.0083 | 0.000 |
| Linear SVM (Platt scaled) | -0.0309 | -0.0458 | -0.0170 | -0.0510 | -0.0109 | 0.000 |
| Gaussian Naive Bayes | -0.0870 | -0.1080 | -0.0666 | -0.1157 | -0.0582 | 0.000 |
| k-nearest neighbours | -0.0370 | -0.0495 | -0.0245 | -0.0546 | -0.0193 | 0.000 |
| Small neural net (MLP) | -0.0222 | -0.0348 | -0.0091 | -0.0400 | -0.0043 | 0.002 |
| Decision tree | -0.0268 | -0.0400 | -0.0152 | -0.0443 | -0.0092 | 0.000 |
| Random forest | -0.0054 | -0.0137 | +0.0036 | -0.0175 | +0.0067 | 0.117 |
| Extra trees | -0.0097 | -0.0176 | -0.0013 | -0.0210 | +0.0017 | 0.009 |
| XGBoost | -0.0123 | -0.0198 | -0.0035 | -0.0236 | -0.0009 | 0.004 |
| LightGBM | -0.0009 | -0.0072 | +0.0065 | -0.0104 | +0.0087 | 0.413 |
| CatBoost | -0.0073 | -0.0159 | +0.0020 | -0.0199 | +0.0053 | 0.070 |

![Paired AP differences from logistic regression, with marginal (dots, thin bars) and simultaneous (thick gold bars) 95% intervals.](/series/classification/figures/leaderboard-paired.png)
*Figure 1. Gold bars that cross the dashed zero line mean the data do not separate that model from the baseline once the number of comparisons is accounted for.*

- **An interval that includes zero is lack of evidence of a difference, not evidence of equality.** Claiming "not worse" would need a pre-specified margin and an analysis built for it, which we do not have. "Resamples above zero" is an empirical resampling proportion, not the probability that a model is better.
- **Against logistic regression:** scikit-learn's booster, LightGBM and CatBoost lead by about 0.02 to 0.03 AP with simultaneous intervals that exclude zero. The forest and XGBoost lead on marginal intervals only. Extra trees, k-NN, the neural net, the single tree and the SVM are not separated from it.
- **Against the top model:** the other boosters and the forest are within 0.013 of it. Which of those differences are real is not settled by one split. Logistic regression, the SVM, k-NN, the neural net, the single tree and Naive Bayes trail it, with simultaneous intervals that exclude zero.
- **Dependence.** The file is in order and records may be dependent. As a stress test we resampled **blocks of 100 consecutive records** (not calendar-exact: the file has no dates). The booster's interval against logistic regression moves from +0.0140 to +0.0415 (records) to +0.0129 to +0.0414 (blocks), so dependence at that scale is not driving the widths. Repeated clients, which neither scheme can see, remain untested.

## What happens on other splits?

To vary the training sample, the seeds and the search too, we repeated the whole procedure on **3 other random 80/20 splits** (seeds 100 to 102). On each, every model is re-tuned from scratch (default plus seven random draws, 3-fold CV), refit and scored on that split's comparison part. Nothing chosen on one split is reused on another.

| model | mean AP | sd | min | max | mean rank | best rank | worst rank |
|---|---|---|---|---|---|---|---|
| LightGBM | 0.465 | 0.015 | 0.455 | 0.482 | 2.0 | 1 | 4 |
| sklearn HistGradientBoosting | 0.462 | 0.016 | 0.448 | 0.480 | 3.7 | 2 | 6 |
| XGBoost | 0.461 | 0.015 | 0.451 | 0.479 | 4.0 | 3 | 5 |
| Random forest | 0.461 | 0.011 | 0.452 | 0.473 | 3.0 | 1 | 5 |
| CatBoost | 0.460 | 0.010 | 0.453 | 0.471 | 3.3 | 2 | 6 |
| Extra trees | 0.460 | 0.015 | 0.450 | 0.478 | 5.0 | 4 | 6 |
| Small neural net (MLP) | 0.449 | 0.016 | 0.438 | 0.468 | 7.7 | 7 | 9 |
| Logistic regression | 0.449 | 0.011 | 0.440 | 0.462 | 7.7 | 7 | 8 |
| Linear SVM (Platt scaled) | 0.444 | 0.011 | 0.436 | 0.456 | 8.7 | 8 | 9 |
| Decision tree | 0.433 | 0.007 | 0.426 | 0.441 | 10.3 | 10 | 11 |
| k-nearest neighbours | 0.433 | 0.020 | 0.417 | 0.456 | 10.7 | 10 | 11 |
| Gaussian Naive Bayes | 0.365 | 0.006 | 0.359 | 0.370 | 12.0 | 12 | 12 |
| Prior (no model) | 0.113 | 0.000 | 0.113 | 0.113 | 13.0 | 13 | 13 |

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
