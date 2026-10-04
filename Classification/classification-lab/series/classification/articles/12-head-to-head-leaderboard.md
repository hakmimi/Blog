---
title: "Twelve Models, One Protocol: The Head-to-Head"
description: "Twelve classifiers and a no-model baseline, tuned under one search protocol on development data and scored once on a comparison split. What is equal, what is not, and what the table can and cannot say."
series: "classification"
order: 12
date: 2026-09-30
updated: 2026-10-04
keywords: ["model comparison", "benchmark", "xgboost", "lightgbm", "catboost", "random forest", "logistic regression"]
readingTime: "14 min read"
figure: "leaderboard-ap.png"
---

Six of the twelve models land between @@v:leaderboard_selected.csv|model=XGBoost|cmp_average_precision|.3f@@ and @@v:leaderboard_selected.csv|model=sklearn HistGradientBoosting|cmp_average_precision|.3f@@ average precision on the comparison split, and a plain logistic regression sits at @@v:leaderboard_selected.csv|model=Logistic regression|cmp_average_precision|.3f@@. Whether that makes a leaderboard useful depends on what the table is allowed to claim, so this chapter spends as much time on the protocol as on the results.

<div class="callout">

**Goal.** Compare twelve classifiers fairly under one stated protocol, and read the result without over-claiming.

**Work plan.** Fix the rows, features and folds. Give each model the same search procedure. Freeze every choice on development data, score the comparison split once, and report ranking, probabilities, speed and tuning gain separately. Close with a table of the model families.

**You will leave with** a leaderboard, a list of what it does not show, and a decision table for the families used in this series.

</div>

## The protocol

Everything is chosen on the 32,950 development records and scored on the 8,238 comparison records (928 subscribers). The comparison split is not used to choose anything. Earlier drafts of this series did look at it while exploring, so treat it as a controlled teaching benchmark, not as a fresh test set.

- **Same records and features.** The 18 features of the main set (part 2), the same stratified split (seed 42), and the same shuffled 3-fold cross-validation for every model.
- **Same search procedure, not the same compute.** Each model with parameters evaluates **8 distinct candidates**: its library default plus seven random draws from its own search space, each scored by mean cross-validated average precision. The best mean wins and ties go to the default. The default is a real candidate, and it is also scored on the comparison split so the effect of tuning can be read directly. Equal candidate counts do not mean equal compute, equal coverage of each model's space, or equal opportunity for models with more settings.
- **Search spaces.** Continuous settings are sampled from continuous distributions (log-uniform for strengths and rates), so seven draws are seven different candidates. A model with a tiny discrete space would have fewer distinct candidates, and a parameter-free baseline has none, so the count is measured and reported, not assumed.
- **Representations follow each family.** One-hot and scaled columns for logistic regression, the SVM, k-NN, the neural net and Naive Bayes. One-hot columns for the tree models. Native categorical columns for XGBoost, LightGBM and scikit-learn's histogram booster, and raw strings for CatBoost, which computes its own target statistics. Comparing these is a comparison of *complete pipelines*, not of isolated algorithms.
- **Early stopping for the four boosters is the same.** The wrapper holds out 10% of the training data it receives, stops after 30 rounds without improvement in validation log loss (at most 2,000 trees) and predicts with the best round. scikit-learn's booster does the same internally with its own validation slice. `n_estimators` is therefore not searched.
- **Two adapters, explained.** CatBoost needs the names of its categorical columns at fit time. Passing them to the constructor makes `sklearn.clone` raise a `RuntimeError` (tested with the installed CatBoost), so the wrapper finds string columns itself at fit time. The linear SVM is wrapped in a Platt-scaling calibrator that contains the preprocessing and the SVM, with shuffled folds, because unshuffled folds on a time-ordered file gave the calibrator different eras and ruined its ranking when we first tried it.
- **Deliberately weak entries.** Gaussian Naive Bayes on one-hot columns is an imperfect baseline (part 5). The RBF SVM is excluded because of its measured fitting cost (part 9).
- **The count.** Twelve predictive models plus one no-model baseline make thirteen entries in the table.

## The result

Models are ordered by comparison-split AP. "CV AP" is the development cross-validation score that selected the configuration. "Default AP" is the library default scored on the comparison split. The no-model baseline gives every record the development prevalence.

@@table:leaderboard_selected.csv|sort=cmp_average_precision|desc|cols=model,family,candidates_evaluated,selected,cv_ap,cmp_average_precision,cmp_ap_default,cmp_roc_auc,cmp_log_loss,cmp_ece_10_quantile|fmt=candidates_evaluated:d|rename=candidates_evaluated:candidates,cv_ap:CV AP,cmp_average_precision:AP,cmp_ap_default:default AP,cmp_roc_auc:AUC,cmp_log_loss:log loss,cmp_ece_10_quantile:ECE@@

![Average precision of each model on the comparison split, with 95% bootstrap intervals for the fitted model. The intervals describe test-sample uncertainty only.](/series/classification/figures/leaderboard-ap.png)
*Figure 1. Intervals overlap heavily across the top six. Part 13 compares models in pairs and across other splits.*

![ROC and precision-recall curves for five of the models.](/series/classification/figures/leaderboard-curves.png)
*Figure 2. The curves for the strongest models are close. Remember that AP depends on the share of positives (part 3).*

## What the table says, and what it does not

- **A top group that cannot be ordered here.** XGBoost, CatBoost, extra trees, the random forest, LightGBM and scikit-learn's booster span @@v:leaderboard_selected.csv|model=XGBoost|cmp_average_precision|.3f@@ to @@v:leaderboard_selected.csv|model=sklearn HistGradientBoosting|cmp_average_precision|.3f@@, a range of about 0.013, while one model's AP has a 95% interval about 0.07 wide. Part 13 shows what can be separated and what cannot.
- **A visible gap to the simple baselines, by a modest margin.** Logistic regression scores @@v:leaderboard_selected.csv|model=Logistic regression|cmp_average_precision|.3f@@, about 0.03 below the best model, and a tuned single tree matches it (@@v:leaderboard_selected.csv|model=Decision tree|cmp_average_precision|.3f@@). The neural net and the linear SVM sit near the logistic regression.
- **Tuning matters very differently by family.** The next table sets the tuned configuration beside the library default, both scored on the comparison split.

@@table:leaderboard_selected.csv|where=model!=Prior (no model)|sort=cmp_average_precision|desc|cols=model,selected,cmp_average_precision,cmp_ap_default|rename=selected:chosen,cmp_average_precision:tuned AP,cmp_ap_default:default AP@@

  For models whose defaults are far from sensible here (a fully grown tree, extra trees, k-NN with k = 5, a default random forest, Naive Bayes) tuning adds a lot. For the four boosters the tuned and default scores differ by at most 0.009 and the sign varies: XGBoost and LightGBM score slightly lower after tuning, scikit-learn's booster and CatBoost slightly higher. Differences of that size are inside the noise of one split, so the right reading is "defaults were already near the plateau", not "tuning helps" or "tuning hurts". It also shows why the default must be in the race.
- **Calibration is not uniform.** Naive Bayes has an ECE of @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_ece_10_quantile|.3f@@ and a log loss of @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_log_loss|.2f@@ against about 0.27 for most models. A contribution calculation on its raw probabilities would be unreliable (part 11).
- **The benchmark is one problem.** About 41,000 records, 18 features, a weak signal and a rare outcome. A different problem could reorder the table.

## Speed and size, measured separately

These numbers come from a separate run on an otherwise idle machine, using the selected configurations. They separate four different quantities: the final fit, the full candidate search (from the leaderboard run, which was **not** on an idle machine, so it is order-of-magnitude only), scoring the 8,238 comparison records in one batch with preprocessing included, and scoring one record at a time.

@@table:timing.csv|cols=model,fit_seconds_best,search_seconds_total,batch_records_per_second,single_record_ms_median|fmt=batch_records_per_second:,.0f;single_record_ms_median:.1f;fit_seconds_best:.1f;search_seconds_total:,.0f|rename=fit_seconds_best:final fit (s),search_seconds_total:search wall-clock (s),batch_records_per_second:batch records per second,single_record_ms_median:single record (ms)@@

![Final fit time and batch throughput against comparison-split average precision.](/series/classification/figures/leaderboard-cost-vs-quality.png)
*Figure 3. Quality against cost. Speeds describe this machine, thread setting and library versions (see `timing_environment.json`).*

The fastest models to fit are the simple ones, and CatBoost is the slowest to search in this setup. Single-record latency is dominated by call overhead in these Python pipelines, so it says little about a production system built differently.

## The families side by side

One table for every family used in this series, with this dataset's finding in the last column. It is a summary of behaviour, not a universal ranking.

| Family (models used) | Main assumption | Nonlinearity and interactions | Categorical columns and scaling | Probabilities | Readability | Cost | Use it when | Here (AP, comparison split) |
|---|---|---|---|---|---|---|---|---|
| Linear: logistic regression, linear SVM | Log-odds (or margin) is linear in the features | Only if you add them | One-hot and scale | Logistic: usually reasonable; SVM: needs calibration | High | Low | A strong, fast, explainable baseline | @@v:leaderboard_selected.csv|model=Logistic regression|cmp_average_precision|.3f@@ / @@v:leaderboard_selected.csv|model=Linear SVM (Platt scaled)|cmp_average_precision|.3f@@ |
| Naive Bayes (Gaussian) | Features independent given the class | None beyond the density model | One-hot and scale; representation matters | Over-confident (double-counts correlated evidence) | Medium | Very low | Quick sanity check; text-like or sparse problems | @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_average_precision|.3f@@ |
| k-nearest neighbours | Similar records have similar outcomes | Yes, through the distance | One-hot, scale, large k for rare positives | Share of neighbours; coarse for small k | Low | Cheap to fit, costly to score | Small data, local structure | @@v:leaderboard_selected.csv|model=k-nearest neighbours|cmp_average_precision|.3f@@ |
| Kernel SVM (RBF) | Smooth boundary in feature space | Yes | One-hot and scale | Needs calibration | Low | Fit cost grows steeply with records (part 9) | Small to medium data | Excluded (measured cost) |
| Neural network (MLP) | Smooth function of the features | Yes | One-hot and scale | Probabilities from log loss; seed-dependent | Low | Moderate | Large data, mixed inputs, when you can tune and repeat seeds | @@v:leaderboard_selected.csv|model=Small neural net (MLP)|cmp_average_precision|.3f@@ |
| Decision tree | Piecewise-constant regions | Yes, greedy | One-hot; no scaling | Leaf proportions; coarse | High for small trees | Low | Explanation, rule discovery | @@v:leaderboard_selected.csv|model=Decision tree|cmp_average_precision|.3f@@ |
| Bagging: random forest, extra trees | Averaging reduces variance of deep trees | Yes | One-hot; no scaling | Depends on leaf size; check (part 11) | Low | Moderate | A forgiving, strong default | @@v:leaderboard_selected.csv|model=Random forest|cmp_average_precision|.3f@@ / @@v:leaderboard_selected.csv|model=Extra trees|cmp_average_precision|.3f@@ |
| Boosting: HistGradientBoosting, XGBoost, LightGBM, CatBoost | Adding small trees to reduce remaining error | Yes | Native categories in several libraries; no scaling | Reasonable when trained on log loss; check | Low | Moderate; early stopping needed | The last few points of ranking quality, with validation discipline | @@v:leaderboard_selected.csv|model=sklearn HistGradientBoosting|cmp_average_precision|.3f@@ to @@v:leaderboard_selected.csv|model=XGBoost|cmp_average_precision|.3f@@ |

Multiclass and multilabel problems are outside this series: everything here is binary classification on a table.

## Analysis and conclusion: what we learned

- **Under this protocol, boosting and bagging models form the best-scoring group and logistic regression is a modest step below.** The order inside the group is not established by this table.
- **A simple baseline is competitive on practical grounds.** It is fast to fit, easy to explain, and close in ranking, so the question is whether the extra points justify the complexity (part 14).
- **Defaults are part of the comparison.** For the boosters, tuning bought nothing measurable. For trees, forests, k-NN and Naive Bayes it bought a lot.
- **Equal candidate counts are a convenience, not a guarantee of fairness.** Results describe complete pipelines with the search spaces we wrote down.

[Part 13](/series/classification/13-is-the-winner-real/) asks how much of this ordering would survive another sample, another split and another search.
