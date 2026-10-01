import time
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat_cols = X.select_dtypes("object").columns.tolist()

def as_category(frame):                       # LightGBM / XGBoost want pandas 'category' dtype
    out = frame.copy()
    for c in cat_cols:
        out[c] = pd.Categorical(out[c], categories=sorted(X[c].unique()))
    return out

def run(name, model, Xa, Xb):
    t0 = time.perf_counter(); model.fit(Xa, ytr); fit_s = time.perf_counter() - t0
    p = model.predict_proba(Xb)[:, 1]
    print(f"{name:<34} AP={average_precision_score(yte, p):.3f}  AUC={roc_auc_score(yte, p):.3f}  "
          f"logloss={log_loss(yte, p):.3f}  fit={fit_s:5.1f}s")

# --- three libraries, three ways of saying "these columns are categorical"
Ctr, Cte = as_category(Xtr), as_category(Xte)
run("LightGBM  (category dtype)", LGBMClassifier(n_estimators=400, learning_rate=0.02, num_leaves=31, min_child_samples=100,
                                                  subsample=0.7, subsample_freq=1, colsample_bytree=0.6, verbose=-1, random_state=42), Ctr, Cte)
run("XGBoost   (category dtype)", XGBClassifier(n_estimators=400, learning_rate=0.02, max_depth=4, subsample=0.7, colsample_bytree=0.6,
                                                 tree_method="hist", enable_categorical=True, random_state=42), Ctr, Cte)
run("CatBoost  (cat_features=names)", CatBoostClassifier(iterations=400, learning_rate=0.06, depth=6, l2_leaf_reg=3,
                                                         cat_features=cat_cols, verbose=0, random_seed=42), Xtr, Xte)

# --- does native categorical handling beat one-hot?  same LightGBM, same params
oh_tr = pd.get_dummies(Xtr, columns=cat_cols, dtype=float)
oh_te = pd.get_dummies(Xte, columns=cat_cols, dtype=float).reindex(columns=oh_tr.columns, fill_value=0.0)
oh_tr.columns = oh_te.columns = [c.replace(" ", "_") for c in oh_tr.columns]      # LightGBM dislikes odd characters
run("LightGBM  (one-hot instead)", LGBMClassifier(n_estimators=400, learning_rate=0.02, num_leaves=31, min_child_samples=100,
                                                   subsample=0.7, subsample_freq=1, colsample_bytree=0.6, verbose=-1, random_state=42), oh_tr, oh_te)

# --- what an integer-coded category does to a linear/tree learner is NOT the same thing: label-encode and see
lab_tr, lab_te = Xtr.copy(), Xte.copy()
for c in cat_cols:
    codes = {v: i for i, v in enumerate(sorted(X[c].unique()))}
    lab_tr[c], lab_te[c] = lab_tr[c].map(codes), lab_te[c].map(codes)
run("LightGBM  (integer codes as numbers)", LGBMClassifier(n_estimators=400, learning_rate=0.02, num_leaves=31, min_child_samples=100,
                                                            subsample=0.7, subsample_freq=1, colsample_bytree=0.6, verbose=-1, random_state=42), lab_tr, lab_te)
