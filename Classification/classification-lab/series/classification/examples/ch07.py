import time
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()
prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)], remainder="passthrough")
A, B = prep.fit_transform(Xtr), prep.transform(Xte)

# ---- bagging from scratch: train each tree on a bootstrap sample, average the probabilities
rng = np.random.default_rng(0)
trees, votes = [], []
for i in range(200):
    rows = rng.integers(0, len(A), len(A))                      # sample WITH replacement
    t = DecisionTreeClassifier(min_samples_leaf=20, random_state=i).fit(A[rows], ytr[rows])
    trees.append(t); votes.append(t.predict_proba(B)[:, 1])
votes = np.array(votes)

print("one tree        AP:", round(average_precision_score(yte, votes[0]), 3))
for n in (5, 25, 100, 200):
    print(f"average of {n:>3} AP:", round(average_precision_score(yte, votes[:n].mean(axis=0)), 3))

# how different are the individual trees from each other?
corr = np.corrcoef(votes[:20])
print("mean correlation between two trees' scores:", round(corr[np.triu_indices(20, 1)].mean(), 3))

# ---- the random forest adds one trick: each split sees only a random subset of features
print()
for name, model in {
    "RF  max_features=sqrt": RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", n_jobs=-1, random_state=0),
    "RF  max_features=0.5 ": RandomForestClassifier(300, min_samples_leaf=10, max_features=0.5, n_jobs=-1, random_state=0),
    "RF  max_features=1.0 ": RandomForestClassifier(300, min_samples_leaf=10, max_features=1.0, n_jobs=-1, random_state=0),
    "Extra trees          ": ExtraTreesClassifier(300, min_samples_leaf=10, max_features="sqrt", n_jobs=-1, random_state=0),
}.items():
    t0 = time.perf_counter(); model.fit(A, ytr); secs = time.perf_counter() - t0
    print(f"{name}  AP={average_precision_score(yte, model.predict_proba(B)[:, 1]):.3f}  fit={secs:.1f}s")

# ---- out-of-bag estimate: a free validation score
rf = RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", oob_score=True, n_jobs=-1, random_state=0).fit(A, ytr)
print("\nOOB accuracy :", round(rf.oob_score_, 3))
print("OOB-based AP :", round(average_precision_score(ytr, rf.oob_decision_function_[:, 1]), 3))
print("test AP      :", round(average_precision_score(yte, rf.predict_proba(B)[:, 1]), 3))

# ---- how many trees are enough?
print()
for n in (10, 50, 100, 300, 600):
    m = RandomForestClassifier(n, min_samples_leaf=10, max_features="sqrt", n_jobs=-1, random_state=0).fit(A, ytr)
    print(f"n_estimators={n:<4} test AP={average_precision_score(yte, m.predict_proba(B)[:, 1]):.3f}")
