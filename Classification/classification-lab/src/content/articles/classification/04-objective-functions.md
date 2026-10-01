---
title: "What the Model Is Actually Minimising"
description: "Log loss, Brier score and class weights, written by hand. We train logistic regression from scratch in NumPy and watch three objectives produce the same ranking but very different behaviour."
series: "classification"
order: 4
date: 2026-09-30
updated: 2026-10-01
keywords: ["loss functions", "log loss", "brier score", "gradient descent", "class weights", "numpy"]
readingTime: "15 min read"
figure: "loss-and-impurity.png"
---

Every classifier in this series is an optimiser in disguise. `fit()` means: *find the parameters that make a number as small as possible.* That number is the **loss**, and choosing it is the most under-appreciated decision in a classification project. It determines what the model cares about, what its outputs mean, and how it behaves on rare classes.

This part is deliberately hands-on. We'll compute losses by hand on four customers, then write logistic regression from scratch in about fifteen lines of NumPy and swap the loss to see what changes.

## Losses on four customers

A classifier that outputs probabilities says, for each customer, "I think there's a *p* chance this person subscribes". A loss turns each (prediction, truth) pair into a penalty.

```python
import numpy as np

y_true = np.array([1, 1, 0, 0])
p      = np.array([0.9, 0.2, 0.1, 0.6])       # model's predicted P(subscribe)

log_loss_each = -(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))
brier_each    = (p - y_true) ** 2
print("log loss per row:", log_loss_each.round(3), "-> mean", log_loss_each.mean().round(3))
print("Brier per row   :", brier_each.round(3),    "-> mean", brier_each.mean().round(3))
```

```output
log loss per row: [0.105 1.609 0.105 0.916] -> mean 0.684
Brier per row   : [0.01 0.64 0.01 0.36] -> mean 0.255
```

Row 2 is the interesting one: the customer *did* subscribe and we said 20%. **Log loss** charges 1.609 — the negative log of the probability we assigned to what actually happened. **Brier** (squared error on the probability) charges 0.64. Both agree on the ordering of mistakes, but they disagree on how much worse confident mistakes are:

```python
for wrong_p in (0.6, 0.9, 0.99):
    print(f"true=0, predicted {wrong_p}: log loss {-np.log(1 - wrong_p):.2f}   Brier {wrong_p ** 2:.2f}")
```

```output
true=0, predicted 0.6: log loss 0.92   Brier 0.36
true=0, predicted 0.9: log loss 2.30   Brier 0.81
true=0, predicted 0.99: log loss 4.61   Brier 0.98
```

![Left: loss as a function of predicted probability for log loss and Brier. Right: Gini and entropy, the impurity measures trees use in part 6.](/series/classification/figures/loss-and-impurity.png)
*Figure 1. Log loss grows without bound as a confident prediction turns out wrong; Brier saturates at 1. Right panel: trees use the same idea with "impurity" instead (part 6).*

Log loss is brutal about over-confidence: saying 99% and being wrong costs 4.6, five times what Brier charges. That's a feature when you want honest probabilities and a hazard when a few mislabelled rows are in your data.

<div class="callout">

**Why log loss is the default.** It's the negative log-likelihood of a Bernoulli model, so minimising it is maximum-likelihood estimation. It's smooth and convex for linear models (one global minimum), and it's a *proper scoring rule*: it's minimised in expectation only by reporting the true probability. Brier is also proper; hinge loss (SVMs) is not — it never outputs probabilities at all.

</div>

## Logistic regression in fifteen lines

Logistic regression says: probability = sigmoid(w · x). Training means finding *w* by gradient descent. The gradient of mean log loss has a famously tidy form: `Xᵀ(q − y) / n` where `q` is the current predictions. Let's build the design matrix from the bank data and do it.

```python
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

cat = X.select_dtypes("object").columns
prep = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                         remainder=StandardScaler())
A = np.c_[np.ones(len(Xtr)), prep.fit_transform(Xtr)]        # design matrix with intercept
B = np.c_[np.ones(len(Xte)), prep.transform(Xte)]
sigmoid = lambda z: 1 / (1 + np.exp(-np.clip(z, -30, 30)))
```

Now the training loop, with a switch for the loss. Each branch is the derivative of its loss with respect to the weights:

```python
def fit(loss, steps=1500, lr=0.5):
    w = np.zeros(A.shape[1])
    pos_weight = (ytr == 0).sum() / (ytr == 1).sum()          # ~7.9
    for _ in range(steps):
        q = sigmoid(A @ w)
        if loss == "log":                                     # d/dw of mean log loss
            grad = A.T @ (q - ytr) / len(ytr)
        elif loss == "weighted log":                          # positives count ~8x
            sw = np.where(ytr == 1, pos_weight, 1.0)
            grad = A.T @ ((q - ytr) * sw) / sw.sum()
        elif loss == "brier":                                 # d/dw of mean (q - y)^2
            grad = A.T @ (2 * (q - ytr) * q * (1 - q)) / len(ytr)
        w -= lr * grad
    return w
```

Three objectives: plain log loss, log loss where each positive row counts about 8× (the standard "fix" for imbalance, `class_weight="balanced"` in scikit-learn), and Brier. Same features, same optimiser, same number of steps. What changes?

```python
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

print(f"{'objective':<14}{'AP':>7}{'AUC':>7}{'logloss':>9}{'mean p':>8}{'calls@0.5':>11}")
for loss in ("log", "weighted log", "brier"):
    q = sigmoid(B @ fit(loss))
    print(f"{loss:<14}{average_precision_score(yte, q):7.3f}{roc_auc_score(yte, q):7.3f}"
          f"{log_loss(yte, q):9.3f}{q.mean():8.3f}{(q >= 0.5).sum():11d}")
```

```output
objective          AP    AUC  logloss  mean p  calls@0.5
log             0.464  0.800    0.272   0.112        293
weighted log    0.460  0.801    0.515   0.391       1662
brier           0.466  0.797    0.273   0.112        290
```

Read the table carefully, because it contains the central lesson of this chapter:

- **Ranking barely changes.** AP is 0.464 / 0.460 / 0.466 and AUC is 0.80 for all three. A linear model with these features can only rank customers one way, and all three objectives find nearly the same direction.
- **Probabilities change dramatically.** The class-weighted model's average predicted probability is **0.391**, but only 11.3% of customers subscribe. Its log loss doubles (0.272 → 0.515). It isn't a worse ranker; it is a *miscalibrated* one, because we told it positives were 8× as important and it believed us.
- **Decisions change dramatically.** At the default threshold 0.5 the weighted model flags 1,662 customers, versus 293 for plain log loss. We didn't improve the model; we moved the threshold. Reweighting is a blunt way of doing what a threshold does cleanly.
- **Brier ≈ log loss** here. On well-behaved data with a linear model, the two proper scoring rules agree.

<div class="callout gotcha">

**Gotcha — "fixing" imbalance with class weights.** `class_weight="balanced"` is often the first thing people reach for. It can be useful (some algorithms rank better with it), but it destroys probability calibration and is equivalent, for a linear model, to shifting the threshold and intercept. If you need *probabilities* — for expected profit, for example — train with the natural weights and choose the threshold later (part 11).

</div>

## Checking our maths against scikit-learn

Hand-written gradient descent is only trustworthy if it agrees with the library. Quick check (same data, `penalty=None` so there's no regularisation):

```python
from sklearn.linear_model import LogisticRegression

ref = LogisticRegression(penalty=None, max_iter=5000).fit(A[:, 1:], ytr)
q_ref = ref.predict_proba(B[:, 1:])[:, 1]
q_mine = sigmoid(B @ fit("log"))
print("max |difference| in predicted probability:", np.abs(q_ref - q_mine).max().round(3))
print("correlation of the two score vectors     :", np.corrcoef(q_ref, q_mine)[0, 1].round(4))
```

```output
max |difference| in predicted probability: 0.201
correlation of the two score vectors     : 0.9929
```

The rankings agree almost perfectly (correlation 0.993). The worst single-customer gap of 0.20 is real, though, and it's instructive: the one-hot columns are collinear (each categorical's levels sum to one), so the unregularised optimum is a long, flat valley. scikit-learn's solver walks much further along it than our 1,500 fixed steps do, and rare category combinations end up with different extremes. This is precisely why real logistic regression adds an L2 penalty — it makes the valley bowl-shaped. That's the point of writing it by hand once: `fit()` is not magic, and its defaults (regularisation, convergence) matter.

## Not every model uses these losses

| Model family | What `fit()` minimises | Output |
|---|---|---|
| Logistic regression | Log loss (+ L2 penalty) | Probabilities |
| Linear SVM | Hinge loss: penalises only points inside the margin | A score; probabilities need calibration |
| Decision trees | Gini / entropy *impurity* at each split (greedy, not global) | Class proportions in a leaf |
| Random forests | Same impurity, then average many trees | Averaged proportions |
| Gradient boosting | Log loss, via its gradient and curvature (2nd-order in XGBoost/LightGBM) | Probabilities |
| Naive Bayes | Not a loss: counts and a Gaussian per feature | Probabilities, often over-confident |
| k-NN | None: memorises | Fraction of neighbours |

Two takeaways for the leaderboard. **(1)** Models that optimise log loss (logistic regression, boosting) tend to produce better-calibrated probabilities out of the box than models that don't (Naive Bayes, SVM, k-NN). **(2)** Ranking quality and calibration are different skills; a model can be great at one and mediocre at the other. We'll measure both, separately.

[Part 5](/series/classification/05-logistic-regression-naive-bayes/) puts the real scikit-learn versions to work and learns to read what a linear model has learned.
