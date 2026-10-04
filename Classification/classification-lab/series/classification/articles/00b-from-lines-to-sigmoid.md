---
title: "Why a Straight Line Fails: Sigmoids, Probabilities and 400 Apples"
description: "Ordinary linear regression on a yes/no label predicts probabilities of -0.51 and 1.49. We see why, fix it with the sigmoid, fit that by hand in NumPy, and then cut the apple plane into a grid to meet overfitting before any model has a name."
series: "classification"
order: 0.5
label: "0b"
date: 2026-10-04
updated: 2026-10-04
keywords: ["logistic regression", "sigmoid", "log-odds", "bias-variance", "overfitting", "synthetic data"]
readingTime: "10 min read"
---

Draw a straight line through a cloud of 0s and 1s and ask it for a probability. It will happily say 1.49 for one apple and -0.51 for another. Neither is a probability, and the reason says a lot about why classification is its own subject.

This part uses 400 made-up apples, not the bank data, because with made-up data we know the truth and can see every point. Two measurements per apple (redness of the skin and acidity of the juice) and one label: **1 is a green apple, 0 is a red apple**. The data are synthetic, and nothing here is a claim about real fruit.

<div class="callout">

**Goal.** Understand why a straight line is the wrong tool for a yes/no label, what the sigmoid does about it, and how too fine a grid of cells overfits.

**Work plan.** Fit a line to 0/1 labels and watch it break. Replace it with a sigmoid and fit that by hand. Then cut the plane into a grid, count the apples in each cell, and watch what happens to the training and test scores as the cells shrink.

</div>

## The line that returns -0.51 and 1.49

**Implementation.** The apples come from `export_apple_grid.py` (seeded, so they are the same on every run). We fit ordinary least squares to the labels and look at what it predicts for the apples we trained on.

```python
import json
import numpy as np

d = json.load(open("../../artifacts/apple_grid.json"))
X = np.column_stack([d["train"]["x"], d["train"]["y"]])      # redness, acidity
y = np.array(d["train"]["label"])
A = np.column_stack([np.ones(len(X)), X])                  # add the intercept column

beta = np.linalg.lstsq(A, y, rcond=None)[0]
line = A @ beta
print(f"{len(y)} training apples, {y.mean():.0%} green")
print(f"line predicts from {line.min():.2f} to {line.max():.2f}")
print(f"below 0: {(line < 0).sum()} apples, above 1: {(line > 1).sum()} apples")
```

**Result.**

```output
(filled in by the build)
```

**What it means.** Nothing stops a line from leaving the 0-to-1 range, and here it does so for dozens of apples. You could clip the values, but the problem is deeper than the range. Four things go wrong when we treat a 0/1 label as an ordinary number:

- **The target is a probability.** The average of 0/1 labels at a given measurement is the *chance* of green there, so it must stay between 0 and 1. A line does not.
- **The spread is not constant.** For a yes/no outcome with chance `p`, the variance is `p(1-p)`. It is largest at `p = 0.5` (0.25) and shrinks toward the ends (0.09 at `p = 0.1`). Least squares assumes the same spread everywhere.
- **The errors are not bell-shaped.** At any given measurement an apple is either 0 or 1, so the error is one of two values, never a smooth cloud around the line.
- **The relationship is not a line.** Chances rise slowly, then quickly, then slowly again: an S shape, not a ramp.

## The fix: a line in log-odds, bent by a sigmoid

**Implementation.** Keep a straight line but let it live on a different scale. Instead of modelling the probability `p`, model its *log-odds*, `log(p / (1 - p))`, which can be any number. Then convert back with the **sigmoid**, `σ(z) = 1 / (1 + e^-z)`, which turns any number into a value strictly between 0 and 1.

```python
z = np.array([-4, -2, -1, 0, 1, 2, 4])
sigma = 1 / (1 + np.exp(-z))
print("z      ", z)
print("sigma  ", sigma.round(3))
print("slope  ", (sigma * (1 - sigma)).round(3))
```

**Result.**

```output
(filled in by the build)
```

**What it means.** Three properties are worth keeping. At `z = 0` the probability is exactly 0.5, so the *decision boundary at 0.5* is the set of points where the line equals zero. The slope is `σ(1 - σ)`, at most 0.25, and nearly flat for very large or very small `z`: extra evidence matters most near the middle. And log-odds have a plain reading. A probability of 0.8 is odds of 4 to 1; a coefficient `w` means *each extra unit of that measurement multiplies the odds by `e^w`*, which is why the series later talks about **odds ratios**.

**Implementation.** To fit the coefficients we maximise the likelihood of the labels, which has no closed-form answer. Newton-Raphson solves it in a few steps with nothing but NumPy: compute the predicted `p`, build the curvature matrix, and take a step.

```python
w = np.zeros(A.shape[1])
for step in range(25):
    p = 1 / (1 + np.exp(-A @ w))
    H = A.T @ (A * (p * (1 - p))[:, None])              # curvature of the log-likelihood
    w = w + np.linalg.solve(H, A.T @ (y - p))           # Newton step

from sklearn.linear_model import LogisticRegression
lib = LogisticRegression(C=np.inf, solver="newton-cholesky").fit(X, y)
print("by hand  ", w.round(3))
print("library  ", np.r_[lib.intercept_, lib.coef_[0]].round(3))
print("largest difference", np.abs(w - np.r_[lib.intercept_, lib.coef_[0]]).max().round(8))
print("odds multiplier for +0.1 redness / +0.1 acidity:", np.exp(0.1 * w[1:]).round(2))
```

**Result.**

```output
(filled in by the build)
```

**What it means.** The hand-written loop and the library agree to about four decimals. Redder skin lowers the odds of green (a +0.1 step multiplies them by about 0.15), more acid raises them (about 2.4 times). These are conditional associations in made-up data, not laws about apples. Part 4 does this fit again for the bank data and shows what happens when the loop is stopped too early.

## Where the sigmoid comes from

The label of an apple is a coin flip (a *Bernoulli* variable) whose chance depends on the measurements. One tidy way to see the sigmoid is a hidden score: each apple has a latent "greenness", equal to a straight-line part plus random noise, and it is green when that score crosses zero. If the noise follows the *logistic* distribution, the chance of crossing is exactly the sigmoid. If the noise is bell-shaped (Normal), the result is the *probit* model, and the two curves are close.

```python
from scipy.stats import norm

zz = np.linspace(-6, 6, 1201)
gap = np.abs(1 / (1 + np.exp(-zz)) - norm.cdf(zz / 1.702)).max()
print(f"largest difference between the logistic curve and a rescaled normal CDF: {gap:.4f}")
```

**Result.**

```output
(filled in by the build)
```

**What it means.** After rescaling, the two S-curves never differ by more than about one percentage point. So the choice between them is rarely what decides an analysis; the habit of using the sigmoid comes from convenience (clean odds-ratio reading and simple maths), not from nature.

## The other way to draw a boundary: cut the plane into cells

A line is a strong assumption: one boundary, straight. The opposite idea is to assume nothing about the shape. Cut the plane into a grid of equal cells, count the green and red training apples in each cell, and let each cell vote. This is what trees do in a more adaptive way (part 6).

**Try it.** The widget below runs on the same 400 training apples and a separate set of 400 test apples. Slide the number of cuts per axis, tick the box to see the test apples, and compare the grid with the logistic line.

<div class="apple-grid-lab" data-src="/series/classification/artifacts/apple_grid.json"></div>
<script src="/js/apple-grid-lab.js"></script>

**Result.** The same quantities for a few grid sizes, computed in Python from the same data:

@@table:apple_grid_table.csv|cols=cuts,cells,empty,median_per_cell,train_acc,test_acc|where=cuts~1;2;4;6;8;12|fmt=cuts:d;cells:d;empty:d;median_per_cell:.1f;train_acc:.3f;test_acc:.3f|rename=cuts:cuts per axis,empty:empty cells,median_per_cell:median apples per cell,train_acc:train accuracy,test_acc:test accuracy@@

For comparison, the logistic line scores @@j:apple_grid.json|logistic.train_acc|.3f@@ on the training apples and @@j:apple_grid.json|logistic.test_acc|.3f@@ on the test apples.

**What it means.** One cell (no cuts) is just the majority vote, about 56% right. A coarse grid of four cells already reaches about 87% on test apples. As cells shrink, training accuracy creeps up (to 0.91) while test accuracy goes nowhere and wobbles. Three things change as the grid gets finer: there are fewer apples per cell, so each vote rests on fewer apples; more cells are empty, so the grid has nothing to say there; and the training score can only improve, because a finer grid can always memorise a bit more. This is the **bias and variance trade-off** you can see: a coarse grid is too rigid (bias), a fine one chases chance (variance).

**A caution about the sizes.** With 400 test apples, one accuracy has a standard error of about 1.7 points, so the wobble between neighbouring grid sizes is noise. The honest reading is the trend: training accuracy rises, test accuracy does not, and the gap opens. The logistic line, with three numbers, matches the best grids. That is not a general victory for lines. These apples were made with a straight boundary, so a line should do well here.

## Analysis and conclusion

A linear model on a 0/1 label can predict "probabilities" outside 0 to 1, assumes a constant spread that cannot hold, and has the wrong shape. A line in log-odds, bent by a sigmoid, fixes the range and the shape, has a clean reading through odds ratios, and can be fitted by hand with Newton-Raphson. A grid needs no shape assumption, but the cost is data: cells that are too small are empty or noisy, and the training score then flatters the model.

That tension, *a rigid model that may miss structure against a flexible one that may chase noise*, runs through the whole series. It returns in part 5 (the linear baseline), part 6 (trees that grow until they memorise), parts 7 and 8 (averaging and boosting as two ways to tame that flexibility), and part 10 (how to choose settings without fooling yourself). Continue with [Part 1](/series/classification/01-classification-is-a-decision/), where we meet the real data and the rules every comparison follows.
