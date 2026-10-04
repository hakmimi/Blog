---
title: "Hyperparameter Search Without Fooling Yourself"
description: "A bigger search always improves the score you used to choose the winner. We measure what it buys on rows the search never saw, for three models, and state exactly how far that inference reaches."
series: "classification"
order: 10
date: 2026-09-30
updated: 2026-10-04
keywords: ["hyperparameter tuning", "random search", "cross-validation", "winner's curse", "overfitting", "scikit-learn"]
readingTime: "12 min read"
figure: "ch10-budget.png"
---

Search more candidates and the best cross-validated score you find can only go up. That is arithmetic, not progress: the maximum of more noisy numbers is larger. The question worth asking is what the winner scores on rows that took no part in the search. This chapter measures that, for three models, and says how much of the answer applies elsewhere.

<div class="callout">

**Goal.** Quantify what a bigger tuning budget buys, honestly, and decide what this series' search protocol can and cannot claim.

**Work plan.** Keep a block of rows out of the search entirely. Draw a pool of candidates for three models, score each by cross-validation on the search rows and by AP on the held-out rows. Then simulate searches of different sizes by drawing random subsets of the pool.

**You will leave with** a budget curve per model, a clear view of the winner's curse, and the limits of the inference.

</div>

## Design

Development rows are split 75/25. The 75% (24,712 records) is the *search* set: every candidate is scored by shuffled 3-fold cross-validation on it, scored by average precision. The other 25% (8,238 records) is an **inner test set that no search ever sees**. It is not the comparison split of part 12, and nothing in this chapter is chosen from the comparison split.

Three models, each with a pool of candidates: the library default plus random draws from its search space (continuous settings from continuous distributions, so every draw is a distinct candidate). The pool sizes are the number in the table below: histogram gradient boosting and LightGBM each 40, the random forest 24 (it is slower). A search of budget *b* is simulated by drawing *b* candidates at random from the pool, picking the one with the best cross-validated score, and reading off its score on the inner test set. We repeat that 300 times per budget.

## What a bigger budget buys

@@table:budget_curve.csv|cols=model,budget,best_cv_ap,val_ap_of_winner,val_ap_sd_across_draws,default_val_ap|fmt=budget:d;best_cv_ap:.4f;val_ap_of_winner:.4f;val_ap_sd_across_draws:.4f;default_val_ap:.4f|rename=best_cv_ap:best cross-validated AP,val_ap_of_winner:AP of the winner on the inner test set,val_ap_sd_across_draws:sd across draws,default_val_ap:default on the inner test set@@

![Average precision of the winner on rows outside the search against search budget, for three models. Dotted lines: library defaults.](/series/classification/figures/ch10-budget.png)
*Figure 1. The inner-test score of the winner rises more slowly than the cross-validated score, and the spread between lucky and unlucky searches shrinks.*

What the numbers say, model by model and within these experiments.

- **The cross-validated score of the winner always rises with budget**, because it is a maximum over a larger set. Compare the "best cross-validated AP" column with the inner-test column: the first overstates what the second delivers. This is the winner's curse. The more candidates you evaluate, the less the winning cross-validated score tells you about future performance.
- **The inner-test score gains less and varies less as the budget grows.** The "sd across draws" column is the luck of the draw of candidates. It is largest for a budget of one (essentially "pick something plausible") and shrinks as the budget grows.
- **Defaults can be competitive.** The dotted lines show the library defaults on the inner test set. A search has to beat the default by more than its own noise to be worth the time, and for a model whose default is already good, a small budget mostly buys reliability, not accuracy.

## What the study does not show

- It covers three models and the search spaces we wrote down. It does not establish that eight candidates suffice for every family. The linear models have one important setting, trees and forests have two or three, boosters five; a family with many interacting settings (a neural network with different architectures, say) could need more.
- A *finite* space changes the picture. A grid of six values for a logistic regression's `C` cannot yield eight distinct candidates, and a parameter-free baseline has no budget at all. In the leaderboard (part 12) every model with parameters evaluated eight distinct candidates, because continuous settings are sampled from continuous distributions. The count is measured and reported, not assumed.
- Equal candidate counts are not equal compute. A search of eight candidates costs seconds for a logistic regression and minutes for CatBoost (part 12 reports it).
- The budget of eight used in part 12 was decided before this chapter's numbers were produced. An earlier draft of the series picked it after looking at the comparison split, so this chapter's experiment is a justification, not a discovery. What it supports is limited to the three models above.

## Doing it for real

In practice you would not write the loop above. `RandomizedSearchCV` does it, with the same arguments we have used:

```python
# schematic: shows the shape of a search, uses names from earlier chapters
from scipy.stats import loguniform, randint
from sklearn.model_selection import RandomizedSearchCV

search = RandomizedSearchCV(
    estimator,                                           # a pipeline, so preprocessing is refit inside every fold
    {"learning_rate": loguniform(0.02, 0.3), "max_leaf_nodes": randint(6, 64)},
    n_iter=8, scoring="average_precision", cv=cv, random_state=42, refit=True,
)
search.fit(X_dev, y_dev)
```

Three habits matter more than the search algorithm. Score the library default as one of the candidates, so you learn whether the search found anything. Use the *same* folds for every candidate and every model. And never report the cross-validated score of the winner as an estimate of future performance: keep rows out of the search, as here, or evaluate the frozen winner on a separate split, as in part 12. If you search much larger spaces, Bayesian optimisation libraries such as Optuna sample candidates more cleverly than random draws. They do not remove the winner's curse.

## Analysis and conclusion: what we learned

- **The winner's cross-validated score is biased upward by construction.** Measure the winner on rows outside the search.
- **For the models tested, a small budget captures much of what a larger one buys on held-out rows**, and larger budgets mainly shrink the luck of the draw. That is a statement about these three models and spaces.
- **Defaults are candidates.** Include them, and report both.
- **State the count you actually used,** and remember that equal candidate counts are not equal compute or equal coverage of each model's space.

[Part 11](/series/classification/11-probabilities-calibration-thresholds-costs/) deals with something tuning cannot fix: scores that rank well but do not behave like probabilities.
