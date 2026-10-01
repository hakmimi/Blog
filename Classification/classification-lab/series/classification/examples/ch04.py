import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ---- 1. the losses, written by hand, on four customers ---------------------------------
y_true = np.array([1, 1, 0, 0])
p      = np.array([0.9, 0.2, 0.1, 0.6])       # model's predicted P(subscribe)

log_loss_each = -(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))
brier_each    = (p - y_true) ** 2
print("log loss per row:", log_loss_each.round(3), "-> mean", log_loss_each.mean().round(3))
print("Brier per row   :", brier_each.round(3),    "-> mean", brier_each.mean().round(3))

# How harshly is a confident mistake punished?
for wrong_p in (0.6, 0.9, 0.99):
    print(f"true=0, predicted {wrong_p}: log loss {-np.log(1 - wrong_p):.2f}   Brier {wrong_p ** 2:.2f}")

# ---- 2. logistic regression from scratch: choose the loss, get a different model ------
df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns
prep = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                         remainder=StandardScaler())
A = np.c_[np.ones(len(Xtr)), prep.fit_transform(Xtr)]        # design matrix with intercept
B = np.c_[np.ones(len(Xte)), prep.transform(Xte)]
sigmoid = lambda z: 1 / (1 + np.exp(-np.clip(z, -30, 30)))

def fit(loss, steps=1500, lr=0.5):
    w = np.zeros(A.shape[1])
    pos_weight = (ytr == 0).sum() / (ytr == 1).sum()          # ~7.9
    for _ in range(steps):
        z = A @ w
        q = sigmoid(z)
        if loss == "log":                                     # d/dw of mean log loss
            grad = A.T @ (q - ytr) / len(ytr)
        elif loss == "weighted log":                          # positives count ~8x
            sw = np.where(ytr == 1, pos_weight, 1.0)
            grad = A.T @ ((q - ytr) * sw) / sw.sum()
        elif loss == "brier":                                 # d/dw of mean (q - y)^2
            grad = A.T @ (2 * (q - ytr) * q * (1 - q)) / len(ytr)
        w -= lr * grad
    return w

print(f"\n{'objective':<14}{'AP':>7}{'AUC':>7}{'logloss':>9}{'mean p':>8}{'calls@0.5':>11}")
for loss in ("log", "weighted log", "brier"):
    q = sigmoid(B @ fit(loss))
    print(f"{loss:<14}{average_precision_score(yte, q):7.3f}{roc_auc_score(yte, q):7.3f}"
          f"{log_loss(yte, q):9.3f}{q.mean():8.3f}{(q >= 0.5).sum():11d}")
