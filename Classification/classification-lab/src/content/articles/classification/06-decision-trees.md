---
title: "Decision Trees: Easy to Read, Easy to Overfit"
description: "A fully grown tree scores 0.99 on the rows it was fitted on and 0.19 on rows it has not seen. We compute a split by hand, watch the gap open as the tree grows, and read a small tree like a flowchart."
series: "classification"
order: 6
date: 2026-09-30
updated: 2026-10-04
keywords: ["decision trees", "gini impurity", "overfitting", "cross-validation", "scikit-learn"]
readingTime: "12 min read"
figure: "ch06-tree-overfit.png"
---

Grow a decision tree until it cannot split any further and it scores 0.99 average precision on the rows it was fitted on. Ask it about rows it has not seen, using cross-validation, and the score is 0.19. A tree can memorise. This chapter shows how to see that in numbers, how to stop it, and what a small tree is good for.

<div class="callout">

**Goal.** Understand how a tree chooses its splits, how its complexity should be controlled, and what it can and cannot tell you.

**Work plan.** Compute one split by hand with Gini impurity. Grow trees of increasing depth and compare scores on fitted rows and on held-out rows. Control complexity with the minimum leaf size. Print a small tree and read it.

</div>

## How a tree chooses a split

A tree is grown greedily. At each node it looks at every feature and every candidate threshold, picks the split that makes the two child groups most "pure", and repeats inside each child. Purity is measured here by **Gini impurity**: for a node where a share *p* of records subscribe, `gini = 2·p·(1−p)`. It is 0 for a node with a single class and 0.5 for a 50/50 mix. A split's value is the impurity it removes, weighted by the size of each child.

**Implementation.** Compute it ourselves on the development rows.

```python
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
Xd, yd = X.iloc[dev], y[dev]

gini = lambda labels: 2 * labels.mean() * (1 - labels.mean())

def gain(feature, threshold):
    left = yd[Xd[feature].to_numpy() <= threshold]
    right = yd[Xd[feature].to_numpy() > threshold]
    child = (len(left) * gini(left) + len(right) * gini(right)) / len(yd)
    return gini(yd) - child

print(f"root impurity: {gini(yd):.4f}")
for feature, t in [("euribor3m", 1.0), ("euribor3m", 5.0), ("pdays", 16.5), ("nr.employed", 5087.65)]:
    print(f"split {feature} <= {t}: impurity removed {gain(feature, t):.4f}")
```

**Result.**

```output
root impurity: 0.1999
split euribor3m <= 1.0: impurity removed 0.0247
split euribor3m <= 5.0: impurity removed 0.0001
split pdays <= 16.5: impurity removed 0.0209
split nr.employed <= 5087.65: impurity removed 0.0297
```

**What it means.** The root impurity is 0.1999, from an 11.3% share of subscribers. Splitting on `nr.employed` at 5,087.65 removes the most of these four candidates, a cut of the interest rate at 5.0 removes almost nothing, and a cut at 1.0 removes a useful amount. A tree-fitting algorithm is this calculation repeated for every feature and every threshold at every node. scikit-learn does it in compiled code, but nothing more mysterious is going on.

## The same tree at different depths

The question that matters is when to stop. We vary `max_depth` and score average precision twice: on the rows the tree was fitted on, and with 5-fold cross-validation on the development rows (each fold's score comes from rows its tree never saw).

**Implementation.**

```python
from sklearn.compose import make_column_transformer
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import average_precision_score
from sklearn.tree import DecisionTreeClassifier

cat = [c for c in X.columns if X[c].dtype == object]
prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder="passthrough")
cv = StratifiedKFold(5, shuffle=True, random_state=42)

print(f"{'max_depth':>9}{'leaves':>8}{'fitted rows':>13}{'held-out (CV)':>15}")
for depth in (2, 3, 5, 8, 12, None):
    tree = make_pipeline(prep, DecisionTreeClassifier(max_depth=depth, random_state=42)).fit(Xd, yd)
    fitted = average_precision_score(yd, tree.predict_proba(Xd)[:, 1])
    held_out = cross_val_score(tree, Xd, yd, scoring="average_precision", cv=cv).mean()
    print(f"{str(depth):>9}{tree[-1].get_n_leaves():>8}{fitted:>13.3f}{held_out:>15.3f}")
```

**Result.**

```output
max_depth  leaves  fitted rows  held-out (CV)
        2       4        0.346          0.346
        3       8        0.374          0.371
        5      32        0.435          0.405
        8     182        0.514          0.389
       12     742        0.644          0.321
     None    5265        0.993          0.186
```

![Average precision on the fitted rows keeps rising with depth, while cross-validated average precision peaks and then falls.](/series/classification/figures/ch06-tree-overfit.png)
*Figure 1. The gap between scores on fitted rows and on held-out rows opens as the tree grows.*

**What it means.** Shallow trees (depth 2 and 3) score about the same on both, so they are too simple. The held-out score peaks near depth 5, while the fitted-rows score keeps climbing to 0.993 for the unlimited tree and the held-out score falls to 0.186 (a random ranking scores 0.113). That tree has 5,265 leaves for about 26,000 training records, so many leaves hold a handful of records. **A score on the rows a flexible model was fitted on says little about new rows.**

## A better dial: the smallest leaf

`max_depth` limits every branch equally. The **minimum leaf size** (`min_samples_leaf`) is more targeted: a split is only allowed if both children keep at least that many records, so a branch can go deep where there is data, and a leaf of three records cannot happen.

| min_samples_leaf | leaves | fitted rows | held-out (CV) | fold sd |
|---|---|---|---|---|
| 1 | 5,265 | 0.993 | 0.186 | 0.007 |
| 5 | 2,438 | 0.727 | 0.313 | 0.009 |
| 10 | 1,600 | 0.633 | 0.366 | 0.012 |
| 25 | 826 | 0.552 | 0.417 | 0.012 |
| 50 | 458 | 0.513 | 0.437 | 0.006 |
| 100 | 254 | 0.486 | 0.441 | 0.015 |
| 200 | 122 | 0.463 | 0.435 | 0.014 |
| 500 | 52 | 0.417 | 0.403 | 0.010 |

On this data, leaf sizes of 50 to 100 give the best held-out scores tried (0.437 and 0.441, against 0.405 for the best depth limit); leaves of 1 or 5 overfit and leaves of 500 underfit. That is a finding about this dataset and its size, not a universal rule: with ten times the data the best leaf is probably larger, and smaller leaves can be sensible inside an ensemble (part 7). Larger leaves also make each leaf value a share of many records, which gives a finer ranking.

## Reading a small tree

The biggest advantage of a small tree is that it documents itself. Here is a tree with depth 3 and leaves of at least 50 records, fitted on the development rows. Each leaf shows `[no, yes]` counts.

**Implementation.**

```python
from sklearn.tree import export_text

small = make_pipeline(prep, DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, random_state=42)).fit(Xd, yd)
print(export_text(small[-1], feature_names=list(small[0].get_feature_names_out()), show_weights=True))
```

**Result.**

```output
|--- remainder__nr.employed <= 5087.65
|   |--- remainder__pdays <= 16.50
|   |   |--- onehotencoder__day_of_week_mon <= 0.50
|   |   |   |--- weights: [205.00, 583.00] class: 1
|   |   |--- onehotencoder__day_of_week_mon >  0.50
|   |   |   |--- weights: [93.00, 109.00] class: 1
|   |--- remainder__pdays >  16.50
|   |   |--- onehotencoder__contact_cellular <= 0.50
|   |   |   |--- weights: [382.00, 110.00] class: 0
|   |   |--- onehotencoder__contact_cellular >  0.50
|   |   |   |--- weights: [1552.00, 957.00] class: 0
|--- remainder__nr.employed >  5087.65
|   |--- remainder__cons.conf.idx <= -46.65
|   |   |--- remainder__euribor3m <= 1.53
|   |   |   |--- weights: [1611.00, 357.00] class: 0
|   |   |--- remainder__euribor3m >  1.53
|   |   |   |--- weights: [110.00, 94.00] class: 0
|   |--- remainder__cons.conf.idx >  -46.65
|   |   |--- onehotencoder__month_oct <= 0.50
|   |   |   |--- weights: [25264.00, 1468.00] class: 0
|   |   |--- onehotencoder__month_oct >  0.50
|   |   |   |--- weights: [21.00, 34.00] class: 1
```

**What it means.** Follow the first branch: `nr.employed` at or below 5,087.65, `pdays` at most 16.5 (contacted in a previous campaign within 16 days), and not on a Monday. That leaf holds 205 "no" and 583 "yes" records (74%), the best segment, and a linear model would need a hand-made interaction to express it. Note what `nr.employed` does at the root: it falls steadily through the file (rank correlation with row position -0.58), so a split on it separates early from late records and works as a stand-in for *time*. Part 16 shows what that does to a model asked to predict later records.

## Analysis and conclusion: what we learned

- **Scores on fitted rows are not evidence of generalisation.** The unlimited tree reached 0.99 on the rows it memorised and 0.19 on held-out rows.
- **Complexity needs a dial.** Depth 5 and a minimum leaf of 50 to 100 are the best settings tested here, and the leaf-size dial did slightly better.
- **A small tree is a readable summary**, but one tree is a high-variance model: changing which records it sees can change its top splits, which is what bagging exploits in part 7.
- **A tree can use a column as a clock.** Treat strong splits on `nr.employed` or the interest rate as a flag to investigate, not as customer behaviour.

*Further reading.* Breiman, Friedman, Olshen and Stone (1984), *Classification and Regression Trees*.

[Part 7](/series/classification/07-bagging-random-forests/) builds on this: if one tree is unstable, what happens when you average many of them?
