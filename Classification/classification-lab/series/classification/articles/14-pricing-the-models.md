---
title: "Pricing the Models: What a Ranking Is Worth Under an Illustrative Price List"
description: "A retrospective simulation with a stated price list, relevant baselines and a capacity ceiling. What the numbers mean, what they do not, and where model choice and cut-off choice matter."
series: "classification"
order: 14
date: 2026-09-30
updated: 2026-10-04
keywords: ["cost-sensitive", "decision threshold", "capacity", "expected value", "uplift", "baselines"]
readingTime: "11 min read"
figure: "leaderboard-profit.png"
---

Under the illustrative price list of this series, contacting every record of the comparison split would *lose* @@v:policy_baselines.csv|policy=call everyone|contribution|d@@ units. The rule "contact only clients whose previous campaign succeeded" earns @@v:policy_baselines.csv|policy=prior-success rule|contribution|d@@ from @@v:policy_baselines.csv|policy=prior-success rule|records_selected|d@@ contacts. The best model policies earn about three times that. What do those numbers mean, how much belongs to the model and how much to the cut-off, and how sure can we be?

<div class="callout">

**Goal.** Turn frozen scores into simulated contributions against relevant baselines, and say exactly what a contribution is.

**Work plan.** State the price list and what the simulation does not measure. Compare policies (break-even threshold, default cut-off, capacity ceiling) with baselines, test whether differences between models are visible, and vary the value of a subscription.

</div>

## What a contribution number is

The price list is an assumption, not the bank's: a contact costs 1 and a subscription is worth 8. For any set of selected records,

> contribution = 8 × (subscriptions among the selected records) − 1 × (selected records)

This is a **retrospective policy simulation**: it counts every subscription among selected records as a gain, whether or not the contact caused it.

| Quantity | Per contacted record | Needs |
|---|---|---|
| Expected contribution | V · p_contact − C | Probability of subscribing when contacted |
| Incremental contribution | V · (p_contact − p_no_contact) − C | The probability *without* a contact as well |

The break-even rule `p > C / V` (here 1/8) comes from the first line. It is right if people would not subscribe without the contact, or if that probability is the same for everyone. The dataset has no records of people who were *not* contacted, so it cannot identify `p_no_contact`, nor separate response propensity from **uplift**. The historical campaign also chose whom to call, so the records are not a sample of the bank's whole client base, and the price list ignores unequal costs, repeated contacts and unreachable clients. Read everything below as a way to compare rankings and policies on equal terms.

## Policies and baselines

Scores are the frozen ones from part 12 on the 8,238 comparison records (928 subscribers). Thresholds are fixed before scoring: the break-even value 1/8, an out-of-fold value from development data, and the library's 0.5.

@@table:policy_baselines.csv|cols=policy,records_selected,contribution|fmt=records_selected:d;contribution:d|rename=records_selected:records selected,contribution:simulated contribution@@

Select every record scoring at least 1/8 ("random same size" selects as many records at random, averaged over 400 draws):

@@table:policy_by_model.csv|where=policy==break-even (1/8)|sort=contribution|desc|cols=model,records_selected,precision,recall,contribution,random_same_size,gain_vs_everyone,gain_vs_prior_rule|fmt=records_selected:d;precision:.3f;recall:.3f;contribution:d;random_same_size:d;gain_vs_everyone:d;gain_vs_prior_rule:d|rename=records_selected:selected,random_same_size:random same size,gain_vs_everyone:gain over call-everyone,gain_vs_prior_rule:gain over prior-success rule@@

![Simulated contribution of each model at the break-even threshold, with the call-everyone and prior-success benchmarks.](/series/classification/figures/leaderboard-profit.png)
*Figure 1. Same frozen scores, one illustrative price list.*

- **Every model beats the baselines widely.** Random selection of the same size loses 130 to 170 units, so the gain does not come from selecting fewer records. The best models earn about 3,300 against the prior-success rule's @@v:policy_baselines.csv|policy=prior-success rule|contribution|d@@, from five to six times as many records.
- **The spread depends on who you include.** Best is @@v:policy_by_model.csv|model=Random forest|policy=break-even (1/8)|contribution|d@@ (random forest), lowest of all twelve @@v:policy_by_model.csv|model=Gaussian Naive Bayes|policy=break-even (1/8)|contribution|d@@ (Naive Bayes), a difference of about 390. Excluding Naive Bayes the lowest is @@v:policy_by_model.csv|model=Decision tree|policy=break-even (1/8)|contribution|d@@ (a single tree), a spread of about 215. Logistic regression earns @@v:policy_by_model.csv|model=Logistic regression|policy=break-even (1/8)|contribution|d@@, about 94% of the best.
- **The cut-off matters.** At the library default of 0.5 the same scores select only about 280 to 370 records (Naive Bayes, with inflated probabilities, @@v:policy_by_model.csv|model=Gaussian Naive Bayes|policy=default cut-off 0.5|records_selected|d@@) and earn roughly 1,300 to 1,600, about half of the break-even policy:

@@table:policy_by_model.csv|where=policy==default cut-off 0.5|sort=contribution|desc|cols=model,records_selected,contribution|fmt=records_selected:d;contribution:d|rename=records_selected:selected@@

That is specific to these prices: a cut-off should come from the economics and be checked, not taken from a default.

**Try it.** The widget below applies any threshold to the frozen scores of five models. Choose a model, move the threshold, and change what a subscription is worth: the dashed line marks the break-even threshold `1/value` and the gold dot the best threshold *on this sample* (not a population optimum).

<div class="threshold-lab" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

## Capacity is a ceiling

Treat capacity as a ceiling: contact at most k records, highest scores first, and never one below the break-even threshold. Solid lines below keep that guard; dashed crosses fill the capacity regardless.

![Simulated contribution against capacity for three models, with and without the break-even guard.](/series/classification/figures/ch14-capacity.png)
*Figure 2. Beyond about 1,500 contacts, filling the list loses value unless the guard stops it.*

@@table:policy_capacity.csv|where=model~LightGBM;Logistic regression;Random forest|where=break_even_guard==True|cols=model,capacity,records_selected,precision,recall,contribution,random_same_size|fmt=capacity:d;records_selected:d;precision:.3f;recall:.3f;contribution:d;random_same_size:d|rename=random_same_size:random same size@@

At 200 contacts nothing separates the models (976 to 1,000). The gaps are largest at 500 to 1,000: at 1,000 LightGBM earns @@v:policy_capacity.csv|model=LightGBM|capacity=1000|break_even_guard=True|contribution|d@@ and logistic regression @@v:policy_capacity.csv|model=Logistic regression|capacity=1000|break_even_guard=True|contribution|d@@, about 8% more. At a ceiling of 2,500 the guarded policy stops at about 1,400 to 1,560 records, while filling the list lowers the contribution (LightGBM @@v:policy_capacity.csv|model=LightGBM|capacity=2500|break_even_guard=False|contribution|d@@ against @@v:policy_capacity.csv|model=LightGBM|capacity=2500|break_even_guard=True|contribution|d@@).

## Are the differences between models visible?

A policy's contribution is a sum over records, so it can be bootstrapped in pairs like AP in part 13, conditional on the frozen scores and thresholds. Differences from logistic regression under the break-even policy, with marginal and simultaneous 95% intervals (eleven comparisons at once):

@@table:policy_paired_bootstrap.csv|where=policy==break-even (1/8)|sort=diff|desc|cols=model,diff,ci95_lo,ci95_hi,simultaneous95_lo,simultaneous95_hi|fmt=diff:+,.0f;ci95_lo:+,.0f;ci95_hi:+,.0f;simultaneous95_lo:+,.0f;simultaneous95_hi:+,.0f|rename=diff:difference,ci95_lo:marginal low,ci95_hi:marginal high,simultaneous95_lo:simultaneous low,simultaneous95_hi:simultaneous high@@

The random forest, XGBoost, LightGBM, scikit-learn's booster, CatBoost and the neural net earn more than logistic regression with simultaneous intervals above zero. Extra trees, the SVM, k-NN and the single tree are not separated from it, and Naive Bayes earns less. The visible advantages are about 150 to 200 units for the forest and the boosters (the neural net's is about 80) on a base of about 3,150, roughly 5% to 6%. An interval that includes zero is lack of evidence of a difference, not proof of equality.

## How much do the assumptions matter?

The table keeps the cost at 1, changes the value, and applies the break-even threshold 1/value to the raw scores; call-everyone is recomputed for each value.

@@table:policy_value_sensitivity.csv|where=model~LightGBM;Logistic regression;Gaussian Naive Bayes|cols=model,value,records_selected,contribution,call_everyone|fmt=value:d;records_selected:d;contribution:d;call_everyone:d|rename=call_everyone:call everyone@@

At a value of 4, calling everyone loses heavily (@@v:policy_value_sensitivity.csv|model=LightGBM|value=4|call_everyone|d@@) and the models earn about 700 to 1,050. At a value of 16, calling everyone earns @@v:policy_value_sensitivity.csv|model=LightGBM|value=16|call_everyone|d@@, and the models' advantage over it is only about 1,100 to 1,950: the more valuable a success, the less a ranking adds. The model ordering stays similar across values, but the *size* of any advantage over a trivial baseline changes with the assumption, so report the advantage over a relevant baseline next to the total and state the prices.

## A simple model or a booster?

The best policies earn about 5% to 6% more than logistic regression on 8,238 records. Whether that justifies a more complex pipeline depends on facts this dataset cannot supply: how many records are scored, what a mistake costs at scale, how often the model must be retrained, who maintains and explains it. Evidence that would change the choice: a larger or more recent evaluation set, a measured cost per contact, a prospective test with a control group (so uplift could be estimated) and a monitoring plan (part 16). Until then, the benefit of the better models is visible but modest, and logistic regression is a strong baseline.

## Analysis and conclusion: what we learned

- **A contribution is a retrospective simulation** under assumed prices; it does not estimate value created by contacting.
- **Compare with relevant baselines.** Call-nobody, call-everyone, matched random selection and a simple rule give context; all twelve models clear them widely under these prices.
- **Take the cut-off from the economics.** Here the break-even threshold roughly doubled the contribution against a default of 0.5 for every model with usable probabilities.
- **Capacity is a ceiling,** and differences between leading models are about 5% of the total and sensitive to the assumed value.

[Part 15](/series/classification/15-inside-the-winner/) opens the model development evidence would have chosen and asks what it relies on and where it fails.
