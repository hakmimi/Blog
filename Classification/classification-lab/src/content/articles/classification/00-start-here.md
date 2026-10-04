---
title: "Start Here: A Map of the Series"
description: "What this series is, the data it uses, the vocabulary it assumes, the rules every comparison follows, and how the sixteen parts fit into one story that starts with a decision and ends with a decision."
series: "classification"
order: 0
label: "0"
date: 2026-10-04
updated: 2026-10-04
keywords: ["classification", "machine learning", "bank marketing", "series map", "evaluation protocol"]
readingTime: "8 min read"
---

A bank can phone a few thousand people a day. Most calls end in "no thanks". The only real question is **whom to call next**, and a classifier is a tool for answering it.

This series takes that question seriously. It uses one real dataset, twelve models and a written evaluation protocol, and it shows every line of code with the output that code produced. Before the first model appears, this page gives you the map, the words, and the rules.

<div class="callout">

**Goal.** Leave with a map of the sixteen parts, a short vocabulary, and a clear idea of what the numbers in the series can and cannot prove.

**Work plan.** Meet the data and its source, fix the vocabulary, state the decision the models serve, write down the protocol, then walk through the parts as one story.

</div>

## The data, and where it comes from

The data is *Bank Marketing* from the [UCI Machine Learning Repository](https://doi.org/10.24432/C5K306), file `bank-additional-full.csv`, published by Moro, Cortez and Rita. It describes telephone marketing calls by a Portuguese bank that offered a term deposit, between May 2008 and November 2010. The documentation says the file is ordered by date, and part 16 relies on that.

There are 41,188 rows, 20 input columns and one outcome, `y`: did the client subscribe. 4,640 rows (11.3%) say yes. The data keeps its own licence (CC BY 4.0), so the series does not redistribute it. A script, `download_data.py`, fetches the file and checks its checksum. Here is the whole check in four lines:

```python
import pandas as pd

df = pd.read_csv("bank-additional-full.csv", sep=";")
print(df.shape, "->", df["y"].eq("yes").mean().round(3), "share of yes")
print(df.columns.tolist()[:6], "...")
```

```output
(41188, 21) -> 0.113 share of yes
['age', 'job', 'marital', 'education', 'default', 'housing'] ...
```

**One word of care.** A row is a *record*, not a customer. The file has no client identifier, so we never claim to know how many distinct people it holds. Part 1 explains why.

## Seven words used everywhere

**Implementation.** There is no heavy mathematics on this page. Each term gets one line, and each is used the same way in every part.

- **Classifier.** A function that takes the facts about a record and returns a *score* for the class we care about, here "will subscribe".
- **Probability against decision.** A score may be (or may be turned into) a probability. A *decision* is what we do with it: call, or do not call. The cut-off between the two is the *threshold*, and choosing it is a business decision.
- **Positive and negative.** Positive is the rare class we look for (a subscription). Negative is everything else.
- **Base rate.** The share of positives in the data. Here it is about one in nine, which is why accuracy alone is a poor judge.
- **Train and test.** Fit on one set of records, grade on records the model never saw. Grading on what the model memorised measures memory, not skill.
- **Leakage.** Using information that would not exist at the moment of the decision. It makes results look better than they will be in real use. Part 2 meets a famous example in this very file.
- **Drift.** The world changes, so a model trained on the past meets different data in the future. Part 16 measures how much that costs.

## The decision behind the models

**Why it matters.** Every call costs agent time and the number of calls per day is limited. If a call costs `c` and a subscription is worth `v`, then calling someone pays off when their chance of subscribing is above `c / v`. That ratio is the *break-even probability*. The prices used here are teaching assumptions, not the bank's figures: 1 for a contact and 8 for a subscription, so the break-even is 0.125. One line to remember: **the score ranks people, and the prices decide where to stop**.

## The rules of the game

Every comparison in the series follows the same written protocol (the [Methods page](/series/classification/methods/) has the full version).

1. **The moment of prediction is just before the call.** Anything known only after the call, such as its length, is not a legal input.
2. **Two splits, once.** Records are divided at random, stratified by outcome with seed 42, into *development* (80%) and *comparison* (20%). Every choice is made on development data. The comparison split grades the finished, frozen pipelines. It was seen in early drafts, so it is a controlled teaching benchmark, not an untouched test set.
3. **The same effort for every model.** Each model gets its default setting plus up to seven random candidates, scored by 3-fold cross-validation on development data.
4. **Several metrics, with uncertainty.** Average precision (AP), ROC-AUC, log loss, a calibration error, and a simulated contribution under the price list, each with a paired bootstrap interval where models are compared.
5. **Time gets its own test.** Part 16 trains on the first 80% of the file and scores the last 20%.

**What the benchmark cannot prove.** It cannot show that calling someone *causes* a subscription. It cannot show that the file's row order is true calendar order. And it cannot crown a model family for every table of data, only describe how twelve concrete pipelines behaved on this one.

## How the sixteen parts fit together

Read as one story with four stages. Click any box to jump to that part.

<div class="flow" role="group" aria-label="Flowchart of the series: four stages, parts 1 to 16">
<div class="flow-start"><a href="/series/classification/00b-from-lines-to-sigmoid/"><b>0 · 0b</b> Map and warm-up: lines, sigmoids, apples</a></div>
<div class="flow-arrow" aria-hidden="true"></div>
<section class="flow-stage"><h4><span>1</span> Foundations</h4><p>What are we deciding, and how do we grade it?</p><ol>
<li><a href="/series/classification/01-classification-is-a-decision/"><b>1</b> The decision</a></li>
<li><a href="/series/classification/02-why-classification-is-hard/"><b>2</b> The data and its traps</a></li>
<li><a href="/series/classification/03-what-does-good-performance-mean/"><b>3</b> What “good” means</a></li>
<li><a href="/series/classification/04-objective-functions/"><b>4</b> What the model minimises</a></li>
</ol></section>
<div class="flow-arrow" aria-hidden="true"></div>
<section class="flow-stage"><h4><span>2</span> Models</h4><p>How does each family work, and how well does it do?</p><ol>
<li><a href="/series/classification/05-logistic-regression-naive-bayes/"><b>5</b> Logistic regression, Naive Bayes</a></li>
<li><a href="/series/classification/06-decision-trees/"><b>6</b> Trees</a></li>
<li><a href="/series/classification/07-bagging-random-forests/"><b>7</b> Forests</a></li>
<li><a href="/series/classification/08-gradient-boosting/"><b>8</b> Boosting</a></li>
<li><a href="/series/classification/09-other-classification-families/"><b>9</b> k-NN, SVM, neural net</a></li>
</ol></section>
<div class="flow-arrow" aria-hidden="true"></div>
<section class="flow-stage"><h4><span>3</span> Calibration and decisions</h4><p>Which model wins, is it real, and what is it worth?</p><ol>
<li><a href="/series/classification/10-hyperparameter-search/"><b>10</b> Tuning without fooling yourself</a></li>
<li><a href="/series/classification/11-probabilities-calibration-thresholds-costs/"><b>11</b> Probabilities, thresholds, cost</a></li>
<li><a href="/series/classification/12-head-to-head-leaderboard/"><b>12</b> The head-to-head</a></li>
<li><a href="/series/classification/13-is-the-winner-real/"><b>13</b> Is the winner real?</a></li>
<li><a href="/series/classification/14-pricing-the-models/"><b>14</b> Pricing the models</a></li>
</ol></section>
<div class="flow-arrow" aria-hidden="true"></div>
<section class="flow-stage"><h4><span>4</span> Audit and time</h4><p>What does it rely on, and does time break it?</p><ol>
<li><a href="/series/classification/15-inside-the-winner/"><b>15</b> Inside the chosen model</a></li>
<li><a href="/series/classification/16-when-time-breaks-the-model/"><b>16</b> When time breaks the model</a></li>
</ol></section>
<div class="flow-arrow" aria-hidden="true"></div>
<div class="flow-end"><b>The result</b> a ranking, a threshold from the prices, and a statement of what it cannot prove</div></div>

*Figure 0. The series as a flow: each stage hands a question to the next.*

**Foundations (parts 1 to 4).** *Classification is a decision* (1) starts from the do-nothing model that is right 88.7% of the time and finds nobody. *Why the data is hard* (2) checks which columns are legal. *What good means* (3) grades one model five ways. *What the model minimises* (4) opens the objective functions.

**Models (parts 5 to 9).** The baseline you must beat, logistic regression and Naive Bayes (5). Then trees (6), forests (7), boosting (8), and distance, margins and networks (9). Each part explains how the model works, then measures it.

**Calibration and decisions (parts 10 to 14).** How to tune without fooling yourself (10). Whether scores are probabilities (11). The head-to-head of all twelve models (12). Whether the winner is real (13). What the ranking is worth in money, under stated prices (14).

**Audit and time (parts 15 and 16).** What the chosen model relies on and whom it misses (15). Then what happens when the future is not like the past (16).

One short detour sits before part 1. [Part 0b](/series/classification/00b-from-lines-to-sigmoid/) shows, with 400 made-up apples, why a straight line fails on a yes/no question and why a grid of cells overfits. It is the cleanest picture of the idea that runs through the whole series.

## Analysis and conclusion

The series begins with *classification is a decision* and ends with a finding about decisions: a good ranking is necessary, but the threshold, the prices and the stability of the data over time decide what a model is worth. Every number in the following parts is printed by code in the repository, so you can rerun it, and each claim is scoped to what the protocol can support.

For the live version, try the [Fruit Lab](/series/classification/fruit-lab/), where you move three fruit measurements and inspect the nearest neighbours behind each prediction. Then continue to [Part 0b](/series/classification/00b-from-lines-to-sigmoid/), or jump straight to [Part 1](/series/classification/01-classification-is-a-decision/).
