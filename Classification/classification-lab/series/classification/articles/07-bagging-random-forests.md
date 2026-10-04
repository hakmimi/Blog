---
title: "Bagging and Random Forests: Averaging Away the Noise"
description: "Each tree overfits differently, so their average is better than any one of them. We build bagging by hand, measure how correlated the trees are, and test what randomness, tree count and out-of-bag scores actually do."
series: "classification"
order: 7
date: 2026-09-30
updated: 2026-10-04
keywords: ["bagging", "random forest", "extra trees", "out-of-bag", "variance reduction"]
readingTime: "11 min read"
figure: "ch07-bagging.png"
---

A single small tree scores about @@v:bagging_curve_summary.csv|trees=1|mean|.2f@@ average precision on rows it has not seen. Average 200 trees, each of them no better than before, and the score is about @@v:bagging_curve_summary.csv|trees=200|mean|.2f@@. Nothing in any individual tree improved. The average did, because the trees' mistakes are partly independent and cancel.

<div class="callout">

**Goal.** Understand why averaging many unstable trees works, what makes it work better, and what a forest costs.

**Work plan.** Build bagging from scratch and score it on inner validation rows while the number of trees grows. Measure how correlated the trees are. Compare random forests and extra trees. Check how many trees are enough, and what the out-of-bag score tells you.

</div>

## Bagging from scratch

**Bagging** (bootstrap aggregating) gives each tree its own sample of the training rows, drawn with replacement, and averages their predicted probabilities. A bootstrap sample contains about 63% of the distinct rows, some of them several times. All experiments in this chapter fit on 75% of the development rows (the *fit* rows) and score on the other 25% (the *validation* rows). The comparison split is not used.

**Implementation.** Fit 200 trees, one per bootstrap sample, and score the average of the first n.

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
fit, val = train_test_split(dev, test_size=0.25, stratify=y[dev], random_state=42)

cat = [c for c in X.columns if X[c].dtype == object]
prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder="passthrough")
A, B = prep.fit_transform(X.iloc[fit]), prep.transform(X.iloc[val])
yf, yv = y[fit], y[val]

rng = np.random.default_rng(0)
votes = []
for i in range(200):
    rows = rng.integers(0, len(A), len(A))                          # a bootstrap sample
    tree = DecisionTreeClassifier(min_samples_leaf=20, random_state=i).fit(A[rows], yf[rows])
    votes.append(tree.predict_proba(B)[:, 1])
votes = np.array(votes)

for n in (1, 5, 25, 100, 200):
    print(f"average of {n:>3} trees: validation AP {average_precision_score(yv, votes[:n].mean(axis=0)):.3f}")
```

**Result.** The snippet runs one bootstrap seed. We repeated the whole experiment with five seeds, so the table shows how much the curve itself varies.

@@table:bagging_curve_summary.csv|cols=trees,mean,std,min,max|rename=trees:trees averaged,mean:mean AP,std:sd,min:min,max:max|fmt=trees:d@@

```output
(filled in by the build)
```

![Validation average precision of a bagged ensemble as trees are added; line is the mean over five seeds, band the range.](/series/classification/figures/ch07-bagging.png)
*Figure 1. Averaging helps quickly, then flattens.*

**What it means.** Averaging lifts the score from about @@v:bagging_curve_summary.csv|trees=1|mean|.2f@@ for one tree to about @@v:bagging_curve_summary.csv|trees=200|mean|.2f@@ for 200, and more than half of the gain arrives with the first five trees; beyond 50 trees the mean moves by less than 0.001 per doubling. That is variance reduction: a one-time gain that saturates, with a seed-to-seed spread that also shrinks (sd @@v:bagging_curve_summary.csv|trees=5|std|.3f@@ at 5 trees, @@v:bagging_curve_summary.csv|trees=200|std|.3f@@ at 200).

Each tree overfits differently, so part of their error is random and cancels in the mean, and how much cancels depends on how **correlated** the trees are (identical trees would gain nothing). The average correlation between pairs of tree scores is @@j:bagging_oob.json|mean_pairwise_tree_correlation_by_seed.0|.2f@@ for the first seed and 0.67 to 0.68 across all five: high, because all trees start from the same strong columns (`nr.employed`, `euribor3m`, `pdays`). There is room for less correlated trees to do better.

## The random-forest idea

A **random forest** adds one ingredient to bagging: at every split, only a random subset of the features is considered (`max_features`). Trees are forced to use different material, which lowers their correlation, at the price of each tree being slightly weaker. **Extra trees** go further and pick the split threshold at random as well. Here are the variants, each with 300 trees and a minimum leaf of 10, three fitting seeds:

@@table:bagging_forest_summary.csv|cols=model,val_ap_mean,val_ap_sd,fit_seconds_mean|rename=model:variant,val_ap_mean:validation AP,val_ap_sd:sd over seeds,fit_seconds_mean:fit seconds|fmt=fit_seconds_mean:.1f@@

`max_features = sqrt` (about 8 of the 62 one-hot columns per split) gives the best score among those tried and the shortest fit. Using all features, which is plain bagging of full-strength trees, gives the lowest AP and the longest fit. Extra trees land close to the forest. These timings come from a shared, busy machine, so trust the ordering, not the seconds (part 12 has timings from an idle machine). The ordering depends on this dataset: with other data a larger `max_features` can win.

## How many trees?

Trees are cheap to add, but is more always better? We scored forests of 10 to 600 trees with five fitting seeds each:

@@table:bagging_n_estimators_summary.csv|cols=n_estimators,mean,std,min,max|rename=n_estimators:trees,mean:mean AP,std:sd,min:min,max:max|fmt=n_estimators:d@@

The score rises from @@v:bagging_n_estimators_summary.csv|n_estimators=10|mean|.3f@@ with 10 trees to @@v:bagging_n_estimators_summary.csv|n_estimators=300|mean|.3f@@ with 300, then stops moving (@@v:bagging_n_estimators_summary.csv|n_estimators=600|mean|.3f@@ at 600). A single run need not improve with every added tree, since the seed-to-seed spread (about 0.003 for small forests) is as large as late gains. Treat `n_estimators` as a resource and stability setting, not a tuning dimension: use enough trees that results stop changing with the seed, and tune `min_samples_leaf` and `max_features`.

## Out-of-bag scores

Each bootstrap sample leaves out about 37% of the rows, so every training row is "out of bag" for about a third of the trees. Averaging only those trees' predictions for each row gives an evaluation that needs no separate validation data.

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", oob_score=True, n_jobs=4, random_state=0).fit(A, yf)
print(f"out-of-bag AP : {average_precision_score(yf, rf.oob_decision_function_[:, 1]):.3f}")
print(f"validation AP : {average_precision_score(yv, rf.predict_proba(B)[:, 1]):.3f}")
```

```output
(filled in by the build)
```

The out-of-bag score is a little lower than the validation score. One tempting explanation is that out-of-bag predictions use only about a third of the trees. We tested it: random subsets of 100 of the 300 trees give a validation AP of @@j:bagging_oob.json|val_ap_random_100_of_300_mean|.3f@@ (sd @@j:bagging_oob.json|val_ap_random_100_of_300_sd|.3f@@ over 20 draws), almost the same as all 300 (@@j:bagging_oob.json|val_ap_300_trees|.3f@@), so that does not explain the gap. We did not test other explanations. Out-of-bag evaluation also assumes exchangeable records and says nothing about later records when the data have a time structure (part 16).

## What a forest costs

- **Bias.** Averaging reduces variance but each tree is still a greedy, fairly shallow piece. Boosting (part 8) corrects errors instead of averaging them.
- **Probabilities.** Averaged leaf proportions can be compressed or over-spread depending on leaf size. Part 11 measures this for the default (minimum leaf 1) and for a leaf of 10.
- **Size and prediction cost.** 300 trees with thousands of leaves mean a larger model file and slower scoring than a linear model. Part 12 reports measured timings.
- **Interpretation.** You cannot read 300 trees. Importance scores exist, with caveats (part 15).

## Analysis and conclusion: what we learned

- **A forest is a variance-reduction machine.** Averaging raised validation AP from about @@v:bagging_curve_summary.csv|trees=1|mean|.2f@@ (one tree) to about @@v:bagging_n_estimators_summary.csv|n_estimators=300|mean|.2f@@ (a forest of 300 with random feature subsets), with most of the gain in the first few trees.
- **Decorrelating trees helps on this data.** Random feature subsets scored @@v:bagging_forest_summary.csv|model=RF max_features=sqrt|val_ap_mean|.3f@@ against @@v:bagging_forest_summary.csv|model=RF max_features=1.0 (bagging)|val_ap_mean|.3f@@ for plain bagging with the same leaf size.
- **Treat the tree count as a resource.** It stabilises results; the settings worth tuning are the leaf size and the feature fraction.
- **Check an out-of-bag score against a real validation set before trusting it**, and never as evidence about future periods.

*Further reading.* Breiman (1996), [Bagging predictors](https://doi.org/10.1007/BF00058655); Breiman (2001), [Random forests](https://doi.org/10.1023/A:1010933404324).

[Part 8](/series/classification/08-gradient-boosting/) attacks the other side of the problem: instead of averaging independent trees, each new tree learns from the mistakes of the ones before it.
