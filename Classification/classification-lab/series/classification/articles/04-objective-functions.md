---
title: "What the Model Is Actually Minimising"
description: "Log loss, Brier score, hinge, exponential and focal losses. We fit logistic regression by hand until it matches the library, find out why our first attempt did not, and see which differences between objectives survive convergence."
series: "classification"
order: 4
date: 2026-09-30
updated: 2026-10-04
keywords: ["loss functions", "log loss", "brier score", "gradient descent", "class weights", "numpy"]
readingTime: "13 min read"
figure: "loss-and-impurity.png"
---

Fit logistic regression by hand with 1,500 steps of gradient descent and compare it with scikit-learn's answer for the same model and data. The predicted probabilities disagree by up to @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|max_abs_prob_diff_vs_reference|.2f@@ for a single record. Which one is wrong? Neither, quite, and finding out why is the quickest way to understand what `fit()` does.

<div class="callout">

**Goal.** Understand what a classifier minimises, and which of the differences between objectives are real once each one has actually converged.

**Work plan.** Compute two losses by hand. Write logistic regression in NumPy and measure how far it is from the library, then close the gap and explain it. Fit six objectives to convergence with the same weak penalty and compare their rankings, probabilities and decisions. Summarise the objectives in one table.

**You will leave with** a way to check that an optimisation has converged, and a decision map for the common classification losses.

</div>

## Two losses on four records

A loss turns each (prediction, outcome) pair into a penalty, and `fit()` finds parameters that make the average penalty small. Take four records with predicted probabilities of success:

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

Do not compare the sizes of the two columns, because the losses have different units. Compare their shapes: log loss keeps growing as a wrong prediction becomes more confident (0.92, then 2.30, then 4.61), while Brier saturates at 1. Log loss is the negative log-likelihood of a Bernoulli model, so minimising it is maximum likelihood. Both are *proper scoring rules*: in expectation, they are minimised by reporting the true probability. That is a statement about the loss, not a guarantee that any finished, restricted, regularised model is calibrated (part 11).

## Logistic regression by hand, and a puzzle

Logistic regression says probability = sigmoid(w · x). The gradient of the mean log loss is `Xᵀ(p − y) / n`, so plain gradient descent is a short loop. The design matrix below uses the full one-hot encoding, with an intercept, on 80% of the development rows. The other 20% of development rows are an inner validation set, and nothing here touches the comparison split.

```python
import pandas as pd
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

Two things stand out. The design matrix has **@@j:objectives_notes.json|rank_deficiency|d@@ more columns than its rank**: each one-hot variable's columns add up to the intercept column, so many coefficient vectors give identical predictions. That could explain different *coefficients*, but it cannot explain different *predictions* for records built the same way. The second observation does: after 1,500 steps the gradient is still not zero. The fit has not converged. Taking more steps shrinks the disagreement, which is what an unfinished optimisation looks like.

The hardest direction is a rare level. `default = yes` occurs in only 3 of the 41,188 records, all with the outcome "no", so an unpenalised fit keeps pushing its coefficient down. The library's solution has it near -8 and the 1,500-step solution near 0, with almost no effect on most records. To finish the job we hand the same objective to a quasi-Newton optimiser:

```python
from scipy.optimize import minimize

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

Once both fits are converged they agree to about 1e-5, whatever the rank deficiency. The hand-written model was fine. Our stopping rule was not. The practical lesson is to **check the gradient, not only the loss**: a loss that "stopped moving" is not evidence of a minimum. This is also why real logistic regression defaults to an L2 penalty: it gives the problem a unique, well-conditioned answer.

## Six objectives, each fitted to convergence

Now compare objectives fairly. Each is fitted with the same L-BFGS routine, the same weak L2 penalty (so that every problem has a unique answer), and a gradient tolerance, on the same 26,360 training records and scored on the same 6,590 validation records. Hinge-type and exponential losses produce margins, not probabilities, so their probability columns come from a one-parameter sigmoid fitted on the training scores. The "weighted" fit counts each positive record @@j:objectives_notes.json|weight_vs_intercept_shift.weight|.1f@@ times as much (the ratio of negatives to positives), which is what `class_weight="balanced"` does.

@@table:objectives_comparison.csv|cols=loss,converged,validation_ap,validation_auc,spearman_with_log_loss_scores,top10pct_overlap_with_log_loss,mean_probability,records_flagged_at_0.5,records_flagged_at_break_even,contribution_at_break_even|fmt=validation_ap:.3f;validation_auc:.3f;spearman_with_log_loss_scores:.3f;top10pct_overlap_with_log_loss:.2f;mean_probability:.3f;records_flagged_at_0.5:d;records_flagged_at_break_even:d;contribution_at_break_even:d|rename=validation_ap:AP,validation_auc:AUC,spearman_with_log_loss_scores:rank agreement with log loss,top10pct_overlap_with_log_loss:top-10% overlap,mean_probability:mean probability,records_flagged_at_0.5:flagged at 0.5,records_flagged_at_break_even:flagged at 1/8,contribution_at_break_even:contribution at 1/8@@

*The share of validation records that subscribe is @@j:objectives_notes.json|validation_prevalence|.3f@@. Contribution uses the illustrative price list (cost 1, value 8) and is a retrospective simulation on the validation records. All six fits converged (largest gradient entry below 2e-7).*

Read the table in three layers, because the objectives differ in different ways at each.

- **Ranking.** For this linear model on these features, the six objectives order records very similarly: AP lies between @@v:objectives_comparison.csv|loss=brier (on sigmoid)|validation_ap|.3f@@ and @@v:objectives_comparison.csv|loss=exponential|validation_ap|.3f@@, and rank agreement with log loss is at least @@v:objectives_comparison.csv|loss=squared hinge|spearman_with_log_loss_scores|.2f@@. That is an observation about this experiment. A linear hypothesis class can produce many different rankings, and a different loss can pick a different one with other data, other features or more noise. Squared hinge differs most from log loss in the top 10%, where the overlap is @@v:objectives_comparison.csv|loss=squared hinge|top10pct_overlap_with_log_loss|.2f@@.
- **Probabilities.** The re-weighted and focal fits give a mean predicted probability of @@v:objectives_comparison.csv|loss=weighted log|mean_probability|.2f@@ and @@v:objectives_comparison.csv|loss=focal|mean_probability|.2f@@ when @@j:objectives_notes.json|validation_prevalence|.1%@@ of validation records subscribe. They were asked to care more about the positives, and they report probabilities for that modified world. They are good rankers and poor probability estimates.
- **Decisions.** A threshold of 1/8 means "select if the probability exceeds the break-even point", and it is only meaningful for probabilities. Applied to the re-weighted and focal outputs it selects all 6,590 records, which is "call everyone", and the contribution falls to @@v:objectives_comparison.csv|loss=weighted log|contribution_at_break_even|d@@. The same ranking with a threshold chosen on suitable data would not have this problem. The loss changed what the numbers *mean*, not what order they put records in.

Does weighting equal shifting the threshold? For a correctly specified, unpenalised model it can (the weighted solution's intercept differs from the unweighted one by the log of the weight). With a finite sample and a penalty it does not exactly: here the weighted model's probabilities differ from "log-loss solution plus log-weight on the intercept" by up to @@j:objectives_notes.json|weight_vs_intercept_shift.max_abs_prob_diff_weighted_vs_shifted_intercept|.2f@@ for one record, with rank agreement @@j:objectives_notes.json|weight_vs_intercept_shift.spearman_weighted_vs_log|.3f@@. If you need probabilities, train with the natural weights and choose the threshold afterwards.

Brier loss applied to a sigmoid is not convex, so the table keeps the better of two starting points (zero, and the log-loss solution). Here both led to a converged fit.

## A decision map for the common objectives

| Loss | Form (for margin or probability) | Output | Typical models | Use it when | Sensitivity to noisy labels | Calibration | Main trade-off |
|---|---|---|---|---|---|---|---|
| Log loss | -[y log p + (1-y) log(1-p)] | Probability | Logistic regression, boosting, neural nets | You need probabilities | High for confident mistakes (unbounded) | Proper rule; fitted model still needs checking | Smooth and convex for linear models |
| Brier | (p - y)² | Probability | Any probabilistic model; used as a score | You want a bounded penalty on probabilities | Lower (bounded) | Proper rule | Weaker gradient when confidently wrong; non-convex on a sigmoid |
| Hinge / squared hinge | max(0, 1 - m)  / its square | Margin (no probability) | Linear and kernel SVMs | Ranking or classification, large margins | Moderate | Not a probability; needs Platt or isotonic scaling | Only records near the boundary matter |
| Exponential | exp(-m) | Margin | AdaBoost | Boosting with exact weight updates | Very high (grows exponentially) | Not a probability | Fast fitting, fragile with label noise |
| Focal / weighted | (1-p_t)^γ · log loss, or class-weighted log loss | Re-weighted probability | Imbalanced detection, neural nets | Rare positives and hard-example emphasis | Depends on γ and weights | Distorts probabilities on purpose | Better emphasis, worse calibration |

Here *m* is the margin y·f(x) with y in {-1, +1}. The map describes the usual behaviour; any particular dataset, penalty or optimiser can differ.

## What other models minimise

Not every classifier is fitted by iterative optimisation.

| Model | What `fit()` does | Output |
|---|---|---|
| Logistic regression | Minimises penalised log loss (convex) | Probabilities |
| Linear SVM | Minimises hinge or squared hinge plus an L2 penalty | A score |
| Decision tree | Chooses each split greedily to reduce impurity (Gini or entropy) | Class proportions in a leaf |
| Random forest | The same, on bootstrap samples with random feature subsets, then averages | Averaged proportions |
| Gradient boosting | Adds trees in the direction that reduces a chosen loss, usually log loss | Probabilities |
| Naive Bayes | Estimates class priors and per-feature densities by maximum likelihood under an independence assumption (counting and averaging, no iteration) | Probabilities that can be over-confident |
| k-nearest neighbours | Stores the data; no fitting | Share of neighbours |
| Neural network | Minimises log loss by stochastic gradient methods (non-convex) | Probabilities |

## Analysis and conclusion: what we learned

- **Check convergence directly.** Our 1,500-step fit left a gradient of about @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|grad_inf_norm|.0e@@ and probabilities up to @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|max_abs_prob_diff_vs_reference|.2f@@ away from the library's. Converged fits agree to 1e-5.
- **Rank deficiency changes coefficients, not predictions** for records encoded the same way. It still makes unpenalised fitting slow and fragile, which is why a small penalty is the default.
- **Objectives differ more in what the numbers mean than in how they order records** for this linear model and these features. Do not generalise the ranking agreement beyond them.
- **Use the right threshold for the right output.** The break-even rule `cost / value` is for probabilities, and re-weighted losses do not provide them.

[Part 5](/series/classification/05-logistic-regression-naive-bayes/) uses the library versions of these models and learns to read what a linear model has learned.
