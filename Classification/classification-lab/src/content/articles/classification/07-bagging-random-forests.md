---
title: "Bagging and Random Forests: Averaging Away the Noise"
description: "Build bagging from scratch in ten lines, watch one tree at 0.365 average precision become 0.489 when averaged, then see what the 'random' in random forest adds."
series: "classification"
order: 7
date: 2026-09-30
updated: 2026-10-02
keywords: ["random forest", "bagging", "extra trees", "bootstrap", "out-of-bag", "ensemble methods"]
readingTime: "15 min read"
figure: "ch07-bagging.png"
---

In [part 6](/series/classification/06-decision-trees/) we found that a single decision tree is an unstable learner: shuffle the training rows slightly and you get a different tree, with different splits and different predictions. That sounds like a flaw. **Bagging turns it into the whole strategy.**

The idea: if each tree makes errors that are partly *independent* of the other trees' errors, averaging many trees cancels the noise while keeping the signal. Let's implement it before using the library version, so that "random forest" stops being a black box.

## Goals: what are we trying to achieve?

One tree is unstable. Our goal is to turn that weakness into a strength by averaging many trees, and to understand why it works instead of treating "random forest" as a black box.

By the end you will be able to:

- **Build bagging in about ten lines** and measure how many trees are enough.
- **Explain the random-forest trick** (a random subset of features at each split) in terms of correlation between trees.
- **Use out-of-bag scores** as a free validation set, and know what to tune.

## The work plan: how do we do it?

We build up from a hand-made ensemble to the library version:

1. **Bagging from scratch**: 200 trees on bootstrap samples, averaged.
2. **Measure the correlation** between trees, to see why more randomness helps.
3. **Random forest and Extra Trees**: vary `max_features` and compare score and fit time.
4. **Out-of-bag score and number of trees**: cheap checks that need no extra data.

## Implementation

### Bagging from scratch

**B**ootstrap **agg**regat**ing**: give each tree its own random sample of the training rows, drawn *with replacement* (so each sample contains about 63% of the distinct rows, some duplicated), then average their predicted probabilities.

```python
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()
prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                         remainder="passthrough")
A, B = prep.fit_transform(Xtr), prep.transform(Xte)

rng = np.random.default_rng(0)
votes = []
for i in range(200):
    rows = rng.integers(0, len(A), len(A))                      # sample WITH replacement
    tree = DecisionTreeClassifier(min_samples_leaf=20, random_state=i).fit(A[rows], ytr[rows])
    votes.append(tree.predict_proba(B)[:, 1])
votes = np.array(votes)                                          # shape (200 trees, 8238 customers)
```

That's the whole algorithm. Now the payoff — score the first tree alone, then the average of the first 5, 25, 100 and all 200:

```python
print("one tree        AP:", round(average_precision_score(yte, votes[0]), 3))
for n in (5, 25, 100, 200):
    print(f"average of {n:>3} AP:", round(average_precision_score(yte, votes[:n].mean(axis=0)), 3))
```

```output
one tree        AP: 0.365
average of   5 AP: 0.469
average of  25 AP: 0.488
average of 100 AP: 0.489
average of 200 AP: 0.489
```

Look at what happened. None of the trees is any better than before — over the first 50, a single tree averages 0.391 (the first one, 0.365, was slightly unlucky) — but **their average is 0.489, a 25% improvement on the typical tree**, larger than anything tuning bought us for a single tree in [part 6](/series/classification/06-decision-trees/). And almost all of it arrives by 25 trees; going from 100 to 200 buys nothing. That's the signature of variance reduction: it's a one-time gain that saturates.

Why does it work? Each tree overfits, but *differently*. Their errors are partly random and cancel in the mean. The key quantity is how *correlated* the trees are. If they were identical, averaging would change nothing. Let's measure:

```python
corr = np.corrcoef(votes[:20])
print("mean correlation between two trees' scores:", round(corr[np.triu_indices(20, 1)].mean(), 3))
```

```output
mean correlation between two trees' scores: 0.661
```

A correlation of 0.66 is high — the trees are still quite similar. They're all greedy, and they all start by splitting on the same strong features (`nr.employed`, `euribor3m`, `pdays`). To squeeze out more variance reduction we need *less* correlated trees.

### The random forest trick

Random forests add one idea to bagging: **at every split, only consider a random subset of the features** (`max_features`). Different trees are forced to build from different raw material, which decorrelates them. The price is that each individual tree is slightly weaker.

```python
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
import time

for name, model in {
    "RF  max_features=sqrt": RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", n_jobs=-1, random_state=0),
    "RF  max_features=0.5 ": RandomForestClassifier(300, min_samples_leaf=10, max_features=0.5, n_jobs=-1, random_state=0),
    "RF  max_features=1.0 ": RandomForestClassifier(300, min_samples_leaf=10, max_features=1.0, n_jobs=-1, random_state=0),
    "Extra trees          ": ExtraTreesClassifier(300, min_samples_leaf=10, max_features="sqrt", n_jobs=-1, random_state=0),
}.items():
    t0 = time.perf_counter(); model.fit(A, ytr); secs = time.perf_counter() - t0
    print(f"{name}  AP={average_precision_score(yte, model.predict_proba(B)[:, 1]):.3f}  fit={secs:.1f}s")
```

```output
RF  max_features=sqrt  AP=0.491  fit=2.5s
RF  max_features=0.5   AP=0.490  fit=6.2s
RF  max_features=1.0   AP=0.486  fit=17.1s
Extra trees            AP=0.484  fit=4.4s
```

- `max_features=1.0` *is* plain bagging of full-strength trees. Its AP is the lowest of the three and it takes **7× longer** than `sqrt`, because every split evaluates every feature (there are 62 columns after one-hot encoding).
- `sqrt` — about 8 features per split — is both the fastest and the best. This is why it's the library default for classification.
- **Extra Trees** ("extremely randomised") go one step further: for each candidate feature they pick the split threshold *at random* instead of searching for the best one. Even less correlated, even faster per tree, at the price of a little more bias. It lands at 0.484 here — within noise of RF. It's a nice sanity check that your forest isn't winning on fine-grained threshold search.

<div class="callout tip">

**What to tune in a random forest.** In order of impact: `min_samples_leaf` (same story as [part 6](/series/classification/06-decision-trees/) — 5–30 works for imbalanced problems, never 1), then `max_features`. `n_estimators` is not a tuning parameter; it's a budget. More trees never hurt accuracy, they just cost time. Use 300–500 and stop thinking about it.

</div>

### A free validation set: out-of-bag scores

Each bootstrap sample omits about 37% of the rows. Those rows are "out of bag" for that tree, which means **every training row was not seen by roughly a third of the trees**. Average only those trees' predictions for each row and you have an honest prediction with no separate validation set:

```python
rf = RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", oob_score=True, n_jobs=-1, random_state=0).fit(A, ytr)
print("OOB accuracy :", round(rf.oob_score_, 3))
print("OOB-based AP :", round(average_precision_score(ytr, rf.oob_decision_function_[:, 1]), 3))
print("test AP      :", round(average_precision_score(yte, rf.predict_proba(B)[:, 1]), 3))
```

```output
OOB accuracy : 0.9
OOB-based AP : 0.466
test AP      : 0.491
```

OOB AP (0.466) lands within 0.025 of the test score (0.491) without touching the test set. It's a convenient smoke test. It's also slightly pessimistic, because each OOB prediction uses only ~100 of the 300 trees. We'll still use cross-validation for model selection, because OOB doesn't generalise to other model families, but it's good to know it exists.

### How many trees?

```python
for n in (10, 50, 100, 300, 600):
    m = RandomForestClassifier(n, min_samples_leaf=10, max_features="sqrt", n_jobs=-1, random_state=0).fit(A, ytr)
    print(f"n_estimators={n:<4} test AP={average_precision_score(yte, m.predict_proba(B)[:, 1]):.3f}")
```

```output
n_estimators=10   test AP=0.487
n_estimators=50   test AP=0.489
n_estimators=100  test AP=0.490
n_estimators=300  test AP=0.491
n_estimators=600  test AP=0.492
```

Ten trees already reach 0.487; the next 590 add 0.005. Don't spend your tuning budget here.

## What did we get? Results

Test average precision, same split as every chapter:

| Model | AP |
|---|---|
| One tree | 0.365 |
| Average of 5 trees | 0.469 |
| Average of 25 trees | 0.488 |
| Average of 200 trees | 0.489 |
| Random forest, `max_features="sqrt"` | 0.491 (fit 2.5 s) |
| Random forest, `max_features=1.0` | 0.486 (fit 17.1 s) |
| Extra Trees | 0.484 |

- **Correlation between two trees' scores:** 0.661.
- **Out-of-bag AP** 0.466 against test AP 0.491.
- **Number of trees:** 10 trees reach 0.487, and 600 reach 0.492.

![Test average precision of a bagged ensemble as the number of trees grows.](/series/classification/figures/ch07-bagging.png)
*Figure 1. Averaging is worth +0.10 to +0.12 average precision, and most of it arrives in the first 25 trees. After that the curve is flat.*

## Analysis and conclusion: what did we learn?

- **Averaging is a one-time gain.** The first 25 trees give almost all of it, and 100 to 200 trees add nothing. That is the signature of variance reduction.
- **Less correlated trees do better.** A correlation of 0.661 means the trees are still similar. Picking about 8 features per split (`sqrt`) gives the best AP and is 7 times faster than using all 62 columns.
- **Do not tune `n_estimators`.** It is a budget, not a parameter. Spend tuning effort on `min_samples_leaf` and `max_features`.
- **A forest reduces variance, not bias.** If a single tree is stable but too simple, a forest will not help. Boosting ([Part 8](/series/classification/08-gradient-boosting/)) attacks the other half.

### Strengths, weaknesses, what to remember

**Strengths.** Excellent out-of-the-box performance, almost no tuning, handles mixed feature types, no scaling needed, parallel training, robust to outliers.

**Weaknesses.**

- **Bias.** Averaging cuts variance but each tree is still a shallow-ish, greedy piece. Forests can't fit very sharp signals as well as boosting, which *corrects* errors rather than averaging them.
- **Probabilities can be compressed.** Averaging leaf proportions pulls scores toward the centre, and forests with tiny leaves rarely output extreme values even for near-certain cases. With `min_samples_leaf=10` on this data the damage is small (we'll measure it in [part 11](/series/classification/11-probabilities-calibration-thresholds-costs/)), but don't assume it: always check calibration.
- **Size and speed at inference.** 300 trees × thousands of leaves means a model file of tens of megabytes and millisecond-scale prediction, compared with microseconds for logistic regression.
- **Interpretability.** You can't read 300 trees. Importance scores exist, but see [part 15](/series/classification/15-inside-the-winner/) for why to be careful with them.

**Mental model:** a forest is a *variance-reduction* machine. If your single tree is unstable, a forest will help a lot; if your single tree is stable but too simple, it won't.

The next part attacks the other half of the problem. [Part 8](/series/classification/08-gradient-boosting/) builds boosting from scratch: instead of averaging independent trees, it trains each new tree to fix the mistakes of the ones before it.

### So what did we do?

We built bagging by hand, saw it lift AP from 0.365 to 0.489, and found that decorrelating the trees with random feature subsets gets a little more, much faster. A forest is a variance-reduction machine that needs almost no tuning.

### In the next part
