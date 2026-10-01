---
title: "When Time Breaks the Model: Train on the Past, Predict the Future"
description: "Re-run the race with a chronological split. The subscription rate jumps from 6% to 31%, the boosters fall to the bottom, logistic regression wins, and a one-line base-rate correction recovers almost all the lost profit."
series: "classification"
order: 16
date: 2026-10-01
keywords: ["distribution shift", "temporal validation", "prior shift", "concept drift", "model robustness", "time series split"]
readingTime: "18 min read"
figure: "ch16-time-shift.png"
---

Everything in parts 12–15 used a random 80/20 split. It's the standard way to compare algorithms, and in part 2 we justified it: it isolates *model* differences from *data-era* differences. But it answers a question nobody is asking in production. A deployed model scores tomorrow's customers, who weren't in last year's data.

The file is in date order, which gives us a free experiment: **train on the first 80% of rows (the past) and test on the last 20% (the future).** Same models, same features, same tuned hyperparameters from the leaderboard. Only the split changes.

## The future is a different place

```python
df = pd.read_csv("bank-additional-full.csv", sep=";")           # the file is in chronological order
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")

cut = int(len(X) * 0.8)                                          # train on the past, test on the future
tr, te = np.arange(cut), np.arange(cut, len(X))
print(f"train rows 0-{cut - 1}: {y[tr].mean():.1%} subscribe   |   test rows {cut}-{len(X) - 1}: {y[te].mean():.1%} subscribe")
```

```output
train rows 0-32949: 6.4% subscribe   |   test rows 32950-41187: 30.8% subscribe
```

The training period has **6.4% subscribers; the test period has 30.8%**. That's the "prior shift" we foreshadowed in part 2: the rate climbs through the file because the economy (and the campaign) changed. In the training era the 12.5% break-even threshold was an unusual customer. In the test era it's *a below-average one*:

```python
COST, VALUE = 1.0, 8.0
def profit(p, t=1 / 8):
    call = p >= t
    return VALUE * y[te][call].sum() - COST * call.sum()
print(f"call everyone: profit {profit(np.ones(len(te)), 0.5):.0f}")
```

```output
call everyone: profit 12082
```

Remember part 14: on the random split, calling everyone *lost* 814. In the future period, calling everyone **earns 12,082**. Any model we train on the past has to beat a "no-model" strategy that is suddenly extremely strong.

## The race, re-run

Seven of the leaderboard models, trained on the past, with the same hyperparameters selected earlier, scored on the future:

```python
candidates = {
    "LightGBM":                     (LGBMClassifier(**params), "cat"),
    "sklearn HistGradientBoosting": (HistGradientBoostingClassifier(max_leaf_nodes=15, learning_rate=0.1, l2_regularization=1,
                                         categorical_features="from_dtype", early_stopping=True, random_state=42), "cat"),
    "XGBoost":                      (XGBClassifier(n_estimators=400, learning_rate=0.02, max_depth=4, subsample=0.7,
                                         colsample_bytree=0.6, tree_method="hist", enable_categorical=True, random_state=42), "cat"),
    "Random forest":                (make_pipeline(dense, RandomForestClassifier(300, min_samples_leaf=10, max_features=0.3, n_jobs=-1, random_state=42)), "raw"),
    "Decision tree":                (make_pipeline(dense, DecisionTreeClassifier(min_samples_leaf=100, random_state=42)), "raw"),
    "Logistic regression":          (make_pipeline(prep, LogisticRegression(C=1, max_iter=2000)), "raw"),
    "k-nearest neighbors":          (make_pipeline(dense, KNeighborsClassifier(120, n_jobs=-1)), "raw"),
}
for name, (est, view) in candidates.items():
    F = Xc if view == "cat" else X                      # categorical dtype for the boosters, raw strings otherwise
    p = est.fit(F.iloc[tr], y[tr]).predict_proba(F.iloc[te])[:, 1]
    ...
```

```output
model                              AP    AUC  mean p  calls@1/8  profit@1/8
k-nearest neighbors             0.537  0.703   0.170       3634        9430
Logistic regression             0.527  0.748   0.257       4692       12332
Random forest                   0.510  0.728   0.143       3765       10179
LightGBM                        0.503  0.694   0.100       1988        7004
Decision tree                   0.476  0.662   0.101       1640        6280
XGBoost                         0.472  0.672   0.125       2167        6617
sklearn HistGradientBoosting    0.456  0.648   0.110       1679        5129
```

![Left: average precision under a random split and under the chronological split, per model. Right: profit at threshold 1/8 on the future test set, with the call-everyone benchmark.](/series/classification/figures/ch16-time-shift.png)
*Figure 1. The same models, two splits. The ranking from part 12 doesn't survive.*

The leaderboard has been reshuffled:

- **k-NN goes from 11th of 12 on the random split to first of these seven** by average precision (0.456 → 0.537). The model that was near the bottom is now at the top.
- **Logistic regression has the best AUC** (0.748 vs 0.694 for LightGBM) and **the best profit by a mile**: 12,332, beating the no-model "call everyone" benchmark (12,082) while every tree-based booster earns *less than call-everyone*.
- **All three boosters finish in the bottom four** on AP, and their AUCs (0.65–0.69) collapse from the 0.81–0.82 they scored on the random split. A likely culprit is the macro-economic columns: flexible tree models can carve them into fine cells that describe the training era exactly (part 15 showed LightGBM leans on them), and in the test era the economy sits in a range the training data barely covers.
- **Random forest** holds up better than boosting (AP 0.510, AUC 0.728).

<div class="callout gotcha">

**Gotcha — "best on a random split" is not "best in production".** The random split taught us that boosting beats logistic regression by 0.03 AP. The chronological split says logistic regression beats the best booster by 0.024 AP. Both statements are true. They answer different questions: *which algorithm learns this relationship best?* versus *which one still works when the relationship moves?* A deployed system lives in the second world.

</div>

## Why the boosters lose the profit race: they don't know the base rate moved

Look at `mean p` and `calls@1/8`. The test period has 30.8% subscribers. Logistic regression's *average predicted probability* is 0.257, closest to the truth: it noticed the world got better. LightGBM's is 0.100, barely above its training-era base rate of 6.4%. At threshold 1/8, LightGBM calls 1,988 customers; logistic regression calls 4,692; the truth is that 2,540 of the 8,238 test customers would have subscribed.

LightGBM isn't ranking customers terribly (AUC 0.694); it's calling too few of them because **its probabilities are calibrated to a world with 6% subscribers.** At a break-even of 12.5%, the model thinks most customers fall below the line, when in the new world most are above it.

That diagnosis suggests a cheap fix. The model outputs `p` for the training prior (6.4%); if we know the new prior is 30.8%, Bayes' rule says to multiply the odds by the ratio of prior odds:

```python
def shift(p, old, new):
    odds = p / (1 - p) * (new / (1 - new)) / (old / (1 - old))
    return odds / (1 + odds)
report("LightGBM + base-rate correction", shift(np.clip(p_l, 1e-6, 1 - 1e-6), y[tr].mean(), y[te].mean()))
```

```output
LightGBM, trained on the past      AP=0.503  AUC=0.694  mean p=0.100  calls@1/8= 1988  profit@1/8=  7004  (best possible 12258)
LightGBM + base-rate correction    AP=0.503  AUC=0.694  mean p=0.360  calls@1/8= 7936  profit@1/8= 12240  (best possible 12258)
```

**One line of arithmetic takes LightGBM from 7,004 to 12,240, 99.9% of the best profit that *any* threshold could have achieved** on this test set (12,258). AP and AUC are identical because a monotone transformation can't change a ranking; only the *decisions* changed. This is the cleanest demonstration in the series of why ranking and decision-making are separate problems.

Try it yourself. Tell the model what base rate to assume and watch profit at the 1/8 threshold. At the training-era rate nothing changes; as you slide toward the real 30.8% the booster's profit climbs to its best, and past it the model over-calls again.

<div class="prior-shift-lab" data-src="/series/classification/artifacts/prior_shift_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/prior-shift-lab.js"></script>

The catch is the argument `new`: we used the test set's actual 30.8%, which you won't know in advance. In production you must estimate it from recent data, e.g. from the last few weeks of outcomes, or from a small randomly-sampled holdout where calls aren't selected by the model. If you can't estimate it, the next best option is to monitor the *mean predicted probability* vs observed subscription rate in a rolling window and recalibrate when they diverge.

## Other things we tried

```python
macro = ["emp.var.rate", "cons.price.idx", "cons.conf.idx", "euribor3m", "nr.employed"]
m2 = LGBMClassifier(**params).fit(Xc.iloc[tr].drop(columns=macro), y[tr])        # (a) without macro columns

recent = tr[len(tr) // 2:]                                                       # (b) newest half of training only
m3 = LGBMClassifier(**params).fit(Xc.iloc[recent], y[recent])
```

```output
LightGBM without macro columns     AP=0.477  AUC=0.669  mean p=0.147  calls@1/8= 2290  profit@1/8= 7542  (best possible 12128)
LightGBM, recent half only         AP=0.525  AUC=0.711  mean p=0.109  calls@1/8= 2309  profit@1/8= 7595  (best possible 12352)
```

- **(a) Dropping the macro columns** hurts ranking (AP 0.503 → 0.477) rather than helping. Those columns carry *real* signal even when their relationship shifts. Throwing out time-proxies isn't a free fix.
- **(b) Training on only the newest half of the training data** helps the ranking (AP 0.525, AUC 0.711): more weight on data closer to the future. But profit stays near 7,600; the base-rate problem remains until you correct it.

Neither alternative is as effective as the base-rate correction, and none rescues the booster's AUC to logistic regression's 0.748.

## What this means for model selection

| Question | Random split | Chronological split |
|---|---|---|
| Best ranker by AP | LightGBM (0.496) | k-NN (0.537), logistic (0.527) |
| Best AUC | LightGBM (0.816) | Logistic regression (0.748) |
| Boosting vs logistic | +0.031 AP | **−0.024 AP** |
| Profit at t = 1/8 | ~3,350 for the top models | Logistic 12,332; LightGBM 7,004 |
| Base rate | 11.3% (stable) | 6.4% → 30.8% |

A defensible conclusion is *not* "logistic regression is better than boosting". It's that **our evidence for deploying boosting rests on an evaluation that doesn't resemble deployment**, and an evaluation that does resemble it says the opposite. In a real project you would:

1. **Evaluate on a forward-in-time split** whenever the data has an order, and treat it as the primary estimate of performance. Use random splits only to compare algorithms *given* the era.
2. **Run several forward folds** (train on rows 0–50%, test 50–66%; train 0–66%, test 66–83%; …) rather than one cut, so you see how the gap varies. We used one cut here because of the file's dramatic shift; the repository's `run_experiments.py` includes a three-fold expanding-window version.
3. **Monitor the base rate and the mean predicted probability in production** and recalibrate. It is cheap and catches the failure that cost LightGBM 5,000 units.
4. **Prefer models whose failure mode you understand.** Logistic regression degraded more gracefully here: its average probability (0.257) moved toward the new base rate, plausibly because it extrapolates smoothly in the economy variables instead of carving them into leaf-shaped cells.
5. **Keep a simple baseline in the race.** A model that's 0.03 AP ahead in a random split is not safe to deploy if a 3-microsecond logistic regression is 0.024 ahead of it in the future.

## Where we've ended up

Sixteen parts, one dataset, thirteen classifiers. If you remember six things:

1. A classifier supports a **decision**; define the prediction moment, the cost table and the capacity before choosing a model.
2. Check for **leakage** (`duration`) and **drift** (6% → 31%) before any algorithm comparison.
3. **Average precision, log loss and profit** answer different questions than accuracy; use the one that matches the decision.
4. On this data gradient boosting and random forests form a **statistically tied top tier**, about 0.03 AP above logistic regression, on a random split.
5. **The threshold matters more than the model**: derive it from costs (`p* = cost/value`), choose it on out-of-fold data, and re-check it when the base rate moves.
6. **The winner depends on the split.** Test the way you will deploy.

All code, data checksums and outputs are in the repository. Every number in this series was printed by a script in `series/classification/`, and every figure was produced by one of them. If a number in a post doesn't reproduce, that's a bug, and I'd like to hear about it.
