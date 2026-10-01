import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.frozen import FrozenEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
Xfit, Xcal, yfit, ycal = train_test_split(Xtr, ytr, test_size=0.25, stratify=ytr, random_state=1)   # carve out a calibration set
cat = X.select_dtypes("object").columns.tolist()
prep = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)], remainder=StandardScaler())

models = {
    "Logistic regression": make_pipeline(prep, LogisticRegression(C=0.1, max_iter=2000)),
    "Random forest":       make_pipeline(prep, RandomForestClassifier(300, min_samples_leaf=10, n_jobs=-1, random_state=0)),
    "Naive Bayes":         make_pipeline(prep, GaussianNB(var_smoothing=1e-3)),
}

def ece(y, p, bins=10):
    edges = np.quantile(p, np.linspace(0, 1, bins + 1)); edges[0], edges[-1] = -np.inf, np.inf
    idx = np.digitize(p, edges[1:-1])
    return sum((idx == b).mean() * abs(p[idx == b].mean() - y[idx == b].mean()) for b in range(bins) if (idx == b).any())

def report(name, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    print(f"{name:<34} AP={average_precision_score(yte, p):.3f}  logloss={log_loss(yte, p):.3f}  "
          f"brier={brier_score_loss(yte, p):.4f}  ECE={ece(yte, p):.3f}  mean p={p.mean():.3f}")

raw = {}
for name, m in models.items():
    raw[name] = m.fit(Xfit, yfit).predict_proba(Xte)[:, 1]
    report(name, raw[name])
print("true base rate:", yte.mean().round(3))

# ---- repair: fit the model on Xfit, learn a monotone map on the held-out calibration slice ------
print()
for name in ("Random forest", "Naive Bayes"):
    for method in ("sigmoid", "isotonic"):
        cal = CalibratedClassifierCV(FrozenEstimator(models[name].fit(Xfit, yfit)), method=method).fit(Xcal, ycal)
        report(f"{name} + {method}", cal.predict_proba(Xte)[:, 1])

# ---- from probability to money -----------------------------------------------------------------
COST, VALUE = 1.0, 8.0          # a call costs 1 unit, a subscription is worth 8
print(f"\nbreak-even probability = cost/value = {COST / VALUE:.3f}")

def profit(p, t): 
    call = p >= t
    return VALUE * yte[call].sum() - COST * call.sum()

fit_rf = models["Random forest"].fit(Xfit, yfit)
cal_rf = CalibratedClassifierCV(FrozenEstimator(fit_rf), method="isotonic").fit(Xcal, ycal)
for label, p in (("RF raw", raw["Random forest"]), ("RF calibrated", cal_rf.predict_proba(Xte)[:, 1])):
    best = max(np.unique(np.quantile(p, np.linspace(0, 0.995, 300))), key=lambda t: profit(p, t))
    print(f"{label:<14} profit at t=0.125: {profit(p, 0.125):6.0f} ({(p >= 0.125).sum():5d} calls)   "
          f"at test-optimal t={best:.3f}: {profit(p, best):6.0f}")
print("call everyone:", profit(np.ones(len(yte)), 0.5), "  call nobody: 0")
