import time
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC, LinearSVC

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()
ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
scaled   = ColumnTransformer([("c", ohe, cat)], remainder=StandardScaler())
unscaled = ColumnTransformer([("c", ohe, cat)], remainder="passthrough")

def ap(m): return average_precision_score(yte, m.predict_proba(Xte)[:, 1])

# ---- k-NN: distance is meaningless without scaling ---------------------------------------
print("kNN, k=50")
for label, prep in (("unscaled", unscaled), ("scaled  ", scaled)):
    m = make_pipeline(prep, KNeighborsClassifier(50, n_jobs=-1)).fit(Xtr, ytr)
    print(f"  {label}  AP={ap(m):.3f}")
print("kNN, scaled, varying k")
for k in (5, 15, 50, 150, 400):
    m = make_pipeline(scaled, KNeighborsClassifier(k, n_jobs=-1)).fit(Xtr, ytr)
    print(f"  k={k:<4} AP={ap(m):.3f}")

# ---- SVM: scores are not probabilities -----------------------------------------------------
svm = make_pipeline(scaled, LinearSVC(C=0.1, dual=False)).fit(Xtr, ytr)
d = svm.decision_function(Xte)
print("\nLinear SVM raw scores: range", d.min().round(2), "to", d.max().round(2), " AP", round(average_precision_score(yte, d), 3))
cal = make_pipeline(scaled, CalibratedClassifierCV(LinearSVC(C=0.1, dual=False), cv=3)).fit(Xtr, ytr)
q = cal.predict_proba(Xte)[:, 1]
print(f"after Platt scaling: AP={average_precision_score(yte, q):.3f}  logloss={log_loss(yte, q):.3f}  brier={brier_score_loss(yte, q):.3f}")

# ---- RBF SVM: cost grows faster than the data ----------------------------------------------
print("\nRBF SVM fit time vs training size")
Atr = scaled.fit_transform(Xtr)
for n in (2000, 4000, 8000, 16000):
    t0 = time.perf_counter()
    SVC(C=1, gamma="scale").fit(Atr[:n], ytr[:n])
    print(f"  n={n:<6} {time.perf_counter() - t0:5.1f}s")

# ---- small neural net ------------------------------------------------------------------------
print("\nMLP (64,32) with early stopping")
for alpha in (1e-4, 1e-2, 1e-1):
    t0 = time.perf_counter()
    m = make_pipeline(scaled, MLPClassifier((64, 32), alpha=alpha, early_stopping=True, max_iter=200, random_state=0)).fit(Xtr, ytr)
    print(f"  alpha={alpha:<7} AP={ap(m):.3f}  epochs={m[-1].n_iter_}  fit={time.perf_counter() - t0:.1f}s")
