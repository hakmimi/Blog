---
title: "Classification Is a Decision, Not a Score"
description: "We open a real bank-marketing dataset, find out how little an 'accurate' model can do, and set the rules for the next fifteen parts."
series: "classification"
order: 1
date: 2026-09-30
updated: 2026-10-01
keywords: ["classification", "machine learning", "baseline", "bank marketing", "pandas"]
readingTime: "11 min read"
figure: "ch01-segments.png"
---

A Portuguese bank phoned 41,188 customers and offered each a term deposit. About one in nine said yes. Somebody now has to decide **whom to call next quarter**, because every call costs an agent's time and most of them go nowhere.

That sentence is the whole problem, and it is worth reading twice, because it contains no algorithm. It contains a *decision* (call or don't), a *cost* (agent time), and a *scarce resource* (only so many calls fit in a day). A classifier is just the machine that turns customer details into a number we can use to make that decision.

This series takes that one problem and runs it through every mainstream classifier — logistic regression, trees, random forests, XGBoost, LightGBM, CatBoost and more — using the same data, the same split and the same tuning budget. Along the way we will break things on purpose, because that is where the learning is. All code is in the repository and every number you see was printed by it.

By the end of the series there will be a leaderboard. But you cannot read a leaderboard until you understand what it is measuring, so we start with the boring part: looking at the data.

## Load it and look

Download `bank-additional-full.csv` from the [UCI repository](https://doi.org/10.24432/C5K306) (the series' `download_data.py` does this and verifies a checksum). Then:

```python
import pandas as pd

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)          # 1 = the customer subscribed
print(df.shape)
print(f"{y.mean():.1%} of calls ended in a subscription")
```

```output
(41188, 20)
11.3% of calls ended in a subscription
```

Twenty input columns: customer facts (`age`, `job`, `education`), campaign facts (`contact`, `month`, `campaign` = how many times we've called this person), history (`poutcome` = what happened last time) and a handful of macro-economic indicators (`euribor3m`, `emp.var.rate`…) that describe the economy on the day of the call.

Two things to notice immediately. The target is **imbalanced** — 11.3% positives. And the raw data is already telling us something, before any model touches it:

```python
for col in ["contact", "poutcome"]:
    rate = y.groupby(df[col]).agg(["mean", "size"]).round(3)
    print(rate, end="\n\n")
```

```output
            mean   size
contact                
cellular   0.147  26144
telephone  0.052  15044

              mean   size
poutcome                 
failure      0.142   4252
nonexistent  0.088  35563
success      0.651   1373
```

Customers reached on a mobile phone subscribe almost three times as often as those on a landline. People who said yes to a *previous* campaign say yes again 65% of the time. That is a huge spread — and a hint that even simple models will find real signal here.

![Subscription rate by contact channel, previous outcome and month. The dashed line is the 11.3% average.](/series/classification/figures/ch01-segments.png)
*Figure 1. Raw subscription rates by segment. Note the months: March, September, October and December convert at 45–50%, but they are also the months with the fewest calls. We will meet that again in part 2.*

## The first baseline: say no to everyone

Before building anything, compute what a model that does nothing clever would score. It is the most valuable line of code in the project:

```python
print(f"accuracy of always saying no: {(y == 0).mean():.3f}")
```

```output
accuracy of always saying no: 0.887
```

**88.7% accuracy from a model that has never looked at a customer.** It also finds exactly zero subscribers. If someone shows you a classifier with 90% accuracy on this data, they have built a model that is 1.3 points better than a rock — and possibly worse at the only thing you care about.

<div class="callout gotcha">

**Gotcha — accuracy on imbalanced data.** Accuracy counts every correct answer equally. When 89% of rows are negatives, the score is dominated by the easy class. We will replace it with metrics that look at the positives in part 3.

</div>

## The second baseline: a rule a human could write

Now a slightly smarter baseline, one you could explain in a meeting: *"only call people who said yes last time."*

```python
rule = (df["poutcome"] == "success")
tp = int((rule & (y == 1)).sum())
print(f"rule calls {rule.sum()} people, {tp} subscribe -> precision {tp / rule.sum():.2f}, recall {tp / y.sum():.2f}")
```

```output
rule calls 1373 people, 894 subscribe -> precision 0.65, recall 0.19
```

This one-line rule is a real classifier, and its numbers already show the central tension of the whole series:

- **Precision 0.65** — two out of three calls succeed. Excellent.
- **Recall 0.19** — but we only reach 19% of everyone who would have subscribed. We leave 81% of the opportunity on the table.

You can make a rule more precise by making it stricter (only call people who said yes *and* are retired…) but each restriction lowers recall. You can raise recall by calling more people, but precision falls. **There is no model that maximises both.** Choosing where to sit on that curve is a business decision, not a statistical one — and it is why this series keeps saying "classification is a decision".

## What we are going to build

Here is the plan for the remaining parts, so you know where each experiment fits.

| Part | Question |
|---|---|
| 2 | What makes this data hard? (imbalance, leakage, time) |
| 3–4 | How do we measure a classifier, and what is it optimising? |
| 5–9 | What does each model family do — and how does it behave on *this* data? |
| 10–11 | How do we tune fairly, and turn scores into calibrated probabilities and thresholds? |
| **12–14** | **Head-to-head: thirteen models, one split — who wins, is it real, and what is it worth in money?** |
| 15–16 | Inside the winner, and what happens when time breaks it. |

The rules of engagement, which we will keep every time we compare models:

1. **Same rows.** One stratified 80/20 split, fixed seed, test set touched once.
2. **Same features.** Everything known *before the call starts*.
3. **Same budget.** Every model gets the same number of tuning candidates and the same cross-validation folds.
4. **Report uncertainty.** A difference of 0.004 in a metric is not a result until we check it survives a different split.

<div class="callout tip">

**Try it yourself.** Clone the repository, run `python series/classification/scripts/download_data.py`, then copy any snippet from this series into a notebook. Every snippet starts from the `df`/`y` you loaded above. If a number in the text doesn't match your output, that is a bug — please open an issue.

</div>

In [part 2](/series/classification/02-why-classification-is-hard/) we find out why the obvious modelling attempt on this data gives a beautiful, useless answer.
