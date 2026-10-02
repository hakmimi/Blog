---
title: "Decision Trees: Easy to Read, Easy to Overfit"
description: "Compute Gini impurity by hand, watch an unrestricted tree score 0.999 on training data and 0.18 on unseen data, and learn the two knobs that fix it."
series: "classification"
order: 6
date: 2026-09-30
updated: 2026-10-02
keywords: ["decision trees", "gini impurity", "overfitting", "min_samples_leaf", "interpretable models"]
readingTime: "15 min read"
figure: "ch06-tree-overfit.png"
---

Logistic regression draws one straight boundary through feature space. A decision tree draws many small ones: *if `nr.employed` ≤ 5087 and `pdays` ≤ 16, then…* It can capture interactions and thresholds that a linear model has to be told about, and it can be printed and read like a flowchart.

It is also the easiest model in this series to ruin. We'll build the intuition with a hand-computed split, then deliberately overfit a tree so you can see the damage in numbers.

## Goals: what are we trying to achieve?

A tree can capture interactions a linear model cannot, and it is the easiest model in this series to ruin. Our goal is to see exactly how it overfits, and how to stop it.

By the end you will be able to:

- **Compute a Gini split gain by hand** and see that fitting a tree is that calculation repeated.
- **Spot overfitting in numbers**: the gap between training and cross-validated scores.
- **Choose a stopping rule** (`max_depth` or `min_samples_leaf`) and read a small tree like a flowchart.

## The work plan: how do we do it?

We start from the split and end at the printed tree:

1. **One split by hand**: Gini impurity and the gain from cutting `euribor3m`.
2. **Depth sweep**: train and cross-validated AP for depths 2 to unlimited.
3. **Leaf-size sweep**: `min_samples_leaf` as a better stopping rule.
4. **Read a tree**: a depth-3 tree printed with `export_text`.

## Implementation

### How a tree decides where to split

A tree is grown greedily. At every node it considers *every feature and every threshold*, picks the split that makes the two child groups as "pure" as possible, and recurses. "Pure" is measured by **Gini impurity**: for a node with positive fraction *p*, `gini = 2·p·(1−p)`. It's 0 for a node with only one class and peaks at 0.5 for a 50/50 mix.

Let's compute it ourselves on the training data:

```python
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

def gini(labels):
    p = np.mean(labels)
    return 2 * p * (1 - p)

def split_gain(feature, threshold, labels):
    left, right = labels[feature <= threshold], labels[feature > threshold]
    child = (len(left) * gini(left) + len(right) * gini(right)) / len(labels)
    return gini(labels) - child                     # impurity removed by the split

ytr_a = ytr.to_numpy()
print("root impurity:", round(gini(ytr_a), 4))
for t in (1.0, 3.0, 5.0):
    print(f"split euribor3m <= {t}: gain {split_gain(Xtr['euribor3m'].to_numpy(), t, ytr_a):.4f}")
```

```output
root impurity: 0.1999
split euribor3m <= 1.0: gain 0.0247
split euribor3m <= 3.0: gain 0.0164
split euribor3m <= 5.0: gain 0.0001
```

The root impurity is 0.1999 (an 11.3% base rate). Splitting on the interest rate at 1.0 removes 0.0247 of it — about 12% — because when rates are very low, subscription rates are much higher. A cut at 5.0 does almost nothing. **A tree fitting algorithm is just this calculation, repeated for every feature and every candidate threshold, at every node.** scikit-learn does it in optimised Cython, but nothing more mysterious is happening.

### The same tree, at different depths

The one thing we have to decide is *when to stop*. Let's vary `max_depth` and measure average precision twice: on the data the tree was trained on, and with 3-fold cross-validation (data it hasn't seen).

```python
from sklearn.compose import ColumnTransformer
from sklearn.metrics import average_precision_score
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

cat = X.select_dtypes("object").columns.tolist()
prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                         remainder="passthrough")          # trees don't need scaling

for depth in (2, 3, 5, 8, 12, None):
    tree = make_pipeline(prep, DecisionTreeClassifier(max_depth=depth, random_state=42))
    tree.fit(Xtr, ytr)
    train_ap = average_precision_score(ytr, tree.predict_proba(Xtr)[:, 1])
    cv_ap = cross_val_score(tree, Xtr, ytr, cv=3, scoring="average_precision").mean()
    leaves = tree[-1].get_n_leaves()
    print(f"max_depth={str(depth):<5} leaves={leaves:>5}  train AP={train_ap:.3f}   CV AP={cv_ap:.3f}")
```

```output
max_depth=2     leaves=    4  train AP=0.346   CV AP=0.345
max_depth=3     leaves=    8  train AP=0.374   CV AP=0.370
max_depth=5     leaves=   32  train AP=0.435   CV AP=0.408
max_depth=8     leaves=  184  train AP=0.517   CV AP=0.384
max_depth=12    leaves=  753  train AP=0.657   CV AP=0.301
max_depth=None  leaves= 4930  train AP=0.999   CV AP=0.176
```

This table is the clearest picture of overfitting you'll see:

- At depth 2 or 3 train and CV scores match: the tree is **underfitting** — too simple to use the signal.
- At **depth 5** validation AP peaks at 0.408. This is the model that generalises best.
- Past that the train score keeps climbing (0.517, 0.657… **0.999**) while the validation score *falls*. With `max_depth=None` the tree grows 4,930 leaves — roughly one per 7 training customers — and scores essentially perfectly on the data it memorised. On new customers it scores 0.176, barely above the 0.113 you'd get from random guessing.

<div class="callout gotcha">

**Gotcha — the score on your training set is worthless for trees.** Unrestricted trees can always reach a training score near 1. If you see a tree or forest report "AP 0.99" it probably reported it on training rows. Always evaluate on data the model never saw.

</div>

### Stopping rules that matter

`max_depth` is a blunt instrument: it limits every branch equally. The more useful knob is **`min_samples_leaf`**: a split is only allowed if both children would contain at least that many customers. Rare-but-genuine patterns can have a deep branch; noise can't, because a leaf of 3 customers fails the test.

```python
for leaf in (1, 10, 50, 200, 500):
    tree = make_pipeline(prep, DecisionTreeClassifier(min_samples_leaf=leaf, random_state=42))
    cv_ap = cross_val_score(tree, Xtr, ytr, cv=3, scoring="average_precision").mean()
    print(f"min_samples_leaf={leaf:<4} CV AP={cv_ap:.3f}")
```

```output
min_samples_leaf=1    CV AP=0.176
min_samples_leaf=10   CV AP=0.352
min_samples_leaf=50   CV AP=0.432
min_samples_leaf=200  CV AP=0.425
min_samples_leaf=500  CV AP=0.398
```

A leaf size of 50–200 beats the best depth-limited tree (0.432 vs 0.408) — unlimited depth but each leaf must be statistically meaningful. There's another benefit: leaf values become *probabilities* (fraction of positives among ≥50 customers) rather than jumpy 0/1 guesses, which matters for ranking. A leaf with one customer says "100%"; a leaf of 50 says something like "34%".

### Reading a tree

The biggest advantage of a small tree is that it doubles as documentation. Here's one with depth 3, printed:

```python
from sklearn.tree import export_text

small = make_pipeline(prep, DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, random_state=42)).fit(Xtr, ytr)
print(export_text(small[-1], feature_names=list(small[0].get_feature_names_out()), show_weights=True))
```

```output
|--- remainder__nr.employed <= 5087.65
|   |--- remainder__pdays <= 16.50
|   |   |--- cat__day_of_week_mon <= 0.50
|   |   |   |--- weights: [205.00, 583.00] class: 1
|   |   |--- cat__day_of_week_mon >  0.50
|   |   |   |--- weights: [93.00, 109.00] class: 1
|   |--- remainder__pdays >  16.50
|   |   |--- cat__contact_telephone <= 0.50
|   |   |   |--- weights: [1552.00, 957.00] class: 0
|   |   |--- cat__contact_telephone >  0.50
|   |   |   |--- weights: [382.00, 110.00] class: 0
|--- remainder__nr.employed >  5087.65
|   |--- remainder__cons.conf.idx <= -46.65
|   |   |--- remainder__euribor3m <= 1.53
|   |   |   |--- weights: [1611.00, 357.00] class: 0
|   |   |--- remainder__euribor3m >  1.53
|   |   |   |--- weights: [110.00, 94.00] class: 0
|   |--- remainder__cons.conf.idx >  -46.65
|   |   |--- cat__month_oct <= 0.50
|   |   |   |--- weights: [25264.00, 1468.00] class: 0
|   |   |--- cat__month_oct >  0.50
|   |   |   |--- weights: [21.00, 34.00] class: 1
```

The `weights` are `[no, yes]` counts in each leaf. Follow the first branch: *the economy is weak (`nr.employed` ≤ 5087) AND the customer was contacted before within 16 days AND it isn't Monday* → 205 no, **583 yes** (74% conversion). That's the best segment in the tree, and it comes from a pattern no linear model would express without hand-made interaction features: "recently contacted, during a downturn".

<div class="callout tip">

**Sanity check:** in that printed tree, `nr.employed ≤ 5087` splits the data at the root because it's a stand-in for *time* — low employment numbers only occur late in the dataset. [Part 16](/series/classification/16-when-time-breaks-the-model/) shows what that does to a model asked to predict the future.

</div>

## What did we get? Results

Average precision by tree depth, trained on the training part and cross-validated (3 folds):

| max_depth | Leaves | Train AP | CV AP |
|---|---|---|---|
| 2 | 4 | 0.346 | 0.345 |
| 3 | 8 | 0.374 | 0.370 |
| 5 | 32 | 0.435 | 0.408 |
| 8 | 184 | 0.517 | 0.384 |
| 12 | 753 | 0.657 | 0.301 |
| None | 4,930 | 0.999 | 0.176 |

- **Best by leaf size:** `min_samples_leaf` of 50 gives CV AP 0.432, and 200 gives 0.425, both above the best depth-limited tree (0.408).
- **Best segment in the printed tree:** 205 no and 583 yes (74% conversion).

![Training average precision keeps rising with depth while cross-validated average precision peaks at depth 5 and then collapses.](/series/classification/figures/ch06-tree-overfit.png)
*Figure 1. The overfitting gap. Train and validation scores agree for shallow trees and diverge once the tree has enough leaves to memorise individual customers.*

## Analysis and conclusion: what did we learn?

- **Overfitting in one table.** The unlimited tree scores 0.999 on the data it memorised and 0.176 on new customers, barely above the 0.113 of random guessing.
- **Depth 5 is the sweet spot for depth alone**, and leaf size does better: every leaf must be statistically meaningful.
- **Small trees document the data.** The best segment (weak economy, contacted before within 16 days, not Monday) is an interaction a linear model would need by hand.
- **`nr.employed` is a stand-in for time.** Low values only occur late in the file, which matters in [Part 16](/series/classification/16-when-time-breaks-the-model/).

### Why single trees aren't the destination

A single tuned tree gets a cross-validated AP of about 0.43 — competitive with logistic regression (0.45) on this data, which is itself a finding. But trees have three weaknesses:

1. **High variance.** Change a few hundred training rows and the top splits can change completely. Two trees with equal accuracy can give opposite explanations.
2. **Blocky probability estimates.** A depth-5 tree has 32 leaves, so it can output at most 32 distinct scores. Ranking is coarse; ties are common.
3. **Hard-edged thresholds.** A customer with `euribor3m=1.52` and one at `1.54` are treated as different species.

The fix for all three is the same idea: don't trust one tree — average hundreds of them. [Part 7](/series/classification/07-bagging-random-forests/) builds exactly that, from scratch.

### So what did we do?

We computed a split by hand, watched a tree go from underfitting to memorising, and saw that leaf size is a better stopping rule than depth. A single tuned tree reaches a cross-validated AP of about 0.43, close to logistic regression, but it is unstable and coarse.

### In the next part
