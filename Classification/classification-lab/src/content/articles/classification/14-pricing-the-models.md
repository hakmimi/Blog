---
title: "Pricing the Models: What a Ranking Is Worth Under an Illustrative Price List"
description: "A retrospective simulation with a stated price list, relevant baselines and a capacity ceiling. What the numbers mean, what they do not, and where model choice and cut-off choice matter."
series: "classification"
order: 14
date: 2026-09-30
updated: 2026-10-04
keywords: ["cost-sensitive", "decision threshold", "capacity", "expected value", "uplift", "baselines"]
readingTime: "11 min read"
figure: "leaderboard-profit.png"
---

Under the illustrative price list of this series, contacting every record of the comparison split would *lose* -814 units. The rule "contact only clients whose previous campaign succeeded" earns 1,148 from 268 contacts. The best model policies earn about three times that. What do those numbers mean, how much belongs to the model and how much to the cut-off, and how sure can we be?

<div class="callout">

**Goal.** Turn frozen scores into simulated contributions against relevant baselines, and say exactly what a contribution is.

**Work plan.** State the price list and what the simulation does not measure. Compare policies (break-even threshold, default cut-off, capacity ceiling) with baselines, test whether differences between models are visible, and vary the value of a subscription.

</div>

## What a contribution number is

The price list is an assumption, not the bank's: a contact costs 1 and a subscription is worth 8. For any set of selected records,

> contribution = 8 × (subscriptions among the selected records) − 1 × (selected records)

This is a **retrospective policy simulation**: it counts every subscription among selected records as a gain, whether or not the contact caused it.

| Quantity | Per contacted record | Needs |
|---|---|---|
| Expected contribution | V · p_contact − C | Probability of subscribing when contacted |
| Incremental contribution | V · (p_contact − p_no_contact) − C | The probability *without* a contact as well |

The break-even rule `p > C / V` (here 1/8) comes from the first line. It is right if people would not subscribe without the contact, or if that probability is the same for everyone. The dataset has no records of people who were *not* contacted, so it cannot identify `p_no_contact`, nor separate response propensity from **uplift**. The historical campaign also chose whom to call, so the records are not a sample of the bank's whole client base, and the price list ignores unequal costs, repeated contacts and unreachable clients. Read everything below as a way to compare rankings and policies on equal terms.

## Policies and baselines

Scores are the frozen ones from part 12 on the 8,238 comparison records (928 subscribers). Thresholds are fixed before scoring: the break-even value 1/8, an out-of-fold value from development data, and the library's 0.5.

| policy | records selected | simulated contribution |
|---|---|---|
| call nobody | 0 | 0 |
| call everyone | 8,238 | -814 |
| prior-success rule | 268 | 1,148 |

Select every record scoring at least 1/8 ("random same size" selects as many records at random, averaged over 400 draws):

| model | selected | precision | recall | contribution | random same size | gain over call-everyone | gain over prior-success rule |
|---|---|---|---|---|---|---|---|
| Random forest | 1,508 | 0.403 | 0.655 | 3,356 | -149 | 4,170 | 2,208 |
| LightGBM | 1,402 | 0.422 | 0.638 | 3,334 | -136 | 4,148 | 2,186 |
| XGBoost | 1,450 | 0.412 | 0.643 | 3,326 | -143 | 4,140 | 2,178 |
| sklearn HistGradientBoosting | 1,404 | 0.421 | 0.637 | 3,324 | -141 | 4,138 | 2,176 |
| CatBoost | 1,398 | 0.421 | 0.634 | 3,306 | -137 | 4,120 | 2,158 |
| Extra trees | 1,520 | 0.393 | 0.644 | 3,264 | -156 | 4,078 | 2,116 |
| Small neural net (MLP) | 1,431 | 0.408 | 0.629 | 3,241 | -142 | 4,055 | 2,093 |
| Linear SVM (Platt scaled) | 1,379 | 0.418 | 0.621 | 3,229 | -137 | 4,043 | 2,081 |
| k-nearest neighbours | 1,474 | 0.398 | 0.631 | 3,214 | -139 | 4,028 | 2,066 |
| Logistic regression | 1,563 | 0.378 | 0.636 | 3,157 | -156 | 3,971 | 2,009 |
| Decision tree | 1,715 | 0.354 | 0.654 | 3,141 | -170 | 3,955 | 1,993 |
| Gaussian Naive Bayes | 1,627 | 0.353 | 0.619 | 2,965 | -162 | 3,779 | 1,817 |

![Simulated contribution of each model at the break-even threshold, with the call-everyone and prior-success benchmarks.](/series/classification/figures/leaderboard-profit.png)
*Figure 1. Same frozen scores, one illustrative price list.*

- **Every model beats the baselines widely.** Random selection of the same size loses 130 to 170 units, so the gain does not come from selecting fewer records. The best models earn about 3,300 against the prior-success rule's 1,148, from five to six times as many records.
- **The spread depends on who you include.** Best is 3,356 (random forest), lowest of all twelve 2,965 (Naive Bayes), a difference of about 390. Excluding Naive Bayes the lowest is 3,141 (a single tree), a spread of about 215. Logistic regression earns 3,157, about 94% of the best.
- **The cut-off matters.** At the library default of 0.5 the same scores select only about 280 to 370 records (Naive Bayes, with inflated probabilities, 1,204) and earn roughly 1,300 to 1,600, about half of the break-even policy:

| model | selected | contribution |
|---|---|---|
| Gaussian Naive Bayes | 1,204 | 2,508 |
| Decision tree | 367 | 1,585 |
| Random forest | 365 | 1,579 |
| sklearn HistGradientBoosting | 342 | 1,546 |
| Extra trees | 347 | 1,533 |
| LightGBM | 342 | 1,530 |
| CatBoost | 312 | 1,456 |
| Logistic regression | 296 | 1,368 |
| Linear SVM (Platt scaled) | 284 | 1,324 |
| XGBoost | 286 | 1,306 |
| k-nearest neighbours | 281 | 1,303 |
| Small neural net (MLP) | 277 | 1,259 |

That is specific to these prices: a cut-off should come from the economics and be checked, not taken from a default.

**Try it.** The widget below applies any threshold to the frozen scores of five models. Choose a model, move the threshold, and change what a subscription is worth: the dashed line marks the break-even threshold `1/value` and the gold dot the best threshold *on this sample* (not a population optimum).

<div class="threshold-lab" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

## Capacity is a ceiling

Treat capacity as a ceiling: contact at most k records, highest scores first, and never one below the break-even threshold. Solid lines below keep that guard; dashed crosses fill the capacity regardless.

![Simulated contribution against capacity for three models, with and without the break-even guard.](/series/classification/figures/ch14-capacity.png)
*Figure 2. Beyond about 1,500 contacts, filling the list loses value unless the guard stops it.*

| model | capacity | records_selected | precision | recall | contribution | random same size |
|---|---|---|---|---|---|---|
| Logistic regression | 200 | 200 | 0.735 | 0.158 | 976 | -17 |
| Logistic regression | 500 | 500 | 0.592 | 0.319 | 1,868 | -51 |
| Logistic regression | 1,000 | 1,000 | 0.485 | 0.523 | 2,880 | -93 |
| Logistic regression | 1,500 | 1,500 | 0.390 | 0.630 | 3,180 | -142 |
| Logistic regression | 2,500 | 1,563 | 0.378 | 0.636 | 3,157 | -160 |
| Random forest | 200 | 200 | 0.750 | 0.162 | 1,000 | -25 |
| Random forest | 500 | 500 | 0.634 | 0.342 | 2,036 | -51 |
| Random forest | 1,000 | 1,000 | 0.502 | 0.541 | 3,016 | -94 |
| Random forest | 1,500 | 1,500 | 0.405 | 0.655 | 3,364 | -140 |
| Random forest | 2,500 | 1,508 | 0.403 | 0.655 | 3,356 | -163 |
| LightGBM | 200 | 200 | 0.745 | 0.161 | 992 | -22 |
| LightGBM | 500 | 500 | 0.628 | 0.338 | 2,012 | -47 |
| LightGBM | 1,000 | 1,000 | 0.515 | 0.555 | 3,120 | -100 |
| LightGBM | 1,500 | 1,402 | 0.422 | 0.638 | 3,334 | -144 |
| LightGBM | 2,500 | 1,402 | 0.422 | 0.638 | 3,334 | -146 |

At 200 contacts nothing separates the models (976 to 1,000). The gaps are largest at 500 to 1,000: at 1,000 LightGBM earns 3,120 and logistic regression 2,880, about 8% more. At a ceiling of 2,500 the guarded policy stops at about 1,400 to 1,560 records, while filling the list lowers the contribution (LightGBM 3,044 against 3,334).

## Are the differences between models visible?

A policy's contribution is a sum over records, so it can be bootstrapped in pairs like AP in part 13, conditional on the frozen scores and thresholds. Differences from logistic regression under the break-even policy, with marginal and simultaneous 95% intervals (eleven comparisons at once):

| model | difference | marginal low | marginal high | simultaneous low | simultaneous high |
|---|---|---|---|---|---|
| Random forest | +199 | +100 | +297 | +59 | +339 |
| LightGBM | +177 | +100 | +251 | +72 | +282 |
| XGBoost | +169 | +109 | +234 | +82 | +256 |
| sklearn HistGradientBoosting | +167 | +82 | +254 | +46 | +288 |
| CatBoost | +149 | +90 | +208 | +66 | +232 |
| Extra trees | +107 | +20 | +198 | -20 | +234 |
| Small neural net (MLP) | +84 | +34 | +130 | +16 | +152 |
| Linear SVM (Platt scaled) | +72 | +9 | +134 | -16 | +160 |
| k-nearest neighbours | +57 | -29 | +141 | -60 | +174 |
| Decision tree | -16 | -132 | +103 | -184 | +152 |
| Gaussian Naive Bayes | -192 | -315 | -67 | -367 | -17 |

The random forest, XGBoost, LightGBM, scikit-learn's booster, CatBoost and the neural net earn more than logistic regression with simultaneous intervals above zero. Extra trees, the SVM, k-NN and the single tree are not separated from it, and Naive Bayes earns less. The visible advantages are about 150 to 200 units for the forest and the boosters (the neural net's is about 80) on a base of about 3,150, roughly 5% to 6%. An interval that includes zero is lack of evidence of a difference, not proof of equality.

## How much do the assumptions matter?

The table keeps the cost at 1, changes the value, and applies the break-even threshold 1/value to the raw scores; call-everyone is recomputed for each value.

| model | value | records_selected | contribution | call everyone |
|---|---|---|---|---|
| Logistic regression | 4 | 968 | 924 | -4,526 |
| Logistic regression | 8 | 1,563 | 3,157 | -814 |
| Logistic regression | 16 | 3,648 | 8,192 | 6,610 |
| Gaussian Naive Bayes | 4 | 1,439 | 677 | -4,526 |
| Gaussian Naive Bayes | 8 | 1,627 | 2,965 | -814 |
| Gaussian Naive Bayes | 16 | 1,755 | 7,733 | 6,610 |
| LightGBM | 4 | 1,106 | 1,046 | -4,526 |
| LightGBM | 8 | 1,402 | 3,334 | -814 |
| LightGBM | 16 | 3,423 | 8,561 | 6,610 |

At a value of 4, calling everyone loses heavily (-4,526) and the models earn about 700 to 1,050. At a value of 16, calling everyone earns 6,610, and the models' advantage over it is only about 1,100 to 1,950: the more valuable a success, the less a ranking adds. The model ordering stays similar across values, but the *size* of any advantage over a trivial baseline changes with the assumption, so report the advantage over a relevant baseline next to the total and state the prices.

## A simple model or a booster?

The best policies earn about 5% to 6% more than logistic regression on 8,238 records. Whether that justifies a more complex pipeline depends on facts this dataset cannot supply: how many records are scored, what a mistake costs at scale, how often the model must be retrained, who maintains and explains it. Evidence that would change the choice: a larger or more recent evaluation set, a measured cost per contact, a prospective test with a control group (so uplift could be estimated) and a monitoring plan (part 16). Until then, the benefit of the better models is visible but modest, and logistic regression is a strong baseline.

## Analysis and conclusion: what we learned

- **A contribution is a retrospective simulation** under assumed prices; it does not estimate value created by contacting.
- **Compare with relevant baselines.** Call-nobody, call-everyone, matched random selection and a simple rule give context; all twelve models clear them widely under these prices.
- **Take the cut-off from the economics.** Here the break-even threshold roughly doubled the contribution against a default of 0.5 for every model with usable probabilities.
- **Capacity is a ceiling,** and differences between leading models are about 5% of the total and sensitive to the assumed value.

[Part 15](/series/classification/15-inside-the-winner/) opens the model development evidence would have chosen and asks what it relies on and where it fails.
