---
title: "What the Model Is Actually Minimising"
description: "Log loss, Brier score, hinge, exponential and focal losses. We fit logistic regression by hand until it matches the library, find out why our first attempt did not, and see which differences between objectives survive convergence."
series: "classification"
order: 4
date: 2026-09-30
updated: 2026-10-04
keywords: ["loss functions", "log loss", "brier score", "gradient descent", "class weights", "numpy"]
readingTime: "11 min read"
figure: "loss-and-impurity.png"
---

Fit logistic regression by hand with 1,500 steps of gradient descent and compare it with scikit-learn on the same model and data. The predicted probabilities differ by up to @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|max_abs_prob_diff_vs_reference|.2f@@ for a single record. Which one is wrong? Neither, quite, and finding out why is the quickest way to understand what `fit()` does.

<div class="callout">

**Goal.** Understand what a classifier minimises, and which differences between objectives are real once each has converged.

**Work plan.** Compute two losses by hand. Write logistic regression in NumPy, measure the gap to the library and close it. Fit six objectives to convergence with the same weak penalty and compare rankings, probabilities and decisions. Summarise the objectives in one table.

</div>

## Two losses on four records

A loss turns each (prediction, outcome) pair into a penalty, and `fit()` finds parameters that make the average penalty small.

```python
import numpy as np

y_true = np.array([1, 1, 0, 0])
p = np.array([0.9, 0.2, 0.1, 0.6])
log_loss = -(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))
brier = (p - y_true) ** 2
print("log loss per record:", log_loss.round(3))
print("Brier per record   :", brier.round(3))
for wrong in (0.6, 0.9, 0.99):
    print(f"true=0, predicted {wrong}: log loss {-np.log(1 - wrong):.2f}, Brier {wrong ** 2:.2f}")
```

```output
(filled in by the build)
```

Do not compare the sizes of the two columns, because the units differ. Compare their shapes: log loss keeps growing as a wrong prediction becomes more confident (0.92, 2.30, 4.61), while Brier saturates at 1. Log loss is the negative log-likelihood of a Bernoulli model, so minimising it is maximum likelihood. Both are *proper scoring rules*: in expectation they are minimised by the true probability. That is a property of the loss, not a guarantee that a finished, restricted, regularised model is calibrated (part 11).

## Logistic regression by hand, and a puzzle

The gradient of the mean log loss is `Xᵀ(p − y) / n`, so gradient descent is a short loop. The design matrix is the full one-hot encoding plus an intercept, on 80% of the development rows. The other 20% is an inner validation set; the comparison split is not touched.

<details>
<summary>Setup code</summary>

```python
import pandas as pd
from scipy.optimize import minimize
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
tr, va = train_test_split(dev, test_size=0.2, stratify=y[dev], random_state=42)
cat = [c for c in X.columns if X[c].dtype == object]
prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder=StandardScaler())
A = np.c_[np.ones(len(tr)), prep.fit_transform(X.iloc[tr])]          # intercept + features
B = np.c_[np.ones(len(va)), prep.transform(X.iloc[va])]
ytr, yva = y[tr], y[va]
sigmoid = lambda z: 1 / (1 + np.exp(-np.clip(z, -35, 35)))
```

</details>

```python
def grad(w):                                                         # gradient of the mean log loss
    return A.T @ (sigmoid(A @ w) - ytr) / len(ytr)

def descend(steps, lr=0.5):
    w = np.zeros(A.shape[1])
    for _ in range(steps):
        w -= lr * grad(w)
    return w

ref = LogisticRegression(penalty=None, max_iter=20000, tol=1e-10).fit(A[:, 1:], ytr)
p_ref = sigmoid(B @ np.r_[ref.intercept_, ref.coef_[0]])

print(f"design matrix: {A.shape[1]} columns, rank {np.linalg.matrix_rank(A)}")
for steps in (1500, 20000):
    w = descend(steps)
    print(f"{steps:>6} steps: largest gradient entry {np.abs(grad(w)).max():.1e}, "
          f"largest probability difference from scikit-learn {np.abs(sigmoid(B @ w) - p_ref).max():.3f}")
```

```output
(filled in by the build)
```

The design matrix has **@@j:objectives_notes.json|rank_deficiency|d@@ more columns than its rank**, because each variable's one-hot columns add up to the intercept column. That could explain different *coefficients*, but not different *predictions* for records built the same way. The second observation does: after 1,500 steps the gradient is not zero. The fit has not converged, and more steps shrink the disagreement. The hardest direction is a rare level: `default = yes` occurs in 3 of 41,188 records, all "no", so an unpenalised fit keeps pushing its coefficient down (near -8 in the library's solution, near 0 after 1,500 steps). A quasi-Newton optimiser finishes the job:

```python
def loss_and_grad(w):
    z = A @ w
    return np.mean(np.logaddexp(0, -(2 * ytr - 1) * z)), grad(w)

res = minimize(loss_and_grad, np.zeros(A.shape[1]), jac=True, method="L-BFGS-B",
               options={"maxiter": 5000, "ftol": 1e-14, "gtol": 1e-9})
print(f"L-BFGS: largest gradient entry {np.abs(grad(res.x)).max():.1e}, "
      f"largest probability difference from scikit-learn {np.abs(sigmoid(B @ res.x) - p_ref).max():.1e}")
```

```output
(filled in by the build)
```

Converged fits agree to about 1e-5, whatever the rank deficiency. The hand-written model was fine; our stopping rule was not. **Check the gradient, not only the loss**: a loss that stopped moving is not evidence of a minimum. This is also why real logistic regression defaults to an L2 penalty, which gives the problem a unique, well-conditioned answer.

## Six objectives, each fitted to convergence

Each objective below is fitted with the same L-BFGS routine, the same weak L2 penalty (so every problem has a unique answer) and a gradient tolerance, on the same 26,360 training records, and scored on the same 6,590 validation records. Hinge and exponential losses give margins, so their probability columns come from a one-parameter sigmoid fitted on the training scores. The "weighted" fit counts each positive @@j:objectives_notes.json|weight_vs_intercept_shift.weight|.1f@@ times as much, as `class_weight="balanced"` does.

@@table:objectives_comparison.csv|cols=loss,validation_ap,spearman_with_log_loss_scores,top10pct_overlap_with_log_loss,mean_probability,records_flagged_at_0.5,records_flagged_at_break_even,contribution_at_break_even|fmt=validation_ap:.3f;spearman_with_log_loss_scores:.3f;top10pct_overlap_with_log_loss:.2f;mean_probability:.3f;records_flagged_at_0.5:d;records_flagged_at_break_even:d;contribution_at_break_even:d|rename=validation_ap:AP,spearman_with_log_loss_scores:rank agreement with log loss,top10pct_overlap_with_log_loss:top-10% overlap,mean_probability:mean probability,records_flagged_at_0.5:flagged at 0.5,records_flagged_at_break_even:flagged at 1/8,contribution_at_break_even:contribution at 1/8@@

*@@j:objectives_notes.json|validation_prevalence|.1%@@ of validation records subscribe. All six fits converged (largest gradient entry below 2e-7). Contribution uses the illustrative price list and is a retrospective simulation.*

- **Ranking.** For this linear model on these features the objectives order records very similarly: AP between @@v:objectives_comparison.csv|loss=brier (on sigmoid)|validation_ap|.3f@@ and @@v:objectives_comparison.csv|loss=exponential|validation_ap|.3f@@, rank agreement with log loss at least @@v:objectives_comparison.csv|loss=squared hinge|spearman_with_log_loss_scores|.2f@@. That is an observation about this experiment: a linear hypothesis class can produce many rankings, and another loss could pick a different one with other data or more noise.
- **Probabilities.** The weighted and focal fits report a mean probability of @@v:objectives_comparison.csv|loss=weighted log|mean_probability|.2f@@ and @@v:objectives_comparison.csv|loss=focal|mean_probability|.2f@@ when @@j:objectives_notes.json|validation_prevalence|.1%@@ subscribe. They were told to care more about positives and report probabilities for that modified world: good rankers, poor probability estimates.
- **Decisions.** A threshold of 1/8 is meaningful only for probabilities. Applied to those two outputs it selects all 6,590 records, which is "call everyone" (contribution @@v:objectives_comparison.csv|loss=weighted log|contribution_at_break_even|d@@). The loss changed what the numbers *mean*, not the order.

Does weighting equal shifting the threshold? For a correctly specified, unpenalised model it can. With a penalty and a finite sample it does not exactly: the weighted model's probabilities differ from "log-loss solution plus log-weight on the intercept" by up to @@j:objectives_notes.json|weight_vs_intercept_shift.max_abs_prob_diff_weighted_vs_shifted_intercept|.2f@@ for one record (rank agreement @@j:objectives_notes.json|weight_vs_intercept_shift.spearman_weighted_vs_log|.3f@@). If you need probabilities, train with natural weights and choose the threshold afterwards. Brier on a sigmoid is not convex, so the table keeps the better of two starts (zero and the log-loss solution); both converged.

## A decision map for the common objectives

| Loss | Form (margin *m* = y·f(x), y in {-1, +1}, or probability) | Output | Typical models | Use it when | Noisy labels | Calibration | Trade-off |
|---|---|---|---|---|---|---|---|
| Log loss | -[y log p + (1-y) log(1-p)] | Probability | Logistic regression, boosting, neural nets | You need probabilities | Confident mistakes cost without bound | Proper rule; the fitted model still needs checking | Smooth, convex for linear models |
| Brier | (p - y)² | Probability | Any probabilistic model; also a score | A bounded penalty on probabilities | More tolerant (bounded) | Proper rule | Weak gradient when confidently wrong; non-convex on a sigmoid |
| Hinge / squared hinge | max(0, 1 - m) / its square | Margin | Linear and kernel SVMs | Large-margin ranking | Moderate | Needs Platt or isotonic scaling | Only records near the boundary matter |
| Exponential | exp(-m) | Margin | AdaBoost | Boosting with exact weight updates | Very sensitive | Not a probability | Fast, fragile with label noise |
| Focal / weighted | (1-p_t)^γ · log loss, or class-weighted log loss | Re-weighted probability | Imbalanced detection, neural nets | Rare positives, hard examples | Depends on γ and weights | Distorts probabilities on purpose | Better emphasis, worse calibration |

The map describes usual behaviour; a particular dataset, penalty or optimiser can differ. Not every classifier minimises a loss by iteration: logistic regression minimises penalised log loss; a linear SVM, hinge plus L2; trees choose splits greedily to reduce impurity; boosting adds trees in the direction that reduces a loss; Naive Bayes estimates priors and densities by maximum likelihood under an independence assumption (counting, no iteration); k-NN stores the data; a neural network minimises log loss by non-convex stochastic gradient methods.

## Analysis and conclusion: what we learned

- **Check convergence directly.** Our 1,500-step fit left a gradient of about @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|grad_inf_norm|.0e@@ and probabilities up to @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|max_abs_prob_diff_vs_reference|.2f@@ off. Converged fits agree to 1e-5.
- **Rank deficiency changes coefficients, not predictions**, but makes unpenalised fitting slow and fragile, which is why a small penalty is the default.
- **Objectives differ more in what the numbers mean than in how they order records** here. Do not generalise that beyond this model and these features.
- **Match threshold and output.** The break-even rule is for probabilities, and re-weighted losses do not provide them.

*Further reading.* Gneiting and Raftery (2007), [Strictly proper scoring rules, prediction, and estimation](https://doi.org/10.1198/016214506000001437); Lin et al. (2017), [Focal loss for dense object detection](https://doi.org/10.1109/ICCV.2017.324).

[Part 5](/series/classification/05-logistic-regression-naive-bayes/) uses the library versions of these models and learns to read what a linear model has learned.
