---
title: "k-NN, SVMs and Neural Nets: The Other Families"
description: "Three very different ways to classify, run on the same customers: what each one assumes, what it costs, and the one-line preprocessing mistake that breaks distance-based models."
series: "classification"
order: 9
date: 2026-09-30
updated: 2026-10-01
keywords: ["knn", "svm", "neural networks", "mlp", "feature scaling", "platt scaling", "scikit-learn"]
readingTime: "16 min read"
figure: "ch09-svm-scaling.png"
---

So far we've covered linear models (part 5), trees (6), bagging (7) and boosting (8). Three more families show up in every "which classifier?" discussion, and on tabular data they each have a characteristic role:

- **k-nearest neighbours** — classify by looking at similar customers. No training at all.
- **Support vector machines** — draw the widest possible margin. Elegant maths, awkward scaling.
- **Neural networks** — stack non-linear layers. Flexible, hungry for tuning.

We'll run each on the same split and focus on the **practical question** for each: what do I have to do *to the data* or *to my expectations* before this model is usable?

```python
import time
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC, LinearSVC

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()
ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
scaled   = ColumnTransformer([("c", ohe, cat)], remainder=StandardScaler())
unscaled = ColumnTransformer([("c", ohe, cat)], remainder="passthrough")

def ap(m): return average_precision_score(yte, m.predict_proba(Xte)[:, 1])
```

## k-nearest neighbours: a model that is *only* a distance

k-NN predicts a customer's probability as the share of subscribers among the *k* most similar training customers. "Similar" means small Euclidean distance — which makes it the model most sensitive to how you encode the features.

```python
print("kNN, k=50")
for label, prep in (("unscaled", unscaled), ("scaled  ", scaled)):
    m = make_pipeline(prep, KNeighborsClassifier(50, n_jobs=-1)).fit(Xtr, ytr)
    print(f"  {label}  AP={ap(m):.3f}")
```

```output
kNN, k=50
  unscaled  AP=0.449
  scaled    AP=0.455
```

The textbook says "always scale for k-NN, or the largest column dominates". The surprise is that here the damage is small: 0.449 vs 0.455. Why? Because the column that dominates the unscaled distance — `nr.employed` (values ≈ 5,000) plus `pdays` (0 or 999) — *also happens to be the most informative* one, and it acts as a proxy for time. Unscaled k-NN is accidentally a "find customers from the same period" model.

<div class="callout gotcha">

**Gotcha — a benign result is not a safe practice.** On a different dataset the dominant column could be noise (customer ID, salary in cents). Scaling is what guarantees you aren't relying on luck. Put it inside the pipeline and forget about it.

</div>

The one parameter that really matters is `k`:

```python
for k in (5, 15, 50, 150, 400):
    m = make_pipeline(scaled, KNeighborsClassifier(k, n_jobs=-1)).fit(Xtr, ytr)
    print(f"  k={k:<4} AP={ap(m):.3f}")
```

```output
  k=5    AP=0.356
  k=15   AP=0.425
  k=50   AP=0.455
  k=150  AP=0.456
  k=400  AP=0.456
```

With `k=5` a probability can only be 0, 0.2, 0.4 … 1 — coarse, noisy, and only 0.356. For a rare-positive problem you need **large k** (50+) so each neighbourhood contains some positives. This is the same bias-variance dial as `min_samples_leaf` in part 6: small = flexible and noisy, large = smooth.

**k-NN's real problem is cost at prediction time.** There is no model to apply: every prediction scans (or indexes) the whole training set. Fine at 33k rows, painful at 33 million, and the model file *is* the dataset.

## SVMs: elegant, but not a probability model

A linear SVM finds the hyperplane that separates the classes with the widest margin; it cares only about the points near the boundary. On this data it ranks about as well as logistic regression. The catch is what it *outputs*:

```python
svm = make_pipeline(scaled, LinearSVC(C=0.1, dual=False)).fit(Xtr, ytr)
d = svm.decision_function(Xte)
print("Linear SVM raw scores: range", d.min().round(2), "to", d.max().round(2), " AP", round(average_precision_score(yte, d), 3))
```

```output
Linear SVM raw scores: range -1.19 to 0.76  AP 0.462
```

The raw scores are signed distances from the boundary. They rank well (AP 0.462) but they're not probabilities: there's no way to read "0.3" as 30%. If you need probabilities (and for expected-profit calculations you do), you **calibrate** — fit a tiny logistic regression on the scores, called Platt scaling. scikit-learn wraps it:

```python
cal = make_pipeline(scaled, CalibratedClassifierCV(LinearSVC(C=0.1, dual=False), cv=3)).fit(Xtr, ytr)
q = cal.predict_proba(Xte)[:, 1]
print(f"after Platt scaling: AP={average_precision_score(yte, q):.3f}  logloss={log_loss(yte, q):.3f}  brier={brier_score_loss(yte, q):.3f}")
```

```output
after Platt scaling: AP=0.462  logloss=0.275  brier=0.078
```

Ranking is untouched (calibration is a monotone transform) but log loss is now 0.275, essentially the same as logistic regression's 0.272 — unsurprising, since we've effectively added a logistic layer on top of a linear classifier.

**The kernel (RBF) SVM** can draw curved boundaries, and that is where it gets expensive. Its training cost grows roughly with the *square* of the number of rows:

```python
Atr = scaled.fit_transform(Xtr)
for n in (2000, 4000, 8000, 16000):
    t0 = time.perf_counter()
    SVC(C=1, gamma="scale").fit(Atr[:n], ytr[:n])
    print(f"  n={n:<6} {time.perf_counter() - t0:5.1f}s")
```

```output
  n=2000     0.2s
  n=4000     0.8s
  n=8000     5.7s
  n=16000    16.2s
```

![Fit time of an RBF SVM versus number of training rows, on a log-log scale, against a linear SVM.](/series/classification/figures/ch09-svm-scaling.png)
*Figure 1. Doubling the data multiplies RBF-SVM training time by 3–7×. The full 32,950-row training set would take a few minutes per fit, which is why the leaderboard uses the linear SVM only.*

Doubling the rows costs 3–7× in time. Extrapolating to the full 32,950-row training set means minutes *per fit*, and tuning needs dozens of fits. This is the well-known reason kernel SVMs faded for datasets beyond ~50k rows. **We therefore leave the RBF SVM out of the leaderboard and say so, rather than quietly training it on a subsample.**

## Neural networks: a flexible learner, a fussy one

A multilayer perceptron stacks layers of weighted sums and non-linearities, trained by gradient descent on log loss — so, unlike SVMs, it outputs probabilities directly. The scikit-learn version is small but real:

```python
for alpha in (1e-4, 1e-2, 1e-1):
    t0 = time.perf_counter()
    m = make_pipeline(scaled, MLPClassifier((64, 32), alpha=alpha, early_stopping=True,
                                            max_iter=200, random_state=0)).fit(Xtr, ytr)
    print(f"  alpha={alpha:<7} AP={ap(m):.3f}  epochs={m[-1].n_iter_}  fit={time.perf_counter() - t0:.1f}s")
```

```output
  alpha=0.0001  AP=0.477  epochs=15  fit=3.3s
  alpha=0.01    AP=0.476  epochs=15  fit=3.3s
  alpha=0.1     AP=0.476  epochs=34  fit=6.8s
```

A small 64×32 network reaches 0.477 — *better than logistic regression (0.464) and any single tree*, only about 0.015 below the best forests and boosters. Stopping after ~15 epochs is `early_stopping=True` at work: the network's validation score stops improving quickly because the dataset is small and the signal is mostly low-order.

The warning label for neural nets on tabular data: **they are competitive, not dominant.** With careful engineering (embeddings for categories, batch norm, long schedules) deep learning can match gradient boosting on some tabular datasets, but rarely beats it by margin, and it needs far more tuning and far more care with feature scaling and random seeds. For a fast baseline, a small MLP is fine. As a final answer, it needs a reason.

## Summary: how each family behaves on this data

| Family | What it needs | Output | Cost profile | Watch out for |
|---|---|---|---|---|
| **k-NN** | Scaled features, large *k* | Fraction of neighbours | Free to train; slow to predict; model = dataset | Distance dominated by big-range columns |
| **Linear SVM** | Scaled features | Raw margin (needs calibration) | Fast | Not a probability model |
| **RBF SVM** | Scaled features, subsampling if large | Raw margin | Quadratic in rows | Doesn't scale past ~50k rows |
| **MLP** | Scaled features, early stopping | Probabilities | Seconds; sensitive to seed | Needs tuning; random-seed variance |

None of these is obviously *wrong* for this data, and all of them land between 0.455 and 0.477. The interesting question — *by how much does a difference of that size matter, and is it stable?* — is answered in part 13.

First, though, we need a fair way to tune all of them. [Part 10](/series/classification/10-hyperparameter-search/) sets the budget.
