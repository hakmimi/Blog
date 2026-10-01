---
title: "What Does 'Good' Mean? Precision, Recall, ROC and PR"
description: "One logistic regression, four ways of grading it. We compute every metric by hand, move the threshold, and see why average precision beats ROC-AUC on imbalanced data."
series: "classification"
order: 3
date: 2026-09-30
updated: 2026-10-01
keywords: ["precision recall", "roc auc", "average precision", "confusion matrix", "metrics"]
readingTime: "14 min read"
figure: "ch03-threshold-roc-pr.png"
---

We need a model to grade, so let's train the simplest serious one: logistic regression on the 19 pre-call features. Don't worry about how it works yet (part 5). The point of this chapter is that **the same set of predictions can look brilliant or useless depending on the metric**.

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

## The confusion matrix: four numbers that contain everything

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

- **Accuracy** = (TP+TN)/all = 0.901. Looks great — but the never-call baseline from part 1 scores 0.887, so the model has bought us 1.4 points.
- **Precision** = TP/(TP+FP) = 0.69. *Of the people we call, how many say yes?* This is your hit rate; it drives cost per acquisition.
- **Recall** = TP/(TP+FN) = 0.22. *Of everyone who would say yes, how many did we reach?* This is your coverage; it drives total revenue.

The model is conservative: it only flags 294 people, and when it does it's usually right. It misses four in five subscribers. Is that good? **It depends entirely on where you put the threshold, and nothing about 0.5 is sacred.**

## The threshold is a dial, not a constant

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

![Left: precision and recall as a function of threshold. Centre: ROC curve. Right: precision-recall curve with the 11.3% baseline.](/series/classification/figures/ch03-threshold-roc-pr.png)
*Figure 1. The three standard views of one model's scores. The left panel is the only one that shows the threshold itself.*

So "how good is this model?" has two separable parts:

1. **Ranking quality** — does it put likely subscribers above unlikely ones? (threshold-free)
2. **Operating point** — given the ranking, where do we cut? (a business decision)

ROC-AUC and average precision measure the first. We'll handle the second in parts 11 and 14.

Reading three thresholds in a table is one thing; dragging the dial is better. Move the slider and watch the confusion matrix, the ROC and precision-recall points, and the profit curve move together (this uses the held-out test scores from part 12's models).

<div class="threshold-lab" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

## ROC-AUC: ranking quality, and its blind spot

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

## A metric that matches the operations: precision at top-k

Real call centres don't have a threshold; they have **capacity**. Suppose agents can phone 10% of the list. Then the only question is: *of the top 10% by score, how many are subscribers?*

```python
k = int(0.10 * len(yte))
top = np.argsort(-p)[:k]
print(f"top 10% of scores: precision={yte.to_numpy()[top].mean():.2f}, captures {yte.to_numpy()[top].sum() / yte.sum():.0%} of all subscribers")
```

```output
top 10% of scores: precision=0.51, captures 45% of all subscribers
```

Calling the top tenth gets us 45% of all subscribers, with a hit rate of 51% (versus 11% for random calling). That is the sentence you'd actually say to a manager, and it doesn't involve a single ROC curve. We'll reuse this idea as a cumulative-gains chart in part 14.

## Which metric should I use?

| If you care about… | Use | Because |
|---|---|---|
| Ranking quality on rare positives | **Average precision** | Sensitive to false positives among the top |
| Ranking quality, balanced classes | ROC-AUC | Threshold-free and intuitive |
| Quality of the *probabilities* | Log loss, Brier (part 4, 11) | They punish over-confident errors |
| A fixed call capacity | Precision / recall at top-k | Matches the real constraint |
| Money | Expected profit at a chosen threshold (part 14) | The only metric your CFO cares about |
| Reporting to people outside ML | The confusion matrix with counts | Nobody misreads "294 calls, 203 successes" |

And the one we are **not** going to lead with: accuracy. On this data its maximum achievable improvement over "always no" is about 2 percentage points, and it cannot tell a useful model from a useless one.

[Part 4](/series/classification/04-objective-functions/) looks inside the training loop: what does a model actually minimise, and why do different losses produce different models?
