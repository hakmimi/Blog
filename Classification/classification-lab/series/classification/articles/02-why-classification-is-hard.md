---
title: "Why This Data Is Harder Than It Looks"
description: "One column lifts the score from 0.45 to 0.59 and cannot be used. Which columns are allowed, which are unclear, what the codes in the file mean, and why the data change over time."
series: "classification"
order: 2
date: 2026-09-30
updated: 2026-10-04
keywords: ["data leakage", "class imbalance", "distribution shift", "feature engineering", "pandas"]
readingTime: "10 min read"
figure: "ch02-duration-leak.png"
---

Add one column, `duration`, to a plain logistic regression and its average precision rises from @@v:data_feature_sets.csv|feature_set=main|model=Logistic regression|cv_ap_mean|.2f@@ to @@v:data_feature_sets.csv|feature_set=main + duration (not eligible; benchmark only)|model=Logistic regression|cv_ap_mean|.2f@@. That is the biggest jump anywhere in this series, and it is worthless. The column exists only after the call is over.

Real datasets are full of columns like that, and of codes and trends that mislead more quietly. This chapter audits the file before any model is trusted.

<div class="callout">

**Goal.** Decide which columns may be used for the decision "rank planned contacts", and understand the codes and the time structure of the rest.

**Work plan.** For each column ask when its value exists. Measure what the unclear ones are worth. Check the codes (`999`, `unknown`). Then look at how the outcome rate moves through the file.

**You will leave with** a feature list you can defend, a sensitivity check showing what each choice costs, and a reason not to read the time trend as a cause.

</div>

## The test every column must pass

For every column ask one question: *at the moment the bank decides whether to make this contact, does the value exist?* The documentation of the file (`bank-additional-names.txt`) says what each column describes, which is enough to sort them.

@@table:feature_availability.csv|cols=feature,group,role,available,in_main_set|rename=in_main_set:in main set@@

Three columns need a comment.

- **Macro indicators** are published quarterly, monthly or daily. Values published before the contact are legitimate inputs. In a real deployment, a decision about *future* contacts would need forecasts or scenarios for them, not the realised values stored in this file.
- **`contact`, `month`, `day_of_week`** are documented as attributes of the *last* contact. We treat them as known once the contact is scheduled. That is an assumption, so one sensitivity run below removes them.
- **`campaign`** is the number of contacts in the campaign, including the last one. We come back to it below.

## Duration: a benchmark number we cannot use

**Implementation.** Score the same model on the development rows with and without `duration`, using 5-fold cross-validation.

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)
dev, _ = train_test_split(np.arange(len(df)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)                      # development rows; the other 20% waits for part 12
cv = StratifiedKFold(5, shuffle=True, random_state=42)

def cv_ap(columns):
    cat = [c for c in columns if df[c].dtype == object]
    model = make_pipeline(make_column_transformer((OneHotEncoder(handle_unknown="ignore"), cat), remainder=StandardScaler()),
                          LogisticRegression(max_iter=2000))
    return cross_val_score(model, df.iloc[dev][columns], y.iloc[dev], cv=cv, scoring="average_precision").mean()

main = [c for c in df.columns if c not in ("duration", "campaign")]
print("main columns   :", round(cv_ap(main), 3))
print("main + duration:", round(cv_ap(main + ["duration"]), 3))
```

```output
main columns   : 0.448
main + duration: 0.589
```

**Result.** Across the feature sets we tried, with a logistic regression and a LightGBM model at library defaults (mean average precision over 5 folds; a random ranking would score @@j:data_profile.json|prevalence|.3f@@):

@@table:data_feature_sets.csv|pivot=feature_set:model:cv_ap_mean|fmt=Logistic regression:.3f;LightGBM:.3f|rename=feature_set:feature set@@

**What it means.** `duration` is the length of the last call. The dataset's own documentation says it "should be discarded if the intention is to have a realistic predictive model", and the reason is simple: the value does not exist before the call. That alone makes it unusable for this decision, whatever the mechanism behind its strength. Quoting the jump as a modelling success would promise a model that cannot be built.

## Campaign: a count tied to when the bank stopped

`campaign` counts the contacts made, including the last one. The record is the *last* contact of the campaign, so the count is also a record of when the bank stopped calling, and that can depend on the outcome (a campaign for a client usually ends after a subscription or after the bank gives up). Here is how the outcome rate falls as the count rises:

@@table:data_campaign_rates.csv|cols=campaign,records,rate|fmt=campaign:d;records:d;rate:.1%|rename=campaign:contacts in campaign (8 = 8 or more)@@

That pattern could mean the later contacts are harder, or that records with large counts are the ones where the bank kept trying, or both. We cannot separate them with this file, so we do not rely on the column. Excluding it costs very little: the main feature set scores @@v:data_feature_sets.csv|feature_set=main|model=Logistic regression|cv_ap_mean|.3f@@ with a logistic regression and @@v:data_feature_sets.csv|feature_set=main + campaign|model=Logistic regression|cv_ap_mean|.3f@@ with `campaign` added (LightGBM: @@v:data_feature_sets.csv|feature_set=main|model=LightGBM|cv_ap_mean|.3f@@ and @@v:data_feature_sets.csv|feature_set=main + campaign|model=LightGBM|cv_ap_mean|.3f@@). The **main feature set** for the rest of the series is therefore the 18 columns marked "yes" in the table above.

Removing the schedule columns as well (`contact`, `month`, `day_of_week`) lowers the score further, to @@v:data_feature_sets.csv|feature_set=no schedule (profile, history, macro)|model=Logistic regression|cv_ap_mean|.3f@@ for the logistic regression. If those columns are not really known at scheduling time, expect results closer to that row.

## Codes that look like numbers or values

- **`pdays = 999`** means "not previously contacted" (@@j:data_profile.json|pdays_999_share|.1%@@ of records). It is a state, not a distance of 999 days. A linear or distance-based model treats it as a number, so we compared that with a representation that separates the state from the recency (a 0/1 flag plus the days, set to 0 when not contacted):

@@table:data_sentinel.csv|pivot=model:pdays_representation:cv_ap_mean|rename=model:model@@

  On this data the two representations score the same within the fold-to-fold spread. We keep the raw column in the main comparison, and the recoding is available for any model that needs it.
- **`unknown`** is a documented label for missing values in `job`, `marital`, `education`, `default`, `housing` and `loan`. The shares range from @@j:data_profile.json|unknown_share_by_column.marital|.1%@@ for `marital` to @@j:data_profile.json|unknown_share_by_column.default|.1%@@ for `default`. We keep it as its own level and make no claim about why a value is missing. Dropping those records would remove @@j:data_profile.json|rows_with_unknown_label|.0%@@ of the data and change who is in the sample.
- **Duplicates.** @@j:data_profile.json|exact_duplicate_rows|d@@ exact duplicate rows is too few to matter here.

## The file moves

The file is ordered by date, but it has no date column, so row position is a proxy for time. Cut it into ten equal chunks of @@j:data_profile.json|chunk_size|d@@ records and look at the outcome rate and the three-month Euribor rate in each:

![Bars: share of records ending in a subscription, per chunk of 4,119 records in file order. Line: mean euribor3m in the same chunks.](/series/classification/figures/ch02-drift.png)
*Figure 1. The outcome rate climbs from @@j:data_profile.json|rate_by_chunk.0|.1%@@ in the first chunk to @@j:data_profile.json|rate_by_chunk.9|.1%@@ in the last, while the Euribor rate falls from about @@j:data_profile.json|euribor3m_by_chunk.0|.1f@@% to @@j:data_profile.json|euribor3m_by_chunk.9|.1f@@%.*

This is a correlation in a file with one economic cycle in it. Later records may differ from early ones for many reasons: the economy, which clients the bank chose to call, how the campaign was run, or how records were kept. We cannot tell which from this file. What we can say is practical: a model trained on early records meets a different world on later ones, so there are two separate questions. *Which algorithm learns this relationship best?* is answered with a random split (parts 3 to 15). *How would a model behave on later records?* needs a chronological split (part 16).

## Analysis and conclusion: what we learned

- **Eligibility comes before modelling.** `duration` fails the test outright. `campaign` is unclear, so it is out of the main set, with a measured cost of about 0.002 average precision.
- **Codes need reading.** `999` and `unknown` are structure, not numbers or noise. On this data the choice of representation barely moves the score.
- **The outcome rate drifts a lot** through the file, and we do not explain the drift. We design around it.

| Question | Decision in this series |
|---|---|
| Which columns are eligible? | The 18 columns of the main set. |
| What if the schedule is not known in advance? | Sensitivity run: scores drop to the "no schedule" row. |
| How are `999` and `unknown` handled? | Raw `pdays` and `unknown` as its own level; flag + recency checked in this chapter. |
| Random or chronological split? | Random for comparing algorithms, chronological for the deployment question. |

[Part 3](/series/classification/03-what-does-good-performance-mean/) turns to the question we keep postponing: if not accuracy, how do we grade a classifier?
