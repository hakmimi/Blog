---
title: "The Baseline You Have to Beat: Logistic Regression and Naive Bayes"
description: "A leak-proof pipeline, the one setting that matters, and how to read coefficients without over-reading them. Two economic indicators correlated at 0.97 get odds ratios on opposite sides of 1. We explain why, then compare two Naive Bayes variants."
series: "classification"
order: 5
date: 2026-09-30
updated: 2026-10-04
keywords: ["logistic regression", "naive bayes", "baseline", "odds ratio", "regularisation", "scikit-learn pipeline"]
readingTime: "12 min read"
figure: "ch05-odds-ratios.png"
---

Fit a logistic regression on this data and look at the two economic indicators `emp.var.rate` and `cons.price.idx`. Their odds ratios, per standard deviation, are @@v:linear_odds_ratios.csv|term=emp.var.rate|odds_ratio|.2f@@ and @@v:linear_odds_ratios.csv|term=cons.price.idx|odds_ratio|.2f@@: one cuts the odds of a subscription by about 90%, the other more than triples them. The two columns are correlated at 0.78, and each is strongly correlated with the other macro columns (see below). That pattern should make you careful about what a coefficient claims.

<div class="callout">

**Goal.** Build the simplest serious model, make it leak-proof, tune its one knob, and learn what its coefficients do and do not say.

**Work plan.** Put the preprocessing inside the model. Sweep the regularisation strength with cross-validation on the development rows. Read the coefficients as odds ratios against a stated reference. Then compare two Naive Bayes variants against it.

</div>

## Preprocessing inside the model

Everything a model learns about the data must come from training rows only: category lists, column means, standard deviations. The simplest way to guarantee that is to put preprocessing *inside* the estimator, so that `fit` learns it and `predict` only applies it, and cross-validation refits the whole chain in each fold.

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
Xd, yd = X.iloc[dev], y[dev]
cat = [c for c in X.columns if X[c].dtype == object]
cv = StratifiedKFold(5, shuffle=True, random_state=42)

def model(C):
    prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore"), cat), remainder=StandardScaler())
    return make_pipeline(prep, LogisticRegression(C=C, max_iter=5000))

for C in (0.001, 0.01, 0.1, 1, 10):
    s = cross_val_score(model(C), Xd, yd, scoring="average_precision", cv=cv)
    print(f"C={C:<6} cross-validated AP {s.mean():.3f} +- {s.std(ddof=1):.3f}")
```

```output
(filled in by the build)
```

`OneHotEncoder` makes 0/1 columns (a category unseen in training becomes all zeros) and `StandardScaler` puts numeric columns on a common scale, which matters for the penalty. Fitting the scaler on *all* development rows before cross-validating, instead of inside each fold, changed AP by @@v:linear_pipeline_isolation.csv|model=Logistic regression|difference|.4f@@ for logistic regression and @@v:linear_pipeline_isolation.csv|model=k-nearest neighbours (k=50)|difference|.4f@@ for k-NN: a negligible leak here. We keep the pipeline anyway, since the habit is free and the effect can be large elsewhere.

## The one setting that matters

Logistic regression minimises log loss plus a penalty proportional to the sum of squared coefficients. In scikit-learn the strength is set backwards: **`C` is the inverse of the penalty strength**, so a small `C` means heavy regularisation and small, stable coefficients.

The table above shows a **plateau**: from `C = 0.1` upward the mean scores (@@v:linear_c_sweep.csv|C=0.1|cv_ap_mean|.3f@@ to @@v:linear_c_sweep.csv|C=10.0|cv_ap_mean|.3f@@) differ by about 0.001, which is much smaller than the fold-to-fold spread of about 0.014. Heavy penalties hurt (`C = 0.001` scores @@v:linear_c_sweep.csv|C=0.001|cv_ap_mean|.3f@@). With ties like this, picking the more regularised setting is a reasonable default. The leaderboard in part 12 tunes `C` with the same protocol as every other model.

## What a coefficient says, and what it does not

For this model the coefficient *w* of a feature is the change in the **log-odds** of a subscription for a one-unit change of that feature, with all other features held fixed. Exponentiate it to get an **odds ratio**: 2.0 means the odds double, 0.5 means they halve.

One technical point first. With every category one-hot encoded plus an intercept, each variable's columns add up to a constant, so single dummy coefficients are not identified (part 4 measured the rank deficiency); only *differences* between levels mean something. The table therefore uses one dropped reference level per variable, the most frequent (@@j:linear_notes.json|reference_levels.contact@@ contacts, `month = @@j:linear_notes.json|reference_levels.month@@`, and so on), so a categorical odds ratio is a ratio against that reference. Numeric columns are per standard deviation, and intervals come from 100 bootstrap refits of the development rows.

@@table:linear_odds_ratios.csv|where=term~emp.var.rate;cons.price.idx;cons.conf.idx;euribor3m;nr.employed|cols=term,odds_ratio,or_lo,or_hi|rename=term:column,odds_ratio:odds ratio,or_lo:2.5%,or_hi:97.5%@@

![Odds ratios on a log scale with bootstrap intervals, for the macro columns, history columns and the largest categorical effects.](/series/classification/figures/ch05-odds-ratios.png)
*Figure 1. Selected odds ratios with the middle 95% of 100 bootstrap refits.*

A few observations. Contact by landline (against cellular), a previous failure and a Monday call each lower the odds, and the intervals are narrow. March, September, October and December raise them sharply against May, though those months hold few records. Retirees have higher odds than administrative staff.

Now the macro columns. Here is how correlated they are:

@@table:linear_macro_correlation.csv|fmt=emp.var.rate:.2f;cons.price.idx:.2f;cons.conf.idx:.2f;euribor3m:.2f;nr.employed:.2f@@

`emp.var.rate`, `euribor3m` and `nr.employed` are nearly the same variable (correlations 0.91 to 0.97), so the model shares credit between them and the *combination* of coefficients carries the signal. "Holding the others fixed" then describes economies that never occurred. Keep three things apart: an individual coefficient can be **unstable** when columns overlap (although the intervals here are fairly narrow), it is a **conditional association** given the other columns, and it is **not a causal effect**. Read correlated columns as a group.

## Naive Bayes: the same data, a different assumption

Naive Bayes models each feature separately within each class and multiplies the results as if the features were independent given the class. Its parameters are estimated by maximum likelihood, which for these models means counting and averaging, with no iteration. We compare two variants, both scored with out-of-fold probabilities on the development rows, and logistic regression for reference.

@@table:linear_naive_bayes.csv|cols=model,average_precision,roc_auc,log_loss,ece_10_quantile,mean_score,share_above_0.9,share_below_0.1|rename=average_precision:AP,roc_auc:AUC,log_loss:log loss,ece_10_quantile:ECE,mean_score:mean p,share_above_0.9:share > 0.9,share_below_0.1:share < 0.1|fmt=share_above_0.9:.3f;share_below_0.1:.3f@@

The share of subscribers is @@j:data_profile.json|prevalence|.3f@@. Gaussian Naive Bayes on one-hot columns, the usual tutorial version, ranks worse than logistic regression and its probabilities are far off: log loss @@v:linear_naive_bayes.csv|model=Gaussian NB on one-hot columns|log_loss|.2f@@ against @@v:linear_naive_bayes.csv|model=Logistic regression (C=0.1)|log_loss|.2f@@, with @@v:linear_naive_bayes.csv|model=Gaussian NB on one-hot columns|share_above_0.9|.0%@@ of records above 0.9. Gaussians on 0/1 columns fit poorly, so this is a deliberately imperfect baseline, not what Naive Bayes can do. The categorical variant with ten quantile bins ranks better (AP @@v:linear_naive_bayes.csv|model=Categorical NB on binned numerics|average_precision|.3f@@) but stays over-confident: correlated evidence (`emp.var.rate`, `euribor3m`, `nr.employed`) is multiplied as if independent. Ranking and probability quality are separate skills (part 11).

## Analysis and conclusion: what we learned

- **Baseline.** A cross-validated AP of about 0.45 with logistic regression. Later models should beat it by more than the fold-to-fold spread.
- **Tuning.** `C` shows a plateau from 0.1 upward, so choose the more regularised setting among ties.
- **Pipelines.** Putting preprocessing inside the model removed a leak that happened to be negligible here.
- **Coefficients.** They are conditional associations relative to a stated reference level, and correlated columns should be read together.
- **Naive Bayes.** Its quality depends on the representation. The Gaussian-on-one-hot variant is a weak baseline, and either variant is over-confident because the independence assumption double-counts correlated evidence.

[Part 6](/series/classification/06-decision-trees/) asks whether a model that can find interactions and thresholds does better, and how easily it overfits.
