---
title: "From Scores to Decisions: Calibration, Thresholds and Money"
description: "Measure whether a model's 30% really means 30%, repair a lying Naive Bayes, and derive the call-or-don't threshold from a simple cost table instead of defaulting to 0.5."
series: "classification"
order: 11
date: 2026-09-30
updated: 2026-10-02
keywords: ["calibration", "threshold", "cost-sensitive learning", "expected profit", "isotonic regression", "platt scaling", "reliability diagram"]
readingTime: "17 min read"
figure: "ch11-calibration.png"
---

A model gives each customer a number. Two questions follow, and they are different:

1. **Is the number honest?** When it says 0.30, do about 30% of those customers subscribe? That's *calibration*.
2. **What do we do with it?** At which number do we pick up the phone? That's the *threshold*, and it's a business decision with a formula.

If the answer to (1) is yes, (2) has a clean closed-form solution. If it's no, you can often repair it. This chapter does both, on three models we've already met.

## Goals: what are we trying to achieve?

A model gives each customer a number. Our goal is to check that the number is honest, repair it when it is not, and then turn it into a decision with a formula.

By the end you will be able to:

- **Measure calibration** with a reliability diagram and the Expected Calibration Error (ECE).
- **Repair a lying model** with Platt scaling or isotonic regression, and know what each one costs.
- **Derive the call threshold from costs**: `p* = cost / value`, and check it on held-out data.

## The work plan: how do we do it?

We use three models we already know, and a separate calibration slice:

1. **Set up** logistic regression, a random forest and Naive Bayes, with a calibration slice carved out of the training data.
2. **Measure honesty**: ECE and a reliability diagram on the test set.
3. **Repair** the models that lie, with sigmoid and isotonic calibration.
4. **Decide**: the break-even threshold from a cost table (a call costs 1, a subscription is worth 8), and the profit it produces.

## Implementation

### Setting up three models

We'll fit logistic regression, a random forest and Gaussian Naive Bayes, and carve a *calibration slice* out of the training data for the repair step later. (Calibration needs its own data: fit the model on one part, fit the correction on another, or you'd measure honesty on the answers the model memorised.)

```python
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
Xfit, Xcal, yfit, ycal = train_test_split(Xtr, ytr, test_size=0.25, stratify=ytr, random_state=1)  # calibration slice
cat = X.select_dtypes("object").columns.tolist()
prep = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                         remainder=StandardScaler())

models = {
    "Logistic regression": make_pipeline(prep, LogisticRegression(C=0.1, max_iter=2000)),
    "Random forest":       make_pipeline(prep, RandomForestClassifier(300, min_samples_leaf=10, n_jobs=-1, random_state=0)),
    "Naive Bayes":         make_pipeline(prep, GaussianNB(var_smoothing=1e-3)),
}
```

### Measuring honesty: ECE and the reliability diagram

Sort the test customers by predicted probability, split them into ten equal groups, and compare **the average prediction** with **the actual subscription rate** in each. A calibrated model has both equal in every group. The *Expected Calibration Error* (ECE) is the size-weighted average gap:

```python
def ece(y, p, bins=10):
    edges = np.quantile(p, np.linspace(0, 1, bins + 1)); edges[0], edges[-1] = -np.inf, np.inf
    idx = np.digitize(p, edges[1:-1])
    return sum((idx == b).mean() * abs(p[idx == b].mean() - y[idx == b].mean())
               for b in range(bins) if (idx == b).any())

def report(name, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    print(f"{name:<34} AP={average_precision_score(yte, p):.3f}  logloss={log_loss(yte, p):.3f}  "
          f"brier={brier_score_loss(yte, p):.4f}  ECE={ece(yte, p):.3f}  mean p={p.mean():.3f}")

raw = {}
for name, m in models.items():
    raw[name] = m.fit(Xfit, yfit).predict_proba(Xte)[:, 1]
    report(name, raw[name])
print("true base rate:", yte.mean().round(3))
```

```output
Logistic regression                AP=0.462  logloss=0.272  brier=0.0771  ECE=0.012  mean p=0.111
Random forest                      AP=0.485  logloss=0.266  brier=0.0750  ECE=0.015  mean p=0.111
Naive Bayes                        AP=0.353  logloss=1.317  brier=0.1343  ECE=0.120  mean p=0.142
true base rate: 0.113
```

Two reassuring results and one bad one:

- **Logistic regression is calibrated** (ECE 0.012). It's trained on log loss, a proper scoring rule, so honest probabilities are what it's *rewarded* for.
- **The random forest is also fine** (ECE 0.015) here. With leaves of at least 10 customers, the averaged proportions are sensible. Many textbooks claim forests are badly calibrated; that depends on leaf size and base rate, and here it is not an issue.
- **Naive Bayes is badly miscalibrated:** ECE 0.120 and a log loss of 1.317, five times worse than the others. Its average prediction (0.142) is already too high, and in the extremes it is wildly over-confident, exactly as [part 5](/series/classification/05-logistic-regression-naive-bayes/) predicted.

<div class="callout gotcha">

**Gotcha — AP does not see calibration.** Naive Bayes has an AP of 0.353 and the others 0.46–0.49: it also ranks worse. But you could imagine a model with a great AP and absurd probabilities: AP and AUC are blind to any monotone transformation of the scores. If downstream code multiplies a probability by a payout, you need log loss, Brier or ECE as well.

</div>

### Repairing a lying model

Calibration repair means learning a monotone function that maps the model's raw score to an honest probability. Two standard choices:

- **Sigmoid (Platt scaling):** fit `p = sigmoid(a·score + b)`. Two parameters, hard to overfit, assumes the distortion is S-shaped.
- **Isotonic regression:** fit any non-decreasing step function. Flexible, but needs plenty of data and produces *plateaus*.

We wrap the already-fitted model in `FrozenEstimator` (so the calibrator can't refit it) and fit the calibration map on the held-out slice:

```python
for name in ("Random forest", "Naive Bayes"):
    for method in ("sigmoid", "isotonic"):
        cal = CalibratedClassifierCV(FrozenEstimator(models[name].fit(Xfit, yfit)), method=method).fit(Xcal, ycal)
        report(f"{name} + {method}", cal.predict_proba(Xte)[:, 1])
```

```output
Random forest + sigmoid            AP=0.485  logloss=0.267  brier=0.0752  ECE=0.015  mean p=0.115
Random forest + isotonic           AP=0.464  logloss=0.266  brier=0.0749  ECE=0.008  mean p=0.114
Naive Bayes + sigmoid              AP=0.368  logloss=0.304  brier=0.0868  ECE=0.027  mean p=0.112
Naive Bayes + isotonic             AP=0.356  logloss=0.288  brier=0.0827  ECE=0.006  mean p=0.112
```

Read this table slowly; each row teaches something.

- **Naive Bayes is rescued.** Platt scaling brings log loss from 1.317 to **0.304** and ECE from 0.120 to 0.027. Isotonic gets ECE down to 0.006. The ranking is the same model's ranking, but the *numbers* are now usable.
- **Random forest barely moves with sigmoid** (it was already honest) — good: calibration doesn't hurt a calibrated model.
- **Isotonic made the forest rank worse: AP fell from 0.485 to 0.464.** This is the sharp edge. An isotonic map is a staircase: different raw scores get collapsed to the same output, creating *ties*. Average precision punishes ties among likely customers, because you can't order them. ECE improved (0.015 → 0.008), AP fell. If you need both ranking and honest probabilities, prefer sigmoid unless you have lots of calibration data, or use isotonic only for the final probability estimate and rank on the raw score.

<div class="callout tip">

**Rule of thumb.** Check calibration *before* trying to fix it; well-trained gradient boosting and logistic regression usually don't need it. For models that need it — Naive Bayes, SVMs, k-NN with small k, heavily regularised boosters — Platt scaling is the safe default.

</div>

### From probability to a decision

Now the part everyone skips: **where do we cut?** Suppose the finance team gives us two numbers:

- A call costs **1** unit of agent time.
- A subscription is worth **8** units of margin.

(These are assumptions for the example; the series repository keeps them in `common.py` so you can change them.)

If a customer has true probability *p* of subscribing, calling them has expected profit `8p − 1`. We should call whenever that is positive:

> **p > cost / value = 1/8 = 0.125**

That's the whole theory. The decision threshold isn't 0.5; it's the break-even probability, and it falls out of the cost table. The catch is the word "true": the formula only works if your probabilities are honest, which is exactly why calibration matters. Let's test it:

```python
COST, VALUE = 1.0, 8.0
print(f"break-even probability = cost/value = {COST / VALUE:.3f}")

def profit(p, t):
    call = p >= t
    return VALUE * yte[call].sum() - COST * call.sum()

fit_rf = models["Random forest"].fit(Xfit, yfit)
cal_rf = CalibratedClassifierCV(FrozenEstimator(fit_rf), method="isotonic").fit(Xcal, ycal)
for label, p in (("RF raw", raw["Random forest"]), ("RF calibrated", cal_rf.predict_proba(Xte)[:, 1])):
    best = max(np.unique(np.quantile(p, np.linspace(0, 0.995, 300))), key=lambda t: profit(p, t))
    print(f"{label:<14} profit at t=0.125: {profit(p, 0.125):6.0f} ({(p >= 0.125).sum():5d} calls)   "
          f"at test-optimal t={best:.3f}: {profit(p, best):6.0f}")
print("call everyone:", profit(np.ones(len(yte)), 0.5), "  call nobody: 0")
```

```output
break-even probability = cost/value = 0.125
RF raw         profit at t=0.125: 3333 ( 1499 calls)   at test-optimal t=0.138: 3372
RF calibrated  profit at t=0.125: 3376 ( 1400 calls)   at test-optimal t=0.127: 3376
call everyone: -814.0
```

The results:

- **Call everyone: −814.** At an 11.3% hit rate and a payout of 8, every call loses money on average. Blind outreach is value-destroying here.
- **A random forest at the theoretical threshold: +3,333** from 1,499 calls, almost all of the best achievable. (The "optimal" threshold in the last column is picked *on the test set* — a cheat that is only possible in hindsight, shown here as an upper bound.)
- **The calibrated forest at the theory threshold is already optimal:** its test-optimal threshold is 0.127, within 0.002 of the 0.125 formula, and its profit at 0.125 equals the best in hindsight (3,376). Calibrated probabilities make the formula work.
- The raw forest's best threshold is 0.138, so the formula was a little off. A small price: 39 units out of 3,372, about 1%.

The right way to find a threshold in practice is **not** to read it off the test set. Either trust the formula with calibrated probabilities, or choose it on out-of-fold training predictions and *freeze it* before touching the test set. The leaderboard does the latter.

## What did we get? Results

Calibration on the test set:

| Model | AP | Log loss | Brier | ECE | Mean p |
|---|---|---|---|---|---|
| Logistic regression | 0.462 | 0.272 | 0.0771 | 0.012 | 0.111 |
| Random forest | 0.485 | 0.266 | 0.0750 | 0.015 | 0.111 |
| Naive Bayes | 0.353 | 1.317 | 0.1343 | 0.120 | 0.142 |

After repair:

| Model | AP | Log loss | ECE |
|---|---|---|---|
| Random forest + sigmoid | 0.485 | 0.267 | 0.015 |
| Random forest + isotonic | 0.464 | 0.266 | 0.008 |
| Naive Bayes + sigmoid | 0.368 | 0.304 | 0.027 |
| Naive Bayes + isotonic | 0.356 | 0.288 | 0.006 |

Profit at the break-even threshold of 0.125 (call costs 1, subscription worth 8):

- **Call everyone:** −814.
- **Random forest, raw:** +3,333 from 1,499 calls (best in hindsight 3,372).
- **Random forest, calibrated:** +3,376 from 1,400 calls, equal to the best in hindsight.

![Reliability diagrams for logistic regression, random forest and Naive Bayes on the test split.](/series/classification/figures/ch11-calibration.png)
*Figure 1. Points on the diagonal are honest. Logistic regression and the forest hug it; Naive Bayes sits far below it in the upper range: when it says 0.9, the truth is much lower.*

## Analysis and conclusion: what did we learn?

- **Logistic regression and the forest are already honest** (ECE 0.012 and 0.015). Naive Bayes is not (ECE 0.120), and Platt scaling brings its log loss from 1.317 down to 0.304.
- **Isotonic can hurt ranking.** It made the forest's AP fall from 0.485 to 0.464, because the staircase creates ties. Prefer sigmoid unless you have a lot of calibration data.
- **The formula only works with honest probabilities.** The calibrated forest's best threshold was 0.127, within 0.002 of the formula. The raw forest's was 0.138, a loss of about 1%.
- **Never choose the threshold on the test set.** Use the formula with calibrated probabilities, or choose it on out-of-fold training predictions and freeze it.

### The policy menu

Thresholds aren't the only decision rule. All of these are legitimate:

| Policy | Rule | When it fits |
|---|---|---|
| **Break-even threshold** | Call if p > cost/value | Unlimited capacity; reliable probabilities |
| **Top-k by score** | Call the k highest scores | Fixed daily capacity, e.g. 1,000 calls a day |
| **Budgeted threshold** | Highest threshold that still uses the full budget | Capacity *and* economics |
| **Segmented thresholds** | Different cut-offs for different groups | Different cost per channel; fairness constraints |

Notice what the *model* is responsible for in each: producing a good ranking, and (for the first and last) honest probabilities. The *policy* turns that into action. Evaluating the model on accuracy at 0.5 skips both.

### Takeaways

1. Check calibration with a reliability diagram and ECE; proper-scoring-rule models (logistic, boosting) usually pass.
2. Repair what fails with Platt scaling first; isotonic can create ties and hurt ranking.
3. Derive the threshold from costs: **p\* = cost / value**, and verify it on held-out data.
4. Never choose the threshold on the test set. Choose it on out-of-fold predictions, then freeze it.
5. Ranking quality (AP) and probability quality (log loss, ECE) are different axes. Look at both.

### So what did we do?

We measured calibration, repaired Naive Bayes, and derived the call threshold from the cost table. Calibrated probabilities make the break-even formula work, and ranking quality and probability quality are separate axes.

### In the next part

That completes the toolkit. [Parts 12](/series/classification/12-head-to-head-leaderboard/)–[14](/series/classification/14-pricing-the-models/) are the payoff: thirteen models, one split, one budget, and all of the above applied to every one of them. [Let's race them.](/series/classification/12-head-to-head-leaderboard/)
