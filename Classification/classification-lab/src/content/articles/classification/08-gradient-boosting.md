---
title: "Gradient Boosting: Learning From the Last Tree's Mistakes"
description: "Boosting builds many small trees in sequence, each fitted to what the ensemble so far gets wrong. We write the loop in a few lines, watch the learning rate trade speed against how long you can run, and see why early stopping exists."
series: "classification"
order: 8
date: 2026-09-30
updated: 2026-10-04
keywords: ["gradient boosting", "learning rate", "early stopping", "xgboost", "lightgbm", "catboost"]
readingTime: "12 min read"
figure: "ch08-boosting-lr.png"
---

Fit a boosting model with a learning rate of 0.5 and its score on rows it has not seen peaks after about 100 trees and then falls. Meanwhile its score on the rows it was fitted on keeps rising. Nothing in the algorithm tells it to stop. That one observation explains most of the practical advice about boosting.

<div class="callout">

**Goal.** Understand the boosting loop, what the learning rate does to it, and how to choose the number of trees without guessing.

**Work plan.** Write gradient boosting with log loss in a few lines. Run it at three learning rates and score each stage on inner validation rows. Then let early stopping choose the number of trees, and place the named libraries in context.

</div>

## The algorithm in plain words

Random forests average many independent, deep trees. Boosting does the opposite: it adds many small trees one after another, and each new tree is trained to fix what the ensemble so far still gets wrong.

1. Start with a constant score: the log-odds of the overall rate.
2. For each record compute the **residual**: outcome minus current predicted probability. For log loss this is exactly the negative gradient of the loss with respect to the current score.
3. Fit a small tree to predict those residuals.
4. Add that tree's output, multiplied by a small **learning rate**, to the running score.
5. Repeat.

The prediction is `sigmoid(F₀ + η·tree₁ + η·tree₂ + …)`. Each step is a gradient-descent step, taken in the space of functions instead of the space of weights. As before we fit on 75% of the development rows and score on the other 25%.

**Implementation.**

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

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
sigmoid = lambda z: 1 / (1 + np.exp(-z))

def boost(lr, stages):
    start = np.log(yf.mean() / (1 - yf.mean()))                     # stage 0: the base rate
    F_fit, F_val = np.full(len(A), start), np.full(len(B), start)
    curve = {}
    for m in range(1, stages + 1):
        residual = yf - sigmoid(F_fit)                              # negative gradient of log loss
        tree = DecisionTreeRegressor(max_depth=3, min_samples_leaf=20).fit(A, residual)
        F_fit += lr * tree.predict(A)
        F_val += lr * tree.predict(B)
        if m in (1, 10, 50, 100, 300):
            curve[m] = (average_precision_score(yv, F_val), average_precision_score(yf, F_fit))
    return curve

for lr in (0.5, 0.1):
    print(f"learning rate {lr}")
    for m, (v, f) in boost(lr, 300).items():
        print(f"  {m:>4} trees: validation AP {v:.3f}   fitted rows AP {f:.3f}")
```

**Result.**

```output
learning rate 0.5
     1 trees: validation AP 0.374   fitted rows AP 0.374
    10 trees: validation AP 0.408   fitted rows AP 0.409
    50 trees: validation AP 0.458   fitted rows AP 0.472
   100 trees: validation AP 0.461   fitted rows AP 0.493
   300 trees: validation AP 0.454   fitted rows AP 0.527
learning rate 0.1
     1 trees: validation AP 0.374   fitted rows AP 0.374
    10 trees: validation AP 0.378   fitted rows AP 0.382
    50 trees: validation AP 0.413   fitted rows AP 0.417
   100 trees: validation AP 0.452   fitted rows AP 0.451
   300 trees: validation AP 0.457   fitted rows AP 0.476
```

That loop is gradient boosting. Real libraries add a second-order step to set the leaf values, regularisation and much faster split finding, but the skeleton is this.

## Learning rate, made visible

The table runs the same loop for 1,000 stages at three learning rates (validation AP; the snippet above shows the first 300 stages for two of them).

| trees | 0.5 | 0.1 | 0.02 |
|---|---|---|---|
| 1 | 0.374 | 0.374 | 0.374 |
| 10 | 0.408 | 0.378 | 0.374 |
| 25 | 0.456 | 0.391 | 0.376 |
| 50 | 0.458 | 0.413 | 0.378 |
| 100 | 0.461 | 0.452 | 0.381 |
| 200 | 0.456 | 0.458 | 0.409 |
| 300 | 0.454 | 0.457 | 0.421 |
| 500 | 0.450 | 0.460 | 0.453 |
| 1,000 | 0.447 | 0.456 | 0.458 |

![Validation average precision against boosting stages for three learning rates.](/series/classification/figures/ch08-boosting-lr.png)
*Figure 1. A large learning rate learns fast and then overfits. A small one is slower and still improving at 1,000 trees.*

What the numbers say:

- **Large steps are fast, then risky.** At a learning rate of 0.5 the validation AP is 0.461 at 100 trees and 0.447 at 1,000, while the AP on the fitted rows climbs from 0.493 to 0.586: the model increasingly describes noise.
- **Small steps need more trees, and compute decides whether you get there.** A rate of 0.1 peaks at 500 trees (0.460). At 0.02 the score is still rising at 1,000 trees (0.458) and far behind at 300 (0.421). Smaller rates often end similar or slightly better, but only if you can afford the trees.
- **The learning rate and the number of trees interact.** Halving the rate roughly doubles the trees you need to reach the same place. That does not make a joint search invalid, but it makes it wasteful, which is why the usual routine is to fix a small learning rate and choose the tree count by early stopping.
- **The best scores of the three runs are within 0.003 of each other**, so on this data the choice of learning rate mostly changes how many trees you need and how carefully you must stop.

## Early stopping

Instead of guessing a number of trees, hold out a slice of the training data, score it after every tree, and stop when it has not improved for a set number of rounds. scikit-learn's `HistGradientBoostingClassifier` has this built in, along with native handling of categorical columns and fast histogram-based split search.

**Implementation.**

```python
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss

cats = {c: sorted(X.iloc[fit][c].unique()) for c in cat}
def as_category(rows):
    Z = X.iloc[rows].copy()
    for c in cat:
        Z[c] = pd.Categorical(Z[c], categories=cats[c])
    return Z

Zf, Zv = as_category(fit), as_category(val)
for lr in (0.3, 0.1, 0.03):
    h = HistGradientBoostingClassifier(learning_rate=lr, max_iter=2000, early_stopping=True, validation_fraction=0.15,
                                       n_iter_no_change=30, categorical_features="from_dtype", random_state=42).fit(Zf, yf)
    q = h.predict_proba(Zv)[:, 1]
    print(f"learning rate {lr}: stopped at {h.n_iter_:>3} trees, validation AP {average_precision_score(yv, q):.3f}, log loss {log_loss(yv, q):.3f}")
```

**Result.**

```output
learning rate 0.3: stopped at  36 trees, validation AP 0.440, log loss 0.283
learning rate 0.1: stopped at  61 trees, validation AP 0.454, log loss 0.275
learning rate 0.03: stopped at 123 trees, validation AP 0.454, log loss 0.274
```

**What it means.** We allowed 2,000 trees and the models stopped between 36 and about 120. The two smaller rates end at almost the same validation AP and log loss; the largest is worse on both. The validation slice must look like the future you care about: a random 15% slice suits a random split, but if the question is about *later* records (part 16), validate on the most recent training data, because a random slice from the past keeps rewarding extra trees long after the model stopped generalising forward in time.

## The named libraries

Everything above is the core. XGBoost, LightGBM and CatBoost are engineering variants of it, and many differences are configurable, so read the table as defaults for the versions used here (XGBoost 3.4.1, LightGBM 4.7.0, CatBoost 1.2.10, scikit-learn 1.8.0).

| | Tree growth by default | Categorical columns | Known for |
|---|---|---|---|
| XGBoost | Level by level, depth-limited | Native support available (`enable_categorical`) | Regularised objective, second-order gradients, a very large ecosystem |
| LightGBM | Leaf by leaf (best leaf first), controlled by `num_leaves` | Native support | Speed on large data |
| CatBoost | Symmetric ("oblivious") trees | Native, with ordered target statistics | Strong defaults for categorical-heavy data |
| scikit-learn `HistGradientBoosting` | Leaf by leaf | Native support | No extra dependency, early stopping built in |

Whether any of these differences matters for *this* problem is an empirical question, answered under one protocol in part 12.

## Boosting and bagging side by side

| | Random forest (part 7) | Gradient boosting |
|---|---|---|
| Trees | Deep, independent, averaged | Shallow, sequential, summed |
| Mainly reduces | Variance | Bias, and variance too at small learning rates |
| Sensitivity to settings | Usually low | Moderate: learning rate, tree size, regularisation, stopping |
| More trees | Rarely hurts, stabilises | Can overfit, so stop on validation data |
| Probabilities | Depend on leaf size | Reasonable when trained on log loss, still worth checking (part 11) |

## Analysis and conclusion: what we learned

- **The loop is short.** Residual, small tree, small step, repeat. Everything else in the libraries is speed, regularisation and convenience.
- **Nothing in boosting says stop.** A large learning rate overfits within a hundred trees on this data. Choose the tree count on validation data.
- **Small steps are not automatically better.** They are smoother and often at least as good, but under a finite budget a small learning rate may simply not have run long enough.
- **Early stopping must validate the right thing.** Use random validation rows for a random split and the latest rows for a time-ordered one.

*Further reading.* Friedman (2001), [Greedy function approximation: a gradient boosting machine](https://doi.org/10.1214/aos/1013203451); Chen and Guestrin (2016), [XGBoost](https://doi.org/10.1145/2939672.2939785); Ke et al. (2017), LightGBM, NeurIPS; Prokhorenkova et al. (2018), [CatBoost](https://arxiv.org/abs/1706.09516).

[Part 9](/series/classification/09-other-classification-families/) goes through the remaining families, k-nearest neighbours, support vector machines and neural networks, which need very different treatment of the same data.
