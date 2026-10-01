import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

COST, VALUE = 1.0, 8.0
df = pd.read_csv("bank-additional-full.csv", sep=";")           # the file is in chronological order
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
cat = X.select_dtypes("object").columns.tolist()
Xc = X.copy()
for c in cat:
    Xc[c] = pd.Categorical(Xc[c], categories=sorted(X[c].unique()))

cut = int(len(X) * 0.8)                                          # train on the past, test on the future
tr, te = np.arange(cut), np.arange(cut, len(X))
print(f"train rows 0-{cut - 1}: {y[tr].mean():.1%} subscribe   |   test rows {cut}-{len(X) - 1}: {y[te].mean():.1%} subscribe")

params = dict(n_estimators=400, learning_rate=0.02, num_leaves=31, min_child_samples=100,
              subsample=0.7, subsample_freq=1, colsample_bytree=0.6, verbose=-1, random_state=42)
prep = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cat)], remainder=StandardScaler())

def profit(p, t=1 / 8):
    call = p >= t
    return VALUE * y[te][call].sum() - COST * call.sum()

def report(name, p):
    best = max(np.unique(np.quantile(p, np.linspace(0, .995, 300))), key=lambda t: profit(p, t))
    print(f"{name:<34} AP={average_precision_score(y[te], p):.3f}  AUC={roc_auc_score(y[te], p):.3f}  mean p={p.mean():.3f}  "
          f"calls@1/8={int((p >= 1 / 8).sum()):5d}  profit@1/8={profit(p):6.0f}  (best possible {profit(p, best):6.0f})")

print(f"call everyone: profit {profit(np.ones(len(te)), 0.5):.0f}\n")
lgbm = LGBMClassifier(**params).fit(Xc.iloc[tr], y[tr]);                   p_l = lgbm.predict_proba(Xc.iloc[te])[:, 1]
logit = make_pipeline(prep, LogisticRegression(C=1, max_iter=2000)).fit(X.iloc[tr], y[tr]); p_g = logit.predict_proba(X.iloc[te])[:, 1]
report("LightGBM, trained on the past", p_l)
report("Logistic regression, past", p_g)
print(f"(the SAME models on a random split scored AP 0.496 / 0.465)\n")

# --- fixes ------------------------------------------------------------------------------------------------
macro = ["emp.var.rate", "cons.price.idx", "cons.conf.idx", "euribor3m", "nr.employed"]
m2 = LGBMClassifier(**params).fit(Xc.iloc[tr].drop(columns=macro), y[tr])
report("LightGBM without macro columns", m2.predict_proba(Xc.iloc[te].drop(columns=macro))[:, 1])

recent = tr[len(tr) // 2:]                                                  # only the newest half of training data
m3 = LGBMClassifier(**params).fit(Xc.iloc[recent], y[recent])
report("LightGBM, recent half only", m3.predict_proba(Xc.iloc[te])[:, 1])

# prior-shift correction: rescale odds by the (known/estimated) change in base rate
def shift(p, old, new):
    odds = p / (1 - p) * (new / (1 - new)) / (old / (1 - old))
    return odds / (1 + odds)
report("LightGBM + base-rate correction", shift(np.clip(p_l, 1e-6, 1 - 1e-6), y[tr].mean(), y[te].mean()))

# --- does the ranking of the models survive the move to a chronological split? ---------------------------------
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

dense = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)], remainder=StandardScaler())
candidates = {
    "LightGBM":                     (LGBMClassifier(**params), "cat"),
    "sklearn HistGradientBoosting": (HistGradientBoostingClassifier(max_leaf_nodes=15, learning_rate=0.1, l2_regularization=1, categorical_features="from_dtype", early_stopping=True, random_state=42), "cat"),
    "XGBoost":                      (XGBClassifier(n_estimators=400, learning_rate=0.02, max_depth=4, subsample=0.7, colsample_bytree=0.6, tree_method="hist", enable_categorical=True, random_state=42), "cat"),
    "Random forest":                (make_pipeline(dense, RandomForestClassifier(300, min_samples_leaf=10, max_features=0.3, n_jobs=-1, random_state=42)), "raw"),
    "Decision tree":                (make_pipeline(dense, DecisionTreeClassifier(min_samples_leaf=100, random_state=42)), "raw"),
    "Logistic regression":          (make_pipeline(prep, LogisticRegression(C=1, max_iter=2000)), "raw"),
    "k-nearest neighbors":          (make_pipeline(dense, KNeighborsClassifier(120, n_jobs=-1)), "raw"),
}
print(f"\n{'model':<30}{'AP':>7}{'AUC':>7}{'mean p':>8}{'calls@1/8':>11}{'profit@1/8':>12}")
rows = []
for name, (est, view) in candidates.items():
    F = Xc if view == "cat" else X
    p = est.fit(F.iloc[tr], y[tr]).predict_proba(F.iloc[te])[:, 1]
    rows.append((name, average_precision_score(y[te], p), roc_auc_score(y[te], p), p.mean(), int((p >= 1 / 8).sum()), profit(p)))
for r in sorted(rows, key=lambda r: -r[1]):
    print(f"{r[0]:<30}{r[1]:7.3f}{r[2]:7.3f}{r[3]:8.3f}{r[4]:11d}{r[5]:12.0f}")
pd.DataFrame(rows, columns=["model", "average_precision", "roc_auc", "mean_p", "calls_at_eighth", "profit_at_eighth"]).to_csv("../../artifacts/chronological_leaderboard.csv", index=False)

# --- export for the in-browser prior-shift lab (public/js/prior-shift-lab.js) ---------------------------------
import json
json.dump({"y": y[te].tolist(), "train_rate": float(y[tr].mean()), "test_rate": float(y[te].mean()),
           "models": {"LightGBM": [round(float(v), 4) for v in p_l], "Logistic regression": [round(float(v), 4) for v in p_g]}},
          open("../../artifacts/prior_shift_lab.json", "w"), separators=(",", ":"))
