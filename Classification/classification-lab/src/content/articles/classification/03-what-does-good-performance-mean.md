---
title: "What Does 'Good' Mean? Precision, Recall, ROC and PR"
description: "One logistic regression, four ways of grading it. We compute every metric by hand, move the threshold, and see why average precision beats ROC-AUC on imbalanced data."
series: "classification"
order: 3
date: 2026-09-30
updated: 2026-10-02
keywords: ["precision recall", "roc auc", "average precision", "confusion matrix", "classification report", "metrics"]
readingTime: "20 min read"
figure: "ch03-threshold-roc-pr.png"
---

## Introduction

A bank that never phones anyone gets 88.7% of its predictions right, because 88.7% of customers say no. A model that actually works, the one we build in this chapter, gets 90.1%. If accuracy were the whole story, 1.4 points would be a poor return on a whole machine-learning project.

Accuracy is not the whole story. The same set of predictions can look brilliant or useless depending on the metric you use to grade it, and picking the wrong metric is one of the quietest ways to ship the wrong model. Here the model finds only 22% of the people who would subscribe, and we can call that a success or a failure depending on what we measure.

So before we compare thirteen classifiers, we need to agree on the yardstick. In this chapter we train one simple model, logistic regression, and keep it fixed. Then we grade the same 8,238 predictions in several ways, until it is clear why average precision is our main metric and why the threshold is a separate decision.

## Goals: what are we trying to achieve?

The same predictions can look brilliant or useless depending on how you grade them. Our goal is to learn which grade to trust on this data.

By the end you will be able to:

- **Read a confusion matrix** and compute accuracy, precision and recall from its four cells.
- **Read a classification report**, row by row, and know why the "yes" row matters more than the averages.
- **Explain why the threshold is a dial**, and what moving it does to calls, hits and misses.
- **Choose between ROC-AUC, average precision and precision at top-k** for a problem with rare positives.

## Theory: what a classifier outputs and how it is graded

### A score, a cut-off, and a decision

Most classifiers do not output "yes" or "no". They output a **score** for each customer, usually a probability between 0 and 1. A **threshold** (also called a cut-off) turns the score into a decision: everything at or above the threshold is "yes", everything below is "no".

That gives two separate questions. *How well does the score rank customers?* (Does it put likely subscribers above unlikely ones?) And *where do we cut?* The first is a property of the model. The second is a decision about money and capacity. Mixing them up is the root of most metric mistakes, and the whole chapter follows this split.

### The confusion matrix

Once we have decisions, we compare them with the truth. Every customer lands in exactly one of four cells:

| | Predicted no | Predicted yes |
|---|---|---|
| **Actually no** | **TN**, true negative: correctly left alone | **FP**, false positive: a wasted call |
| **Actually yes** | **FN**, false negative: a missed customer | **TP**, true positive: a win |

Two conventions to keep in mind. In scikit-learn, **rows are the truth and columns are the prediction**, and `confusion_matrix(y_true, y_pred).ravel()` returns the cells in the order TN, FP, FN, TP. And "positive" does not mean "good": it means *the class we are looking for*. Here that is "subscribes".

The two kinds of error are not equal. A false positive costs one phone call. A false negative costs a subscription, which in our later cost model is worth eight calls. The matrix keeps the two errors apart, which is exactly what a single accuracy number hides.

Every standard metric is a ratio of these four cells:

| Metric | Formula | The question it answers |
|---|---|---|
| **Accuracy** | (TP + TN) / all | How often is the decision right? |
| **Precision** | TP / (TP + FP) | Of the people we call, how many say yes? |
| **Recall** (true positive rate, sensitivity) | TP / (TP + FN) | Of everyone who would say yes, how many did we reach? |
| **Specificity** | TN / (TN + FP) | Of the people who would say no, how many did we leave alone? |
| **False positive rate** | FP / (FP + TN) = 1 − specificity | Of the people who would say no, how many did we call anyway? |
| **F1** | 2 · precision · recall / (precision + recall) | One number that is high only when both precision and recall are high. |

Precision and recall pull in opposite directions. Lower the threshold and you call more people, so recall rises and precision usually falls. F1 is the harmonic mean of the two, so it punishes a model that is good at only one of them.

### The classification report

`sklearn.metrics.classification_report` prints these ratios **for each class**, as if each class were the "positive" one in turn, plus three summary rows. You read it like this:

- **precision, recall, f1-score:** the formulas above, computed once for the class "no" and once for the class "yes".
- **support:** how many real customers belong to each class. Always read it first, because it tells you how much weight each row carries (here 7,310 "no" against 928 "yes").
- **accuracy:** one number for the whole table.
- **macro avg:** the plain average of the two classes. It treats a rare class and a common class as equally important, so it exposes a model that ignores the minority.
- **weighted avg:** the average weighted by support. It is dominated by the common class, so on imbalanced data it looks flattering.

For imbalanced data, the row to look at is the one for the minority class: the "yes" row.

### Ranking quality: ROC and precision-recall curves

Sliding the threshold from 1 down to 0 traces out a curve. The **ROC curve** plots recall against the false positive rate, and its area (**ROC-AUC**) has a clean meaning: the probability that a random subscriber scores higher than a random non-subscriber. The **precision-recall curve** plots precision against recall, and its area is summarised by **average precision (AP)**. Neither depends on any one threshold, so they grade the ranking and nothing else. Why they behave very differently when positives are rare is the main experiment of this chapter.

## The work plan: how do we do it?

We train one simple model, logistic regression, and keep it fixed. We then grade the same 8,238 predictions in four ways:

1. **Confusion matrix and classification report** at a cut-off of 0.5, and the ratios built from them.
2. **Threshold sweep**: move the cut-off and watch precision and recall trade places.
3. **ROC-AUC against average precision**: a test that shows which one is fooled by imbalance.
4. **Precision at top-k**: the metric that matches a call centre with limited capacity.

## Implementation

### Train the model we will grade

We need a model to grade, so we train the simplest serious one: logistic regression on the 19 pre-call features. Don't worry about how it works yet ([part 5](/series/classification/05-logistic-regression-naive-bayes/)).

```python
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)
X = df.drop(columns="duration")                       # not known before the call (part 2)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

cat = X.select_dtypes("object").columns
model = make_pipeline(
    ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cat)], remainder=StandardScaler()),
    LogisticRegression(max_iter=2000),
)
p = model.fit(Xtr, ytr).predict_proba(Xte)[:, 1]      # probability of "subscribes"
```

`p` is a vector of 8,238 numbers between 0 and 1, one per held-out customer. A *classifier* is what you get when you choose a cut-off and call everything above it "yes". Everything below is about how we grade that choice.

### The confusion matrix: four numbers that contain everything

Cut at 0.5 and count:

```python
tn, fp, fn, tp = confusion_matrix(yte, p >= 0.5).ravel()
print(f"TN={tn} FP={fp} FN={fn} TP={tp}")
print(f"accuracy={(tp + tn) / len(yte):.3f}  precision={tp / (tp + fp):.3f}  recall={tp / (tp + fn):.3f}")
```

```output
TN=7219 FP=91 FN=725 TP=203
accuracy=0.901  precision=0.690  recall=0.219
```

| | Predicted no | Predicted yes |
|---|---|---|
| **Actually no** | 7,219 (TN) | 91 (FP) — wasted calls |
| **Actually yes** | 725 (FN) — missed customers | 203 (TP) — wins |

Every metric is a ratio of these four cells:

- **Accuracy** = (TP+TN)/all = 0.901. Looks great — but the never-call baseline from [part 1](/series/classification/01-classification-is-a-decision/) scores 0.887, so the model has bought us 1.4 points.
- **Precision** = TP/(TP+FP) = 0.69. *Of the people we call, how many say yes?* This is your hit rate; it drives cost per acquisition.
- **Recall** = TP/(TP+FN) = 0.22. *Of everyone who would say yes, how many did we reach?* This is your coverage; it drives total revenue.

The model is conservative: it only flags 294 people, and when it does it's usually right. It misses four in five subscribers. Is that good? **It depends entirely on where you put the threshold, and nothing about 0.5 is sacred.**

### The classification report: the same numbers, per class

Writing those ratios by hand is useful once. In practice you let scikit-learn print them for both classes:

```python
from sklearn.metrics import classification_report

print(classification_report(yte, p >= 0.5, target_names=["no", "yes"], digits=3))
```

```output
              precision    recall  f1-score   support

          no      0.909     0.988     0.947      7310
         yes      0.690     0.219     0.332       928

    accuracy                          0.901      8238
   macro avg      0.800     0.603     0.639      8238
weighted avg      0.884     0.901     0.877      8238
```

Read it from the bottom of the problem up. Start with **support**: 7,310 "no" and 928 "yes", so the "yes" class is 11.3% of the rows. Now read the two class rows:

- **The "no" row looks excellent**: precision 0.909, recall 0.988. The model leaves almost all non-subscribers alone. That is easy, because "no" is the majority.
- **The "yes" row tells the real story**: precision 0.690 matches the confusion matrix (203 / 294), but recall is only 0.219 and F1 is 0.332. The model is right when it calls, and it calls rarely.
- **The averages disagree about how good the model is.** The weighted average F1 is 0.877, and the macro average F1 is 0.639. Weighted is dominated by the 7,310 easy customers. Macro gives both classes equal weight, so it is the honest one for a rare-positive problem. (The macro recall of 0.603 is also called *balanced accuracy*: the average of recall and specificity, my own reading of the printed numbers.)

Two more ratios from the same cells, computed on the same predictions: the false positive rate is 91 / 7,310 = 0.012, and specificity is 0.988. Only 1.2% of non-subscribers get a pointless call, which is why ROC-AUC will look so comfortable later.

The report also moves with the threshold. At 0.12 (calls rise from 294 to 1,613) it reads:

```output
              precision    recall  f1-score   support

          no      0.950     0.861     0.903      7310
         yes      0.369     0.642     0.469       928

    accuracy                          0.836      8238
   macro avg      0.660     0.752     0.686      8238
weighted avg      0.885     0.836     0.854      8238
```

Accuracy fell from 0.901 to 0.836, and the model is still better by most measures that matter for the "yes" class: recall tripled (0.219 to 0.642) and F1 for "yes" rose from 0.332 to 0.469. **Accuracy went down while the model got more useful.** That is the whole argument against grading this problem by accuracy.

### The threshold is a dial, not a constant

```python
for t in (0.5, 0.25, 0.12):
    tn, fp, fn, tp = confusion_matrix(yte, p >= t).ravel()
    print(f"threshold {t:<4}: calls={tp + fp:5d}  precision={tp / (tp + fp):.2f}  recall={tp / (tp + fn):.2f}")
```

```output
threshold 0.5 : calls=  294  precision=0.69  recall=0.22
threshold 0.25: calls=  964  precision=0.49  recall=0.51
threshold 0.12: calls= 1613  precision=0.37  recall=0.64
```

Same model, same predictions, same 8,238 people. At 0.25 we make 3× as many calls and reach more than twice as many subscribers, at the price of one extra wasted call for every hit. Lower it again to 0.12 and we reach 64% of subscribers but only one call in three succeeds.

So "how good is this model?" has two separable parts:

1. **Ranking quality** — does it put likely subscribers above unlikely ones? (threshold-free)
2. **Operating point** — given the ranking, where do we cut? (a business decision)

ROC-AUC and average precision measure the first. We'll handle the second in [parts 11](/series/classification/11-probabilities-calibration-thresholds-costs/) and [14](/series/classification/14-pricing-the-models/).

### ROC-AUC: ranking quality, and its blind spot

The ROC curve (middle panel) plots recall against the false-positive *rate* as the threshold slides. **AUC is the probability that a random subscriber scores higher than a random non-subscriber.** 0.5 is a coin flip; 1.0 is perfect separation.

```python
print("ROC-AUC          :", round(roc_auc_score(yte, p), 3))
print("Average precision:", round(average_precision_score(yte, p), 3), " (random guessing ->", round(yte.mean(), 3), ")")
```

```output
ROC-AUC          : 0.801
Average precision: 0.465  (random guessing -> 0.113 )
```

AUC of 0.80 sounds strong; AP of 0.465 sounds modest. They're grading the same scores. Why the gap? Because the false-positive *rate* divides by the 7,310 negatives: a model can produce hundreds of false positives and still have a tiny FPR. **On imbalanced data ROC-AUC is optimistic because the huge negative class absorbs the damage.**

We can demonstrate it. Take the same scores, randomly throw away 80% of the positives (so the data is even more imbalanced) and re-grade:

```python
rng = np.random.default_rng(0)
keep = (yte.to_numpy() == 0) | (rng.random(len(yte)) < 0.2)
print("after dropping 80% of positives -> AUC", round(roc_auc_score(yte[keep], p[keep]), 3),
      " AP", round(average_precision_score(yte[keep], p[keep]), 3))
```

```output
after dropping 80% of positives -> AUC 0.805  AP 0.181
```

The model's *ranking* didn't change, and ROC-AUC barely moved (0.801 → 0.805). Average precision collapsed from 0.465 to 0.181, because precision *does* notice that false positives now outnumber true positives. **AP reflects how hard the job is; ROC-AUC reflects only how well the ranking separates.** When you care about the positives and they're rare, AP is the honest one — it's our primary selection metric for the series.

<div class="callout gotcha">

**Gotcha — AP is not comparable across datasets.** AP depends on the base rate: 0.465 means "4× better than random" here (random = 0.113) but would be poor on a dataset with 50% positives. Always report the random baseline next to it.

</div>

### A metric that matches the operations: precision at top-k

Real call centres don't have a threshold; they have **capacity**. Suppose agents can phone 10% of the list. Then the only question is: *of the top 10% by score, how many are subscribers?*

```python
k = int(0.10 * len(yte))
top = np.argsort(-p)[:k]
print(f"top 10% of scores: precision={yte.to_numpy()[top].mean():.2f}, captures {yte.to_numpy()[top].sum() / yte.sum():.0%} of all subscribers")
```

```output
top 10% of scores: precision=0.51, captures 45% of all subscribers
```

Calling the top tenth gets us 45% of all subscribers, with a hit rate of 51% (versus 11% for random calling). That is the sentence you'd actually say to a manager, and it doesn't involve a single ROC curve. We'll reuse this idea as a cumulative-gains chart in [part 14](/series/classification/14-pricing-the-models/).

## What did we get? Results

The numbers this chapter printed, for the same model and the same 8,238 customers:

- **At threshold 0.5:** 294 calls, precision 0.69, recall 0.22, F1 for "yes" 0.332 (macro F1 0.639).
- **At threshold 0.12:** 1,613 calls, precision 0.37, recall 0.64, F1 for "yes" 0.469, and accuracy down from 0.901 to 0.836.
- **Ranking quality:** ROC-AUC 0.801, average precision 0.465 (random guessing gives 0.113).
- **After dropping 80% of the positives:** AUC 0.805, but AP 0.181.
- **Top 10% of scores:** precision 0.51, capturing 45% of all subscribers.

![Left: precision and recall as a function of threshold. Centre: ROC curve. Right: precision-recall curve with the 11.3% baseline.](/series/classification/figures/ch03-threshold-roc-pr.png)
*Figure 1. The three standard views of one model's scores. The left panel is the only one that shows the threshold itself.*

Reading three thresholds in a table is one thing; dragging the dial is better. Move the slider and watch the confusion matrix, the ROC and precision-recall points, and the profit curve move together (this uses the held-out test scores from [part 12](/series/classification/12-head-to-head-leaderboard/)'s models).

<div class="threshold-lab" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

## Analysis and conclusion: what did we learn?

- **The same predictions get very different grades.** Accuracy says 0.901, recall says 0.22, and AUC says 0.80, all for one model.
- **Read the "yes" row of the classification report, not the averages.** Weighted-average F1 (0.877) is dominated by the easy majority, and macro-average F1 (0.639) is the honest summary.
- **Accuracy can fall while the model gets more useful.** Moving the threshold from 0.5 to 0.12 cost 6.5 points of accuracy and tripled recall.
- **ROC-AUC is optimistic on imbalanced data.** Dropping 80% of the positives left AUC almost unchanged (0.801 to 0.805) but cut AP from 0.465 to 0.181. AP tells you how hard the job really is.
- **A threshold is a business decision**, not a model property. The metrics above grade ranking quality. [Parts 11](/series/classification/11-probabilities-calibration-thresholds-costs/) and [14](/series/classification/14-pricing-the-models/) handle where to cut.

### Which metric should I use?

| If you care about… | Use | Because |
|---|---|---|
| Ranking quality on rare positives | **Average precision** | Sensitive to false positives among the top |
| Ranking quality, balanced classes | ROC-AUC | Threshold-free and intuitive |
| Quality of the *probabilities* | Log loss, Brier ([part 4](/series/classification/04-objective-functions/), [11](/series/classification/11-probabilities-calibration-thresholds-costs/)) | They punish over-confident errors |
| A fixed call capacity | Precision / recall at top-k | Matches the real constraint |
| Money | Expected profit at a chosen threshold ([part 14](/series/classification/14-pricing-the-models/)) | The only metric your CFO cares about |
| Reporting to people outside ML | The confusion matrix with counts | Nobody misreads "294 calls, 203 successes" |

And the one we are **not** going to lead with: accuracy. On this data its maximum achievable improvement over "always no" is about 2 percentage points, and it cannot tell a useful model from a useless one.

### So what did we do?

We took one logistic regression and graded it four ways. Accuracy hides the problem, ROC-AUC flatters it, and average precision and precision at top-k tell the truth about rare positives. Average precision is our main selection metric for the rest of the series.

### In the next part

[Part 4](/series/classification/04-objective-functions/) looks inside the training loop: what does a model actually minimise, and why do different losses produce different models?
