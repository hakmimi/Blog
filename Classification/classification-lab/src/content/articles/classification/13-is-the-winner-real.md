---
title: "Is the Winner Real? Bootstrap Intervals and Five Other Splits"
description: "LightGBM beat XGBoost by 0.006 average precision. We test whether that is a result or a coin flip using paired bootstrap, five different random splits, and a rank-stability table."
series: "classification"
order: 13
date: 2026-10-01
updated: 2026-10-02
keywords: ["bootstrap", "confidence intervals", "statistical significance", "model comparison", "rank stability", "paired test"]
readingTime: "16 min read"
figure: "leaderboard-stability.png"
---

The leaderboard says LightGBM 0.496, HistGradientBoosting 0.494, random forest 0.490, XGBoost 0.490. Somebody will want to write "LightGBM wins" on a slide. Before they do, we should ask how much of that ordering would survive a different draw of customers.

There are two different sources of randomness hiding in a single number like "AP = 0.496":

1. **Test-set sampling noise.** The 8,238 test customers are one sample. A different 8,238 would give a different AP for every model, and most of that variation is *shared* between models (easy and hard customers are easy and hard for everybody).
2. **Split and training noise.** A different train/test partition changes what each model learns, not only how it's graded.

We have tools for each. This chapter uses them both.

## Goals: what are we trying to achieve?

Somebody will want to write "LightGBM wins" on a slide. Our goal is to find out how much of that ordering survives a different draw of customers.

By the end you will be able to:

- **Separate two sources of noise**: the test sample, and the split and training.
- **Run a paired bootstrap**, and say why it is sharper than comparing two intervals.
- **Write a claim the data licenses**, and not one it does not.

## The work plan: how do we do it?

Three tests, each answering a different question:

1. **Part A, single interval:** the bootstrap of one model's AP on the saved test scores.
2. **Part B, paired comparison:** the difference between LightGBM and every other model, on the same resamples.
3. **Part C, other splits:** the whole procedure on five different random 80/20 splits.

## Implementation

### Part A: how precise is a single AP?

The bootstrap resamples the 8,238 test customers *with replacement*, recomputes the metric, and repeats. The spread of the results estimates the sampling noise. Since `run_leaderboard.py` saved every model's test-set scores, you can reproduce everything here without retraining anything:

```python
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

pred = pd.read_csv("artifacts/leaderboard_predictions.csv")       # one score column per model
y = pred["y"].to_numpy()
print(len(y), "test customers,", y.sum(), "subscribers")

rng = np.random.default_rng(42)
boots = rng.integers(0, len(y), size=(1000, len(y)))               # 1000 resamples of the customers

def ap_samples(model):
    p = pred[model].to_numpy()
    return np.array([average_precision_score(y[b], p[b]) for b in boots])

lgbm = ap_samples("LightGBM")
lo, hi = np.quantile(lgbm, [.025, .975])
print(f"LightGBM alone: AP = {average_precision_score(y, pred['LightGBM']):.3f}, 95% interval {lo:.3f} to {hi:.3f}  (width {hi - lo:.3f})")
```

```output
8238 test customers, 928 subscribers
LightGBM alone: AP = 0.496, 95% interval 0.464 to 0.531  (width 0.067)
```

The 95% interval for LightGBM's AP alone is **0.464 to 0.531**, a width of 0.067. That's *wider than the entire gap between the first and fifth models in the table*. With only 928 subscribers in the test set, no AP is known to better than about ±0.03.

That is exactly why the whiskers in Figure 1 of the last chapter overlap everywhere in tier 1. If we stopped here the correct conclusion would be "we can't separate them".

### Part B: the paired comparison is much sharper

But that's the wrong test. We care about the *difference* between two models, and the two models are scored on the **same customers**. Whatever makes a sample hard for LightGBM (a cluster of unusual subscribers) usually makes it hard for XGBoost too. Resample once, score both models on the same resample, and take the difference *within* each resample; the shared noise cancels.

```python
print("PAIRED difference vs LightGBM (same resample for both models)")
for m in ["sklearn HistGradientBoosting", "Random forest", "XGBoost", "CatBoost", "Extra trees",
          "Small neural net (MLP)", "Logistic regression", "Gaussian Naive Bayes"]:
    d = ap_samples(m) - lgbm
    lo, hi = np.quantile(d, [.025, .975])
    print(f"{m:<30} {d.mean():+.3f}   [{lo:+.3f}, {hi:+.3f}]   P(LightGBM worse) = {(d > 0).mean():.2f}")
```

```output
PAIRED difference vs LightGBM (same resample for both models)
sklearn HistGradientBoosting   -0.003   [-0.012, +0.006]   P(LightGBM worse) = 0.25
Random forest                  -0.006   [-0.014, +0.001]   P(LightGBM worse) = 0.06
XGBoost                        -0.006   [-0.014, -0.000]   P(LightGBM worse) = 0.03
CatBoost                       -0.009   [-0.018, +0.000]   P(LightGBM worse) = 0.03
Extra trees                    -0.012   [-0.020, -0.004]   P(LightGBM worse) = 0.00
Small neural net (MLP)         -0.020   [-0.031, -0.009]   P(LightGBM worse) = 0.00
Logistic regression            -0.032   [-0.045, -0.018]   P(LightGBM worse) = 0.00
Gaussian Naive Bayes           -0.084   [-0.106, -0.064]   P(LightGBM worse) = 0.00
```

The paired intervals are about three times narrower (width ≈ 0.02 instead of 0.067), so differences become visible. Reading the table:

| Comparison | Difference | Verdict |
|---|---|---|
| LightGBM vs HistGradientBoosting | −0.003 [−0.012, +0.006] | **Tie.** One in four resamples puts HistGB ahead. |
| LightGBM vs Random forest | −0.006 [−0.014, +0.001] | **Probably a tie.** The interval includes zero. |
| LightGBM vs XGBoost | −0.006 [−0.014, −0.000] | **Borderline.** Interval touches zero. |
| LightGBM vs CatBoost | −0.009 [−0.018, +0.000] | **Borderline.** |
| LightGBM vs Extra trees | −0.012 [−0.020, −0.004] | LightGBM better (small) |
| LightGBM vs MLP | −0.020 [−0.031, −0.009] | LightGBM clearly better |
| LightGBM vs Logistic regression | −0.032 [−0.045, −0.018] | LightGBM clearly better |
| LightGBM vs Naive Bayes | −0.084 [−0.106, −0.064] | Overwhelming |

Two conclusions fall out:

1. **The gap between tiers is real.** Boosting beats logistic regression by 0.03 AP with an interval that excludes zero by a wide margin, and also beats the small neural net.
2. **The ordering within tier 1 is not.** HistGB, random forest, XGBoost, CatBoost and LightGBM are statistically a cluster. If the leaderboard had been drawn with a different random seed it's quite plausible that any of the first four would be on top.

<div class="callout gotcha">

**Gotcha — twelve comparisons, one lucky one.** We computed several 95% intervals at once. Even if every model were equally good we'd expect about one in twenty to exclude zero by chance. The borderline results (XGBoost, CatBoost) deserve no more than a shrug. A defensible reading: "LightGBM is *not worse than* any other model, and is clearly better than everything outside the top cluster."

</div>

### Part C: does the ranking survive a different split?

The bootstrap resamples the test rows but leaves the *training set* fixed. To also vary what each model learns, we repeat the whole train/test procedure on **five different random 80/20 splits** (`random_state` 100–104): refit every model (with the hyperparameters it chose on the original split) on the new training set and score it on the new test set.

Here are the numbers. The column "std" is how much a model's own AP bounces between splits; "mean rank" is its average position out of 12:

| Model | Mean AP | Std | Range | Rank on each split (0–4) | Mean rank |
|---|---|---|---|---|---|
| LightGBM | 0.478 | 0.023 | 0.459–0.515 | 1, 3, 1, 1, 1 | **1.4** |
| sklearn HistGradientBoosting | 0.476 | 0.021 | 0.457–0.511 | 2, 1, 3, 3, 2 | 2.2 |
| XGBoost | 0.473 | 0.022 | 0.456–0.509 | 4, 4, 2, 4, 4 | 3.6 |
| CatBoost | 0.472 | 0.020 | 0.451–0.504 | 3, 2, 6, 7, 5 | 4.6 |
| Random forest | 0.472 | 0.023 | 0.455–0.510 | 5, 5, 4, 6, 3 | 4.6 |
| Extra trees | 0.469 | 0.021 | 0.454–0.503 | 6, 6, 5, 5, 6 | 5.6 |
| Small neural net (MLP) | 0.460 | 0.019 | 0.444–0.490 | 9, 7, 7, 2, 7 | 6.4 |
| Logistic regression | 0.456 | 0.018 | 0.442–0.484 | 7, 8, 8, 8, 8 | 7.8 |
| Linear SVM (calibrated) | 0.451 | 0.017 | 0.437–0.479 | 10, 9, 9, 9, 10 | 9.4 |
| Decision tree | 0.448 | 0.021 | 0.428–0.482 | 8, 11, 11, 11, 9 | 10.0 |
| k-nearest neighbors | 0.444 | 0.016 | 0.429–0.465 | 11, 10, 10, 10, 11 | 10.4 |
| Gaussian Naive Bayes | 0.397 | 0.014 | 0.375–0.412 | 12, 12, 12, 12, 12 | 12.0 |

This is the more convincing evidence. Three observations:

**1. LightGBM stays on top, and the top two boosters are consistent.** LightGBM is ranked first on four of five splits and third on the other (mean rank 1.4); HistGB is always in the top three. Gradient boosting ends up in front of the forests more often than not.

**2. But the *absolute* AP moves a lot more than the gaps do.** A model's AP ranges over about 0.05 from split to split (LightGBM 0.459 to 0.515!). That's larger than the whole difference between the first-ranked and fifth-ranked model. A single AP number, from a single split, should always be quoted with ±0.02 around it.

**3. Some orderings flip.** The decision tree was 8th on the original split (0.468, above logistic regression) but 9–11th on four of the five new ones, finishing below logistic regression on average (0.448 vs 0.456). Its apparent strength on the original split was at least partly luck. The small neural net ranks anywhere from 2nd to 9th depending on the split. These are the effects of *single-split* noise, and they're why one split can never support a claim like "the tree beats logistic regression".

<div class="callout">

**A caveat about this stability check.** The hyperparameters for each model were chosen using the original split's training data, and the new splits' test rows overlap those training rows. Final models are always refit from scratch on each new training partition and graded on rows that partition left out, so there is no leakage into *fitting*. But the hyperparameter choices have seen some of these test rows, which makes the stability AP numbers very slightly optimistic. For *ranking* models against each other, which share that optimism equally, it's a small effect. For quoting absolute performance, rely on the original locked test set.

</div>

## What did we get? Results

- **One AP is not precise:** LightGBM's AP of 0.496 has a 95% interval of 0.464 to 0.531 (width 0.067), with only 928 subscribers in the test set.
- **Paired differences are about three times narrower** (width about 0.02).

| Comparison | Difference | Verdict |
|---|---|---|
| LightGBM vs HistGradientBoosting | −0.003 [−0.012, +0.006] | Tie |
| LightGBM vs Random forest | −0.006 [−0.014, +0.001] | Probably a tie |
| LightGBM vs XGBoost | −0.006 [−0.014, −0.000] | Borderline |
| LightGBM vs CatBoost | −0.009 [−0.018, +0.000] | Borderline |
| LightGBM vs Extra trees | −0.012 [−0.020, −0.004] | LightGBM better (small) |
| LightGBM vs MLP | −0.020 [−0.031, −0.009] | Clearly better |
| LightGBM vs Logistic regression | −0.032 [−0.045, −0.018] | Clearly better |
| LightGBM vs Naive Bayes | −0.084 [−0.106, −0.064] | Overwhelming |

- **Five other splits:** LightGBM ranked first on four of five (mean rank 1.4, mean AP 0.478). The decision tree was 8th on the original split but 9th to 11th on four of the five new ones.

![Mean average precision over five random splits for each model with standard-deviation whiskers.](/series/classification/figures/leaderboard-stability.png)
*Figure 1. Mean ± standard deviation of AP across five other random splits. The same three tiers show up.*

## Analysis and conclusion: what did we learn?

- **The gap between tiers is real.** Boosting beats logistic regression by about 0.03 AP, with an interval far from zero.
- **The order inside tier 1 is not.** HistGB, random forest, XGBoost, CatBoost and LightGBM form a statistical cluster.
- **One split can mislead.** The tree's apparent strength over logistic regression on the original split was partly luck.
- **A single AP carries about ±0.03 of noise** at this base rate and test size. Treat differences below 0.01 as ties unless a paired test says otherwise.

### What we'd put on the slide

> *On this dataset, gradient-boosted trees (LightGBM, scikit-learn's HistGradientBoosting, XGBoost, CatBoost) and random forests form a top tier with average precision about 0.49 ± 0.02, statistically hard to separate from each other. They beat logistic regression and a small neural network by 0.02–0.03 AP, a gap that holds across five splits and survives paired testing. A calibrated Naive Bayes model, k-NN and a single tuned tree trail.*

Everything in that sentence is supported. "LightGBM is the best model" is not, and neither is "CatBoost is worse than XGBoost". That is not hedging; it's what the data licenses.

### Practical rules from this chapter

1. **Never compare two models by looking at two numbers.** Compare them on the same resamples (paired), and show the interval.
2. **A single AP carries about ±0.03 of sampling noise** at this base rate and test size. Differences below 0.01 should be treated as ties unless you have a paired test that says otherwise.
3. **If the choice between candidates doesn't matter statistically, choose on other grounds:** speed, simplicity, inference cost, library maintenance. Here that argues for HistGradientBoosting (0.5 s fit, 5 µs/row, no extra dependency) or LightGBM over CatBoost.
4. **Repeat the split.** Five repeated splits cost five refits and revealed one *apparent* strength (the tree) that wasn't real.
5. **Save the predictions.** `leaderboard_predictions.csv` is how a reader reproduces all the numbers in this chapter in seconds.

### So what did we do?

We bootstrapped the test set, compared models in pairs, and repeated the race on five splits. Boosting and forests are a real top tier, their internal order is mostly noise, and the claim the data supports is "LightGBM is not worse than any other model".

### In the next part

Having established that the top tier is real and its order is mostly noise, we should ask the question the business actually cares about. [Part 14](/series/classification/14-pricing-the-models/) prices the models in money.
