import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import average_precision_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier, export_text

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)
X = df.drop(columns="duration")
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cat = X.select_dtypes("object").columns.tolist()
prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)],
                         remainder="passthrough")          # trees don't need scaling

# ---- Gini impurity by hand ----------------------------------------------------------
def gini(labels):
    p = np.mean(labels)
    return 2 * p * (1 - p)

def split_gain(feature, threshold, labels):
    left, right = labels[feature <= threshold], labels[feature > threshold]
    child = (len(left) * gini(left) + len(right) * gini(right)) / len(labels)
    return gini(labels) - child

ytr_a = ytr.to_numpy()
print("root impurity:", round(gini(ytr_a), 4))
for t in (1.0, 3.0, 5.0):
    print(f"split euribor3m <= {t}: gain {split_gain(Xtr['euribor3m'].to_numpy(), t, ytr_a):.4f}")

# ---- an unrestricted tree memorises the training set -------------------------------
print()
for depth in (2, 3, 5, 8, 12, None):
    tree = make_pipeline(prep, DecisionTreeClassifier(max_depth=depth, random_state=42))
    tree.fit(Xtr, ytr)
    train_ap = average_precision_score(ytr, tree.predict_proba(Xtr)[:, 1])
    cv_ap = cross_val_score(tree, Xtr, ytr, cv=3, scoring="average_precision").mean()
    leaves = tree[-1].get_n_leaves()
    print(f"max_depth={str(depth):<5} leaves={leaves:>5}  train AP={train_ap:.3f}   CV AP={cv_ap:.3f}")

# ---- regularise by leaf size instead of depth --------------------------------------
print()
for leaf in (1, 10, 50, 200, 500):
    tree = make_pipeline(prep, DecisionTreeClassifier(min_samples_leaf=leaf, random_state=42))
    cv_ap = cross_val_score(tree, Xtr, ytr, cv=3, scoring="average_precision").mean()
    print(f"min_samples_leaf={leaf:<4} CV AP={cv_ap:.3f}")

# ---- read a small tree --------------------------------------------------------------
small = make_pipeline(prep, DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, random_state=42)).fit(Xtr, ytr)
print()
print(export_text(small[-1], feature_names=list(small[0].get_feature_names_out()), max_depth=3, show_weights=True))
