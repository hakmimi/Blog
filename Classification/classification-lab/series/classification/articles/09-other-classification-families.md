---
title: "Distance, Margins and Networks: k-NN, SVMs and a Small Neural Net"
description: "What distance actually responds to, why an SVM score is not a probability, what the RBF kernel costs when you measure it, and how much a neural network's score depends on its seed."
series: "classification"
order: 9
date: 2026-09-30
updated: 2026-10-04
keywords: ["k-nearest neighbors", "support vector machine", "neural network", "platt scaling", "feature scaling"]
readingTime: "12 min read"
figure: "ch09-svm-scaling.png"
---

A k-nearest-neighbours classifier at its library default of k = 5 scores @@v:leaderboard_selected.csv|model=k-nearest neighbours|cmp_ap_default|.3f@@ average precision on the comparison split. The same algorithm with k chosen by a search scores @@v:leaderboard_selected.csv|model=k-nearest neighbours|cmp_average_precision|.3f@@. Three families in this chapter, k-NN, support vector machines and neural networks, each have one decision that matters more than the algorithm's name, and finding it is the point.

<div class="callout">

**Goal.** For each family, learn what you must do to the data or to your expectations before the model is usable.

**Work plan.** Look at what distance responds to and how k changes k-NN. Compare linear SVM scores with probabilities, and test how Platt scaling can go wrong. Measure what an RBF SVM costs. Check how much a small neural network's score moves with its seed.

**You will leave with** the practical catch for each family, with numbers from this data.

</div>

All experiments here fit on 75% of the development rows and score on the other 25% (inner validation). The comparison split is not used.

## k-NN: a model that is only a distance

k-NN predicts the share of subscribers among the k most similar training records, where "similar" means close in Euclidean distance. That makes it sensitive to how each column is encoded, but not in the way a rule of thumb suggests.

Euclidean distance responds to *differences* between values, in units of each column. A column contributes a lot to the distance when its values vary a lot across records (a large standard deviation) and little when they vary a little. A constant offset does not matter. Here is the spread of some columns before scaling:

@@table:families_notes_std.csv|rename=feature:column,std:standard deviation@@

`pdays` varies by about 187 units because 96% of records carry the code 999 and the rest carry 0 to 27, and `nr.employed` by about 72, while the one-hot columns that carry the categories vary between 0 and 1. Unscaled, distance is mostly a distance in `pdays` and `nr.employed`. We compared that with scaled columns, and with the `pdays` code recoded as a flag plus a recency (part 2):

@@table:families_knn.csv|where=setting==k=50|cols=model,setting,val_ap|rename=val_ap:validation AP@@

On this data the three versions score alike at k = 50. That is a result about this dataset, where the two columns that dominate the unscaled distance are also strongly related to the outcome. It is not a reason to skip scaling: on another dataset the dominant column could be noise, and scaling inside the pipeline is what stops you from depending on luck.

The setting that matters is k:

@@table:families_knn.csv|where=model==kNN scaled|cols=setting,val_ap|rename=val_ap:validation AP@@

With k = 5 a probability can only be 0, 0.2, 0.4, 0.6, 0.8 or 1, which is coarse and noisy when subscribers are 11% of records. Larger k smooths it. Small k is not wrong in general (it can be right when classes are dense and well separated), but for a rare outcome with weak signal it is a poor setting here, and the score plateaus from about k = 50. k-NN also has no fitted model to apply: every prediction searches the training data, so the model file *is* the dataset and scoring cost grows with it (part 12 has measured throughput).

## Support vector machines: a score, not a probability

A linear SVM draws the boundary with the widest margin and cares mostly about records near it. Its output is a signed distance from the boundary. It ranks about as well as logistic regression here (the Platt-scaled version scores @@v:leaderboard_selected.csv|model=Linear SVM (Platt scaled)|cmp_average_precision|.3f@@ on the comparison split), but a margin of 0.3 does not mean a 30% chance. If you need probabilities, as the break-even rule does, fit a small logistic map on the scores, called **Platt scaling**. `CalibratedClassifierCV` does it with cross-validation.

There is a trap, and we fell into it. The folds inside the calibrator must be *shuffled* when the data are in time order. Unshuffled folds are contiguous blocks of the file, so each fold's model and each fold's calibration map come from a different era, and the ensemble they form is not one coherent model.

@@table:families_svm_calibration_folds.csv|rename=calibrator folds:folds inside the calibrator,ap_calibrated:AP calibrated,auc_calibrated:AUC calibrated,ap_uncalibrated_margin:AP of the raw margin,auc_uncalibrated_margin:AUC of the raw margin@@

The raw margin ranks at about 0.46 AP either way. The calibrated version with unshuffled folds collapsed to @@v:families_svm_calibration_folds.csv|calibrator folds=3 folds, not shuffled (contiguous blocks of the file)|ap_calibrated|.2f@@. It looked like a problem with the SVM, but it was a problem with the folds. In this series the calibrator always wraps the complete preprocessing-plus-SVM pipeline and uses shuffled folds.

## The RBF kernel: measure the cost

An RBF-kernel SVM can draw curved boundaries. Its training cost grows quickly with the number of records, so we measured it on this machine, scaled features, one fit each (repeated twice up to 8,000 rows):

@@table:families_svm_timing.csv|cols=rows,fit_seconds_min,repetitions|fmt=rows:d;fit_seconds_min:.1f;repetitions:d|rename=fit_seconds_min:fit seconds (best)@@

![Fit time of the RBF SVM against the number of training records on log-log axes.](/series/classification/figures/ch09-svm-scaling.png)
*Figure 1. Measured fit time of one RBF SVM. The slope between 2,000 and 16,000 records is about @@j:families_notes.json|svm_loglog_slope_up_to_16000_rows|.1f@@ on these axes.*

Between 2,000 and 16,000 records, the time grows a little faster than quadratically. One fit on all @@j:families_notes.json|svm_full_development_rows|d@@ fitting rows took @@v:families_svm_timing.csv|rows=24712|fit_seconds_min|.0f@@ seconds. Under our search protocol (8 candidates, 3 folds, about 22,000 records per fold) that is 24 fits of that order, many times the search cost of the other models in part 12, which finish whole searches in seconds to minutes. So the RBF SVM is excluded from the common search for **cost under this protocol**, not because it cannot be fitted. A smaller, separate protocol for it would be a different comparison and we say so instead of quietly training it on a subsample.

## A small neural network: a fussy learner

A multilayer perceptron stacks layers of weighted sums and non-linearities, trained by gradient methods on log loss, so it outputs probabilities directly. The scikit-learn version here has two hidden layers (64 and 32 units) and stops early on a validation slice. Because its training starts from random weights, its score depends on the seed:

@@table:families_mlp_seeds.csv|cols=seed,val_ap,epochs|fmt=seed:d;epochs:d|rename=val_ap:validation AP@@

Over five seeds the validation AP ranges from @@v:families_mlp_seeds.csv|seed=2|val_ap|.3f@@ to @@v:families_mlp_seeds.csv|seed=3|val_ap|.3f@@. A single-seed difference of a few thousandths between this network and another model is therefore not informative. The network is competitive on this data (comparison-split AP @@v:leaderboard_selected.csv|model=Small neural net (MLP)|cmp_average_precision|.3f@@) and needs more care than a booster in return: scaled inputs, a seed policy and early stopping. As a quick baseline it is fine. As a final answer, it needs a reason (part 12).

## Analysis and conclusion: what we learned

- **k-NN lives and dies by k.** The default (5) is poor here and large k (50 and up) is stable. Distance depends on variation, so scale inside the pipeline.
- **An SVM score needs a calibrator, and the calibrator needs sensible folds.** Unshuffled folds on time-ordered data cut the calibrated AP from about 0.46 to 0.18.
- **Measure kernel costs.** One RBF fit on 24,712 rows took about a minute, which makes a 24-fit search heavy compared with the others.
- **Neural-net scores are seed-dependent.** Quote a spread, not a single run.

[Part 10](/series/classification/10-hyperparameter-search/) sets the rules for tuning all of these fairly.
