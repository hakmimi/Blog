import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()
prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)], remainder="passthrough")
A, B = prep.fit_transform(Xtr), prep.transform(Xte)
sigmoid = lambda z: 1 / (1 + np.exp(-z))

# ---- gradient boosting from scratch --------------------------------------------------
def boost(lr, n_stages=300, depth=3):
    base = np.log(ytr.mean() / (1 - ytr.mean()))             # stage 0: predict the base rate
    F_tr, F_te = np.full(len(A), base), np.full(len(B), base)
    history = []
    for m in range(1, n_stages + 1):
        residual = ytr - sigmoid(F_tr)                        # negative gradient of log loss
        tree = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=20).fit(A, residual)
        F_tr += lr * tree.predict(A)
        F_te += lr * tree.predict(B)
        if m in (1, 10, 25, 50, 100, 200, 300):
            q = sigmoid(F_te)
            history.append((m, average_precision_score(yte, q), log_loss(yte, q),
                            average_precision_score(ytr, sigmoid(F_tr))))
    return history

for lr in (0.5, 0.1, 0.02):
    print(f"\nlearning rate {lr}")
    print("  stages   test AP  test logloss  train AP")
    for m, ap, ll, tap in boost(lr):
        print(f"  {m:>6}   {ap:.3f}    {ll:.3f}        {tap:.3f}")

# ---- the library version, with early stopping on an internal validation slice --------
Xc = X.copy()
for c in cat:
    Xc[c] = Xc[c].astype("category")
Xctr, Xcte = Xc.loc[Xtr.index], Xc.loc[Xte.index]
for lr in (0.3, 0.1, 0.03):
    h = HistGradientBoostingClassifier(learning_rate=lr, max_iter=2000, early_stopping=True, validation_fraction=0.15,
                                       n_iter_no_change=30, categorical_features="from_dtype", random_state=0).fit(Xctr, ytr)
    q = h.predict_proba(Xcte)[:, 1]
    print(f"\nHistGB lr={lr}: stopped at {h.n_iter_} trees  test AP={average_precision_score(yte, q):.3f}  logloss={log_loss(yte, q):.3f}")
