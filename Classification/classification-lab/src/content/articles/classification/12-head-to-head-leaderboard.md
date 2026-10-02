---
title: "Head to Head: Thirteen Classifiers, One Split, One Budget"
description: "XGBoost vs LightGBM vs CatBoost vs random forest vs logistic regression and seven more, on identical data with an identical tuning budget. The full table, the curves, and what the numbers do and don't say."
series: "classification"
order: 12
date: 2026-10-01
updated: 2026-10-02
keywords: ["model comparison", "xgboost", "lightgbm", "catboost", "random forest", "benchmark", "leaderboard"]
readingTime: "20 min read"
figure: "leaderboard-ap.png"
---

For eleven parts we've been building up to this one. We know what the data hides ([part 2](/series/classification/02-why-classification-is-hard/)), how to grade a model (3), what each family does (5–9), how to tune fairly (10) and how to turn scores into decisions (11). Now we race everything.

The rules from [part 1](/series/classification/01-classification-is-a-decision/) are enforced by code, not by good intentions:

- **Same rows:** one stratified 80/20 split (`random_state=42`): 32,950 training rows, 8,238 test rows, 11.27% positives in both.
- **Same features:** the 19 pre-call columns. No `duration`.
- **Same budget:** each model gets **8 random-search candidates × 3 stratified folds**, scored on average precision, drawn from a search space of its own parameters. The same `RandomizedSearchCV` call, the same CV splits.
- **One look at the test set.** Parameters are chosen from the training data alone; the test set is used to score each model once.

## Goals: what are we trying to achieve?

This is the payoff chapter: thirteen entries, one split, one budget. Our goal is to produce a leaderboard that is fair by construction, and to read it without over-claiming.

By the end you will be able to:

- **List the rules that make a comparison fair**: same rows, same features, same budget, one look at the test set.
- **Read the three tiers** in the table and the gaps between them.
- **Explain why speed and simplicity belong next to accuracy** when you pick a model.

## The work plan: how do we do it?

The rules from [Part 1](/series/classification/01-classification-is-a-decision/) are enforced by code, not by good intentions:

1. **Same rows:** one stratified 80/20 split (`random_state=42`), 32,950 training and 8,238 test rows.
2. **Same features:** the 19 pre-call columns, no `duration`.
3. **Same budget:** 8 random-search candidates, 3 stratified folds, scored on average precision.
4. **One look at the test set.** Parameters come from the training data alone.

Each model uses its native representation (one-hot, `category` columns, or raw strings for CatBoost).

## Implementation

### The contenders

Thirteen entries, covering every family in the series. The full harness is [`run_leaderboard.py`](/series/classification/code/run_leaderboard.py); here's its core:

```python
def specs():
    """(name, family, view, estimator, search space). One entry per contender."""
    lin, tre = linear_prep(X), tree_prep(X)
    return [
        ("Prior (no model)", "baseline", "raw", DummyClassifier(strategy="prior"), {}),
        ("Logistic regression", "linear", "raw",
         Pipeline([("prep", lin), ("m", LogisticRegression(max_iter=2000, solver="liblinear"))]),
         {"m__C": [0.01, 0.03, 0.1, 0.3, 1, 3]}),
        ...
        ("XGBoost", "boosting", "category",
         XGBClassifier(n_estimators=400, tree_method="hist", enable_categorical=True, n_jobs=-1),
         {"learning_rate": [0.02, 0.05, 0.1], "max_depth": [3, 4, 6], "subsample": [0.7, 1.0],
          "colsample_bytree": [0.6, 1.0], "min_child_weight": [1, 10]}),
        ("LightGBM", "boosting", "category",
         LGBMClassifier(n_estimators=400, n_jobs=-1, verbose=-1),
         {"learning_rate": [0.02, 0.05, 0.1], "num_leaves": [7, 15, 31], "subsample": [0.7, 1.0],
          "subsample_freq": [1], "colsample_bytree": [0.6, 1.0], "min_child_samples": [20, 100]}),
        ("CatBoost", "boosting", "raw", CatBoostSK(iterations=400),
         {"learning_rate": [0.03, 0.06, 0.1], "depth": [4, 6, 8], "l2_leaf_reg": [1, 3, 10]}),
    ]
```

and the loop that treats them all identically:

```python
for name, family, view, est, space in specs():
    Xtr, Xte = V[view].iloc[tr], V[view].iloc[te]            # same rows, encoding differs by family
    search = RandomizedSearchCV(est, space, n_iter=8, scoring="average_precision",
                                cv=StratifiedKFold(3, shuffle=True, random_state=42),
                                random_state=42, refit=False).fit(Xtr, y[tr])
    final = clone(est).set_params(**search.best_params_).fit(Xtr, y[tr])
    p = final.predict_proba(Xte)[:, 1]                        # the only time the test set is touched
```

Only the *encoding* differs: logistic regression, SVM, k-NN, Naive Bayes and the neural net get one-hot + scaled features; trees get one-hot; LightGBM, XGBoost and scikit-learn's histogram booster get pandas `category` columns; CatBoost gets raw strings and does its own categorical statistics. Letting each model use its *native* representation is part of what we're comparing.

<div class="callout">

**How the three boosting libraries handle categories.** In the code above LightGBM and XGBoost receive `category` dtype columns, and CatBoost a list of column names (we wrap it in a tiny scikit-learn-compatible class, `CatBoostSK` in `common.py`, because CatBoost's own estimator can't be cloned by `RandomizedSearchCV`). Does it matter? Part-12 side experiment: the same tuned LightGBM trained on (a) native categories, (b) one-hot columns, (c) integer codes treated as numbers gives AP **0.496, 0.496 and 0.499**. With low-cardinality categoricals like `month` (10 levels) and `job` (12), all three are equivalent. Native handling earns its keep on columns with hundreds of levels, which this dataset doesn't have.

</div>

## What did we get? Results

Twelve models and a no-model baseline, on the 8,238 held-out customers. Ordered by AP:

### The result

All numbers below are on the 8,238 held-out customers. AP = average precision (the selection metric), ECE = calibration error, Precision@10% = hit rate among the top-scoring tenth, and Profit is computed in [part 14](/series/classification/14-pricing-the-models/). Ordered by AP:

| # | Model | Family | AP | ROC-AUC | Log loss | ECE | Precision@10% | Fit (s) | µs / row | Profit |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | LightGBM | boosting | **0.496** | 0.816 | 0.262 | 0.009 | 0.54 | 1.5 | 11 | 3,341 |
| 2 | sklearn HistGradientBoosting | boosting | **0.494** | 0.814 | 0.264 | 0.011 | 0.55 | 0.5 | 5 | 3,323 |
| 3 | Random forest | bagging | **0.490** | 0.808 | 0.266 | 0.012 | 0.54 | 3.9 | 20 | 3,343 |
| 4 | XGBoost | boosting | **0.490** | 0.815 | 0.264 | 0.013 | 0.54 | 1.0 | 3 | 3,377 |
| 5 | CatBoost | boosting | **0.487** | 0.813 | 0.264 | 0.010 | 0.54 | 47.4 | 7 | 3,299 |
| 6 | Extra trees | bagging | **0.485** | 0.807 | 0.268 | 0.012 | 0.54 | 9.9 | 54 | 3,291 |
| 7 | Small neural net (MLP) | neural | **0.477** | 0.803 | 0.269 | 0.013 | 0.53 | 2.2 | 3 | 3,251 |
| 8 | Decision tree | tree | **0.468** | 0.802 | 0.285 | 0.017 | 0.53 | 0.3 | 3 | 3,272 |
| 9 | Logistic regression | linear | **0.465** | 0.801 | 0.272 | 0.012 | 0.50 | 0.5 | 3 | 3,178 |
| 10 | Linear SVM (calibrated) | linear | **0.462** | 0.798 | 0.275 | 0.018 | 0.50 | 0.7 | 3 | 3,230 |
| 11 | k-nearest neighbors | instance | **0.456** | 0.798 | 0.276 | 0.014 | 0.50 | 0.1 | 75 | 3,184 |
| 12 | Gaussian Naive Bayes | probabilistic | **0.413** | 0.780 | 0.820 | 0.111 | 0.43 | 0.1 | 4 | 3,040 |
| – | Prior (no model) | baseline | 0.113 | 0.500 | 0.352 | 0.000 | 0.11 | 0.0 | 0 | 0 |

(The prior row is a constant: every customer gets the 11.3% base rate. It anchors the scale: AP of a random ranking *is* the base rate.)

![Horizontal bars of test average precision for 13 models with 95% bootstrap intervals, coloured by model family.](/series/classification/figures/leaderboard-ap.png)
*Figure 1. Average precision with bootstrap intervals. Whiskers overlap heavily across the top six.*

![ROC and precision-recall curves for seven of the models.](/series/classification/figures/leaderboard-curves.png)
*Figure 2. ROC and precision-recall curves for the main contenders. The four strongest curves are nearly on top of one another.*

![Test AP against fit time on a log axis for each model.](/series/classification/figures/leaderboard-cost-vs-quality.png)
*Figure 3. Quality versus training cost. The efficient frontier is HistGradientBoosting, XGBoost and LightGBM, the top-left corner; CatBoost buys nothing for its 47 seconds.*

## Analysis and conclusion: what did we learn?

- **Three tiers.** Tier 1 (AP 0.485 to 0.496): the four boosters, the random forest and extra trees. Tier 2 (0.456 to 0.477): the neural net, a tuned tree, logistic regression, the linear SVM and k-NN. Tier 3: Naive Bayes at 0.413.
- **The gap between tiers is about +0.025 AP.** The gap within tier 1 (CatBoost to LightGBM) is 0.009, and [Part 13](/series/classification/13-is-the-winner-real/) shows it is mostly noise.
- **Simple models are not far behind.** Logistic regression is 0.031 below the winner. At a top-10% hit rate that is about 4 more subscribers per 100 calls, which is real money at scale and not a revolution.
- **Speed varies 500 times.** HistGradientBoosting trains in 0.5 s and ranks second, while CatBoost needs 47 s for no gain.

### What the table says

**1. The race has three tiers, and the gaps between tiers are bigger than the gaps within them.**

- *Tier 1, AP 0.485–0.496:* the four boosters, random forest and extra trees. Six models, spanning 0.011 of AP.
- *Tier 2, AP 0.456–0.477:* the small neural net, a tuned single tree, logistic regression, the linear SVM and k-NN. Five models spanning 0.021.
- *Tier 3:* Gaussian Naive Bayes at 0.413, and the base-rate model at 0.113.

Moving from tier 2 to tier 1 is worth about **+0.025 AP** (about 5% relative). Moving *within* tier 1, e.g. from CatBoost to LightGBM, is worth 0.009, and as [part 13](/series/classification/13-is-the-winner-real/) shows, that is mostly noise.

**2. "XGBoost vs LightGBM vs CatBoost" is not the interesting question here.** LightGBM led by 0.006–0.009 on AP, but the paired bootstrap intervals in the next part include or touch zero for LightGBM against XGBoost, HistGB, random forest. The three libraries and scikit-learn's own booster all end within 0.009 of each other, on the *same* tuning budget. The thing that matters is "gradient boosting vs other approaches", not which library you pick.

**3. A random forest is within noise of the boosters.** 0.490 vs 0.496. We spent tuning effort on boosting hyperparameters that bought roughly nothing over a forest with two knobs. This is a common outcome on small, mostly-categorical tabular data with a weak signal.

**4. The simple models are not far behind.** Logistic regression is at 0.465, **0.031 AP below the winner**, and a single tuned decision tree is at 0.468, *above* logistic regression. In terms of the top-10% hit rate, logistic regression gets 0.50 vs 0.54–0.55. If you can phone one customer in ten, the best model gets about 4 more subscribers per 100 calls than logistic regression. That is real money at scale, and it isn't a revolution.

**5. Calibration is a non-event, except for Naive Bayes.** Every model except Naive Bayes has ECE ≤ 0.018 and log loss between 0.262 and 0.285. Naive Bayes' log loss of 0.820 and ECE of 0.111 are alarming, and a profit calculation based on its raw probabilities would be nonsense ([part 14](/series/classification/14-pricing-the-models/) shows what a *threshold chosen on training data* does to rescue it).

**6. Speed has a spread of 500×.** From 0.1 s (k-NN, Naive Bayes) to 47 s (CatBoost).

Look at the top-left of that chart. **scikit-learn's own `HistGradientBoostingClassifier` trains in half a second and ranks second.** It sits on the frontier with XGBoost (1.0 s) and LightGBM (1.5 s). CatBoost is 30–100× slower to fit here. (On this machine with default threading, one CatBoost fit took anywhere between 47 and 95 seconds depending on what else was running. Treat its fit time as order-of-magnitude. And in fairness, CatBoost is designed for far more categorical levels than this dataset has, and for GPU training.) Inference cost is separate: k-NN and extra trees pay 50–75 µs per row, against 3–5 µs for XGBoost and logistic regression.

### The mistakes this chapter avoids

This table is deceptively simple. Several of the usual ways to get a misleading leaderboard are *excluded by construction*:

- **Different splits per model** (the winner got an easier test set). Here: one split.
- **Unequal tuning** (the favourite got 200 candidates, the rest defaults). Here: 8 for everyone.
- **Selecting on the test set.** Hyperparameters come from CV on the training portion only.
- **Reporting only the metric you won on.** We give AUC, log loss, ECE and top-10% precision.
- **Declaring a winner without error bars.** That is the entire next chapter.

### Caveats before you quote this table

- **One dataset.** This ranking is about *this problem*: ~41k rows, 19 features, a weak signal, a rare positive class. On a dataset with 10 million rows, many numeric features, or text, the order would differ.
- **Random-split evaluation.** We treat rows as exchangeable. They are not ([part 2](/series/classification/02-why-classification-is-hard/)); [part 16](/series/classification/16-when-time-breaks-the-model/) re-runs a version of the race on a train-on-past, test-on-future split.
- **A small search budget** favours models with few hyperparameters or good defaults. A larger budget might re-order places 2–5. [Part 10](/series/classification/10-hyperparameter-search/) suggests it wouldn't move them much.

### So what did we do?

We raced thirteen entries under identical rules. Gradient boosting and forests form a top tier, the simple models are not far behind, and the speed spread is huge. Whether LightGBM's first place is real is the question for the next part.

### In the next part

So who won? On the single test split: LightGBM, by a hair. Whether that is a *result* or a coin flip is the question for [part 13](/series/classification/13-is-the-winner-real/).
