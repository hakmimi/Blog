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

A record's score is 0.125. Do 12.5% of records with that score subscribe? That decides whether the break-even rule `cost / value` can be applied to a model's output, and models differ a lot. The Gaussian Naive Bayes model of part 5 has a mean predicted probability of @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|mean_score|.2f@@ when only @@j:calibration_notes.json|validation_prevalence|.1%@@ of the validation records subscribe. A logistic regression is within @@v:calibration_summary.csv|model=Logistic regression|calibration=none (raw)|ece_10_quantile|.3f@@ on average.

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
(filled in by the build)
```

**What it means.** The raw mean score is more than double the true rate of @@j:calibration_notes.json|validation_prevalence|.3f@@, with a large log loss and an ECE of about @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|ece_10_quantile|.2f@@. After sigmoid calibration the mean score matches the rate and log loss and ECE drop sharply, while AP barely changes.

## Five models, three treatments

Scores on the 6,590 validation records: no repair, a sigmoid (Platt) calibrator and an isotonic calibrator, each wrapped around the pipeline with 5-fold cross-validation.

@@table:calibration_summary.csv|where=calibration~none (raw);sigmoid, 5-fold ensemble around the pipeline;isotonic, 5-fold ensemble around the pipeline|cols=model,calibration,average_precision,log_loss,brier,ece_10_quantile,mean_score,distinct_scores|fmt=distinct_scores:d|rename=average_precision:AP,log_loss:log loss,brier:Brier,ece_10_quantile:ECE,mean_score:mean score,distinct_scores:distinct scores@@

![Reliability diagrams on the validation records. Left: ten equal-count groups; right: zoom on scores up to 0.4, where the break-even threshold of 0.125 lies. Bars are Wilson 95% intervals.](/series/classification/figures/ch11-calibration.png)
*Figure 1. Points on the diagonal are calibrated. Naive Bayes sits far below it until repaired.*

- **Logistic regression** is close to calibrated (ECE @@v:calibration_summary.csv|model=Logistic regression|calibration=none (raw)|ece_10_quantile|.3f@@) and neither calibrator improves it. That is a finding about this fitted model, not a guarantee.
- **A random forest depends on its leaves.** At the library default (leaves of one record) the raw log loss is @@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|log_loss|.3f@@ and ECE @@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|ece_10_quantile|.3f@@; with leaves of at least 10 the ECE is @@v:calibration_summary.csv|model=Random forest (min_samples_leaf=10)|calibration=none (raw)|ece_10_quantile|.3f@@. "Forests are badly calibrated" describes a setting, not forests.
- **Naive Bayes** needs repair, and either calibrator fixes log loss and ECE. **LightGBM at defaults** is reasonably calibrated (ECE @@v:calibration_summary.csv|model=LightGBM (library default)|calibration=none (raw)|ece_10_quantile|.3f@@).
- **Calibrators can change the ranking.** The calibrated columns average five models fitted on different parts of the training rows, so they are slightly different models. The default forest gains AP (@@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|average_precision|.3f@@ to @@v:calibration_summary.csv|model=Random forest (library default)|calibration=sigmoid, 5-fold ensemble around the pipeline|average_precision|.3f@@), better read as an ensembling effect (part 7) than a calibration effect.

## Ties: why isotonic can hurt the ranking

A strictly increasing map cannot change the ranking of one fixed score vector. A sigmoid map is strictly increasing: AP and AUC are identical to the digit below. An isotonic map is a staircase, so many raw scores land on one value and create ties.

@@table:calibration_rank_checks.csv|cols=model,map,ap_raw,ap_after_map,distinct_scores_raw,distinct_scores_after_map|fmt=distinct_scores_raw:d;distinct_scores_after_map:d|rename=map:map fitted on out-of-fold scores,ap_raw:AP before,ap_after_map:AP after,distinct_scores_raw:distinct before,distinct_scores_after_map:distinct after@@

Isotonic leaves between 34 and 76 distinct scores and lowers AP by about 0.01 to 0.02 in every row, because ties among likely records cannot be ordered. If you need both ranking and probabilities, use a sigmoid map unless you have plenty of calibration data, or rank on the raw score and report the calibrated number beside it.

## Calibration where it matters

Overall ECE averages over the whole range, but the decision sits at 0.125. Calibration by score window, with group sizes:

@@table:calibration_threshold_windows.csv|cols=model,score_window,records,mean_score,observed_rate,rate_lo,rate_hi|fmt=records:d|rename=score_window:raw score,observed_rate:observed rate,rate_lo:95% low,rate_hi:95% high@@

Matching group averages is a weak check, not proof of calibration inside a window. Logistic regression, LightGBM and the default forest have mean scores inside the observed-rate interval in all three windows. The forest with leaves of 10 overstates in the 0.15 to 0.25 window (mean score @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|mean_score|.3f@@, observed rate @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|observed_rate|.3f@@, interval @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|rate_lo|.3f@@ to @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|rate_hi|.3f@@), as does Naive Bayes (@@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|mean_score|.3f@@ against @@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|observed_rate|.3f@@, with only @@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|records|d@@ records). An overall ECE can hide a problem exactly where the decision is made.

## From scores to a decision

If a client with true probability *p* is contacted, the expected simulated contribution is `value · p − cost`: with cost 1 and value 8 (illustrative) it is positive when `p > cost / value = 0.125`. That **break-even threshold** assumes four things: scores are calibrated near 0.125, cost and value are the same for every record, contacting one record does not change the value of another, and the quantity maximised is this simulated contribution (part 14 says what it does not measure). Calibrating Naive Bayes cuts the records selected at 1/8 from @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|records_at_or_above_break_even|d@@ to @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=sigmoid, 5-fold ensemble around the pipeline|records_at_or_above_break_even|d@@ with a slightly higher simulated contribution (@@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|contribution_at_break_even|d@@ to @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=sigmoid, 5-fold ensemble around the pipeline|contribution_at_break_even|d@@). Differences of a few dozen units between other rows are within the noise of one validation sample, so do not rank calibration methods on contribution. And never choose a threshold on the records you report it on: choose it on out-of-fold development scores and freeze it, as part 12 does.

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
