---
title: "Are the Scores Probabilities? Calibration, Thresholds and Cost"
description: "When a model says 12.5%, do 12.5% of those records subscribe? How to check, what repairing a model costs in ranking, and what the break-even threshold needs from the scores."
series: "classification"
order: 11
date: 2026-09-30
updated: 2026-10-04
keywords: ["calibration", "platt scaling", "isotonic regression", "reliability diagram", "expected calibration error", "decision threshold"]
readingTime: "13 min read"
figure: "ch11-calibration.png"
---

A record's score is 0.125. Do 12.5% of records with that score subscribe? That one question decides whether the break-even rule `cost / value` can be applied to a model's output, and models differ a lot in how they answer. The Gaussian Naive Bayes model from part 5 has a mean predicted probability of @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|mean_score|.2f@@ when only @@j:calibration_notes.json|validation_prevalence|.1%@@ of the validation records subscribe. A logistic regression is within @@v:calibration_summary.csv|model=Logistic regression|calibration=none (raw)|ece_10_quantile|.3f@@ on average. This chapter shows how to check, how to repair, and what the repair costs.

<div class="callout">

**Goal.** Judge whether a model's scores can be read as probabilities near the decision threshold, and repair them without damaging the ranking more than necessary.

**Work plan.** Measure calibration with reliability tables and the expected calibration error. Repair the models that need it with two standard methods, wrapped around the whole pipeline. Check the ranking before and after. Then use the break-even threshold and compare it with simpler decision policies.

**You will leave with** a checklist for calibration, and a clear statement of what the break-even threshold assumes.

</div>

## What "calibrated" means and how to measure it

A set of scores is **calibrated** if, among records scored near *p*, about a share *p* subscribe. The standard picture is a **reliability diagram**: sort records by score, cut them into groups, and plot the mean score against the observed rate in each group. The **expected calibration error (ECE)** is the size-weighted average gap between the two. ECE depends on how the groups are cut and how many records each holds, so we use ten equal-count groups and say so. Log loss and Brier score are also affected by calibration, but they combine it with the ability to separate the classes. Neither measures calibration alone.

Calibration is checked on rows the model has not seen. Here the development rows are split 75/25: models and calibrators are fitted on the 75% (calibrators with 5-fold cross-validation inside it) and everything below is scored on the other 25%. The comparison split is not used. Two details matter. A calibrator is wrapped around the **complete pipeline** (preprocessing and model), so each fold refits both and no step sees the records it is later scored on. And ranking metrics (AP, AUC) are computed from the original scores. Clipping probabilities to avoid taking the logarithm of zero is applied only inside log loss.

**Implementation.** Take Gaussian Naive Bayes and wrap it in a calibrator.

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

**What it means.** The raw model's mean score is more than double the true rate of @@j:calibration_notes.json|validation_prevalence|.3f@@, its log loss is large, and its ECE is about @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|ece_10_quantile|.2f@@. After sigmoid calibration the mean score matches the rate and both the log loss and the ECE drop sharply. The ranking (AP) is almost unchanged.

## Five models, three treatments

The table covers four model families (the random forest at two leaf sizes) with no repair, a sigmoid (Platt) calibrator and an isotonic calibrator, each wrapped around the pipeline with 5-fold cross-validation. Scores are on the 6,590 validation records, of which @@j:calibration_notes.json|validation_prevalence|.1%@@ subscribe.

@@table:calibration_summary.csv|where=calibration~none (raw);sigmoid, 5-fold ensemble around the pipeline;isotonic, 5-fold ensemble around the pipeline|cols=model,calibration,average_precision,roc_auc,log_loss,brier,ece_10_quantile,mean_score,distinct_scores|fmt=distinct_scores:d|rename=average_precision:AP,roc_auc:AUC,log_loss:log loss,brier:Brier,ece_10_quantile:ECE,mean_score:mean score,distinct_scores:distinct scores@@

![Reliability diagrams on the validation records. Left: ten equal-count groups; right: zoom on scores up to 0.4, where the break-even threshold of 0.125 lies. Bars are Wilson 95% intervals.](/series/classification/figures/ch11-calibration.png)
*Figure 1. Points on the diagonal are calibrated. Naive Bayes sits far below it without repair and close to it after a sigmoid calibrator.*

Read the table row by row.

- **Logistic regression** is already close to calibrated (ECE @@v:calibration_summary.csv|model=Logistic regression|calibration=none (raw)|ece_10_quantile|.3f@@), and neither calibrator improves it. A proper scoring rule rewards honest probabilities, but this is a finding about this fitted model, not a guarantee for every logistic regression.
- **A random forest depends on its leaves.** At the library default (leaves of one record) the raw log loss is @@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|log_loss|.3f@@ and the ECE @@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|ece_10_quantile|.3f@@. With leaves of at least 10 records, the raw ECE is @@v:calibration_summary.csv|model=Random forest (min_samples_leaf=10)|calibration=none (raw)|ece_10_quantile|.3f@@, and calibration adds nothing. The common claim that "forests are badly calibrated" is about a setting, not about forests.
- **Naive Bayes** is the model that needs repair, and either calibrator does the job on log loss and ECE.
- **LightGBM at library defaults** is reasonably calibrated here (ECE @@v:calibration_summary.csv|model=LightGBM (library default)|calibration=none (raw)|ece_10_quantile|.3f@@). Calibration changes its scores a little, which is a reason to check, not to assume.
- **Calibrators can change the ranking.** The two calibrated columns are averages of five models fitted on different parts of the training rows, so they are slightly different models, and AP and AUC can move. The default random forest gains in AP (@@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|average_precision|.3f@@ to @@v:calibration_summary.csv|model=Random forest (library default)|calibration=sigmoid, 5-fold ensemble around the pipeline|average_precision|.3f@@), but that gain is better read as an ensembling effect (part 7) than as a calibration effect.

## Ties: why isotonic can hurt the ranking

Calibration repair is a map from a raw score to a corrected probability. A strictly increasing map cannot change the ranking of one fixed score vector. A sigmoid map is strictly increasing, and the check below confirms that it leaves AP and AUC unchanged. An isotonic map is a staircase, so it is not strictly increasing: many different raw scores land on one value, which creates ties. How many distinct scores survive?

@@table:calibration_rank_checks.csv|cols=model,map,ap_raw,ap_after_map,distinct_scores_raw,distinct_scores_after_map|fmt=distinct_scores_raw:d;distinct_scores_after_map:d|rename=map:map fitted on out-of-fold scores,ap_raw:AP before,ap_after_map:AP after,distinct_scores_raw:distinct scores before,distinct_scores_after_map:distinct after@@

With isotonic maps the number of distinct scores falls from thousands to between 34 and 76, and AP falls by about 0.01 to 0.02 in every row, because ties among likely records cannot be ordered. With a sigmoid map the AP is identical to the digit, in every row. So if you need both ranking and probabilities, use a sigmoid map unless you have a lot of calibration data, or rank on the raw score and report the calibrated number alongside it.

## Calibration where it matters

Overall ECE averages over the whole score range, but the decision threshold sits at 0.125. A table of calibration around it is more informative, with the group sizes shown because small groups are noisy.

@@table:calibration_threshold_windows.csv|cols=model,score_window,records,mean_score,observed_rate,rate_lo,rate_hi|fmt=records:d|rename=score_window:raw score,observed_rate:observed rate,rate_lo:95% low,rate_hi:95% high@@

Matching mean score and observed rate in a window is a group-level check, not proof of calibration inside the window. With that caveat the pattern is as follows. For logistic regression and LightGBM the mean score lies inside the interval of the observed rate in all three windows. The default random forest is inside in all three as well. The forest with leaves of 10 overstates in the 0.15 to 0.25 window (mean score @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|mean_score|.3f@@, observed rate @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|observed_rate|.3f@@ with an interval of @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|rate_lo|.3f@@ to @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|rate_hi|.3f@@, @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|records|d@@ records), even though its overall ECE looks fine. Naive Bayes overstates in the same window (mean score @@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|mean_score|.3f@@, observed rate @@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|observed_rate|.3f@@), although with only @@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|records|d@@ records the interval is wide. An overall ECE can hide a problem exactly where the decision is made.

## From scores to a decision

If a client with true probability *p* of subscribing is contacted, the expected simulated contribution is `value · p − cost`. With a cost of 1 and a value of 8 (an illustrative price list) that is positive when `p > cost / value = 0.125`. That is the **break-even threshold**. It rests on four assumptions: the scores are calibrated probabilities near 0.125, the cost and value are the same for every record, contacting one record does not change the value of another, and the quantity being maximised is this simulated contribution (see part 14 for what it does not measure).

The last two columns of the earlier table apply the rule to each variant: how many validation records score at or above 1/8 and what the simulated contribution of selecting them would have been.

@@table:calibration_summary.csv|where=calibration~none (raw);sigmoid, 5-fold ensemble around the pipeline;isotonic, 5-fold ensemble around the pipeline|cols=model,calibration,records_at_or_above_break_even,contribution_at_break_even|fmt=records_at_or_above_break_even:d;contribution_at_break_even:d|rename=records_at_or_above_break_even:records selected,contribution_at_break_even:contribution@@

Calibrating Naive Bayes cuts the selected records from @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|records_at_or_above_break_even|d@@ to @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=sigmoid, 5-fold ensemble around the pipeline|records_at_or_above_break_even|d@@ with a slightly higher contribution, which is what honest probabilities should do. Differences of a few dozen units between other rows are within the noise of one validation sample, so do not use this column to rank calibration methods. And never pick the threshold on the same records you report it on: choose it on out-of-fold development scores and freeze it, as part 12 does.

## The policy menu

A threshold is not the only decision rule.

| Policy | Rule | Fits when |
|---|---|---|
| Break-even threshold | Select if p ≥ cost / value | Capacity is not binding and scores are calibrated near the threshold |
| Top-k by score | Select the k highest-scoring records | Capacity is fixed and only the ranking is trusted |
| Capped break-even | Select at most k, highest scores first, and never one below the break-even threshold | Capacity is a ceiling, not an obligation. Calibrated scores let you stop before capacity is exhausted |
| Segmented thresholds | Different cut-offs for different groups | Costs or values differ by channel or segment |

Capacity is a maximum. If calibrated scores say the k-th record is worth less than it costs, the economically sensible policy is to select fewer than k. Part 14 compares these policies under the illustrative price list.

## Analysis and conclusion: what we learned

- **Check before you repair.** Logistic regression and a forest with leaves of 10 were close to calibrated here; Naive Bayes was not. Calibration depends on the model *and its settings*.
- **Repair with a sigmoid map unless you have plenty of calibration data.** It preserves the ranking exactly for a fixed score vector. Isotonic maps create ties and lowered AP in every row.
- **Wrap the calibrator around the full pipeline,** and compute AP and AUC from unclipped scores.
- **The break-even threshold is a statement about calibrated probabilities near one value.** Check that region, with group sizes and intervals, before relying on it.

[Part 12](/series/classification/12-head-to-head-leaderboard/) runs all twelve models under one protocol and prices the result.
