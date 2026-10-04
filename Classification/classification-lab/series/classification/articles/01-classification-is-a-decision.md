---
title: "Classification Is a Decision, Not a Score"
description: "A model that never looks at a client is right 88.7% of the time and finds nobody. Why that number says so little, what one row of this dataset is, and the rules every comparison in the series follows."
series: "classification"
order: 1
date: 2026-09-30
updated: 2026-10-04
keywords: ["classification", "machine learning", "baseline", "bank marketing", "pandas"]
readingTime: "9 min read"
figure: "ch01-segments.png"
---

A model that has never looked at a single client is right 88.7% of the time. It also finds none of the people we are looking for.

That pair of facts is the reason for this series. The data come from a Portuguese bank's telephone campaigns for a term deposit: @@j:data_profile.json|rows|d@@ records, @@j:data_profile.json|positives|d@@ of them (@@j:data_profile.json|prevalence|.1%@@) ending in a subscription. Contacts cost effort and most go nowhere, so the practical question is **which planned contacts deserve that effort**.

<div class="callout">

**Goal.** Understand the data and the decision well enough to judge any classifier fairly.

**Work plan.** Pin down what a row is, count the outcomes, score two baselines (do nothing, and a rule a human could write), look for signal in the raw rates, and fix the rules every later comparison follows.

</div>

## What one row is, and what it is not

The file is `bank-additional-full.csv` from the [UCI Machine Learning Repository](https://doi.org/10.24432/C5K306) (CC BY 4.0): 20 input columns plus the outcome `y`, "ordered by date (from May 2008 to November 2010)", according to its documentation. That documentation matters, because the older `bank-full` variant of this dataset defines some columns differently (for example `pdays`).

Three words need care.

- **Record.** One row. The file has no client identifier, so we cannot say how many distinct clients it holds, or whether one client appears in several records. @@j:data_profile.json|exact_duplicate_rows|d@@ rows are exact duplicates of another row.
- **Contact.** One call attempt. The documentation describes `contact`, `month`, `day_of_week` and `duration` as attributes of "the last contact of the current campaign", and `campaign` as the "number of contacts performed during this campaign and for this client (includes last contact)". `campaign` is above 1 in @@j:data_profile.json|campaign_gt1_share|.1%@@ of records and reaches @@j:data_profile.json|campaign_max|d@@. So a record looks like a summary of one client's campaign: the last contact plus a count of how many contacts it took.
- **Decision.** Just before a planned contact, rank the planned contacts by how likely each is to end in a subscription, so the bank can choose which to make. Only information that exists at that moment may be a feature, and the schedule (channel, month, weekday) is assumed to be known. Part 2 checks every column against that rule.

The label `y` says whether the client subscribed. It does not say how many calls it took, what they cost, or whether the client would have subscribed anyway; part 14 depends on these limits.

## Two numbers before any model

**Implementation.** Count the outcomes and score the laziest possible classifier. All snippets in this series read the file from the working directory.

```python
import pandas as pd

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)          # 1 = the client subscribed

print(df.shape)
print(f"{y.sum()} subscriptions = {y.mean():.1%} of records")
print(f"accuracy of always saying no: {(y == 0).mean():.3f}")
```

**Result.**

```output
(41188, 20)
4640 subscriptions = 11.3% of records
accuracy of always saying no: 0.887
```

**What it means.** Accuracy is a legitimate metric, but it hides the question here. Saying "no" to everyone scores 0.887 and finds zero subscribers. A perfect classifier would score 1.000, so the whole room for improvement is 11.3 points, and it all sits in the 11.3% minority. Metrics that look at the positives are the subject of part 3.

## A rule you could say out loud

**Implementation.** A baseline you could explain in a meeting: *only contact people who said yes in the previous campaign.*

```python
rule = df["poutcome"] == "success"
hits = int((rule & (y == 1)).sum())
print(f"rule selects {rule.sum()} records, {hits} subscribe -> precision {hits / rule.sum():.2f}, recall {hits / y.sum():.2f}")
```

**Result.**

```output
rule selects 1373 records, 894 subscribe -> precision 0.65, recall 0.19
```

**What it means.** Two of every three selected contacts succeed (precision 0.65), but the rule reaches only 19% of all subscribers (recall 0.19). A stricter rule would raise precision and lower recall. A better model can lift both at once, but for any single score, moving the cut-off trades one for the other. **Where to sit on that trade is a business decision, not a statistical one.** That is why this series says "classification is a decision".

## Where the signal is

**Implementation.** Even raw counts show structure. Here is the subscription rate by contact channel and by the outcome of the previous campaign, with sizes:

```python
for col in ["contact", "poutcome"]:
    print(y.groupby(df[col]).agg(["mean", "size"]).round(3), end="\n\n")
```

**Result.**

```output
            mean   size
contact                
cellular   0.147  26144
telephone  0.052  15044

              mean   size
poutcome                 
failure      0.142   4252
nonexistent  0.088  35563
success      0.651   1373
```

![Subscription rate by contact channel, previous outcome and month. The dashed line is the 11.3% average.](/series/classification/figures/ch01-segments.png)
*Figure 1. Raw subscription rates by segment. March, September, October and December reach 44% to 51%, but together they hold only 2,016 records (4.9%).*

**What it means.** Cellular contacts end in a subscription 14.7% of the time and landline contacts 5.2%, a ratio of about 2.8 to 1. Previous successes succeed again 65.1% of the time. These are descriptive rates, not causes. The bank decided when to use each channel, so a channel gap can reflect who was reached and when, not what the channel does. Part 2 shows how much the calendar matters.

## Analysis and conclusion: what we learned

Accuracy alone cannot grade this problem (do-nothing scores 0.887 and finds nothing), a one-line rule is already a real classifier with a trade-off every model must face, and the raw rates are descriptive and shaped by the bank's own choices. Four rules hold for the rest of the series.

1. **Records, not clients.** "Record" is a row, "contact" a call, "client" the person the documentation describes. We never claim records are distinct people.
2. **An illustrative price list.** A contact costs 1 and a subscription is worth 8: teaching assumptions, not the bank's figures. On past records they give a retrospective policy simulation, not value created by calling (part 14).
3. **A written protocol.** Records are split once, at random and stratified, into *development* (80%, seed 42) and *comparison* (20%). Every choice is made on development data with cross-validation; algorithms are compared on the comparison part with settings frozen. Earlier drafts did look at it while exploring, so it is a controlled benchmark, not an untouched test set. A chronological evaluation covers later records (part 16).
4. **Uncertainty with every comparison.** A difference of 0.004 is not a result until we know how much it moves with a different sample.

*Sources.* Moro, Cortez and Rita (2014), [A data-driven approach to predict the success of bank telemarketing](https://doi.org/10.1016/j.dss.2014.03.001); the dataset and its documentation at the [UCI repository](https://doi.org/10.24432/C5K306).

The races use twelve models plus a no-model baseline. [Part 2](/series/classification/02-why-classification-is-hard/) first asks which columns we are allowed to use at all, because one of them changes everything.
