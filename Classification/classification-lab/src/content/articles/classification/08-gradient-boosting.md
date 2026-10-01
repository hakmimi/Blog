---
title: "Gradient Boosting, Built From Scratch"
description: "Write gradient boosting in 15 lines of Python, see what the learning rate really does to the learning curve, then let early stopping pick the number of trees for you."
series: "classification"
order: 8
date: 2026-09-30
updated: 2026-10-01
keywords: ["gradient boosting", "learning rate", "early stopping", "histgradientboosting", "xgboost", "lightgbm", "catboost"]
readingTime: "17 min read"
figure: "ch08-boosting-lr.png"
---

Random forests average many independent, fully-grown trees. **Gradient boosting does the opposite: it builds many small, weak trees in sequence, and each new tree is trained to fix what the ensemble so far is still getting wrong.**

XGBoost, LightGBM and CatBoost are all industrial-strength versions of this one idea, and they dominate tabular-data competitions. Before we race them in part 12, let's build the core loop ourselves. It's shorter than you'd expect.

## The algorithm in plain words

1. Start with a constant prediction: the log-odds of the base rate.
2. Compute each customer's **residual**: how wrong is the current prediction? For log loss, the residual is simply `y − p`.
3. Fit a small tree (depth 3) to predict those residuals.
4. Add that tree's output, **multiplied by a small learning rate**, to the running score.
5. Repeat.

Score = `F₀ + η·tree₁ + η·tree₂ + …`, and the probability is `sigmoid(score)`. "Gradient" comes from the fact that the residual is the negative gradient of the loss with respect to the current score — each tree is a step of gradient descent, *in function space*.

```python
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import average_precision_score, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()
prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                         remainder="passthrough")
A, B = prep.fit_transform(Xtr), prep.transform(Xte)
sigmoid = lambda z: 1 / (1 + np.exp(-z))

def boost(lr, n_stages=300, depth=3):
    base = np.log(ytr.mean() / (1 - ytr.mean()))             # stage 0: predict the base rate
    F_tr, F_te = np.full(len(A), base), np.full(len(B), base)
    history = []
    for m in range(1, n_stages + 1):
        residual = ytr - sigmoid(F_tr)                        # negative gradient of log loss
        tree = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=20).fit(A, residual)
        F_tr += lr * tree.predict(A)
        F_te += lr * tree.predict(B)
        if m in (1, 10, 25, 50, 100, 200, 300):
            q = sigmoid(F_te)
            history.append((m, average_precision_score(yte, q), log_loss(yte, q),
                            average_precision_score(ytr, sigmoid(F_tr))))
    return history
```

That is gradient boosting. The loop body is five lines. (Real libraries also do a second-order Newton step to set the leaf values and add regularisation, but the skeleton is this.)

## The learning rate, made visible

Everything interesting is in `lr`. Let's train the same model with three learning rates and print the score at several stages:

```python
for lr in (0.5, 0.1, 0.02):
    print(f"\nlearning rate {lr}")
    print("  stages   test AP  test logloss  train AP")
    for m, ap, ll, tap in boost(lr):
        print(f"  {m:>6}   {ap:.3f}    {ll:.3f}        {tap:.3f}")
```

```output
learning rate 0.5
  stages   test AP  test logloss  train AP
       1   0.388    0.342        0.374
      10   0.426    0.293        0.409
      25   0.464    0.276        0.451
      50   0.479    0.270        0.473
     100   0.484    0.266        0.491
     200   0.484    0.265        0.505
     300   0.486    0.265        0.517

learning rate 0.1
  stages   test AP  test logloss  train AP
       1   0.388    0.350        0.374
      10   0.388    0.333        0.374
      25   0.405    0.313        0.392
      50   0.434    0.294        0.418
     100   0.461    0.280        0.446
     200   0.477    0.272        0.470
     300   0.478    0.269        0.477

learning rate 0.02
  stages   test AP  test logloss  train AP
       1   0.388    0.352        0.374
      10   0.388    0.348        0.374
      25   0.393    0.342        0.378
      50   0.394    0.333        0.381
     100   0.395    0.319        0.383
     200   0.410    0.300        0.395
     300   0.451    0.289        0.435
```

![Test average precision versus number of boosting stages for three learning rates.](/series/classification/figures/ch08-boosting-lr.png)
*Figure 1. Smaller learning rates take many more trees to reach the same place, but the destination is at least as good.*

What to see in these numbers:

- **A very first tree already gets 0.388.** A depth-3 tree is weak, but not useless (recall part 6: shallow trees reach ~0.37).
- **Learning rate is a speed dial.** At `lr=0.5` the model reaches 0.479 in 50 stages. At `lr=0.1` it needs 200 stages for 0.477. At `lr=0.02` it hasn't finished after 300: it's at 0.451 and still climbing.
- **Test log loss tracks AP.** They improve together — boosting with log loss is directly optimising probability quality, and ranking improves as a by-product.
- **Watch the train/test gap.** At `lr=0.5`, train AP reaches 0.517 after 300 stages while test AP is 0.486: it's starting to fit noise, and the test curve has flattened. Nothing in the algorithm says "stop now". *You* have to.

The standard rule of thumb: **use a small learning rate and many trees, and let early stopping choose the number.** Small steps rarely overshoot, so the final model is smoother. The price is compute.

<div class="callout gotcha">

**Gotcha — `learning_rate` and `n_estimators` are not independent.** Halving the learning rate roughly doubles the number of trees you need. If you tune them together you waste budget. Fix a small learning rate (0.03–0.1) and tune `n_estimators` via early stopping, or fix `n_estimators` and tune the learning rate — never a grid over both.

</div>

## Early stopping: let validation data choose the number of trees

Instead of guessing 300, hold out a slice of the training data, evaluate after each tree, and stop when the validation loss hasn't improved for `n_iter_no_change` rounds. scikit-learn's `HistGradientBoostingClassifier` has this built in, plus native categorical-feature support and multi-threaded histogram-based split search (the same trick LightGBM popularised):

```python
from sklearn.ensemble import HistGradientBoostingClassifier

Xc = X.copy()
for c in cat:
    Xc[c] = Xc[c].astype("category")                          # tell the model which columns are categorical
Xctr, Xcte = Xc.loc[Xtr.index], Xc.loc[Xte.index]

for lr in (0.3, 0.1, 0.03):
    h = HistGradientBoostingClassifier(learning_rate=lr, max_iter=2000, early_stopping=True,
                                       validation_fraction=0.15, n_iter_no_change=30,
                                       categorical_features="from_dtype", random_state=0).fit(Xctr, ytr)
    q = h.predict_proba(Xcte)[:, 1]
    print(f"HistGB lr={lr}: stopped at {h.n_iter_} trees  test AP={average_precision_score(yte, q):.3f}  logloss={log_loss(yte, q):.3f}")
```

```output
HistGB lr=0.3: stopped at 40 trees  test AP=0.483  logloss=0.270
HistGB lr=0.1: stopped at 63 trees  test AP=0.496  logloss=0.263
HistGB lr=0.03: stopped at 138 trees  test AP=0.496  logloss=0.263
```

Several things happened at once:

1. **Early stopping replaced our guess.** We allowed 2,000 trees; the model stopped at 40, 63 and 138.
2. **Smaller learning rates found a slightly better place.** lr = 0.3 ended at AP 0.483; lr = 0.1 and 0.03 both hit 0.496. After a point, making the step smaller yields no further benefit — the extra trees are pure cost.
3. **It beat our from-scratch version (0.486).** Native categorical handling (no one-hot), leaf-value regularisation and histogram splits each contribute a little. This single-digit-second model is already ahead of everything in parts 5–7: logistic regression 0.464, tuned tree ~0.43, forest 0.491.

<div class="callout tip">

**Early stopping and time.** The early-stopping slice here is a *random* 15% of the training rows, which is fine for this series' random split. If your deployment predicts the *future* (part 16), validate on the most recent slice instead; a random slice from the past will tell you to keep training long after the model has stopped generalising forward in time.

</div>

## What the named libraries add

Everything above is the core. The three famous libraries differ on engineering choices:

| | Split search | Trees grow | Categorical handling | Known for |
|---|---|---|---|---|
| **XGBoost** | Histogram (`hist`) or exact | Level-wise (depth-limited) | Native (`enable_categorical`) in recent versions | Regularised objective, 2nd-order gradients, huge ecosystem |
| **LightGBM** | Histogram, gradient-based sampling | Leaf-wise (best leaf first) | Native, optimal partitioning of categories | Speed on large data; needs `num_leaves` care |
| **CatBoost** | Symmetric ("oblivious") trees | Level-wise, same split per level | Native, **ordered target statistics** | Strong defaults, best handling of high-cardinality categories |
| scikit-learn `HistGB` | Histogram | Leaf-wise | Native | No extra dependency, good defaults |

These are differences of engineering and inductive bias, not of idea. Whether they translate into better *test scores on this problem* is an empirical question — the subject of part 12, where all three race on identical data.

## Boosting vs bagging: which, when?

| | Random forest | Gradient boosting |
|---|---|---|
| Trees | Deep, independent, averaged | Shallow, sequential, summed |
| Reduces | Variance | Bias (and variance, with small lr) |
| Tuning sensitivity | Low | Medium (lr, depth/leaves, regularisation) |
| Overfits with more trees? | No | Yes — needs early stopping |
| Probabilities | Compressed toward centre | Good when trained on log loss |
| Best when | You want a strong, forgiving default | You want the last few points of accuracy and can validate properly |

On this dataset, both land around 0.49 average precision. The gap between them is tiny; the gap between them and a single tree (0.43) or Naive Bayes (0.37) is large. **Part of the craft of applied ML is knowing which gaps matter** — and in part 13 we'll measure whether 0.496 versus 0.491 is a real difference at all.

[Part 9](/series/classification/09-other-classification-families/) goes through the remaining families — k-nearest neighbours, SVMs and neural nets — that need very different treatment of the same data.
