---
title: "What Does 'Good' Mean? Precision, Recall, ROC and PR"
description: "One logistic regression graded five ways. A confusion matrix, a classification report, ROC-AUC and average precision, and what changes when the share of positives changes but the model does not."
series: "classification"
order: 3
date: 2026-09-30
updated: 2026-10-04
keywords: ["precision recall", "roc auc", "average precision", "confusion matrix", "classification report", "metrics"]
readingTime: "14 min read"
figure: "ch03-threshold-roc-pr.png"
---

At a cut-off of 0.5, a logistic regression on this data is right @@v:metrics_confusion.csv|threshold=0.5|accuracy|.1%@@ of the time and finds @@v:metrics_confusion.csv|threshold=0.5|recall|.0%@@ of the subscribers. At a cut-off of 0.125 it is right @@v:metrics_confusion.csv|threshold=0.125|accuracy|.1%@@ of the time and finds @@v:metrics_confusion.csv|threshold=0.125|recall|.0%@@. It is the same model and the same predictions. Which setting is "better" depends on what you measure, so this chapter is about choosing the measurement.

<div class="callout">

**Goal.** Know which number to look at for a problem where the interesting class is rare.

**Work plan.** Fit one model and keep it fixed. Read its confusion matrix and classification report at two cut-offs. Separate the quality of the *ranking* from the choice of *cut-off*. Check what ROC-AUC and average precision do when the share of positives changes. Finish with the metric that matches a call centre's capacity.

**You will leave with** a reading of every cell and row of the standard reports, and a rule for choosing between accuracy, F1, ROC-AUC, average precision and precision at the top of a ranked list.

</div>

## A score, a cut-off, and a decision

Most classifiers output a **score** for each record, usually a number between 0 and 1. A **threshold** (cut-off) turns it into a decision: score at or above the threshold means "select", below means "leave". That makes two separate questions. *How well does the score rank records?* is a property of the model. *Where do we cut?* is a decision about cost and capacity. Many metric mistakes come from mixing the two.

## The confusion matrix and the classification report

Every record lands in one of four cells. In scikit-learn, rows are the truth, columns are the prediction, and `confusion_matrix(y_true, y_pred).ravel()` returns TN, FP, FN, TP. "Positive" means the class we are looking for (here, a subscription), not "good".

| | Predicted no | Predicted yes |
|---|---|---|
| **Actually no** | TN: correctly left alone | FP: a wasted contact |
| **Actually yes** | FN: a missed subscriber | TP: a win |

The usual ratios are built from those cells.

| Metric | Formula | Question it answers |
|---|---|---|
| Accuracy | (TP + TN) / all | How often is the decision right? |
| Precision | TP / (TP + FP) | Of the contacts we select, how many succeed? |
| Recall (true positive rate) | TP / (TP + FN) | Of all subscribers, how many do we reach? |
| Specificity | TN / (TN + FP) | Of all non-subscribers, how many do we leave alone? |
| False positive rate | FP / (FP + TN) | Of all non-subscribers, how many do we select anyway? |
| F1 | 2 · precision · recall / (precision + recall) | High only when precision and recall are both high |

`classification_report` prints precision, recall and F1 for each class in turn (as if each were the positive class), the number of records in each class (**support**), and two averages. **Macro average** weights the classes equally. **Weighted average** weights them by support, so on imbalanced data it mostly describes the majority class. Neither average is automatically "the right one": which one matters depends on whether you care about each class equally.

**Implementation.** Fit a logistic regression on the development rows, score the comparison split once, and print the report at two cut-offs.

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
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

for t in (0.5, 0.125):
    tn, fp, fn, tp = confusion_matrix(yc, p >= t).ravel()
    print(f"threshold {t}: TN={tn} FP={fp} FN={fn} TP={tp}")
    print(classification_report(yc, p >= t, target_names=["no", "yes"], digits=3))
```

**Result.**

```output
(filled in by the build)
```

**What it means.** Read the **support** column first: 7,310 records are "no" and 928 are "yes". Then read the "yes" row, because that is the class we care about. At 0.5 the model is precise (about 0.69 of selected contacts succeed) and finds little (recall about 0.22). At 0.125 it selects far more records, precision falls to about 0.38, and recall rises to about 0.64. Accuracy fell from 0.901 to 0.842 while the "yes" row improved on recall and F1, so **accuracy went down while the model became more useful for finding subscribers**. Whether that is the right trade depends on the cost of a wasted contact against the value of a subscriber, which is the subject of part 11.

The macro and weighted averages disagree: macro F1 is @@v:metrics_report.csv|threshold=0.5|row=macro avg|f1-score|.3f@@ at 0.5 and weighted F1 is @@v:metrics_report.csv|threshold=0.5|row=weighted avg|f1-score|.3f@@. The gap is the majority class pulling the weighted number up. Macro averages treat a rare class and a common class as equally important, which is a choice, not a verdict.

## Ranking quality: ROC and precision-recall curves

Sliding the threshold from high to low traces a curve. The **ROC curve** plots recall (true positive rate) against the false positive rate. The **ROC-AUC** is the probability that a randomly chosen subscriber gets a higher score than a randomly chosen non-subscriber, so it describes how well the two classes are separated by score. It does not mention how many records you select or how many of them are right.

The **precision-recall curve** plots precision against recall. **Average precision (AP)** summarises it as a sum over thresholds of (increase in recall) × (precision at that threshold). This is what scikit-learn's `average_precision_score` computes. It is related to, but not the same as, the trapezoidal area under the precision-recall curve (`auc(recall, precision)`). On these scores the two are @@j:metrics_notes.json|average_precision|.3f@@ and @@j:metrics_notes.json|pr_auc_trapezoid|.3f@@. We use AP throughout. A model that ranks at random has AP equal to the share of positives, @@j:metrics_notes.json|prevalence|.3f@@ here.

![Left: precision and recall as the threshold moves. Centre: ROC curve. Right: precision-recall curve with the share of positives as the baseline.](/series/classification/figures/ch03-threshold-roc-pr.png)
*Figure 1. Three views of one model's scores. Only the left panel shows the threshold itself.*

## Why ROC-AUC and AP disagree on rare positives

The same scores give an ROC-AUC of @@j:metrics_notes.json|roc_auc|.3f@@ and an AP of @@j:metrics_notes.json|average_precision|.3f@@. They are not in conflict. They answer different questions, and the difference becomes visible if we change how many positives there are while keeping every record's score fixed.

**Implementation.** Randomly drop a share of the positives from the comparison set and recompute both metrics. Each row averages 200 random drops, and the scores of the remaining records do not change.

```python
from sklearn.metrics import average_precision_score, roc_auc_score

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

**What it means.** ROC-AUC barely moves, because it compares subscribers with non-subscribers, and removing some subscribers at random leaves the score distribution of each class unchanged. AP falls steeply, because precision depends on the mix: with fewer positives, the same ranking puts more non-subscribers among the selected records. The last column shows that AP relative to a random ranking actually *rises* as positives get rarer, so AP depends on prevalence in two ways, and a bare AP number is only comparable between models evaluated on the same records. ROC-AUC is not "inflated" by imbalance. It simply does not tell you how many wasted contacts come with each win, which is what an operations team feels.

## The metric that matches a capacity

A call centre usually has a daily capacity, not a threshold. If it can handle 10% of the list, the question is: *of the top 10% by score, how many are subscribers?*

**Implementation.**

```python
order = np.argsort(-p)
for share in (0.05, 0.10, 0.20):
    k = int(share * len(p)); hits = yc[order[:k]]
    print(f"top {share:.0%} ({k} records): precision {hits.mean():.2f}, recall {hits.sum() / yc.sum():.2f}, lift {hits.mean() / yc.mean():.1f}x")
```

**Result.**

```output
(filled in by the build)
```

**What it means.** "Lift" is precision divided by the overall rate of positives, so it says how many times better than random selection the top of the list is. Precision at the top of a list is easy to explain to someone who does not know what an ROC curve is, and it ties directly to capacity. It is also noisy when k is small, so quote the number of records next to it.

## Drag the threshold

The widget below uses the frozen comparison-split scores of five of the models from part 12. Move the threshold and watch the confusion matrix, the ROC and precision-recall positions, and the simulated contribution curve respond. The price list (a contact costs 1, a subscription is worth 8) is an assumption, and the contribution is a retrospective simulation, not a measure of value caused by contacting (part 14). The gold marker is the best threshold *on this sample*, not a population optimum.

<div class="threshold-lab" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

If the widget is unavailable in the printable edition, the numbers it shows at the thresholds 0.5 and 0.125 are the ones in the report above.

## Analysis and conclusion: what we learned

| If you care about… | Look at | Watch out for |
|---|---|---|
| Whether the score separates the two classes | ROC-AUC | Says nothing about precision or workload |
| Selected contacts that succeed, when positives are rare | Average precision, precision at the top | Depends on the share of positives; compare models on the same records only |
| One cut-off's balance of precision and recall | F1 for the positive class | Ignores true negatives; equal weighting of the two errors is an assumption |
| Overall correctness | Accuracy | Dominated by the majority class; the do-nothing baseline scores @@j:metrics_notes.json|always_no_accuracy|.3f@@ |
| A fixed capacity | Precision and recall at the top k | Noisy for small k |
| Money | Contribution at a chosen threshold (part 14) | Depends on the price list and on calibrated scores |

The room for improvement in accuracy is large in principle (from @@j:metrics_notes.json|always_no_accuracy|.3f@@ to 1.000, about 11 points), but it is not where the information is: nearly all useful change happens in the minority class. For this series the main selection metric is **average precision**, always reported next to the share of positives, and the threshold is a separate decision made later.

[Part 4](/series/classification/04-objective-functions/) looks inside training: what does a model actually minimise, and what does the choice change?
