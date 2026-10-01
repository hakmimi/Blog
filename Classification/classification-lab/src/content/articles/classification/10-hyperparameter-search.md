---
title: "Hyperparameter Search Without Fooling Yourself"
description: "A 1,800-combination search space, 40 random candidates, and a bootstrap-style experiment that shows what a bigger tuning budget actually buys, and how much of it is optimism."
series: "classification"
order: 10
date: 2026-09-30
updated: 2026-10-01
keywords: ["hyperparameter tuning", "random search", "cross-validation", "overfitting", "scikit-learn", "histgradientboosting"]
readingTime: "14 min read"
figure: "ch10-budget.png"
---

Every model so far has had knobs: `C`, `max_depth`, `min_samples_leaf`, `learning_rate`. Tuning them is where projects quietly burn days and where comparisons quietly become unfair. If model A got 200 tuning candidates and model B got 5, the winner tells you about budgets, not algorithms.

This chapter does two things. It shows how to search sensibly, and, more importantly, it **measures what a tuning budget is worth**, so that the leaderboard in part 12 can use a small, equal one without apology.

## The setup

We'll tune scikit-learn's `HistGradientBoostingClassifier` (it has plenty of knobs and trains in seconds). The search space is deliberately large:

```python
import time
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import ParameterSampler, StratifiedKFold, cross_val_score, train_test_split

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
for c in X.select_dtypes("object"):
    X[c] = X[c].astype("category")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

base = HistGradientBoostingClassifier(categorical_features="from_dtype", early_stopping=True, random_state=0)
space = {
    "learning_rate":     [0.02, 0.03, 0.05, 0.08, 0.12, 0.2],
    "max_leaf_nodes":    [4, 8, 15, 31, 63],
    "min_samples_leaf":  [10, 20, 50, 100, 200],
    "l2_regularization": [0, 0.1, 1, 10],
    "max_features":      [0.3, 0.6, 1.0],
}
print("search space size:", np.prod([len(v) for v in space.values()]), "combinations")
```

```output
search space size: 1800 combinations
```

1,800 combinations × 3 folds is 5,400 model fits. Nobody should run that grid. Here's the first reason **random search beats grid search**: with five parameters and, say, 3 values each, a grid spends 243 runs but only tries 3 distinct values of each parameter. Random sampling spends the same 243 runs on 243 *different* values of each. If only two of the five parameters matter (usually the case), random search explores those two much more densely.

## Step zero: always score the defaults

```python
cv = StratifiedKFold(3, shuffle=True, random_state=0)
d = base.fit(Xtr, ytr)
print(f"defaults: CV AP={cross_val_score(base, Xtr, ytr, cv=cv, scoring='average_precision').mean():.3f}"
      f"  test AP={average_precision_score(yte, d.predict_proba(Xte)[:, 1]):.3f}")
```

```output
defaults: CV AP=0.458  test AP=0.492
```

Remember this number: **0.492**. Any tuning has to beat it, and if the gain is below the noise, the honest conclusion is "the defaults were fine".

(Cross-validation AP is lower than test AP here, 0.458 vs 0.492. Not a bug: each CV fold trains on only two thirds of the training rows, and the test set can be slightly easier or harder by chance. Compare CV numbers with CV numbers.)

## Random search: 40 candidates

We evaluate 40 random draws from the space. For each we compute the cross-validated AP, which is what a real search would use to pick a winner. Just for this experiment, we also record the test AP, which a real search must never look at, so we can study the search itself:

```python
rows = []
for params in ParameterSampler(space, n_iter=40, random_state=0):
    m = base.set_params(**params)
    cv_ap = cross_val_score(m, Xtr, ytr, cv=cv, scoring="average_precision").mean()
    te_ap = average_precision_score(yte, m.fit(Xtr, ytr).predict_proba(Xte)[:, 1])
    rows.append({**params, "cv_ap": cv_ap, "test_ap": te_ap})
table = pd.DataFrame(rows)
print(table.sort_values("cv_ap", ascending=False).head(5).round(3).to_string(index=False))
print("range of CV AP over all 40:", table.cv_ap.min().round(3), "to", table.cv_ap.max().round(3))
```

```output
 min_samples_leaf  max_leaf_nodes  max_features  learning_rate  l2_regularization  cv_ap  test_ap
               50              15           0.6           0.05               10.0  0.466    0.495
               10              31           0.3           0.02                0.1  0.465    0.496
               20              15           0.3           0.08                1.0  0.465    0.496
               10              31           0.6           0.03               10.0  0.465    0.491
               50              31           0.6           0.05                0.1  0.463    0.497
range of CV AP over all 40: 0.439 to 0.466
```

Four things are worth noticing:

1. **The top five are indistinguishable.** CV AP 0.463–0.466 with completely different settings (leaf sizes 10 to 50, learning rates 0.02 to 0.08). The score surface has a broad plateau, not a sharp peak.
2. **The whole space spans only 0.027** (0.439 → 0.466). Even the worst of 40 random configurations isn't a disaster. This model family is forgiving.
3. **The winner by CV isn't the winner on test.** The best CV candidate (0.466) scores 0.495 on the test set; the fifth (CV 0.463) scores **0.497**. The differences here, ±0.003, are inside the noise of an 8,238-row test set.
4. **Best tuned test AP ≈ 0.495 vs defaults 0.492.** Three thousandths.

## What does a bigger budget actually buy?

The 40 candidates give us a way to measure it. Draw a random subset of size *b* from the table, pick the candidate with the best CV score (what a real search of budget *b* would do), look up its test score, and repeat 200 times with different random subsets:

```python
rng = np.random.default_rng(0)
print("budget  best CV AP   test AP of the winner   spread(test AP)")
for budget in (1, 2, 4, 8, 16, 40):
    cvs, tes = [], []
    for _ in range(200):
        pick = table.iloc[rng.permutation(len(table))[:budget]]
        w = pick.loc[pick.cv_ap.idxmax()]
        cvs.append(w.cv_ap); tes.append(w.test_ap)
    print(f"{budget:>5}   {np.mean(cvs):.3f}        {np.mean(tes):.3f}                 +-{np.std(tes):.3f}")
```

```output
budget  best CV AP   test AP of the winner   spread(test AP)
    1   0.459        0.488                 +-0.007
    2   0.462        0.491                 +-0.005
    4   0.463        0.493                 +-0.004
    8   0.465        0.494                 +-0.002
   16   0.465        0.495                 +-0.001
   40   0.466        0.495                 +-0.000
```

![Test average precision of the tuning winner as the number of random candidates grows, with the default-parameters score as a reference line.](/series/classification/figures/ch10-budget.png)
*Figure 1. Diminishing returns: most of the benefit arrives by 4–8 candidates, and the variance between lucky and unlucky searches collapses.*

This table is the justification for the rest of the series:

- **One random candidate** (essentially "pick something plausible") averages 0.488 on test, with ±0.007 of luck either way.
- **Eight candidates** gets 0.494: within 0.001 of what forty candidates achieve, and the luck factor is down to ±0.002.
- Beyond that you are buying *reliability* (smaller spread), not *accuracy*.
- The defaults (0.492) sit between budget 2 and budget 4. They're a good starting point because the library authors tuned them on many datasets.

**So the leaderboard uses 8 random candidates, 3-fold CV, for every model**, and we'll report that figure. Eight is enough to reach the plateau for most families, and it keeps the comparison equal and affordable.

<div class="callout gotcha">

**Gotcha — the winner's CV score is optimistic.** In the budget-40 row the best CV AP is 0.466 and it only improves because we selected the maximum of 40 noisy numbers. Selecting the max of many noisy estimates biases it upward ("winner's curse"). The more candidates you evaluate, the less you should trust the winning CV score as an estimate of future performance. That's what the untouched **test set** is for: it was never used to choose anything.

</div>

## Doing it for real: `RandomizedSearchCV`

You don't need the manual loop outside of experiments. The library version of what the leaderboard script does:

```python
from sklearn.model_selection import RandomizedSearchCV

search = RandomizedSearchCV(
    HistGradientBoostingClassifier(categorical_features="from_dtype", early_stopping=True, random_state=0),
    space, n_iter=8, cv=StratifiedKFold(3, shuffle=True, random_state=0),
    scoring="average_precision", random_state=0, n_jobs=1,
)
search.fit(Xtr, ytr)               # refits the best candidate on all of Xtr
print(search.best_params_, round(search.best_score_, 3))
print("test AP:", round(average_precision_score(yte, search.predict_proba(Xte)[:, 1]), 3))
```

Three habits that matter more than the algorithm:

1. **Search over a pipeline, not a pre-transformed matrix.** If preprocessing is inside the estimator, each CV fold refits it. (Part 5.)
2. **Optimise the metric you will be judged on**, here `average_precision`. The default `scoring=None` uses accuracy, which is useless for this problem.
3. **Never tune on the test set**, and never peek at it to "decide whether to search more". Once you have looked at it, it is a validation set and you need a new test set.

## Choosing what to search

A practical priority list for tree ensembles:

| Priority | Parameter | Why |
|---|---|---|
| 1 | `learning_rate` (+ early stopping for tree count) | Controls bias/variance trade-off of the whole ensemble |
| 2 | Tree size: `max_leaf_nodes` / `max_depth` | Interaction depth |
| 3 | `min_samples_leaf` (`min_child_samples`) | The anti-overfitting knob for rare classes |
| 4 | Regularisation: `l2_regularization` / `reg_lambda` | Smoother leaf values |
| 5 | Row/column subsampling | Variance reduction |

Search **log-uniformly** over learning rates and regularisation strengths (0.02 → 0.2, 0.1 → 10) and linearly over small integers. For logistic regression only `C` matters; for random forests `min_samples_leaf` and `max_features`.

Two refinements exist but are beyond this series: **successive halving** (`HalvingRandomSearchCV`) discards poor candidates early on small subsets, and Bayesian optimisers (Optuna, Hyperopt) pick the next candidate based on previous results. They help when single fits are expensive. At 3–30 seconds per fit, 8 random candidates are fine.

## What to remember

1. Score the defaults first. Your tuned model has to beat them by more than the noise.
2. Random search beats grid search at equal budget.
3. **Returns diminish fast.** On this problem 8 candidates reach about 99% of what 40 do.
4. Equal budgets make model comparisons fair. Unequal budgets compare effort.
5. The winning CV score is biased upward; only an untouched test set tells the truth.

[Part 11](/series/classification/11-probabilities-calibration-thresholds-costs/) deals with something tuning can't fix: a model that ranks well but outputs numbers that aren't probabilities.
