---
title: "Are the Scores Probabilities? Calibration, Thresholds and Cost"
description: "When a model says 12.5%, do 12.5% of those records subscribe? How to check, what repairing a model costs in ranking, and what the break-even threshold needs from the scores."
series: "classification"
order: 11
date: 2026-09-30
updated: 2026-10-04
keywords: ["calibration", "platt scaling", "isotonic regression", "reliability diagram", "expected calibration error", "decision threshold"]
readingTime: "11 min read"
figure: "ch11-calibration.png"
---

A record's score is 0.125. Do 12.5% of records with that score subscribe? That decides whether the break-even rule `cost / value` can be applied to a model's output, and models differ a lot. The Gaussian Naive Bayes model of part 5 has a mean predicted probability of 0.23 when only 11.3% of the validation records subscribe. A logistic regression is within 0.005 on average.

<div class="callout">

**Goal.** Judge whether scores can be read as probabilities near the decision threshold, and repair them without more damage to the ranking than necessary.

**Work plan.** Measure calibration with reliability tables and the expected calibration error. Repair models with two standard methods wrapped around the whole pipeline. Check the ranking before and after. Then state what the break-even threshold assumes.

</div>

## What "calibrated" means and how to measure it

Scores are **calibrated** if, among records scored near *p*, about a share *p* subscribe. A **reliability diagram** sorts records by score, cuts them into groups, and plots mean score against observed rate. The **expected calibration error (ECE)** is the size-weighted average gap; it depends on how the groups are cut, so we use ten equal-count groups. Log loss and Brier score mix calibration with the ability to separate the classes, so neither measures calibration alone.

Everything is scored on rows the model has not seen: development rows are split 75/25, models and calibrators are fitted on the 75% (calibrators with 5-fold cross-validation inside it), and the comparison split is not used. A calibrator wraps the **complete pipeline** (preprocessing and model) so each fold refits both. AP and AUC come from unclipped scores; clipping to avoid log(0) happens only inside log loss.

**Implementation.** Wrap Gaussian Naive Bayes in a calibrator.

<details>
<summary>Setup code</summary>

```python
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import make_column_transformer
from sklearn.metrics import average_precision_score, log_loss
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
fit, val = train_test_split(dev, test_size=0.25, stratify=y[dev], random_state=42)
cat = [c for c in X.columns if X[c].dtype == object]

def pipeline():
    prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder=StandardScaler())
    return make_pipeline(prep, GaussianNB())

def ece(y_true, p, bins=10):                       # expected calibration error with equal-count bins
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    which = np.clip(np.digitize(p, edges[1:-1]), 0, len(edges) - 2)
    return sum((which == b).mean() * abs(p[which == b].mean() - y_true[which == b].mean()) for b in np.unique(which))
```

</details>

```python
raw = pipeline().fit(X.iloc[fit], y[fit]).predict_proba(X.iloc[val])[:, 1]
cv = StratifiedKFold(5, shuffle=True, random_state=42)
cal = CalibratedClassifierCV(pipeline(), method="sigmoid", cv=cv).fit(X.iloc[fit], y[fit]).predict_proba(X.iloc[val])[:, 1]
yv = y[val]
for name, p in (("raw", raw), ("sigmoid, calibrated", cal)):
    print(f"{name:<20} mean score {p.mean():.3f}  log loss {log_loss(yv, np.clip(p, 1e-12, 1 - 1e-12)):.3f}  "
          f"ECE {ece(yv, p):.3f}  AP {average_precision_score(yv, p):.3f}")
```

**Result.**

```output
raw                  mean score 0.230  log loss 2.311  ECE 0.189  AP 0.352
sigmoid, calibrated  mean score 0.114  log loss 0.307  ECE 0.039  AP 0.355
```

**What it means.** The raw mean score is more than double the true rate of 0.113, with a large log loss and an ECE of about 0.19. After sigmoid calibration the mean score matches the rate and log loss and ECE drop sharply, while AP barely changes.

## Five models, three treatments

Scores on the 6,590 validation records: no repair, a sigmoid (Platt) calibrator and an isotonic calibrator, each wrapped around the pipeline with 5-fold cross-validation.

| model | calibration | AP | log loss | Brier | ECE | mean score | distinct scores |
|---|---|---|---|---|---|---|---|
| Logistic regression | none (raw) | 0.461 | 0.277 | 0.078 | 0.005 | 0.114 | 8,024 |
| Logistic regression | sigmoid, 5-fold ensemble around the pipeline | 0.461 | 0.277 | 0.078 | 0.005 | 0.113 | 8,024 |
| Logistic regression | isotonic, 5-fold ensemble around the pipeline | 0.457 | 0.287 | 0.078 | 0.007 | 0.114 | 1,093 |
| Random forest (library default) | none (raw) | 0.394 | 0.376 | 0.087 | 0.038 | 0.117 | 1,769 |
| Random forest (library default) | sigmoid, 5-fold ensemble around the pipeline | 0.413 | 0.290 | 0.083 | 0.013 | 0.113 | 7,635 |
| Random forest (library default) | isotonic, 5-fold ensemble around the pipeline | 0.415 | 0.288 | 0.082 | 0.005 | 0.113 | 3,024 |
| Random forest (min_samples_leaf=10) | none (raw) | 0.467 | 0.274 | 0.077 | 0.010 | 0.114 | 8,023 |
| Random forest (min_samples_leaf=10) | sigmoid, 5-fold ensemble around the pipeline | 0.466 | 0.274 | 0.077 | 0.011 | 0.114 | 8,024 |
| Random forest (min_samples_leaf=10) | isotonic, 5-fold ensemble around the pipeline | 0.464 | 0.274 | 0.077 | 0.008 | 0.114 | 2,086 |
| Gaussian Naive Bayes | none (raw) | 0.352 | 2.311 | 0.189 | 0.189 | 0.230 | 7,385 |
| Gaussian Naive Bayes | sigmoid, 5-fold ensemble around the pipeline | 0.355 | 0.307 | 0.089 | 0.039 | 0.114 | 7,398 |
| Gaussian Naive Bayes | isotonic, 5-fold ensemble around the pipeline | 0.351 | 0.294 | 0.084 | 0.007 | 0.114 | 445 |
| LightGBM (library default) | none (raw) | 0.459 | 0.275 | 0.078 | 0.009 | 0.115 | 2,912 |
| LightGBM (library default) | sigmoid, 5-fold ensemble around the pipeline | 0.468 | 0.275 | 0.077 | 0.016 | 0.114 | 7,822 |
| LightGBM (library default) | isotonic, 5-fold ensemble around the pipeline | 0.468 | 0.272 | 0.077 | 0.007 | 0.114 | 3,117 |

![Reliability diagrams on the validation records. Left: ten equal-count groups; right: zoom on scores up to 0.4, where the break-even threshold of 0.125 lies. Bars are Wilson 95% intervals.](/series/classification/figures/ch11-calibration.png)
*Figure 1. Points on the diagonal are calibrated. Naive Bayes sits far below it until repaired.*

- **Logistic regression** is close to calibrated (ECE 0.005) and neither calibrator improves it. That is a finding about this fitted model, not a guarantee.
- **A random forest depends on its leaves.** At the library default (leaves of one record) the raw log loss is 0.376 and ECE 0.038; with leaves of at least 10 the ECE is 0.010. "Forests are badly calibrated" describes a setting, not forests.
- **Naive Bayes** needs repair, and either calibrator fixes log loss and ECE. **LightGBM at defaults** is reasonably calibrated (ECE 0.009).
- **Calibrators can change the ranking.** The calibrated columns average five models fitted on different parts of the training rows, so they are slightly different models. The default forest gains AP (0.394 to 0.413), better read as an ensembling effect (part 7) than a calibration effect.

## Ties: why isotonic can hurt the ranking

A strictly increasing map cannot change the ranking of one fixed score vector. A sigmoid map is strictly increasing: AP and AUC are identical to the digit below. An isotonic map is a staircase, so many raw scores land on one value and create ties.

| model | map fitted on out-of-fold scores | AP before | AP after | distinct before | distinct after |
|---|---|---|---|---|---|
| Logistic regression | sigmoid | 0.461 | 0.461 | 8,024 | 8,024 |
| Logistic regression | isotonic | 0.461 | 0.442 | 8,024 | 68 |
| Random forest (library default) | sigmoid | 0.394 | 0.394 | 1,769 | 1,691 |
| Random forest (library default) | isotonic | 0.394 | 0.378 | 1,769 | 47 |
| Random forest (min_samples_leaf=10) | sigmoid | 0.467 | 0.467 | 8,023 | 8,023 |
| Random forest (min_samples_leaf=10) | isotonic | 0.467 | 0.451 | 8,023 | 76 |
| Gaussian Naive Bayes | sigmoid | 0.352 | 0.352 | 7,385 | 7,385 |
| Gaussian Naive Bayes | isotonic | 0.352 | 0.343 | 7,385 | 34 |
| LightGBM (library default) | sigmoid | 0.459 | 0.459 | 2,912 | 2,912 |
| LightGBM (library default) | isotonic | 0.459 | 0.442 | 2,912 | 47 |

Isotonic leaves between 34 and 76 distinct scores and lowers AP by about 0.01 to 0.02 in every row, because ties among likely records cannot be ordered. If you need both ranking and probabilities, use a sigmoid map unless you have plenty of calibration data, or rank on the raw score and report the calibrated number beside it.

## Calibration where it matters

Overall ECE averages over the whole range, but the decision sits at 0.125. Calibration by score window, with group sizes:

| model | raw score | records | mean_score | observed rate | 95% low | 95% high |
|---|---|---|---|---|---|---|
| Logistic regression | [0.05, 0.10) | 3,010 | 0.067 | 0.063 | 0.055 | 0.073 |
| Logistic regression | [0.10, 0.15) | 483 | 0.118 | 0.108 | 0.083 | 0.138 |
| Logistic regression | [0.15, 0.25) | 442 | 0.201 | 0.197 | 0.162 | 0.236 |
| Random forest (library default) | [0.05, 0.10) | 1,196 | 0.070 | 0.066 | 0.053 | 0.082 |
| Random forest (library default) | [0.10, 0.15) | 565 | 0.122 | 0.103 | 0.080 | 0.130 |
| Random forest (library default) | [0.15, 0.25) | 562 | 0.192 | 0.183 | 0.153 | 0.217 |
| Random forest (min_samples_leaf=10) | [0.05, 0.10) | 2,952 | 0.069 | 0.063 | 0.054 | 0.072 |
| Random forest (min_samples_leaf=10) | [0.10, 0.15) | 489 | 0.119 | 0.112 | 0.087 | 0.144 |
| Random forest (min_samples_leaf=10) | [0.15, 0.25) | 213 | 0.193 | 0.127 | 0.089 | 0.178 |
| Gaussian Naive Bayes | [0.05, 0.10) | 158 | 0.073 | 0.101 | 0.063 | 0.158 |
| Gaussian Naive Bayes | [0.10, 0.15) | 118 | 0.125 | 0.127 | 0.079 | 0.199 |
| Gaussian Naive Bayes | [0.15, 0.25) | 117 | 0.195 | 0.094 | 0.053 | 0.161 |
| LightGBM (library default) | [0.05, 0.10) | 4,169 | 0.066 | 0.064 | 0.057 | 0.072 |
| LightGBM (library default) | [0.10, 0.15) | 434 | 0.119 | 0.090 | 0.066 | 0.120 |
| LightGBM (library default) | [0.15, 0.25) | 231 | 0.198 | 0.208 | 0.160 | 0.265 |

Matching group averages is a weak check, not proof of calibration inside a window. Logistic regression, LightGBM and the default forest have mean scores inside the observed-rate interval in all three windows. The forest with leaves of 10 overstates in the 0.15 to 0.25 window (mean score 0.193, observed rate 0.127, interval 0.089 to 0.178), as does Naive Bayes (0.195 against 0.094, with only 117 records). An overall ECE can hide a problem exactly where the decision is made.

## From scores to a decision

If a client with true probability *p* is contacted, the expected simulated contribution is `value · p − cost`: with cost 1 and value 8 (illustrative) it is positive when `p > cost / value = 0.125`. That **break-even threshold** assumes four things: scores are calibrated near 0.125, cost and value are the same for every record, contacting one record does not change the value of another, and the quantity maximised is this simulated contribution (part 14 says what it does not measure). Calibrating Naive Bayes cuts the records selected at 1/8 from 2,207 to 1,947 with a slightly higher simulated contribution (2,585 to 2,605). Differences of a few dozen units between other rows are within the noise of one validation sample, so do not rank calibration methods on contribution. And never choose a threshold on the records you report it on: choose it on out-of-fold development scores and freeze it, as part 12 does.

A threshold is not the only decision rule.

| Policy | Rule | Fits when |
|---|---|---|
| Break-even threshold | Select if p ≥ cost / value | Capacity is not binding and scores are calibrated near the threshold |
| Top-k by score | Select the k highest scores | Capacity is fixed and only the ranking is trusted |
| Capped break-even | Select at most k, highest first, never below break-even | Capacity is a ceiling, not an obligation |
| Segmented thresholds | Different cut-offs per group | Costs or values differ by channel or segment |

## Analysis and conclusion: what we learned

- **Check before you repair.** Logistic regression and the forest with leaves of 10 were close to calibrated overall; Naive Bayes was not. Calibration depends on the model *and its settings*, and overall ECE can hide a window that matters.
- **Prefer a sigmoid map** unless calibration data are plentiful: it preserves the ranking exactly, while isotonic maps created ties and lowered AP in every row.
- **Wrap the calibrator around the full pipeline** and compute AP and AUC from unclipped scores.
- **The break-even threshold is a statement about calibrated probabilities near one value.** Check that region, with counts and intervals, first.

*Further reading.* Platt (1999), Probabilistic outputs for support vector machines; Zadrozny and Elkan (2002), [Transforming classifier scores into accurate multiclass probability estimates](https://doi.org/10.1145/775047.775151); Niculescu-Mizil and Caruana (2005), [Predicting good probabilities with supervised learning](https://doi.org/10.1145/1102351.1102430).

[Part 12](/series/classification/12-head-to-head-leaderboard/) runs all twelve models under one protocol and prices the result.
