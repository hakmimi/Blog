---
title: "The Baseline You Must Beat: Logistic Regression and Naive Bayes"
description: "Build a proper preprocessing pipeline, tune regularisation, read the coefficients as odds ratios, and find out why Naive Bayes ranks fine but lies about probabilities."
series: "classification"
order: 5
date: 2026-09-30
updated: 2026-10-02
keywords: ["logistic regression", "naive bayes", "baseline", "scikit-learn pipeline", "odds ratio", "regularisation"]
readingTime: "16 min read"
figure: "ch05-odds-ratios.png"
---

If there's one habit that separates people who ship working models from people who ship impressive-looking ones, it's this: **build the dumbest serious model first, and make everything else beat it.** On tabular data that model is logistic regression. It trains in a second, it has one important knob, and you can read what it learned.

It also has a bad habit of being hard to beat. Keep that in mind when we reach the leaderboard.

## Goals: what are we trying to achieve?

Before any clever model, we need a bar to beat. Our goal is to build the dumbest serious model, make it leak-proof, and learn what it tells us.

By the end you will be able to:

- **Build a pipeline** where preprocessing is fitted on training rows only.
- **Tune the one knob**, regularisation, and recognise a plateau.
- **Read odds ratios**, and know when a coefficient should not be trusted.
- **Explain why Naive Bayes ranks decently but lies about probabilities.**

## The work plan: how do we do it?

Three steps for logistic regression, then a contrast:

1. **A pipeline that can't leak**: one-hot encoding and scaling inside the model object.
2. **The one knob**: sweep `C` with 3-fold cross-validation on the training part only.
3. **Read the model**: odds ratios, then a correlation check on the economic columns.
4. **Naive Bayes**: the same data, a completely different route, graded on the same metrics.

## Implementation

### Step 1: a pipeline that can't leak

Every fitted number — category vocabulary, column means, column standard deviations — must come from *training rows only*. The way to guarantee it is to put preprocessing *inside* the model object, so `fit` learns it and `predict` merely applies it.

```python
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()

prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), cat)],
                         remainder=StandardScaler())
logit = make_pipeline(prep, LogisticRegression(C=0.1, max_iter=2000))
logit.fit(Xtr, ytr)
p = logit.predict_proba(Xte)[:, 1]
print(f"logistic  AP={average_precision_score(yte, p):.3f}  AUC={roc_auc_score(yte, p):.3f}  "
      f"logloss={log_loss(yte, p):.3f}  brier={brier_score_loss(yte, p):.3f}")
```

```output
logistic  AP=0.464  AUC=0.801  logloss=0.272  brier=0.077
```

What each piece does:

- **`OneHotEncoder`** turns each categorical column into 0/1 indicator columns — `job_retired`, `job_student`, … A linear model can't use the string "retired", only a number. `handle_unknown="ignore"` means a category never seen in training (a new job title next year) becomes all zeros instead of crashing.
- **`StandardScaler`** (applied to the numeric `remainder`) rescales each numeric column to mean 0, SD 1. Regularisation (below) penalises coefficient size, which is only fair if features share a scale. It also means coefficients read as "effect of +1 standard deviation".
- **`make_pipeline`** glues them so `cross_val_score` and `RandomizedSearchCV` refit the *whole chain* inside each fold. If you scale first and split after, every validation fold has leaked its mean into training.

<div class="callout gotcha">

**Gotcha — scaling before splitting.** `StandardScaler().fit_transform(X)` followed by `train_test_split` is the most common leakage bug in published notebooks. The effect on a linear model is small; on k-NN or neural nets it can be large. Pipelines make the mistake impossible.

</div>

### Step 2: the one knob — regularisation

Logistic regression minimises log loss plus a penalty, `λ · Σ wⱼ²`, that discourages large weights. In scikit-learn it's parameterised backwards: **`C` is the inverse of regularisation strength** — small C = heavy penalty = small, stable coefficients. Sweep it with cross-validation on the training part only:

```python
for C in (0.001, 0.01, 0.1, 1, 10):
    m = make_pipeline(prep, LogisticRegression(C=C, max_iter=2000))
    s = cross_val_score(m, Xtr, ytr, cv=3, scoring="average_precision")
    print(f"C={C:<6} CV average precision = {s.mean():.3f} +- {s.std():.3f}")
```

```output
C=0.001  CV average precision = 0.428 +- 0.015
C=0.01   CV average precision = 0.443 +- 0.015
C=0.1    CV average precision = 0.448 +- 0.015
C=1      CV average precision = 0.450 +- 0.014
C=10     CV average precision = 0.450 +- 0.014
```

Two things to notice. Heavy regularisation hurts (0.428 at C=0.001), and once C is about 0.1 the curve is flat: differences of 0.002 are an order of magnitude smaller than the ±0.015 fold-to-fold noise. **This is what a well-posed tuning problem looks like — a plateau, not a peak.** Any C from 0.1 to 10 is a fine answer; we use 0.1 because when two settings tie, the more regularised one is safer.

### Step 3: read the model

The killer feature of logistic regression is that the coefficient *w* for a feature tells you how the **log-odds** of subscribing change when that feature increases by one unit (one SD, for scaled columns). Exponentiate and you get an **odds ratio**: 2.0 means the odds double, 0.5 means they halve.

```python
names = logit[0].get_feature_names_out()
coef = pd.Series(logit[-1].coef_[0], index=names).sort_values()
odds = np.exp(coef).round(2)
print("lowest odds ratios :\n", odds.head(6).to_string())
print("highest odds ratios:\n", odds.tail(6).to_string())
```

```output
lowest odds ratios :
 remainder__emp.var.rate    0.26
cat__month_may             0.55
cat__month_nov             0.64
cat__month_jun             0.71
cat__poutcome_failure      0.71
cat__contact_telephone     0.72
highest odds ratios:
 cat__poutcome_success        1.26
cat__contact_cellular        1.32
cat__job_retired             1.34
cat__month_dec               1.37
remainder__cons.price.idx    2.02
cat__month_mar               2.81
```

A story jumps out: May calls are bad, cellular beats landline, retirees and past-successes are good. All of it matches the raw rates from [part 1](/series/classification/01-classification-is-a-decision/). But look at the two *numeric* entries, because they should make you suspicious:

- `emp.var.rate` has odds ratio **0.26**: one SD higher employment-variation rate cuts the odds by 74%.
- `cons.price.idx` has odds ratio **2.02**: one SD higher consumer-price index *doubles* the odds.

Do those two economic indicators really push in opposite directions? Check how related the macro columns are:

```python
print(df[["emp.var.rate", "cons.price.idx", "euribor3m", "nr.employed"]].corr().round(2))
```

```output
                emp.var.rate  cons.price.idx  euribor3m  nr.employed
emp.var.rate            1.00            0.78       0.97         0.91
cons.price.idx          0.78            1.00       0.69         0.52
euribor3m               0.97            0.69       1.00         0.95
nr.employed             0.91            0.52       0.95         1.00
```

`emp.var.rate` and `euribor3m` correlate at **0.97**. They are nearly the same variable. When features are this collinear, a linear model splits credit between them arbitrarily: one gets a large negative weight and another a large positive one to compensate, and the *individual* coefficients stop meaning anything even though the model's *predictions* are fine.

<div class="callout gotcha">

**Gotcha — coefficients are not causal effects.** An odds ratio says "holding every other column fixed". With correlated macro indicators, "holding the others fixed" describes economies that never existed. Interpret groups of correlated features together, never one at a time, and never say "raising X by one unit causes…".

</div>

That is a useful finding in itself: a model that looks transparent can still mislead. Transparency is necessary, not sufficient.

### Naive Bayes: the confident guesser

Naive Bayes takes a completely different route. It estimates, for each class, the distribution of each feature separately (here a Gaussian per column), then multiplies the per-feature likelihoods *as if features were independent given the class* — that's the "naive" part. No optimisation loop; fitting is just computing means and variances.

```python
dense = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                          remainder=StandardScaler())
nb = make_pipeline(dense, GaussianNB(var_smoothing=1e-3)).fit(Xtr, ytr)
q = nb.predict_proba(Xte)[:, 1]
print(f"naive bayes AP={average_precision_score(yte, q):.3f}  AUC={roc_auc_score(yte, q):.3f}  "
      f"logloss={log_loss(yte, np.clip(q, 1e-6, 1 - 1e-6)):.3f}  brier={brier_score_loss(yte, q):.3f}")
print("mean predicted probability: logistic", p.mean().round(3), " naive bayes", q.mean().round(3), " truth", yte.mean().round(3))
print("share of NB scores above 0.9 / below 0.1:", (q > 0.9).mean().round(3), (q < 0.1).mean().round(3))
```

```output
naive bayes AP=0.369  AUC=0.776  logloss=1.310  brier=0.133
mean predicted probability: logistic 0.112  naive bayes 0.141  truth 0.113
share of NB scores above 0.9 / below 0.1: 0.12 0.829
```

Compare with logistic regression:

| | AP | AUC | Log loss | Brier |
|---|---|---|---|---|
| Logistic regression | **0.464** | **0.801** | **0.272** | **0.077** |
| Gaussian Naive Bayes | 0.369 | 0.776 | 1.310 | 0.133 |

Naive Bayes is worse at ranking, but the real damage is in the probabilities: log loss is nearly **5× worse**. The last line shows why. Some 12% of NB's predictions are above 0.9 and 83% below 0.1 — it's behaving like a model that's nearly certain about everyone, when the truth is an 11% base rate and a messy signal. The independence assumption counts the same evidence repeatedly (`emp.var.rate`, `euribor3m` and `nr.employed` each "vote" that the economy is weak, and Naive Bayes multiplies those three votes as if they were independent witnesses), so its confidence snowballs.

That's a classic pattern: **a model can rank decently and still produce probabilities you must not use.** If the next stage is "estimate expected profit", NB's output is unusable without calibration ([part 11](/series/classification/11-probabilities-calibration-thresholds-costs/)).

## What did we get? Results

Same split, same 8,238 held-out customers:

| | AP | AUC | Log loss | Brier |
|---|---|---|---|---|
| Logistic regression | **0.464** | **0.801** | **0.272** | **0.077** |
| Gaussian Naive Bayes | 0.369 | 0.776 | 1.310 | 0.133 |

- **Tuning `C`:** cross-validated AP goes 0.428, 0.443, 0.448, 0.450, 0.450 for C = 0.001 to 10. The plateau starts around C = 0.1, and the fold-to-fold noise is ±0.015.
- **Collinearity:** `emp.var.rate` and `euribor3m` correlate at 0.97.
- **Naive Bayes confidence:** 12% of its scores are above 0.9 and 83% below 0.1, against a true base rate of 11.3%.

![Bar chart of the eight lowest and eight highest odds ratios from the logistic regression.](/series/classification/figures/ch05-odds-ratios.png)
*Figure 1. Odds ratios on a log scale. Left of the line lowers the odds of subscribing; right raises them.*

## Analysis and conclusion: what did we learn?

- **Logistic regression is hard to beat.** AP 0.464 and AUC 0.80 are our bar for the rest of the series.
- **A plateau is a good tuning result.** Differences of 0.002 are far smaller than the ±0.015 noise, so any `C` from 0.1 to 10 is fine. We pick the more regularised one.
- **Coefficients mislead when features are collinear.** The two economic indicators with opposite odds ratios (0.26 and 2.02) are nearly the same variable. This is correlation, not a causal effect.
- **Naive Bayes counts the same evidence several times**, so its probabilities are over-confident (log loss about 5 times worse). We fix that kind of problem in [Part 11](/series/classification/11-probabilities-calibration-thresholds-costs/).

### What to take from this chapter

1. **Always build the pipeline so preprocessing is fitted per training fold.**
2. Logistic regression gives you a strong score, calibrated probabilities (log loss 0.272) and a readable model — in a few lines and a second of compute.
3. Tuning `C` showed a plateau. When differences are smaller than the fold noise, pick the simpler model.
4. Coefficients lie when features are collinear.
5. Naive Bayes is a good reminder that AUC and probability quality are separate: it's a useful *feature-selection sanity check* and a fast baseline, rarely a final model.

Logistic regression's AP of 0.464 and AUC of 0.80 are now our bar. [Part 6](/series/classification/06-decision-trees/) asks whether a model that can capture interactions and non-linear effects does better — and how easily it cheats.

### So what did we do?

We built a leak-proof logistic regression, found that its tuning curve is a plateau, and learned to read its coefficients with care. Naive Bayes showed that a model can rank decently and still produce probabilities you must not use. Logistic regression's AP of 0.464 is now the bar to beat.

### In the next part
