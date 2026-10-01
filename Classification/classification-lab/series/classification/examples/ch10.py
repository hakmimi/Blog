import time
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import ParameterSampler, StratifiedKFold, cross_val_score, train_test_split

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
for c in X.select_dtypes("object"):
    X[c] = X[c].astype("category")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

base = HistGradientBoostingClassifier(categorical_features="from_dtype", early_stopping=True, random_state=0)
space = {
    "learning_rate":     [0.02, 0.03, 0.05, 0.08, 0.12, 0.2],
    "max_leaf_nodes":    [4, 8, 15, 31, 63],
    "min_samples_leaf":  [10, 20, 50, 100, 200],
    "l2_regularization": [0, 0.1, 1, 10],
    "max_features":      [0.3, 0.6, 1.0],
}
print("search space size:", np.prod([len(v) for v in space.values()]), "combinations")

# ---- defaults first -------------------------------------------------------------------------
cv = StratifiedKFold(3, shuffle=True, random_state=0)
d = base.fit(Xtr, ytr)
print(f"defaults: CV AP={cross_val_score(base, Xtr, ytr, cv=cv, scoring='average_precision').mean():.3f}"
      f"  test AP={average_precision_score(yte, d.predict_proba(Xte)[:, 1]):.3f}")

# ---- evaluate 40 random candidates once; reuse the table for every budget analysis ---------------
rows = []
t0 = time.perf_counter()
for params in ParameterSampler(space, n_iter=40, random_state=0):
    m = base.set_params(**params)
    cv_ap = cross_val_score(m, Xtr, ytr, cv=cv, scoring="average_precision").mean()
    te_ap = average_precision_score(yte, m.fit(Xtr, ytr).predict_proba(Xte)[:, 1])
    rows.append({**params, "cv_ap": cv_ap, "test_ap": te_ap})
table = pd.DataFrame(rows)
table.to_csv("../../artifacts/ch10_candidates.csv", index=False)   # reused by the chapter figure
print(f"40 candidates x 3 folds took {time.perf_counter() - t0:.0f}s")
print(table.sort_values("cv_ap", ascending=False).head(5).round(3).to_string(index=False))
print("range of CV AP over all 40:", table.cv_ap.min().round(3), "to", table.cv_ap.max().round(3))

# ---- what does a bigger budget buy? shuffle the candidate order 200 times ---------------------------
rng = np.random.default_rng(0)
print("\nbudget  best CV AP   test AP of the winner   spread(test AP)")
for budget in (1, 2, 4, 8, 16, 40):
    cvs, tes = [], []
    for _ in range(200):
        pick = table.iloc[rng.permutation(len(table))[:budget]]
        w = pick.loc[pick.cv_ap.idxmax()]
        cvs.append(w.cv_ap); tes.append(w.test_ap)
    print(f"{budget:>5}   {np.mean(cvs):.3f}        {np.mean(tes):.3f}                 +-{np.std(tes):.3f}")
