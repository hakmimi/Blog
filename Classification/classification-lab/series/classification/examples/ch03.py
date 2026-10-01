import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, precision_recall_curve,
                             roc_auc_score, classification_report)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

cat = X.select_dtypes("object").columns
model = make_pipeline(ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cat)],
                                        remainder=StandardScaler()),
                      LogisticRegression(max_iter=2000))
p = model.fit(Xtr, ytr).predict_proba(Xte)[:, 1]

# The confusion matrix at the default 0.5 threshold
tn, fp, fn, tp = confusion_matrix(yte, p >= 0.5).ravel()
print(f"TN={tn} FP={fp} FN={fn} TP={tp}")
print(f"accuracy={(tp + tn) / len(yte):.3f}  precision={tp / (tp + fp):.3f}  recall={tp / (tp + fn):.3f}")

# The same model, three different thresholds
for t in (0.5, 0.25, 0.12):
    tn, fp, fn, tp = confusion_matrix(yte, p >= t).ravel()
    print(f"threshold {t:<4}: calls={tp + fp:5d}  precision={tp / (tp + fp):.2f}  recall={tp / (tp + fn):.2f}")

# Threshold-free summaries
print("ROC-AUC          :", round(roc_auc_score(yte, p), 3))
print("Average precision:", round(average_precision_score(yte, p), 3), " (random guessing ->", round(yte.mean(), 3), ")")

# "Top-k" view: what a call centre with capacity for 10% of the list actually gets
k = int(0.10 * len(yte))
top = np.argsort(-p)[:k]
print(f"top 10% of scores: precision={yte.to_numpy()[top].mean():.2f}, captures {yte.to_numpy()[top].sum() / yte.sum():.0%} of all subscribers")

# ROC-AUC vs AP under heavier imbalance: subsample positives
rng = np.random.default_rng(0)
keep = (yte.to_numpy() == 0) | (rng.random(len(yte)) < 0.2)
print("after dropping 80% of positives -> AUC", round(roc_auc_score(yte[keep], p[keep]), 3),
      " AP", round(average_precision_score(yte[keep], p[keep]), 3))
