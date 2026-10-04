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

Add one column, `duration`, to a plain logistic regression and its average precision rises from 0.45 to 0.59. That is the biggest jump anywhere in this series, and it is worthless. The column exists only after the call is over.

Real datasets are full of columns like that, and of codes and trends that mislead more quietly. This chapter audits the file before any model is trusted.

<div class="callout">

**Goal.** Decide which columns may be used for the decision "rank planned contacts", and understand the codes and the time structure of the rest.

**Work plan.** For each column ask when its value exists. Measure what the unclear ones are worth. Check the codes (`999`, `unknown`). Then look at how the outcome rate moves through the file.

</div>

## The test every column must pass

For every column ask one question: *at the moment the bank decides whether to make this contact, does the value exist?* The documentation of the file (`bank-additional-names.txt`) says what each column describes, which is enough to sort them.

| feature | group | role | available | in main set |
|---|---|---|---|---|
| age | profile | customer | before | yes |
| job | profile | customer | before | yes |
| marital | profile | customer | before | yes |
| education | profile | customer | before | yes |
| default | profile | customer | before | yes |
| housing | profile | customer | before | yes |
| loan | profile | customer | before | yes |
| contact | schedule | policy | when scheduled | yes |
| month | schedule | policy | when scheduled | yes |
| day_of_week | schedule | policy | when scheduled | yes |
| duration | call outcome | outcome of the contact | after | no |
| campaign | contact count | policy | unclear | no |
| pdays | history | customer | before | yes |
| previous | history | customer | before | yes |
| poutcome | history | customer | before | yes |
| emp.var.rate | macro | context | before (as published) | yes |
| cons.price.idx | macro | context | before (as published) | yes |
| cons.conf.idx | macro | context | before (as published) | yes |
| euribor3m | macro | context | before (as published) | yes |
| nr.employed | macro | context | before (as published) | yes |

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

**Result.** Across the feature sets we tried, with a logistic regression and a LightGBM model at library defaults (mean average precision over 5 folds; a random ranking would score 0.113):

| feature set | Logistic regression | LightGBM |
|---|---|---|
| main | 0.448 | 0.463 |
| main + campaign | 0.449 | 0.465 |
| no schedule (profile, history, macro) | 0.423 | 0.444 |
| profile + history only | 0.338 | 0.344 |
| main + duration (not eligible; benchmark only) | 0.589 | 0.662 |

**What it means.** `duration` is the length of the last call. The dataset's own documentation says it "should be discarded if the intention is to have a realistic predictive model", and the reason is simple: the value does not exist before the call. That alone makes it unusable for this decision, whatever the mechanism behind its strength. Quoting the jump as a modelling success would promise a model that cannot be built.

## Campaign: a count tied to when the bank stopped

`campaign` counts the contacts made, including the last one. The other contact columns describe that last contact, so the count may also record *when the bank stopped calling*, which could depend on the outcome (plausibly after a subscription, or after the bank gave up; the documentation does not say). Here is how the outcome rate falls as the count rises:

| contacts in campaign (8 = 8 or more) | records | rate |
|---|---|---|
| 1 | 17,642 | 13.0% |
| 2 | 10,570 | 11.5% |
| 3 | 5,341 | 10.8% |
| 4 | 2,651 | 9.4% |
| 5 | 1,599 | 7.5% |
| 6 | 979 | 7.7% |
| 7 | 629 | 6.0% |
| 8 | 1,777 | 4.1% |

Later contacts may be harder, or large counts may mark records where the bank kept trying, or both; this file cannot separate them, so we do not rely on the column. Excluding it costs very little: the main feature set scores 0.448 with a logistic regression and 0.449 with `campaign` added (LightGBM: 0.463 and 0.465). The **main feature set** for the rest of the series is therefore the 18 columns marked "yes" in the table above.

Removing the schedule columns too lowers the logistic regression to 0.423; if they are not known at scheduling time, expect results closer to that row.

## Codes that look like numbers or values

- **`pdays = 999`** means "not previously contacted" (96.3% of records). It is a state, not a distance of 999 days. A linear or distance-based model treats it as a number, so we compared that with a representation that separates the state from the recency (a 0/1 flag plus the days, set to 0 when not contacted):

| model | raw value (999 = never contacted) | flag + recency |
|---|---|---|
| Logistic regression | 0.448 | 0.447 |
| k-nearest neighbours | 0.320 | 0.316 |
| LightGBM | 0.463 | 0.462 |

  On this data the two representations score the same within the fold-to-fold spread. We keep the raw column in the main comparison, and the recoding is available for any model that needs it.
- **`unknown`** is a documented label for missing values in `job`, `marital`, `education`, `default`, `housing` and `loan`. The shares range from 0.2% for `marital` to 20.9% for `default`. We keep it as its own level and make no claim about why a value is missing. Dropping those records would remove 26% of the data and change who is in the sample.
- **Duplicates.** 12 exact duplicate rows is too few to matter here.

## The file moves

The file is ordered by date, but it has no date column, so row position is a proxy for time. Cut it into ten equal chunks of 4,119 records and look at the outcome rate and the three-month Euribor rate in each:

![Bars: share of records ending in a subscription, per chunk of 4,119 records in file order. Line: mean euribor3m in the same chunks.](/series/classification/figures/ch02-drift.png)
*Figure 1. The outcome rate climbs from 2.8% in the first chunk to 46.0% in the last, while the Euribor rate falls from about 4.9% to 0.8%.*

This is a correlation in a file with one economic cycle. Later records may differ because of the economy, which clients the bank chose to call, how the campaign ran, or how records were kept; the file cannot say which. Practically, a model trained on early records meets a different world later, so there are two questions: *which algorithm learns this relationship best?* (a random split, parts 3 to 15) and *how would a model behave on later records?* (a chronological split, part 16).

## Analysis and conclusion: what we learned

`duration` fails the eligibility test; `campaign` is unclear and costs about 0.002 AP to leave out; `999` and `unknown` are structure, and the representation barely moves the score here; and the outcome rate drifts through the file without a known cause, so we design around it.

| Question | Decision in this series |
|---|---|
| Which columns are eligible? | The 18 columns of the main set. |
| What if the schedule is not known in advance? | Sensitivity run: scores drop to the "no schedule" row. |
| How are `999` and `unknown` handled? | Raw `pdays` and `unknown` as its own level; flag + recency checked in this chapter. |
| Random or chronological split? | Random for comparing algorithms, chronological for the deployment question. |

[Part 3](/series/classification/03-what-does-good-performance-mean/) turns to the question we keep postponing: if not accuracy, how do we grade a classifier?
