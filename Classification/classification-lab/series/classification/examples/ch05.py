import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()

prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), cat)], remainder=StandardScaler())
logit = make_pipeline(prep, LogisticRegression(C=0.1, max_iter=2000))
logit.fit(Xtr, ytr)
p = logit.predict_proba(Xte)[:, 1]
print(f"logistic  AP={average_precision_score(yte, p):.3f}  AUC={roc_auc_score(yte, p):.3f}  "
      f"logloss={log_loss(yte, p):.3f}  brier={brier_score_loss(yte, p):.3f}")

# --- how much regularisation? 3-fold CV on the training part only
for C in (0.001, 0.01, 0.1, 1, 10):
    m = make_pipeline(prep, LogisticRegression(C=C, max_iter=2000))
    s = cross_val_score(m, Xtr, ytr, cv=3, scoring="average_precision")
    print(f"C={C:<6} CV average precision = {s.mean():.3f} +- {s.std():.3f}")

# --- read the coefficients
names = logit[0].get_feature_names_out()
coef = pd.Series(logit[-1].coef_[0], index=names).sort_values()
odds = np.exp(coef).round(2)
print("\nlowest odds ratios :\n", odds.head(6).to_string())
print("highest odds ratios:\n", odds.tail(6).to_string())

# --- Gaussian Naive Bayes on the same data (dense input needed)
dense = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                          remainder=StandardScaler())
nb = make_pipeline(dense, GaussianNB(var_smoothing=1e-3)).fit(Xtr, ytr)
q = nb.predict_proba(Xte)[:, 1]
print(f"\nnaive bayes AP={average_precision_score(yte, q):.3f}  AUC={roc_auc_score(yte, q):.3f}  "
      f"logloss={log_loss(yte, np.clip(q, 1e-6, 1 - 1e-6)):.3f}  brier={brier_score_loss(yte, q):.3f}")
print("mean predicted probability: logistic", p.mean().round(3), " naive bayes", q.mean().round(3), " truth", yte.mean().round(3))
print("share of NB scores above 0.9 / below 0.1:", (q > 0.9).mean().round(3), (q < 0.1).mean().round(3))
