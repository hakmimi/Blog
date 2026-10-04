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

Shuffle the five macroeconomic columns together in the comparison data and the model's average precision falls by @@v:importance_groups.csv|group=macro (5 columns)|grouped_ap_drop_mean|.3f@@. Shuffle them one at a time and the five drops add up to @@v:importance_groups.csv|group=macro (5 columns)|sum_of_single_column_drops|.3f@@. Retrain the model without them and it loses only @@v:importance_groups.csv|group=macro (5 columns)|ap_drop_vs_full|.3f@@. Three experiments, three different numbers, all of them true. They answer different questions, and this chapter is about telling them apart.

<div class="callout">

**Goal.** Describe what a fitted model relies on, with tools whose meanings are not confused, and find out where it errs under the policy we would actually run.

**Work plan.** Pick the model development evidence would choose. Apply gain importance, permutation importance, grouped permutation and drop-group retraining. Then analyse the errors of the frozen policy by segment, with the group sizes and intervals.

</div>

## Which model, and how it was chosen

The model audited is the one a reader would have chosen from *development* evidence: the highest mean cross-validated AP in the leaderboard search, which is @@j:importance_notes.json|audited_model@@ (cross-validated AP @@j:importance_notes.json|cv_ap|.3f@@; comparison-split AP @@j:importance_notes.json|comparison_ap|.3f@@). The policy used for the error analysis is its out-of-fold threshold of @@j:importance_notes.json|threshold_oof|.3f@@, fixed before the comparison split was scored. Everything here describes this fitted model on this data, with these features, not boosting in general.

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

@@table:importance_permutation.csv|head=10|cols=feature,ap_drop_mean,ap_drop_sd|fmt=ap_drop_mean:.4f;ap_drop_sd:.4f|rename=ap_drop_mean:AP drop,ap_drop_sd:sd over shuffles@@

@@table:importance_gain_lightgbm.csv|head=8|cols=feature,gain_share|fmt=gain_share:.1%|rename=gain_share:share of training gain@@

The two rankings overlap and differ. `nr.employed` and `euribor3m` lead both, `pdays` is far stronger in permutation than in gain, and `age` holds @@v:importance_gain_lightgbm.csv|feature=age|gain_share|.1%@@ of the training gain (many candidate thresholds for a continuous column) yet its permutation drop is only @@v:importance_permutation.csv|feature=age|ap_drop_mean|.4f@@. A column can be heavily used in training and hardly relied on at prediction time.

## Groups

Columns in a group carry overlapping information, so single-column numbers understate them. Three things are measured for each group: shuffle the whole group together, shuffle its columns separately (sum), and retrain without the group. The retrained AP is the mean of three fitting seeds.

@@table:importance_groups.csv|cols=group,grouped_ap_drop_mean,sum_of_single_column_drops,retrained_ap_mean,retrained_ap_sd,ap_drop_vs_full|fmt=grouped_ap_drop_mean:.3f;sum_of_single_column_drops:.3f;retrained_ap_mean:.3f;retrained_ap_sd:.4f;ap_drop_vs_full:.3f|rename=grouped_ap_drop_mean:group shuffled together,sum_of_single_column_drops:sum of single shuffles,retrained_ap_mean:AP retrained without,retrained_ap_sd:sd,ap_drop_vs_full:drop after retraining@@

![Left: permutation importance of the ten most important columns. Right: three measurements for each group of columns.](/series/classification/figures/leaderboard-importance.png)
*Figure 1. Gold: group shuffled together. Grey: sum of single-column shuffles. Navy: drop after retraining without the group.*

How to read this:

- **Shuffling a group together is much larger than the sum for the macro columns** (@@v:importance_groups.csv|group=macro (5 columns)|grouped_ap_drop_mean|.3f@@ against @@v:importance_groups.csv|group=macro (5 columns)|sum_of_single_column_drops|.3f@@). The model copes when one overlapping column is scrambled but not when all are. The shuffled-together rows also pair economic values with records they never belonged to, so this describes reliance on a distorted input, not the information in the columns, and is **not** a bound on how much they matter.
- **Retraining tells you what the other columns can substitute for.** Without the macro group the same settings lose about @@v:importance_groups.csv|group=macro (5 columns)|ap_drop_vs_full|.3f@@ AP; without history (`pdays`, `previous`, `poutcome`) @@v:importance_groups.csv|group=history (pdays, previous, poutcome)|ap_drop_vs_full|.3f@@; without the schedule columns @@v:importance_groups.csv|group=schedule (contact, month, day_of_week)|ap_drop_vs_full|.3f@@; and without the seven customer-profile columns only @@v:importance_groups.csv|group=customer profile (7 columns)|ap_drop_vs_full|.3f@@, about the size of the fitting-seed spread (@@v:importance_groups.csv|group=customer profile (7 columns)|retrained_ap_sd|.4f@@).
- **What that last number means.** For this pipeline and split the profile columns add little *once the others are present*. That does not make clients' characteristics irrelevant or personalisation impossible; it says these seven columns add little beyond history, schedule and macro context here.
- **The macro columns may stand in for time** (part 6 showed `nr.employed` tracks position in the file). A model that leans on them is exposed to whatever drives them. Part 16 tests what that costs.

## Who does the policy miss?

Under the frozen policy (@@j:importance_notes.json|audited_model@@, threshold @@j:importance_notes.json|threshold_oof|.3f@@) the comparison split gives:

@@table:errors_policy_counts.csv|cols=policy,records_selected,true_positives,false_negatives,positives|fmt=records_selected:d;true_positives:d;false_negatives:d;positives:d@@

So **@@v:errors_policy_counts.csv|false_negatives|d@@ of the 928 subscribers are false negatives**: positives the policy did not select. Another way to slice the positives is by where they sit in the ranking. Three groups, all reported:

@@table:errors_positive_rank_groups.csv|cols=positives_group,positives,share_of_positives|fmt=positives:d;share_of_positives:.1%|rename=positives_group:group of subscribers,share_of_positives:share@@

Counting misses by composition is misleading, because a segment with many records has many misses. Rates are better. For each segment, here is the **false-negative rate among its own subscribers**, with the number of subscribers and a Wilson 95% interval:

@@table:errors_segments.csv|where=column~contact;poutcome;month|cols=column,level,records,positives,observed_rate,false_negatives,false_negative_rate_among_positives,fn_rate_lo,fn_rate_hi|fmt=records:d;positives:d;false_negatives:d;observed_rate:.3f;false_negative_rate_among_positives:.3f;fn_rate_lo:.3f;fn_rate_hi:.3f|rename=observed_rate:subscription rate,false_negatives:missed,false_negative_rate_among_positives:missed share of subscribers,fn_rate_lo:95% low,fn_rate_hi:95% high@@

The policy misses @@v:errors_segments.csv|column=contact|level=telephone|false_negative_rate_among_positives|.0%@@ of the subscribers contacted by landline, @@v:errors_segments.csv|column=month|level=may|false_negative_rate_among_positives|.0%@@ of those in May and @@v:errors_segments.csv|column=month|level=jul|false_negative_rate_among_positives|.0%@@ of those in July, against @@v:errors_segments.csv|column=contact|level=cellular|false_negative_rate_among_positives|.0%@@ for cellular contacts, and almost none with a previous success (@@v:errors_segments.csv|column=poutcome|level=success|false_negatives|d@@ of @@v:errors_segments.csv|column=poutcome|level=success|positives|d@@). May alone holds @@v:errors_segments.csv|column=month|level=may|false_negatives|d@@ of the @@v:errors_policy_counts.csv|false_negatives|d@@ misses because it is the largest month. These describe what a score-based policy does, not irreducible error: subscribers in May look much like the many non-subscribers in May, so the scores rank them low. Whether new information would separate them (a measured channel history, a richer contact record) is a hypothesis to test, not a promised gain.

## Calibration by segment, with intervals

A group-level check: does the mean score of a segment sit inside the 95% interval of its observed subscription rate? Across the 27 segments in `errors_segments.csv` (contact, previous outcome, month and job), the answer is yes for every one (column `mean_score_inside_rate_interval`). Matching the group average is a weak check, it does not establish calibration *within* a segment, and with 27 unadjusted intervals we would expect one or two to miss by chance. Small segments, such as the @@v:errors_segments.csv|column=job|level=unknown|records|d@@ records with an unknown job, have intervals too wide to say much.

## Analysis and conclusion: what we learned

- **Keep the four importance questions apart.** Usage in training, reliance of a fitted model, reliance on a group, and the loss after retraining are different numbers. The macro group shows all three spreads at once.
- **Single-column permutation understates grouped columns, and group permutation overstates dependence** by feeding the model unrealistic inputs. Use retraining as the comparison, with its own caveats.
- **Limit conclusions to the pipeline, split and features.** A small drop for the profile group is a statement about this model with these alternatives.
- **Describe errors by rate and by count.** The policy misses @@v:errors_policy_counts.csv|false_negatives|d@@ of 928 subscribers, concentrated in segments (landline, May, July) where scores are low. The file cannot tell us why.

[Part 16](/series/classification/16-when-time-breaks-the-model/) asks what happens when the model has to predict records that come after the ones it was trained on.
