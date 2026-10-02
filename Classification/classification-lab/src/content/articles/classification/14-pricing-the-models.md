---
title: "Pricing the Models: Profit, Thresholds and Call-Centre Capacity"
description: "Take the same thirteen models and put them in a spreadsheet: expected profit under three decision policies, a call-capacity curve, and a bootstrap that asks whether the money ranking is any more real than the AP ranking."
series: "classification"
order: 14
date: 2026-10-01
updated: 2026-10-02
keywords: ["expected profit", "cost-sensitive", "threshold selection", "cumulative gains", "business metrics", "model evaluation"]
readingTime: "16 min read"
figure: "leaderboard-profit.png"
---

Average precision tells us which model ranks best. It doesn't tell us what we should *do*, or what it's worth. In [part 11](/series/classification/11-probabilities-calibration-thresholds-costs/) we derived the call-or-don't rule from a cost table. Here we apply it to every model in the leaderboard and ask the question a manager would ask: **how much money, and how sure are we?**

The economics are the same assumptions as [part 11](/series/classification/11-probabilities-calibration-thresholds-costs/), now kept in `common.py`:

- A call costs **1** unit.
- A subscription is worth **8** units.
- So a customer is worth calling when the probability of subscribing exceeds `1/8 = 0.125`.

A baseline to beat: calling *everyone* loses **814** units on the test set. Blind outreach destroys value, so *all* of the profit below is created by the models' ability to avoid bad calls.

## Goals: what are we trying to achieve?

Average precision says which model ranks best. It does not say what to do, or what it is worth. Our goal is to put a price on every model and to see how much the model choice really matters.

By the end you will be able to:

- **Compare three threshold policies** (0.5, break-even 1/8, and out-of-fold) in profit.
- **Read a capacity curve** when a call centre can only phone the top k.
- **Test whether a profit gap is real**, and check how fragile the economics are.

## The work plan: how do we do it?

The economics are the assumptions from [Part 11](/series/classification/11-probabilities-calibration-thresholds-costs/): a call costs 1, a subscription is worth 8, so the break-even probability is 1/8. We apply them in four steps:

1. **Three policies, thirteen models**: profit at t=0.5, t=1/8 and an out-of-fold threshold frozen before the test set.
2. **Try it**: drag the threshold yourself for every model.
3. **Capacity**: profit when only the top k customers can be called.
4. **Is it real?**: a paired bootstrap on profit, and a sensitivity check on the value of a subscription.

## Implementation

### Three policies, thirteen models

For each model we compare three ways of choosing who to call:

- **t = 0.5**: the default threshold most tutorials use.
- **t = 1/8**: the textbook break-even threshold, applied to the model's raw probabilities.
- **t = OOF**: a threshold chosen on **out-of-fold predictions from the training set only**, maximising profit there, then frozen before looking at the test set. (This is what `run_leaderboard.py` does; no test data is involved in choosing it.)

```python
COST, VALUE = 1.0, 8.0
pred = pd.read_csv("artifacts/leaderboard_predictions.csv")        # saved by run_leaderboard.py
board = pd.read_csv("artifacts/leaderboard.csv").set_index("model")
y = pred["y"].to_numpy()

def profit(p, t, value=VALUE):
    call = p >= t
    return value * y[call].sum() - COST * call.sum()

print(f"{'model':<30}{'t=0.5':>8}{'t=1/8':>8}{'t=OOF':>8}   {'calls':>6}{'hit rate':>9}")
for m in models:                                                   # sorted by AP
    p = pred[m].to_numpy(); t = board.loc[m, "profit_threshold"]; call = p >= t
    print(f"{m:<30}{profit(p, .5):8.0f}{profit(p, 1 / VALUE):8.0f}{profit(p, t):8.0f}   {call.sum():6d}{y[call].mean():9.2f}")
print("call everyone:", profit(np.ones(len(y)), .5))
```

```output
model                            t=0.5   t=1/8   t=OOF    calls hit rate
LightGBM                          1666    3352    3341     1587     0.39
sklearn HistGradientBoosting      1602    3366    3323     1645     0.38
Random forest                     1628    3314    3343     1489     0.41
XGBoost                           1530    3350    3377     1407     0.43
CatBoost                          1633    3320    3299     1621     0.38
Extra trees                       1535    3262    3291     1413     0.42
Small neural net (MLP)            1394    3261    3251     1333     0.43
Decision tree                     1557    3143    3272     1344     0.43
Logistic regression               1356    3187    3178     1510     0.39
Linear SVM (calibrated)           1331    3235    3230     1394     0.41
k-nearest neighbors               1287    3208    3184     1368     0.42
Gaussian Naive Bayes              2510    3033    3040     1720     0.35
call everyone: -814.0
```

The first insight is the biggest one:

**The threshold matters more than the model.** Going from the default t=0.5 to a cost-aware threshold roughly **doubles profit for every real model** (LightGBM: 1,666 → 3,352; Naive Bayes is the odd one out, see below). At t=0.5, a model only calls customers it believes are *more likely than not* to subscribe, and with an 11% base rate that's a tiny, highly selective group, leaving thousands of profitable calls unmade. The gap between the best and worst real model at the right threshold (3,377 − 3,178 ≈ 200 units) is a tenth of the gap between the right and wrong threshold for the *same* model (≈1,700).

### What if you can only call k people?

Most call centres don't have a threshold; they have a headcount. If capacity limits you to the top *k* customers by score, the same models produce this:

```python
for k in (200, 500, 1000, 1500, 2500):
    row = f"{k:>6}"
    for m in ["LightGBM", "XGBoost", "Logistic regression", "Gaussian Naive Bayes"]:
        top = np.argsort(-pred[m].to_numpy())[:k]
        row += f"{VALUE * y[top].sum() - COST * k:14.0f}"
    print(row)
```

```output
     k      LightGBM       XGBoost  Logistic reg  Gaussian Nai
   200           992           992           992           976
   500          2028          1988          1868          1580
  1000          3120          3096          2872          2256
  1500          3356          3332          3188          2932
  2500          2980          3068          2892          2828
```

Where models differ depends on where you cut:

- **At k = 200 nothing separates them.** All four reach 992 (or 976): the top 200 customers are obvious (typically past successes in the low-rate months), and any reasonable model finds them. A narrow call budget makes model choice irrelevant.
- **In the middle (k = 500–1,500) the boosters pull ahead:** at k = 1,000 LightGBM earns 3,120 vs 2,872 for logistic regression: **+8.6%**. That's the regime where the extra AP shows up in real money.
- **Past the break-even point, everybody declines.** At k = 2,500, LightGBM *loses* money relative to k = 1,500 (2,980 vs 3,356), because we're now calling customers whose chance is below 12.5%. More capacity isn't better.
- **Naive Bayes is clearly worse in the middle** (k = 500: 1,580 vs 2,028). Its ranking, not just its probabilities, is poorer, which AP already told us.

### Is the money ranking real? Another bootstrap

The profit differences between the top models look small (3,341 vs 3,377). We should apply the same discipline as in [part 13](/series/classification/13-is-the-winner-real/). Each customer contributes `8·y − 1` if called and 0 if not, so a model's profit is a *sum* we can bootstrap, paired across models:

```python
rng = np.random.default_rng(1)
boots = rng.integers(0, len(y), size=(1000, len(y)))
def boot_profit(m):
    p = pred[m].to_numpy(); t = board.loc[m, "profit_threshold"]
    gain = np.where(p >= t, VALUE * y - COST, 0.0)                   # each customer's contribution
    return gain[boots].sum(axis=1)

ref = boot_profit("XGBoost")
for m in ["LightGBM", "Random forest", "CatBoost", "Logistic regression", "Gaussian Naive Bayes"]:
    d = boot_profit(m) - ref; lo, hi = np.quantile(d, [.025, .975])
    print(f"{m:<26}{d.mean():+8.0f}   [{lo:+6.0f}, {hi:+6.0f}]")
```

```output
LightGBM                       -35   [   -99,    +35]
Random forest                  -32   [  -111,    +51]
CatBoost                       -76   [  -138,     -9]
Logistic regression           -200   [  -264,   -133]
Gaussian Naive Bayes          -336   [  -445,   -217]
```

XGBoost had the highest profit on this split, but the table says:

- **LightGBM and the random forest are indistinguishable from XGBoost** (intervals straddle zero). "XGBoost wins on profit" is no more defensible than "LightGBM wins on AP".
- **CatBoost is slightly behind** (−76, interval just excludes zero).
- **Logistic regression leaves about 200 units on the table (6%)**, and that difference is solid: [−264, −133].

In other words the profit ranking tells the *same story* as AP: a top cluster that's tied, a clear but modest gap to the linear baseline, and a clear gap to Naive Bayes. Two metrics with different foundations agreeing is reassuring.

### How fragile are the economics?

All of this rests on "a subscription is worth 8 calls". What if that's wrong? The decision threshold moves with it (`1/value`), and so do calls and profit:

```python
for m in ["LightGBM", "Logistic regression", "Gaussian Naive Bayes"]:
    p = pred[m].to_numpy()
    print(f"{m:<24}" + "".join(f"  value={v:>2}: {profit(p, 1 / v, v):7.0f} ({(p >= 1 / v).sum():5d} calls)" for v in (4, 8, 16)))
```

```output
LightGBM                  value= 4:    1075 ( 1057 calls)  value= 8:    3352 ( 1480 calls)  value=16:    8429 ( 3315 calls)
Logistic regression       value= 4:     928 (  960 calls)  value= 8:    3187 ( 1557 calls)  value=16:    8212 ( 3724 calls)
Gaussian Naive Bayes      value= 4:     707 ( 1537 calls)  value= 8:    3033 ( 1759 calls)  value=16:    7981 ( 2067 calls)
```

Profit scales with the value of a success, from ~1,000 to ~8,400 for LightGBM; that's the assumption doing the work, not the model. The *ranking* of the models stays the same at all three values, and so does the lesson: the cheaper a call is relative to a win, the more of the list you should phone (1,057 → 3,315 calls), and the more the choice of threshold matters.

## What did we get? Results

Calling everyone loses 814 units on the test set, so all of the profit below comes from the models avoiding bad calls.

- **Default threshold 0.5 against a cost-aware threshold:** profit roughly doubles for every real model (LightGBM 1,666 to 3,352).
- **Best against worst real model at the right threshold:** about 200 units (3,377 against 3,178), a tenth of the gap between the right and the wrong threshold for the same model (about 1,700).
- **Capacity:** at k = 1,000, LightGBM earns 3,120 against 2,872 for logistic regression (+8.6%). At k = 200 nothing separates the models.
- **Paired profit bootstrap against XGBoost:** LightGBM −35 [−99, +35], Random forest −32 [−111, +51], CatBoost −76 [−138, −9], Logistic regression −200 [−264, −133].

### Try it: drag the threshold

Everything above is one slider position per model. Here is the whole slider. Pick a model, move the threshold, and watch the confusion matrix, the ROC and precision-recall points, and the profit curve respond. The dashed gold line on the profit chart is the break-even threshold `1/value`; the gold dot is the best threshold on this test set. Change what a subscription is worth and see the break-even line move.

<div class="threshold-lab" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

Things to try: slide to 0.5 and watch recall collapse; slide to 0.02 and watch the profit curve go negative as you call nearly everyone; switch to Gaussian Naive Bayes and see how differently its histogram is spread.

A few other things to read in that table:

- **The two principled thresholds agree.** t=1/8 on raw probabilities and t=OOF land within about 1–4% of each other for the well-calibrated models. Both are sound; the OOF one needs no calibration assumption and is what you'd use when probabilities are questionable.
- **Naive Bayes is the exception that proves the rule.** At t=0.5 it earns 2,510, *by far* the best of the t=0.5 column, because its over-confident probabilities spill above 0.5 for many more customers than the honest models do. It's right for the wrong reason: the threshold happens to be compensating for miscalibration. Once everyone gets a proper threshold, it's back at the bottom (3,040).
- **The hit rate at the optimum is 35–43%.** At the best operating point, 60% of calls fail, and that is still the profit-maximising behaviour, because a success is worth eight failures. A model that insisted on 70% precision would be "more accurate" and earn much less.

![Test profit for each model at its out-of-fold-chosen threshold.](/series/classification/figures/leaderboard-profit.png)
*Figure 1. Profit per model at its frozen, training-derived threshold. The spread between the best and the worst serious model is under 10%.*

![Cumulative gains: the share of all subscribers reached against the share of customers called, for four models.](/series/classification/figures/leaderboard-gains.png)
*Figure 2. Cumulative gains. Calling the top 20% of the list by LightGBM score reaches about two thirds of the subscribers.*

## Analysis and conclusion: what did we learn?

- **The threshold matters more than the model.** It is worth about 100% of the profit, the model choice inside the top cluster about 3%.
- **The profit ranking tells the same story as AP.** A tied top cluster, a modest but solid gap to the linear baseline, and a clear gap to Naive Bayes.
- **Naive Bayes looks best at t=0.5 for the wrong reason.** Its over-confidence happens to compensate for the wrong threshold. With a proper threshold it is last again.
- **The assumptions do the work.** Profit scales with the value of a success (about 1,000 to 8,400 for LightGBM across values 4 to 16), but the ranking of the models stays the same.

### The decision-maker's summary

1. **Choose the threshold from the economics and verify on out-of-fold data.** It's worth ~100% of profit compared with the default 0.5; the model choice in the top cluster is worth about 3%.
2. **The "best" model changes with the metric** (LightGBM by AP, XGBoost by profit), but within the top tier none of those differences are statistically reliable. Pick on cost, speed and simplicity.
3. **Logistic regression is a respectable fallback**: ~94% of the best profit with 3 µs scoring and a model you can explain to a regulator. Whether the last 6% justifies a boosting pipeline depends on the number of customers: at 8,238 customers it's 200 units; at ten million it's a budget line.
4. **Capacity changes everything.** With a tiny call budget, a simple rule works; the gap opens at medium capacity.

### So what did we do?

We priced every model. The threshold is worth far more than the choice of model, logistic regression keeps about 94% of the best profit, and capacity changes which model wins. All of this holds only while the base rate stays where it was, which is the subject of the last part.

### In the next part

[Part 15](/series/classification/15-inside-the-winner/) opens the winning model and asks what it uses and where it fails.
