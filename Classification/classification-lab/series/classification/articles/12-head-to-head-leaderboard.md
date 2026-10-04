---
title: "Twelve Models, One Protocol: The Head-to-Head"
description: "Twelve classifiers and a no-model baseline, tuned under one search protocol on development data and scored once on a comparison split. What is equal, what is not, and what the table can and cannot say."
series: "classification"
order: 12
date: 2026-09-30
updated: 2026-10-04
keywords: ["model comparison", "benchmark", "xgboost", "lightgbm", "catboost", "random forest", "logistic regression"]
readingTime: "12 min read"
figure: "leaderboard-ap.png"
---

Six of the twelve models land between @@v:leaderboard_selected.csv|model=XGBoost|cmp_average_precision|.3f@@ and @@v:leaderboard_selected.csv|model=sklearn HistGradientBoosting|cmp_average_precision|.3f@@ average precision on the comparison split, and a plain logistic regression sits at @@v:leaderboard_selected.csv|model=Logistic regression|cmp_average_precision|.3f@@. Whether a leaderboard is useful depends on what it is allowed to claim, so this chapter spends as much time on the protocol as on the results.

<div class="callout">

**Goal.** Compare twelve classifiers fairly under one stated protocol, and read the result without over-claiming.

**Work plan.** Fix the rows, features and folds, and give each model the same search procedure. Freeze every choice on development data, score the comparison split once, and report ranking, probabilities, speed and tuning gain separately. Close with a table of the model families.

</div>

## The protocol

Everything is chosen on the 32,950 development records and scored on the 8,238 comparison records (928 subscribers). Earlier drafts of this series did look at the comparison split while exploring, so it is a controlled teaching benchmark, not a fresh test set.

- **Same records, features and folds.** The 18 main features (part 2), the stratified split (seed 42) and shuffled 3-fold cross-validation for every model.
- **Same search procedure, not the same compute.** Each model with parameters evaluates **8 distinct candidates**: its library default plus seven random draws from its own space, each scored by mean cross-validated AP; the best mean wins, ties go to the default. The default is also scored on the comparison split so the effect of tuning can be read. Continuous settings are sampled from continuous distributions, so seven draws are seven different candidates; the count is measured, and a parameter-free baseline has none. Equal candidate counts do not mean equal compute, coverage of each space, or opportunity for models with more settings.
- **Representations follow each family:** one-hot and scaled columns for logistic regression, the SVM, k-NN, the neural net and Naive Bayes; one-hot for trees; native categories for XGBoost, LightGBM and scikit-learn's booster; raw strings for CatBoost, which computes its own target statistics. This compares *complete pipelines*, not isolated algorithms.
- **Boosters stop the same way:** 10% of the training data held out, 30 rounds without improvement in validation log loss, at most 2,000 trees, prediction with the best round (scikit-learn's booster does this internally). `n_estimators` is not searched.
- **Two adapters.** CatBoost needs its categorical column names at fit time, and passing them to the constructor makes `sklearn.clone` raise a `RuntimeError` (tested with the installed CatBoost), so the wrapper finds string columns itself. The linear SVM sits inside a Platt calibrator that contains the preprocessing, with shuffled folds, because unshuffled folds on a time-ordered file ruined its ranking (part 9).
- **Deliberately weak or excluded entries.** Gaussian Naive Bayes on one-hot columns is an imperfect baseline (part 5); the RBF SVM is excluded for its measured cost (part 9). **Twelve predictive models plus one no-model baseline make thirteen entries.**

## The result

Ordered by comparison-split AP. "CV AP" selected the configuration on development data; "default AP" is the library default scored on the comparison split; the baseline gives every record the development prevalence.

@@table:leaderboard_selected.csv|sort=cmp_average_precision|desc|cols=model,family,candidates_evaluated,selected,cv_ap,cmp_average_precision,cmp_ap_default,cmp_roc_auc,cmp_log_loss,cmp_ece_10_quantile|fmt=candidates_evaluated:d|rename=candidates_evaluated:candidates,cv_ap:CV AP,cmp_average_precision:AP,cmp_ap_default:default AP,cmp_roc_auc:AUC,cmp_log_loss:log loss,cmp_ece_10_quantile:ECE@@

![Average precision of each model on the comparison split, with 95% bootstrap intervals for the fitted model (test-sample uncertainty only).](/series/classification/figures/leaderboard-ap.png)
*Figure 1. Intervals overlap heavily across the top six.*

![ROC and precision-recall curves for five models.](/series/classification/figures/leaderboard-curves.png)
*Figure 2. The curves for the strongest models are close. AP depends on the share of positives (part 3).*

## What the table says, and what it does not

- **A top group that this table cannot order.** XGBoost, CatBoost, extra trees, the forest, LightGBM and scikit-learn's booster span about 0.013 AP, while one model's AP has a 95% interval about 0.07 wide. Part 13 shows what can be separated.
- **A modest gap to the simple baselines.** Logistic regression is about 0.03 below the best, and a tuned single tree matches it (@@v:leaderboard_selected.csv|model=Decision tree|cmp_average_precision|.3f@@). The neural net and the SVM sit close to it.
- **Tuning matters very differently by family.**

@@table:leaderboard_selected.csv|where=model!=Prior (no model)|sort=cmp_average_precision|desc|cols=model,selected,cmp_average_precision,cmp_ap_default|rename=selected:chosen,cmp_average_precision:tuned AP,cmp_ap_default:default AP@@

  Where the default is far from sensible here (a fully grown tree, extra trees, k-NN with k = 5, a default forest, Naive Bayes) tuning adds a lot. For the four boosters, tuned and default scores differ by at most 0.009 with varying sign (XGBoost and LightGBM slightly lower, the other two slightly higher), which is inside the noise of one split: "defaults were already near the plateau". It also shows why the default must be in the race.
- **Calibration is not uniform.** Naive Bayes has ECE @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_ece_10_quantile|.3f@@ and log loss @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_log_loss|.2f@@ against about 0.27 for most models (part 11).
- **One problem.** About 41,000 records, 18 features, a weak signal and a rare outcome. Another problem could reorder the table.

## Speed and size, measured separately

These come from a separate run on an otherwise idle machine, with the selected configurations: the final fit, the full candidate search (from the leaderboard run, which was **not** on an idle machine, so order-of-magnitude only), scoring the 8,238 comparison records in one batch with preprocessing included, and scoring one record at a time.

@@table:timing.csv|cols=model,fit_seconds_best,search_seconds_total,batch_records_per_second,single_record_ms_median|fmt=batch_records_per_second:,.0f;single_record_ms_median:.1f;fit_seconds_best:.1f;search_seconds_total:,.0f|rename=fit_seconds_best:final fit (s),search_seconds_total:search wall-clock (s),batch_records_per_second:batch records per second,single_record_ms_median:single record (ms)@@

![Final fit time and batch throughput against comparison-split average precision.](/series/classification/figures/leaderboard-cost-vs-quality.png)
*Figure 3. Quality against cost on this machine, thread setting and library versions (`timing_environment.json`).*

Simple models are fastest to fit, and CatBoost is the slowest to search in this setup. Single-record latency is dominated by call overhead in these Python pipelines, so it says little about a production system built differently.

## The families side by side

One table for every family used in this series, with this dataset's finding last. It summarises behaviour; it is not a universal ranking.

| Family (models used) | Main assumption | Interactions | Categorical columns, scaling | Probabilities | Readable? | Cost | Use it when | Here (AP) |
|---|---|---|---|---|---|---|---|---|
| Linear: logistic regression, linear SVM | Log-odds (or margin) linear in the features | Only if added | One-hot, scale | Logistic: usually reasonable; SVM: needs calibration | High | Low | A fast, explainable baseline | @@v:leaderboard_selected.csv|model=Logistic regression|cmp_average_precision|.3f@@ / @@v:leaderboard_selected.csv|model=Linear SVM (Platt scaled)|cmp_average_precision|.3f@@ |
| Naive Bayes (Gaussian) | Features independent given the class | Through the densities only | One-hot, scale; representation matters | Over-confident (correlated evidence counted twice) | Medium | Very low | A quick sanity check | @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_average_precision|.3f@@ |
| k-nearest neighbours | Similar records, similar outcomes | Through distance | One-hot, scale, large k | Share of neighbours | Low | Cheap to fit, costly to score | Small data, local structure | @@v:leaderboard_selected.csv|model=k-nearest neighbours|cmp_average_precision|.3f@@ |
| Kernel SVM (RBF) | Smooth boundary | Yes | One-hot, scale | Needs calibration | Low | Fit cost grows steeply (part 9) | Small to medium data | Excluded (cost) |
| Neural network (MLP) | Smooth function | Yes | One-hot, scale | From log loss; seed-dependent | Low | Moderate | Large data, repeated seeds | @@v:leaderboard_selected.csv|model=Small neural net (MLP)|cmp_average_precision|.3f@@ |
| Decision tree | Piecewise-constant regions | Yes, greedy | One-hot; no scaling | Leaf proportions, coarse | High if small | Low | Explanation, rules | @@v:leaderboard_selected.csv|model=Decision tree|cmp_average_precision|.3f@@ |
| Bagging: forest, extra trees | Averaging cuts variance | Yes | One-hot; no scaling | Depends on leaf size (part 11) | Low | Moderate | A forgiving strong default | @@v:leaderboard_selected.csv|model=Random forest|cmp_average_precision|.3f@@ / @@v:leaderboard_selected.csv|model=Extra trees|cmp_average_precision|.3f@@ |
| Boosting: HistGradientBoosting, XGBoost, LightGBM, CatBoost | Small trees reduce remaining error | Yes | Native categories in several libraries; no scaling | Reasonable with log loss; check | Low | Moderate; early stopping | The last points of ranking quality, with validation discipline | @@v:leaderboard_selected.csv|model=XGBoost|cmp_average_precision|.3f@@ to @@v:leaderboard_selected.csv|model=sklearn HistGradientBoosting|cmp_average_precision|.3f@@ |

Multiclass and multilabel problems are outside this series: everything here is binary classification on a table.

## Analysis and conclusion: what we learned

- **Boosting and bagging models scored highest, a simple baseline a modest step below, and the order within the top group is not established here.**
- **A simple baseline is competitive on practical grounds:** fast, explainable and close in ranking. Whether the extra points justify the complexity is a question for part 14.
- **Defaults are part of the comparison.** For boosters tuning bought nothing measurable; for trees, forests, k-NN and Naive Bayes it bought a lot.
- **Equal candidate counts are a convenience, not fairness.** Results describe complete pipelines with the spaces we wrote down.

[Part 13](/series/classification/13-is-the-winner-real/) asks how much of the ordering would survive another sample, another split and another search.
