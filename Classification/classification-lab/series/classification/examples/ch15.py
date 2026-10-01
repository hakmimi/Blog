import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns="duration")
for c in X.select_dtypes("object"):
    X[c] = pd.Categorical(X[c], categories=sorted(X[c].unique()))
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

params = dict(n_estimators=400, learning_rate=0.02, num_leaves=31, min_child_samples=100,
              subsample=0.7, subsample_freq=1, colsample_bytree=0.6, verbose=-1, random_state=42)
model = LGBMClassifier(**params).fit(Xtr, ytr)
base_ap = average_precision_score(yte, model.predict_proba(Xte)[:, 1])
print(f"LightGBM test AP = {base_ap:.3f}")

# --- 1. permutation importance: shuffle one column, measure the drop in AP --------------------------------
imp = permutation_importance(model, Xte, yte, scoring="average_precision", n_repeats=10, random_state=0, n_jobs=1)
perm = pd.Series(imp.importances_mean, index=X.columns).sort_values(ascending=False)
print("\npermutation importance (drop in AP):")
print(perm.head(8).round(4).to_string())

# --- 2. the built-in 'gain' importance tells a different story ---------------------------------------------
gain = pd.Series(model.booster_.feature_importance("gain"), index=X.columns)
print("\nbuilt-in gain importance (share of total):")
print((gain / gain.sum()).sort_values(ascending=False).head(8).round(3).to_string())

# --- 3. correlated features: shuffle the four macro columns TOGETHER ---------------------------------------
macro = ["emp.var.rate", "cons.price.idx", "cons.conf.idx", "euribor3m", "nr.employed"]
rng = np.random.default_rng(0); drops = []
for _ in range(10):
    Xs = Xte.copy(); perm_idx = rng.permutation(len(Xs))
    Xs[macro] = Xs[macro].iloc[perm_idx].to_numpy()                 # same shuffle for all macro columns
    drops.append(base_ap - average_precision_score(yte, model.predict_proba(Xs)[:, 1]))
print(f"\nshuffling all 5 macro columns together: AP drops by {np.mean(drops):.3f}  (sum of their individual drops: {perm[macro].sum():.3f})")

# --- 4. drop-column retraining: how much does the model NEED each group? ------------------------------------
print("\nretrain without a group of columns:")
groups = {"pdays + previous + poutcome": ["pdays", "previous", "poutcome"],
          "macro (5 columns)": macro,
          "contact + month + day_of_week": ["contact", "month", "day_of_week"],
          "customer profile (age, job, marital, education, default, housing, loan)": ["age", "job", "marital", "education", "default", "housing", "loan"]}
for name, cols in groups.items():
    m = LGBMClassifier(**params).fit(Xtr.drop(columns=cols), ytr)
    ap = average_precision_score(yte, m.predict_proba(Xte.drop(columns=cols))[:, 1])
    print(f"  without {name:<72} AP {ap:.3f}  ({ap - base_ap:+.3f})")

# --- 5. who do we miss? subscribers the model scored in the bottom half ---------------------------------------
p = model.predict_proba(Xte)[:, 1]
sub = pd.DataFrame({"p": p, "y": yte}, index=Xte.index).join(Xte)
missed = sub[(sub.y == 1) & (sub.p < np.median(p))]
caught = sub[(sub.y == 1) & (sub.p >= np.quantile(p, .9))]
print(f"\nsubscribers: {sub.y.sum()}, of which {len(missed)} score below the median and {len(caught)} are in the top 10%")
for col in ("contact", "poutcome", "month"):
    print(f"\n{col}: share of missed vs caught subscribers")
    print(pd.concat([missed[col].value_counts(normalize=True).rename("missed"),
                     caught[col].value_counts(normalize=True).rename("caught")], axis=1).round(2).sort_values("missed", ascending=False).head(5).to_string())
