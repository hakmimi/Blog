---
title: "Inside the Chosen Model: Reliance, Groups of Columns and Who It Misses"
description: "Gain importance, permutation importance, grouped permutation and drop-group retraining answer four different questions. We apply all four to the model development evidence would have chosen, then look at errors under the frozen policy."
series: "classification"
order: 15
date: 2026-09-30
updated: 2026-10-04
keywords: ["feature importance", "permutation importance", "ablation", "error analysis", "calibration by segment", "lightgbm"]
readingTime: "14 min read"
figure: "leaderboard-importance.png"
---

Shuffle the five macroeconomic columns together in the comparison data and the model's average precision falls by 0.285. Shuffle them one at a time and the five drops add up to 0.077. Retrain the model without them and it loses only 0.047. Three experiments, three different numbers, all of them true. They answer different questions, and this chapter is about telling them apart.

<div class="callout">

**Goal.** Describe what a fitted model relies on, with tools whose meanings are not confused, and find out where it errs under the policy we would actually run.

**Work plan.** Pick the model development evidence would choose. Apply gain importance, permutation importance, grouped permutation and drop-group retraining. Then analyse the errors of the frozen policy by segment, with the group sizes and intervals.

</div>

## Which model, and how it was chosen

The model audited is the one a reader would have chosen from *development* evidence: the highest mean cross-validated AP in the leaderboard search, which is LightGBM (cross-validated AP 0.465; comparison-split AP 0.491). The policy used for the error analysis is its out-of-fold threshold of 0.168, fixed before the comparison split was scored. Everything here describes this fitted model on this data, with these features, not boosting in general.

## Four tools, four questions

| Tool | Question it answers | What it cannot say |
|---|---|---|
| Gain importance | How much did the training loss fall at splits on this column? (usage during training) | Whether the model *needs* the column on new data; it favours columns with many possible splits |
| Permutation importance | How much does this fitted model's AP drop when the column's values are shuffled across records? (reliance) | Shuffling can create combinations that never occur, and correlated columns can stand in for one another |
| Grouped permutation | The same, shuffling several columns together so their relationships *inside* the group survive | It still breaks the relationships between the group and the other columns, so the drop is not a bound on anything |
| Drop-group retraining | How much AP is lost when a model with the same settings is refit without the group? (what the other columns can substitute for) | Settings were not re-tuned, and it is one split with a few fitting seeds |

None of them is a causal effect. Nothing here says that changing the economy, the channel or the month would change a client's decision.

## What the model uses and what it relies on

Permutation importance on the comparison split (10 shuffles per column), next to the share of training gain:

| feature | AP drop | sd over shuffles |
|---|---|---|
| nr.employed | 0.0418 | 0.0048 |
| pdays | 0.0356 | 0.0057 |
| euribor3m | 0.0253 | 0.0022 |
| month | 0.0234 | 0.0028 |
| contact | 0.0212 | 0.0034 |
| poutcome | 0.0121 | 0.0010 |
| emp.var.rate | 0.0089 | 0.0023 |
| day_of_week | 0.0089 | 0.0019 |
| age | 0.0019 | 0.0011 |
| default | 0.0019 | 0.0010 |

| feature | share of training gain |
|---|---|
| nr.employed | 31.4% |
| euribor3m | 20.2% |
| emp.var.rate | 9.3% |
| pdays | 8.9% |
| cons.conf.idx | 7.1% |
| month | 6.9% |
| poutcome | 2.9% |
| age | 2.5% |

The two rankings overlap and differ. `nr.employed` and `euribor3m` lead both, `pdays` is far stronger in permutation than in gain, and `age` holds 2.5% of the training gain (many candidate thresholds for a continuous column) yet its permutation drop is only 0.0019. A column can be heavily used in training and hardly relied on at prediction time.

## Groups

Columns in a group carry overlapping information, so single-column numbers understate them. Three things are measured for each group: shuffle the whole group together, shuffle its columns separately (sum), and retrain without the group. The retrained AP is the mean of three fitting seeds.

| group | group shuffled together | sum of single shuffles | AP retrained without | sd | drop after retraining |
|---|---|---|---|---|---|
| macro (5 columns) | 0.285 | 0.077 | 0.443 | 0.0004 | 0.047 |
| history (pdays, previous, poutcome) | 0.066 | 0.049 | 0.439 | 0.0018 | 0.051 |
| schedule (contact, month, day_of_week) | 0.054 | 0.053 | 0.471 | 0.0022 | 0.020 |
| customer profile (7 columns) | 0.007 | 0.004 | 0.486 | 0.0027 | 0.005 |

![Left: permutation importance of the ten most important columns. Right: three measurements for each group of columns.](/series/classification/figures/leaderboard-importance.png)
*Figure 1. Gold: group shuffled together. Grey: sum of single-column shuffles. Navy: drop after retraining without the group.*

How to read this:

- **Shuffling a group together is much larger than the sum for the macro columns** (0.285 against 0.077). The model copes when one overlapping column is scrambled but not when all are. The shuffled-together rows also pair economic values with records they never belonged to, so this describes reliance on a distorted input, not the information in the columns, and is **not** a bound on how much they matter.
- **Retraining tells you what the other columns can substitute for.** Without the macro group the same settings lose about 0.047 AP; without history (`pdays`, `previous`, `poutcome`) 0.051; without the schedule columns 0.020; and without the seven customer-profile columns only 0.005, about the size of the fitting-seed spread (0.0027).
- **What that last number means.** For this pipeline and split the profile columns add little *once the others are present*. That does not make clients' characteristics irrelevant or personalisation impossible; it says these seven columns add little beyond history, schedule and macro context here.
- **The macro columns may stand in for time** (part 6 showed `nr.employed` tracks position in the file). A model that leans on them is exposed to whatever drives them. Part 16 tests what that costs.

## Who does the policy miss?

Under the frozen policy (LightGBM, threshold 0.168) the comparison split gives:

| policy | records_selected | true_positives | false_negatives | positives |
|---|---|---|---|---|
| LightGBM, out-of-fold threshold 0.168 | 1,247 | 574 | 354 | 928 |

So **354 of the 928 subscribers are false negatives**: positives the policy did not select. Another way to slice the positives is by where they sit in the ranking. Three groups, all reported:

| group of subscribers | positives | share |
|---|---|---|
| high-ranked (top 10% of scores) | 441 | 47.5% |
| middle | 346 | 37.3% |
| low-ranked (below the median score) | 141 | 15.2% |

Counting misses by composition is misleading, because a segment with many records has many misses. Rates are better. For each segment, here is the **false-negative rate among its own subscribers**, with the number of subscribers and a Wilson 95% interval:

| column | level | records | positives | subscription rate | missed | missed share of subscribers | 95% low | 95% high |
|---|---|---|---|---|---|---|---|---|
| contact | cellular | 5,236 | 779 | 0.149 | 247 | 0.317 | 0.285 | 0.351 |
| contact | telephone | 3,002 | 149 | 0.050 | 107 | 0.718 | 0.641 | 0.784 |
| poutcome | failure | 823 | 111 | 0.135 | 32 | 0.288 | 0.212 | 0.379 |
| poutcome | nonexistent | 7,147 | 640 | 0.089 | 321 | 0.502 | 0.463 | 0.540 |
| poutcome | success | 268 | 177 | 0.660 | 1 | 0.006 | 0.001 | 0.031 |
| month | apr | 547 | 112 | 0.205 | 14 | 0.125 | 0.076 | 0.199 |
| month | aug | 1,230 | 124 | 0.101 | 47 | 0.379 | 0.298 | 0.467 |
| month | dec | 39 | 17 | 0.436 | 0 | 0.000 | 0.000 | 0.184 |
| month | jul | 1,411 | 117 | 0.083 | 80 | 0.684 | 0.595 | 0.761 |
| month | jun | 1,071 | 118 | 0.110 | 31 | 0.263 | 0.192 | 0.349 |
| month | mar | 110 | 59 | 0.536 | 0 | 0.000 | 0.000 | 0.061 |
| month | may | 2,758 | 187 | 0.068 | 151 | 0.807 | 0.745 | 0.858 |
| month | nov | 835 | 84 | 0.101 | 30 | 0.357 | 0.263 | 0.464 |
| month | oct | 131 | 61 | 0.466 | 1 | 0.016 | 0.003 | 0.087 |
| month | sep | 106 | 49 | 0.462 | 0 | 0.000 | 0.000 | 0.073 |

The policy misses 72% of the subscribers contacted by landline, 81% of those in May and 68% of those in July, against 32% for cellular contacts, and almost none with a previous success (1 of 177). May alone holds 151 of the 354 misses because it is the largest month. These describe what a score-based policy does, not irreducible error: subscribers in May look much like the many non-subscribers in May, so the scores rank them low. Whether new information would separate them (a measured channel history, a richer contact record) is a hypothesis to test, not a promised gain.

## Calibration by segment, with intervals

A group-level check: does the mean score of a segment sit inside the 95% interval of its observed subscription rate? Across the 27 segments in `errors_segments.csv` (contact, previous outcome, month and job), the answer is yes for every one (column `mean_score_inside_rate_interval`). Matching the group average is a weak check, it does not establish calibration *within* a segment, and with 27 unadjusted intervals we would expect one or two to miss by chance. Small segments, such as the 65 records with an unknown job, have intervals too wide to say much.

## Analysis and conclusion: what we learned

- **Keep the four importance questions apart.** Usage in training, reliance of a fitted model, reliance on a group, and the loss after retraining are different numbers. The macro group shows all three spreads at once.
- **Single-column permutation understates grouped columns, and group permutation overstates dependence** by feeding the model unrealistic inputs. Use retraining as the comparison, with its own caveats.
- **Limit conclusions to the pipeline, split and features.** A small drop for the profile group is a statement about this model with these alternatives.
- **Describe errors by rate and by count.** The policy misses 354 of 928 subscribers, concentrated in segments (landline, May, July) where scores are low. The file cannot tell us why.

[Part 16](/series/classification/16-when-time-breaks-the-model/) asks what happens when the model has to predict records that come after the ones it was trained on.
