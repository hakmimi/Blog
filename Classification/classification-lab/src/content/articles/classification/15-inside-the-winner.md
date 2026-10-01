---
title: "Inside the Winner: What the Model Uses and Who It Misses"
description: "Permutation importance versus built-in importance, why shuffling correlated columns one at a time lies, which feature groups the model can't live without, and the profile of subscribers it never finds."
series: "classification"
order: 15
date: 2026-10-01
keywords: ["feature importance", "permutation importance", "error analysis", "lightgbm", "model interpretation", "correlated features"]
readingTime: "17 min read"
figure: "leaderboard-importance.png"
---

A leaderboard answers "which model?". It doesn't answer the questions you get from the person who has to use it: *What is it looking at? Where does it fail? Would it still work if column X disappeared?* This chapter opens up LightGBM, the nominal winner, and works through those.

The conclusions here are about *this model on this data*. The more important thing is the method, because two of the three standard tools mislead if used carelessly, and we'll see exactly how.

## Retrain the winner

We refit LightGBM with the parameters the leaderboard search selected and confirm we're looking at the same model (AP 0.496):

```python
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
for c in X.select_dtypes("object"):
    X[c] = pd.Categorical(X[c], categories=sorted(X[c].unique()))
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

params = dict(n_estimators=400, learning_rate=0.02, num_leaves=31, min_child_samples=100,
              subsample=0.7, subsample_freq=1, colsample_bytree=0.6, verbose=-1, random_state=42)
model = LGBMClassifier(**params).fit(Xtr, ytr)
base_ap = average_precision_score(yte, model.predict_proba(Xte)[:, 1])
print(f"LightGBM test AP = {base_ap:.3f}")
```

```output
LightGBM test AP = 0.496
```

## Two importance rankings that disagree

**Permutation importance** shuffles one column on the *test* data, breaking its relationship with the target, and measures how much AP drops. A big drop means the model relied on that column. It's model-agnostic and tied to the metric we care about.

```python
imp = permutation_importance(model, Xte, yte, scoring="average_precision", n_repeats=10, random_state=0, n_jobs=1)
perm = pd.Series(imp.importances_mean, index=X.columns).sort_values(ascending=False)
print(perm.head(8).round(4).to_string())
```

```output
pdays           0.0380
nr.employed     0.0303
euribor3m       0.0258
contact         0.0207
month           0.0129
emp.var.rate    0.0117
poutcome        0.0105
day_of_week     0.0104
```

LightGBM also keeps its own tally, **gain importance**: the total loss reduction attributable to splits on each feature during training.

```python
gain = pd.Series(model.booster_.feature_importance("gain"), index=X.columns)
print((gain / gain.sum()).sort_values(ascending=False).head(8).round(3).to_string())
```

```output
euribor3m         0.254
nr.employed       0.218
pdays             0.071
age               0.067
emp.var.rate      0.058
cons.conf.idx     0.053
month             0.052
cons.price.idx    0.041
```

![Permutation importance of the ten most important features for LightGBM, with standard deviations.](/series/classification/figures/leaderboard-importance.png)
*Figure 1. Permutation importance on the test set (5 repeats, from the leaderboard run). Same ordering story as the table above: `pdays`, `nr.employed`, `euribor3m`, `contact` at the top.*

They don't agree:

| Feature | Permutation rank | Gain rank | What happened |
|---|---|---|---|
| `pdays` | **1** (0.038) | 3 (7%) | A single column carrying a lot of *test-time* value |
| `euribor3m` | 3 | **1** (25%) | The model split on it constantly during training |
| `age` | 10 (0.004) | **4** (6.7%) | Many splits, little predictive value |
| `contact` | 4 (0.021) | not in top 8 | Few splits, but decisive ones |

The most striking row is `age`. Gain importance gives it 6.7% of the total, the fourth largest share, but shuffling it at test time costs only 0.004 AP. A continuous feature offers many candidate thresholds, so a tree can find *some* split that reduces training loss; that makes gain-style importance biased toward high-cardinality and continuous features, and it measures training-set usage, not generalisation value. **Permutation importance on held-out data measures what the model needs; gain measures what it used.**

<div class="callout gotcha">

**Gotcha — built-in importances reward noise.** Impurity and gain importances are computed on training data, and a feature that lets the model memorise training noise can look important. Always sanity-check against permutation importance on data the model didn't train on.

</div>

## Why shuffling one correlated column understates

Now the second trap. In part 5 we saw that four macro-economic columns are correlated at 0.5–0.97. If you shuffle `euribor3m` alone, the model still has `emp.var.rate` and `nr.employed` carrying almost the same information. The drop is modest. What happens if we shuffle all the macro columns *together* (same shuffle for each, so the rows stay internally consistent among themselves)?

```python
macro = ["emp.var.rate", "cons.price.idx", "cons.conf.idx", "euribor3m", "nr.employed"]
rng = np.random.default_rng(0); drops = []
for _ in range(10):
    Xs = Xte.copy(); perm_idx = rng.permutation(len(Xs))
    Xs[macro] = Xs[macro].iloc[perm_idx].to_numpy()                 # same shuffle for all macro columns
    drops.append(base_ap - average_precision_score(yte, model.predict_proba(Xs)[:, 1]))
print(f"shuffling all 5 macro columns together: AP drops by {np.mean(drops):.3f}  (sum of their individual drops: {perm[macro].sum():.3f})")
```

```output
shuffling all 5 macro columns together: AP drops by 0.293  (sum of their individual drops: 0.068)
```

Shuffled one at a time, the five columns look worth **0.068 AP in total**. Shuffled as a block they're worth **0.293**, over four times as much. Redundancy hides importance: remove one voice from a chorus and the song hardly changes; remove the chorus and it's silent.

(Careful with the reverse conclusion, though. Shuffling the block creates test rows with *internally consistent macro columns that don't match anything else about the customer*: a world the model never saw. The 0.293 is an upper bound on dependence, not a measurement of what we'd lose. For that, we need to *retrain without the columns*.)

## How much does the model *need* each group? Drop-column retraining

Retraining with a group of columns removed is the cleanest experiment, because the model gets a chance to compensate with what's left:

```python
groups = {"pdays + previous + poutcome": ["pdays", "previous", "poutcome"],
          "macro (5 columns)": macro,
          "contact + month + day_of_week": ["contact", "month", "day_of_week"],
          "customer profile (age, job, marital, education, default, housing, loan)": ["age", "job", "marital", "education", "default", "housing", "loan"]}
for name, cols in groups.items():
    m = LGBMClassifier(**params).fit(Xtr.drop(columns=cols), ytr)
    ap = average_precision_score(yte, m.predict_proba(Xte.drop(columns=cols))[:, 1])
    print(f"  without {name:<72} AP {ap:.3f}  ({ap - base_ap:+.3f})")
```

```output
  without pdays + previous + poutcome                                              AP 0.449  (-0.047)
  without macro (5 columns)                                                        AP 0.449  (-0.048)
  without contact + month + day_of_week                                            AP 0.481  (-0.015)
  without customer profile (age, job, marital, education, default, housing, loan)  AP 0.494  (-0.003)
```

This table is the real story of the dataset:

- **History with the customer** (`pdays`, `previous`, `poutcome`): −0.047. Whether we've talked to them before, and how it went, is worth about 10% of the model's AP.
- **The macro-economy**: −0.048, but note it is *not* −0.293. When the model is retrained without those columns it compensates with other time-correlated signals (`month`, `contact`), losing only 0.048.
- **Contact circumstances** (channel, month, weekday): −0.015.
- **Who the customer is** (age, job, marital status, education, credit default, mortgage, loan): **−0.003**. Removing all seven columns reduces average precision by 0.003, which is well inside the noise.

So: **this model barely knows who it is calling.** Almost all of its predictive power comes from *how and when* we call (history, economy, channel, season). That has practical consequences. The "personalisation" a project might have hoped for is nearly absent, and the model is exposed to whatever drives the economy and the campaign calendar, which is the subject of the next chapter.

## Where does it do well and badly? Calibration by segment

An aggregate ECE of 0.009 could hide a model that's honest on average and wrong for subgroups. We check calibration inside slices: the average predicted probability should match the actual subscription rate.

| Segment | Customers | Actual rate | Mean score | Share we'd call |
|---|---|---|---|---|
| contact = cellular | 5,236 | 14.9% | 14.7% | 27% |
| contact = telephone | 3,002 | 5.0% | 5.1% | 5% |
| poutcome = success | 268 | 66.0% | 62.5% | 99% |
| poutcome = nonexistent | 7,147 | 9.0% | 8.9% | 15% |
| month = may | 2,758 | 6.8% | 6.3% | 10% |
| month = mar | 110 | 53.6% | 51.6% | 100% |
| job = retired | 354 | 24.3% | 27.1% | 53% |
| job = student | 164 | 35.4% | 30.4% | 69% |
| job = unknown | 65 | 6.2% | 11.0% | 22% |

(Selected rows from `leaderboard_segments.csv`, which has every slice; "share we'd call" uses the model's frozen profit threshold.)

The model is well calibrated in the large, high-volume slices: 14.9% vs 14.7% for cellular, 5.0% vs 5.1% for landline. Gaps appear in tiny groups: students are *under*-predicted (35% actual vs 30% scored), the 65 `unknown`-job customers are over-predicted (6% vs 11%). With 65–164 customers each, those deviations are well within sampling noise. We note them and don't act.

## Who do we miss?

The last diagnostic is the most practical: look at the subscribers the model *failed* to flag, and compare them with the ones it nailed. Take the 928 test-set subscribers: 143 score below the median and 448 are in the top decile.

```python
p = model.predict_proba(Xte)[:, 1]
sub = pd.DataFrame({"p": p, "y": yte}, index=Xte.index).join(Xte)
missed = sub[(sub.y == 1) & (sub.p < np.median(p))]
caught = sub[(sub.y == 1) & (sub.p >= np.quantile(p, .9))]
for col in ("contact", "poutcome", "month"):
    print(f"\n{col}: share of missed vs caught subscribers")
    print(pd.concat([missed[col].value_counts(normalize=True).rename("missed"),
                     caught[col].value_counts(normalize=True).rename("caught")], axis=1).round(2).sort_values("missed", ascending=False).head(5).to_string())
```

```output
contact: share of missed vs caught subscribers
           missed  caught
contact                  
telephone    0.58    0.07
cellular     0.42    0.93

poutcome: share of missed vs caught subscribers
             missed  caught
poutcome                   
nonexistent  0.94    0.51
failure      0.06    0.11
success      0.00    0.38

month: share of missed vs caught subscribers
       missed  caught
month                
may      0.43    0.06
jul      0.17    0.06
aug      0.15    0.12
jun      0.14    0.14
nov      0.10    0.10
```

The profile is stark.

- **The model's hits are cellular (93%), many are past successes (38%), and rarely May (6%).**
- **The missed subscribers are mostly landline callers (58%), never previously contacted (94%), disproportionately in May (43%).**

In short, the model finds the customers who *look like* subscribers (previous success, cellular, quiet months) and misses the ones who subscribe despite looking like everyone else: a landline call in May to someone never contacted. Is that a failing? Partly it is the nature of rare events: those customers have a low chance of saying yes, and nothing in the data distinguishes them from the many who say no. Those 143 missed subscribers are the price of not phoning thousands of near-hopeless numbers. At a break-even of 12.5%, rightly ignoring them is the profitable decision.

It does tell us where *new information* would pay off: anything that separates the May landline subscribers (a better channel history, an income proxy, a trigger event) would add recall exactly where the current features are blind. The right next step is a data conversation, not a bigger model.

## Summary: an audit checklist you can reuse

1. **Don't trust built-in importances alone.** Check against permutation importance on held-out data.
2. **Shuffle correlated features as a group**, and *retrain without the group* to see what the model really needs.
3. **Look at calibration by segment**, but weigh each gap by the sample size behind it.
4. **Profile the misses.** The errors tell you which information is missing.
5. **Importance is not causation.** Nothing here says changing the economy or calling on a different day changes anyone's behaviour. It describes what this model uses to predict.

The macro columns and `pdays` dominate, and they have something in common: they're proxies for *time*. [Part 16](/series/classification/16-when-time-breaks-the-model/) asks what happens when the model has to predict a future that doesn't look like the past.
