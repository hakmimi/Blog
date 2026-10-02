---
title: "Why This Data Is Harder Than It Looks"
description: "Four traps in one CSV: imbalance, sentinel values, a leaky column that doubles your score, and a dataset that quietly changes over time."
series: "classification"
order: 2
date: 2026-09-30
updated: 2026-10-02
keywords: ["data leakage", "class imbalance", "distribution shift", "feature engineering", "pandas"]
readingTime: "13 min read"
figure: "ch02-duration-leak.png"
---

Most classification tutorials go: load CSV, `train_test_split`, `fit`, print accuracy, celebrate. That workflow works on toy datasets because toy datasets have no traps. Real ones do. This one has four, and each can change which model "wins".

## Goals: what are we trying to achieve?

One column in this file lifts the score from 0.80 to 0.94 AUC. It also does not exist at the moment you have to decide whom to call. Finding that out *before* modelling is the whole point of this chapter.

By the end you will be able to:

- **Spot the four traps** in this CSV: imbalance, disguised missing values, a leaky column, and drift over time.
- **Say what we decide** for each one, and where that decision shows up in later parts.
- **Apply the prediction-moment test** to any column in any dataset.

## The work plan: how do we do it?

We audit the data before we fit anything, one trap at a time, from the quietest to the loudest. Each check gives a number, and each number gives a decision.

| Trap | How we check it | What we need to decide |
|---|---|---|
| Imbalance | Count the classes ([part 1](/series/classification/01-classification-is-a-decision/) gave 88.7% "no") | Split and metrics |
| Missing values in disguise | Look for suspiciously common values: `999`, `"unknown"` | Keep, flag, or recode |
| Target leakage | Same model with and without the suspect column | Keep or drop |
| Drift | Subscription rate across the file, oldest to newest | How to split |

The test we apply to every column is the **prediction moment**: *"At the exact moment the model must output a number, is this value known?"* Here that moment is "before dialling".

## Implementation

### Trap 1: imbalance makes easy metrics lie

We saw in [part 1](/series/classification/01-classification-is-a-decision/) that 88.7% of rows are "no". Every model in this series will be judged against that. The consequence is concrete:

- A model minimising plain error can reach a low loss simply by predicting "no" for nearly everyone.
- Stratified splits become mandatory. A random 20% sample of 41k rows will hold about 928 positives; an unlucky unstratified one can drift.
- Metrics that only look at the majority class (accuracy, specificity) become meaningless. We use **average precision**, **log loss** and **profit** instead ([parts 3](/series/classification/03-what-does-good-performance-mean/) and [14](/series/classification/14-pricing-the-models/)).

Nothing to fix in the data here. It is a property of the world, but it dictates choices everywhere else.

### Trap 2: missing values wearing a disguise

Don't just call `df.isna().sum()`. Pandas says there are zero missing values, which is true and misleading. Instead, audit the values that show up too often:

```python
import pandas as pd

df = pd.read_csv("bank-additional-full.csv", sep=";")      # same load as part 1
y = (df.pop("y") == "yes").astype(int)

print("pdays == 999 (never contacted before):", f"{(df.pdays == 999).mean():.1%}")
print("rows with an 'unknown' somewhere:", f"{(df == 'unknown').any(axis=1).mean():.1%}")
print("exact duplicate rows:", df.duplicated().sum())
```

```output
pdays == 999 (never contacted before): 96.3%
rows with an 'unknown' somewhere: 26.0%
exact duplicate rows: 12
```

- **`pdays` = 999** is not "999 days since last contact". It is a code meaning *never contacted before*. Fed to a linear model as a number, it creates a giant fake gap between 0–30 days and 999. Trees don't mind (they split on it), but linear models and k-nearest neighbours do.
- **`unknown`** is a category in `job`, `education`, `default`, `housing`, `loan`. A quarter of rows have one. Dropping those rows would throw away 26% of the data *and* bias the sample, because "unknown" customers behave differently. We keep `unknown` as its own level. It is information (the agent didn't record it).
- **12 duplicate rows** out of 41,188 is noise-level. We leave them. Any duplicate straddling a train/test split would leak a little, but at 0.03% it doesn't matter here.

<div class="callout tip">

**Rule of thumb.** Before modelling, list every column where a *specific value* is suspiciously common (`999`, `-1`, `0`, `"unknown"`, `"N/A"`). Decide for each: keep as-is, flag with a boolean, or recode. Write the decision down.

</div>

### Trap 3: the column that answers the question

Now the big one. There is a column called `duration`, the length of the last call in seconds. To see what it is worth, we train the same model on the same split, with and without it:

```python
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def score(frame):
    cat = frame.select_dtypes("object").columns
    prep = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cat)],
                             remainder=StandardScaler())
    model = make_pipeline(prep, LogisticRegression(max_iter=2000))
    Xtr, Xte, ytr, yte = train_test_split(frame, y, test_size=0.2, stratify=y, random_state=42)
    p = model.fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    return round(average_precision_score(yte, p), 3), round(roc_auc_score(yte, p), 3)

print("with duration    (AP, AUC):", score(df))
print("without duration (AP, AUC):", score(df.drop(columns="duration")))
print(df.join(y.rename("y")).groupby("y").duration.median().rename("median call seconds"))
```

```output
with duration    (AP, AUC): (0.636, 0.942)
without duration (AP, AUC): (0.465, 0.801)
y
0    163.5
1    449.0
Name: median call seconds, dtype: float64
```

Once we have the verdict, the fix is one line, and it lives in `common.py` so every later script gets it:

```python
df = df.drop(columns="duration")
```

Leakage analysis is about timing, not column names. Look at `campaign`: it counts contacts *during this campaign*, including the current one. If the current call is the 4th, `campaign` is already 4 before dialling. Fine, so we keep it.

### Trap 4: the dataset moves

The file is sorted by date (May 2008 → November 2010). Slice it into ten chunks of 4,119 rows and look at the subscription rate, and at the interest rate `euribor3m` in the same chunks:

```python
import numpy as np

chunk = np.arange(len(df)) // 4119
print(y.groupby(chunk).mean().round(3).tolist())
print(df.euribor3m.groupby(chunk).mean().round(2).tolist())
```

```output
[0.028, 0.035, 0.042, 0.066, 0.062, 0.055, 0.102, 0.12, 0.157, 0.46]
[4.86, 4.86, 4.94, 4.96, 4.96, 4.84, 3.37, 1.35, 1.26, 0.8]
```

## What did we get? Results

**Leakage.** One column moves the same logistic regression a long way:

| Model | Average precision | ROC-AUC |
|---|---|---|
| With `duration` | 0.636 | 0.942 |
| Without `duration` | 0.465 | 0.801 |

![ROC-AUC and average precision for the same logistic regression with and without the duration column.](/series/classification/figures/ch02-duration-leak.png)
*Figure 1. One column lifts ROC-AUC from 0.80 to 0.94 and average precision from 0.47 to 0.64.*

**Drift.** The subscription rate climbs from 2.8% to 46%, while the interest rate falls from about 4.9% to 0.8%:

![Bars: subscription rate per chunk of 4,119 calls, oldest to newest. Line: mean euribor3m in the same chunks.](/series/classification/figures/ch02-drift.png)
*Figure 2. The last chunk is not the same problem as the first. The rate rises as `euribor3m` falls.*

**Decisions.** What we do about each trap, and where it shows up later:

| Trap | What we do | Where it shows up |
|---|---|---|
| Imbalance | Stratified split, average precision + profit, never accuracy alone | Every chapter |
| Sentinels / unknown | Keep `unknown` as a category; note `pdays=999` | [Parts 5](/series/classification/05-logistic-regression-naive-bayes/), [9](/series/classification/09-other-classification-families/) |
| Leakage (`duration`) | Drop it, always | Everywhere |
| Drift | Random split for algorithm comparison; chronological for deployment realism | [Parts 12](/series/classification/12-head-to-head-leaderboard/) and [16](/series/classification/16-when-time-breaks-the-model/) |

## Analysis and conclusion: what did we learn?

**The jump in score is not a feature-engineering triumph.** A 37% jump in average precision from one column (0.465 → 0.636) is too good. Subscribers talk for a median of 449 seconds, non-subscribers hang up after 164. That is about 2.7 times longer (my own calculation from the printed medians). **You cannot know how long a call will last before you make it.** The column is a *consequence* of the outcome, not a cause. The UCI documentation itself says it "should be discarded if the intention is to have a realistic predictive model".

This is **target leakage**: information that exists in the training table but would not exist at prediction time. The test score is honest, because the split was clean, but the *deployed* model would never see the column. You would promise 0.94 AUC and ship 0.80.

<div class="callout gotcha">

**Gotcha: the prediction moment.** For every feature, ask whether the value is known at the exact moment the model must output a number. Here the decision moment is "before dialling". That rules out `duration`, and anything recorded during or after the call. (If instead you were scoring *completed* calls to prioritise follow-ups, `duration` would be legal. The same column is leakage or signal depending on the decision.)

</div>

**The drift is real, but the cause is not proven.** A chart like Figure 2 shows correlation, not cause. When deposits pay little elsewhere, a bank's term deposit looks better, so part of the climb is the economy. But later rows also contain the months where the bank may have targeted warmer customers. We cannot separate the two from this file alone.

<div class="callout">

**Why this matters later.** If we shuffle the rows and split randomly (what we do for [parts 1](/series/classification/01-classification-is-a-decision/)–[15](/series/classification/15-inside-the-winner/)), the training set contains every era and the test set is "interpolation". If we train on the past and test on the future ([part 16](/series/classification/16-when-time-breaks-the-model/)), models trained on the 3%-era face a 30%+ world. The model ranking can change. We'll do both.

</div>

For the main leaderboard we use a **stratified random split** for one practical reason: it gives a stable, interpretable comparison of *algorithms*. The chronological split answers a different question, *how would this have behaved in production?*, and deserves its own chapter.

### So what did we do?

We found four traps in one CSV and made a decision for each. We keep `unknown` as a category, we judge models by average precision and profit instead of accuracy, we drop `duration` everywhere, and we treat the time drift as its own question. The code for all of it lives in [`common.py`](/series/classification/code/common.py), which every later script imports.

### In the next part

[Part 3](/series/classification/03-what-does-good-performance-mean/) turns to the question we keep dodging: if not accuracy, then *what*?
