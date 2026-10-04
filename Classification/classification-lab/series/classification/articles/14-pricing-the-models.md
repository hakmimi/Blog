---
title: "Pricing the Models: What a Ranking Is Worth Under an Illustrative Price List"
description: "A retrospective simulation with a stated price list, honest baselines and a capacity ceiling. What the numbers mean, what they do not, and where model choice and cut-off choice matter."
series: "classification"
order: 14
date: 2026-09-30
updated: 2026-10-04
keywords: ["cost-sensitive", "decision threshold", "capacity", "expected value", "uplift", "baselines"]
readingTime: "14 min read"
figure: "leaderboard-profit.png"
---

Under the illustrative price list used in this series, contacting every record on the comparison split would *lose* @@v:policy_baselines.csv|policy=call everyone|contribution|d@@ units. The one-line rule "contact only clients whose previous campaign succeeded" earns @@v:policy_baselines.csv|policy=prior-success rule|contribution|d@@ from @@v:policy_baselines.csv|policy=prior-success rule|records_selected|d@@ contacts. The best model policies earn over three times that. This chapter asks what those numbers mean, how much of the gain belongs to the model and how much to the cut-off, and how sure we can be.

<div class="callout">

**Goal.** Turn frozen scores into simulated contributions against honest baselines, and say precisely what a contribution number is.

**Work plan.** State the price list and what the simulation does not measure. Compare policies (break-even threshold, an out-of-fold threshold, a capacity ceiling) with baselines. Test whether the differences between models are visible. Vary the value of a subscription.

**You will leave with** a way to read a simulated contribution, and a view of when a simpler model is a sensible choice.

</div>

## What a contribution number is

The price list is an assumption, not a figure from the bank: a contact costs 1 unit and a subscription is worth 8. For any set of selected records,

> contribution = 8 × (subscriptions among the selected records) − 1 × (selected records)

This is a **retrospective policy simulation**. It counts every subscription among selected records as a gain, whether or not the contact caused it. Two quantities are easy to confuse.

| Quantity | Formula (per contacted record) | What it needs |
|---|---|---|
| Expected contribution of a contacted record | V · p_contact − C | The probability of subscribing when contacted |
| Incremental contribution of contacting | V · (p_contact − p_no_contact) − C | The probability of subscribing *without* a contact as well |

The break-even rule `p > C / V` (here 1/8) comes from the first line. It treats every subscription among contacted records as caused by the contact, which holds only if people would not subscribe without being contacted, or if that probability is the same for everyone. This dataset contains no records of people who were *not* contacted, so it cannot identify `p_no_contact`, and it cannot tell response propensity (who is likely to say yes) from **uplift** (who says yes *because* of the contact). A model that finds likely subscribers may waste contacts on people who would have subscribed anyway. A second limit is selection: the historical campaign chose whom to call, so the records are not a sample of the bank's whole client base. And the price list is a simplification: costs and values differ between clients, repeated contacts cost more, and some clients cannot be reached. Everything below should be read with those limits in mind, as a way to compare rankings and policies on equal terms.

## Policies and baselines

All scores are the frozen scores from part 12 on the 8,238 comparison records (928 subscribers). Thresholds are fixed before this split is scored: the break-even value 1/8, a threshold chosen on development out-of-fold scores, and the library's usual 0.5.

Baselines first. "Random, same size" selects as many records as the policy it is compared with, at random (averaged over 400 draws).

@@table:policy_baselines.csv|cols=policy,records_selected,contribution|fmt=records_selected:d;contribution:d@@

The policy "break-even threshold": select every record whose score is at least 1/8.

@@table:policy_by_model.csv|where=policy==break-even (1/8)|sort=contribution|desc|cols=model,records_selected,precision,recall,contribution,random_same_size,gain_vs_everyone,gain_vs_prior_rule|fmt=records_selected:d;precision:.3f;recall:.3f;contribution:d;random_same_size:d;gain_vs_everyone:d;gain_vs_prior_rule:d|rename=records_selected:selected,random_same_size:random, same size,gain_vs_everyone:gain over call-everyone,gain_vs_prior_rule:gain over prior-success rule@@

![Simulated contribution of each model at the break-even threshold, with the call-everyone and prior-success benchmarks.](/series/classification/figures/leaderboard-profit.png)
*Figure 1. Same frozen scores, one illustrative price list.*

Three things to take from it.

- **Every model beats the baselines by a wide margin.** Random selection at the same size loses money for every model (about 130 to 170 units), so none of the gain comes from simply selecting fewer records. The prior-success rule earns @@v:policy_baselines.csv|policy=prior-success rule|contribution|d@@ and the best models about 3,300, roughly three times as much, from five to six times as many records.
- **The spread among the learned models depends on which ones you include.** The best break-even contribution is @@v:policy_by_model.csv|model=Random forest|policy=break-even (1/8)|contribution|d@@ (random forest) and the lowest among all twelve is @@v:policy_by_model.csv|model=Gaussian Naive Bayes|policy=break-even (1/8)|contribution|d@@ (Naive Bayes), a difference of about 390. Among the eleven learned models other than Naive Bayes the lowest is @@v:policy_by_model.csv|model=Decision tree|policy=break-even (1/8)|contribution|d@@ (a single tree), so the spread there is about 215. Logistic regression earns @@v:policy_by_model.csv|model=Logistic regression|policy=break-even (1/8)|contribution|d@@, or about 94% of the best.
- **The cut-off matters a lot, and for some models more than the model.** The next table applies the library's default of 0.5 to the same scores.

@@table:policy_by_model.csv|where=policy==default cut-off 0.5|sort=contribution|desc|cols=model,records_selected,contribution|fmt=records_selected:d;contribution:d|rename=records_selected:selected@@

At 0.5, the models select only about 280 to 370 records (Naive Bayes, whose probabilities are inflated, selects @@v:policy_by_model.csv|model=Gaussian Naive Bayes|policy=default cut-off 0.5|records_selected|d@@) and earn roughly 1,300 to 1,600, about half of what the break-even threshold gives. That comparison is specific to these prices. It says that a cut-off should come from the economics and be checked, not taken from a library default, not that thresholds "always matter more than models".

## Capacity is a ceiling

Call centres have a headcount. The right way to model it is as a **ceiling**: contact at most k records, highest scores first, and never one below the break-even threshold, because capacity is not an obligation to make unprofitable contacts. The figure and table compare that policy (solid) with one that fills the capacity regardless (dashed crosses).

![Simulated contribution against capacity for three models, with and without the break-even guard.](/series/classification/figures/ch14-capacity.png)
*Figure 2. When capacity is small, every model fills it with obvious records. Beyond about 1,500 contacts, filling the list loses value unless the break-even guard stops it.*

@@table:policy_capacity.csv|where=model~LightGBM;Logistic regression;Random forest|where=break_even_guard==True|cols=model,capacity,records_selected,precision,recall,contribution,random_same_size|fmt=capacity:d;records_selected:d;precision:.3f;recall:.3f;contribution:d;random_same_size:d|rename=random_same_size:random, same size@@

- **At very small capacity nothing separates the models**: the top 200 are the obvious records for every model (contributions between 976 and 1,000).
- **In the middle (500 to 1,000 contacts) the gaps are largest.** At 1,000 contacts LightGBM earns @@v:policy_capacity.csv|model=LightGBM|capacity=1000|break_even_guard=True|contribution|d@@ and logistic regression @@v:policy_capacity.csv|model=Logistic regression|capacity=1000|break_even_guard=True|contribution|d@@, about 8% more.
- **Above the break-even region, filling the capacity loses value.** At a ceiling of 2,500 the guarded policy stops at about 1,400 to 1,560 records, while filling the list lowers the contribution (LightGBM @@v:policy_capacity.csv|model=LightGBM|capacity=2500|break_even_guard=False|contribution|d@@ against @@v:policy_capacity.csv|model=LightGBM|capacity=2500|break_even_guard=True|contribution|d@@).

## Are the differences between models visible?

The contribution of a policy is a sum over records, so it can be bootstrapped in pairs like AP in part 13, conditional on the frozen scores and thresholds. Differences from logistic regression under the break-even policy, with marginal and simultaneous 95% intervals (simultaneous because eleven models are compared at once):

@@table:policy_paired_bootstrap.csv|where=policy==break-even (1/8)|sort=diff|desc|cols=model,diff,ci95_lo,ci95_hi,simultaneous95_lo,simultaneous95_hi|fmt=diff:+,.0f;ci95_lo:+,.0f;ci95_hi:+,.0f;simultaneous95_lo:+,.0f;simultaneous95_hi:+,.0f|rename=diff:difference,ci95_lo:marginal low,ci95_hi:marginal high,simultaneous95_lo:simultaneous low,simultaneous95_hi:simultaneous high@@

The random forest, the three boosters other than CatBoost, CatBoost and the neural net earn more than logistic regression in a way the intervals support (simultaneous intervals above zero). Extra trees, the SVM and k-NN do not separate from it, and the single tree does not either. Naive Bayes earns less. The visible advantages are around 150 to 200 units for the forest and the boosters (the neural net's is smaller, about 80) on a base of about 3,150, or roughly 5% to 6%. Intervals that include zero show lack of evidence of a difference, not that the models earn the same.

## How much do the assumptions matter?

Everything depends on the value of a subscription. The table keeps the cost at 1, changes the value, and applies the break-even threshold 1/value to the raw scores. Call-everyone is recomputed for each value.

@@table:policy_value_sensitivity.csv|where=model~LightGBM;Logistic regression;Gaussian Naive Bayes|cols=model,value,records_selected,contribution,call_everyone|fmt=value:d;records_selected:d;contribution:d;call_everyone:d|rename=call_everyone:call everyone@@

- **At a value of 4, calling everyone loses heavily** (@@v:policy_value_sensitivity.csv|model=LightGBM|value=4|call_everyone|d@@) and the models earn about 700 to 1,050.
- **At a value of 16, calling everyone earns @@v:policy_value_sensitivity.csv|model=LightGBM|value=16|call_everyone|d@@.** The models earn about 7,700 to 8,600, so their advantage over the simplest baseline is only about 1,100 to 1,950. The more valuable a success, the less a ranking adds relative to contacting everyone.
- **Naive Bayes earns the least of the three at every value** (at a value of 4, @@v:policy_value_sensitivity.csv|model=Gaussian Naive Bayes|value=4|contribution|d@@ against @@v:policy_value_sensitivity.csv|model=LightGBM|value=4|contribution|d@@ for LightGBM).

The ranking of the models stays similar across the three values, but the *size* of any model's advantage over a trivial baseline changes with the assumption. That is a reason to report the advantage over a relevant baseline next to the total, and to state the price list.

## A simple model or a booster?

The best-scoring policies earn about 5% to 6% more than logistic regression under this price list, on 8,238 records. Whether that justifies a more complex pipeline depends on facts this dataset cannot supply: how many records are scored, what a mistake costs at scale, how often the model must be retrained, and who has to maintain and explain it. Evidence that would change the choice: a larger or more recent evaluation set, a measured cost per contact, a prospective test with a control group (so uplift could be estimated), and a monitoring plan (part 16). Until then, a defensible reading is that the extra benefit of the better models is visible but modest, and that the logistic regression is a strong baseline.

## Analysis and conclusion: what we learned

- **A contribution is a retrospective policy simulation** under assumed prices. It does not estimate value created by contacting, which would need uplift.
- **Compare with relevant baselines.** Call-nobody, call-everyone, matched-size random selection and a simple rule give the numbers context. All twelve models clear them by a wide margin under these prices.
- **The cut-off should come from the economics.** Under these prices the break-even threshold roughly doubled the contribution compared with a default of 0.5, for every model with usable probabilities.
- **Capacity is a ceiling.** Filling it regardless lowers the contribution once the list runs past the break-even region.
- **Differences between leading models are about 5% of the total**, visible for several boosters and the forest against logistic regression, and sensitive to the assumed value of a subscription.

[Part 15](/series/classification/15-inside-the-winner/) opens the model we would have chosen from development evidence and asks what it relies on and where it fails.
