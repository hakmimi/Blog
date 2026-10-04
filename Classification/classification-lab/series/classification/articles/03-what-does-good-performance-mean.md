---
title: "What Does 'Good' Mean? Precision, Recall, ROC and PR"
description: "One logistic regression graded five ways: confusion matrix, classification report, ROC-AUC, average precision and precision at the top. What changes when the share of positives changes but the model does not."
series: "classification"
order: 3
date: 2026-09-30
updated: 2026-10-04
keywords: ["precision recall", "roc auc", "average precision", "confusion matrix", "classification report", "metrics"]
readingTime: "11 min read"
figure: "ch03-threshold-roc-pr.png"
---

At a cut-off of 0.5, a logistic regression on this data is right @@v:metrics_confusion.csv|threshold=0.5|accuracy|.1%@@ of the time and finds @@v:metrics_confusion.csv|threshold=0.5|recall|.0%@@ of the subscribers. At 0.125 it is right @@v:metrics_confusion.csv|threshold=0.125|accuracy|.1%@@ of the time and finds @@v:metrics_confusion.csv|threshold=0.125|recall|.0%@@. Same model, same predictions. Which setting is "better" depends on what you measure, so this chapter is about choosing the measurement.

<div class="callout">

**Goal.** Know which number to look at when the interesting class is rare.

**Work plan.** Fix one model, read its confusion matrix and classification report at two cut-offs, separate ranking quality from the cut-off, test ROC-AUC and average precision when the share of positives changes, and end with the metric that matches a capacity.

</div>

## A score, a cut-off, and a decision

Most classifiers output a **score** per record, usually between 0 and 1. A **threshold** turns it into a decision: at or above means "select". That makes two questions. *How well does the score rank records?* is a property of the model. *Where do we cut?* is a decision about cost and capacity. Many metric mistakes mix them up.

## The confusion matrix and the classification report

Every record lands in one of four cells (in scikit-learn rows are the truth, and `confusion_matrix(...).ravel()` returns TN, FP, FN, TP). "Positive" means the class we look for, not "good".

| | Predicted no | Predicted yes |
|---|---|---|
| **Actually no** | TN: correctly left alone | FP: a wasted contact |
| **Actually yes** | FN: a missed subscriber | TP: a win |

| Metric | Formula | Question it answers |
|---|---|---|
| Accuracy | (TP + TN) / all | How often is the decision right? |
| Precision | TP / (TP + FP) | Of the contacts we select, how many succeed? |
| Recall (true positive rate) | TP / (TP + FN) | Of all subscribers, how many do we reach? |
| Specificity | TN / (TN + FP) | Of all non-subscribers, how many do we leave alone? |
| False positive rate | FP / (FP + TN) | Of all non-subscribers, how many do we select anyway? |
| F1 | 2 · precision · recall / (precision + recall) | High only when both are high |

`classification_report` prints precision, recall and F1 for each class in turn, the class sizes (**support**), and two averages. **Macro** weights classes equally. **Weighted** weights them by support, so on imbalanced data it mostly describes the majority class. Neither is automatically right: it depends on whether you care about the classes equally.

**Implementation.** Fit a logistic regression on the development rows (the setup is folded below), score the comparison split once, and print the report at two cut-offs.

<details>
<summary>Setup code</summary>

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])                       # the main feature set (part 2)
dev, cmp_ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
cat = [c for c in X.columns if X[c].dtype == object]
model = make_pipeline(make_column_transformer((OneHotEncoder(handle_unknown="ignore"), cat), remainder=StandardScaler()),
                      LogisticRegression(max_iter=2000))
p = model.fit(X.iloc[dev], y[dev]).predict_proba(X.iloc[cmp_])[:, 1]     # one score per record
yc = y[cmp_]
```

</details>

```python
for t in (0.5, 0.125):
    tn, fp, fn, tp = confusion_matrix(yc, p >= t).ravel()
    print(f"threshold {t}: TN={tn} FP={fp} FN={fn} TP={tp}")
    print(classification_report(yc, p >= t, target_names=["no", "yes"], digits=3))
```

**Result.**

```output
(filled in by the build)
```

**What it means.** Read the support first (7,310 "no", 928 "yes"), then the "yes" row. At 0.5 the model is precise (about 0.69) and finds little (recall 0.22). At 0.125 it selects far more records: precision falls to 0.38 and recall rises to 0.64. Accuracy fell from 0.901 to 0.842 while recall and F1 for "yes" rose, so **accuracy went down while the model became more useful for finding subscribers**. Whether that is the right trade depends on cost against value (part 11). The averages disagree: macro F1 is @@v:metrics_report.csv|threshold=0.5|row=macro avg|f1-score|.3f@@, weighted F1 @@v:metrics_report.csv|threshold=0.5|row=weighted avg|f1-score|.3f@@, because the majority class pulls the weighted number up.

## Ranking quality: ROC and precision-recall

Sliding the threshold traces curves. The **ROC curve** plots recall against the false positive rate; its area, **ROC-AUC**, is the probability that a random subscriber scores higher than a random non-subscriber. It describes class separation, not how many selected records are right. The **precision-recall curve** plots precision against recall. **Average precision (AP)** sums (increase in recall) × (precision) over thresholds, which is what `average_precision_score` computes. It is related to, but not the same as, the trapezoidal area `auc(recall, precision)`: here @@j:metrics_notes.json|average_precision|.3f@@ and @@j:metrics_notes.json|pr_auc_trapezoid|.3f@@. We use AP. A random ranking scores the share of positives, @@j:metrics_notes.json|prevalence|.3f@@.

![Left: precision and recall as the threshold moves. Centre: ROC curve. Right: precision-recall curve with the share of positives as the baseline.](/series/classification/figures/ch03-threshold-roc-pr.png)
*Figure 1. Three views of one model's scores. Only the left panel shows the threshold.*

## Why ROC-AUC and AP disagree on rare positives

The same scores give ROC-AUC @@j:metrics_notes.json|roc_auc|.3f@@ and AP @@j:metrics_notes.json|average_precision|.3f@@. They answer different questions, as we can see by changing the number of positives while keeping every score fixed.

**Implementation.** Randomly drop a share of the positives and recompute both metrics (200 drops per row).

```python
rng = np.random.default_rng(42)
print(f"{'positives kept':>15}{'share positive':>16}{'ROC-AUC':>10}{'AP':>8}{'AP / share':>12}")
for keep in (1.0, 0.5, 0.2, 0.1):
    auc, ap, share = [], [], []
    for _ in range(200 if keep < 1 else 1):
        m = (yc == 0) | (rng.random(len(yc)) < keep)
        auc.append(roc_auc_score(yc[m], p[m])); ap.append(average_precision_score(yc[m], p[m])); share.append(yc[m].mean())
    print(f"{keep:>15.0%}{np.mean(share):>16.3f}{np.mean(auc):>10.3f}{np.mean(ap):>8.3f}{np.mean(ap) / np.mean(share):>12.1f}")
```

**Result.**

```output
(filled in by the build)
```

**What it means.** ROC-AUC barely moves: dropping positives at random leaves each class's score distribution unchanged. AP falls steeply, because precision depends on the mix: with fewer positives the same ranking puts more non-subscribers among the selected records. (AP relative to a random ranking rises, so AP depends on prevalence in two ways.) A bare AP is only comparable between models on the same records. ROC-AUC is not "inflated" by imbalance; it just does not say how many wasted contacts come with each win, which is what operations feel.

## The metric that matches a capacity

A call centre has a capacity, not a threshold. If it can handle 10% of the list: *of the top 10% by score, how many are subscribers?*

```python
order = np.argsort(-p)
for share in (0.05, 0.10, 0.20):
    k = int(share * len(p)); hits = yc[order[:k]]
    print(f"top {share:.0%} ({k} records): precision {hits.mean():.2f}, recall {hits.sum() / yc.sum():.2f}, lift {hits.mean() / yc.mean():.1f}x")
```

```output
(filled in by the build)
```

Lift is precision divided by the overall rate, so it says how many times better than random the top of the list is. It is easy to explain and ties to capacity, but it is noisy for small k, so quote the record count.

## Drag the threshold

The widget uses the frozen comparison-split scores of five models from part 12. Move the threshold and watch the confusion matrix, the ROC and precision-recall positions and the simulated contribution. Prices (cost 1, value 8) are assumptions and the contribution is a retrospective simulation (part 14). The gold marker is the best threshold *on this sample*, not a population optimum.

<div class="threshold-lab" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

## Analysis and conclusion: what we learned

| If you care about… | Look at | Watch out for |
|---|---|---|
| Class separation | ROC-AUC | Silent on precision and workload |
| Selected contacts that succeed | Average precision, precision at the top | Depends on prevalence; compare on the same records |
| One cut-off's balance | F1 for the positive class | Ignores true negatives; equal weighting is an assumption |
| Overall correctness | Accuracy | Dominated by the majority; do-nothing scores @@j:metrics_notes.json|always_no_accuracy|.3f@@ |
| A fixed capacity | Precision and recall at the top k | Noisy for small k |
| Money | Contribution at a threshold (part 14) | Needs a price list and calibrated scores |

Accuracy has 11 points of room (from @@j:metrics_notes.json|always_no_accuracy|.3f@@ to 1.000), but the information is in the minority class. The main selection metric here is **average precision**, always next to the share of positives. The threshold is decided separately.

*Further reading.* Davis and Goadrich (2006), [The relationship between precision-recall and ROC curves](https://doi.org/10.1145/1143844.1143874); Saito and Rehmsmeier (2015), [PLOS ONE](https://doi.org/10.1371/journal.pone.0118432); scikit-learn's documentation of [`average_precision_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html), which states how it differs from the trapezoidal area.

[Part 4](/series/classification/04-objective-functions/) looks inside training: what does a model minimise, and what does the choice change?
