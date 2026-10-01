import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)

# --- 1. imbalance: what does "accuracy" reward?
print("majority-class accuracy:", round(1 - y.mean(), 3))

# --- 2. hidden sentinel values
print("pdays == 999 (never contacted before):", f"{(df.pdays == 999).mean():.1%}")
print("rows with an 'unknown' somewhere:", f"{(df == 'unknown').any(axis=1).mean():.1%}")
print("exact duplicate rows:", df.duplicated().sum())

# --- 3. leakage: train once with `duration`, once without
def score(frame):
    cat = frame.select_dtypes("object").columns
    prep = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cat)],
                             remainder=StandardScaler())
    model = make_pipeline(prep, LogisticRegression(max_iter=2000))
    Xtr, Xte, ytr, yte = train_test_split(frame, y, test_size=0.2, stratify=y, random_state=42)
    p = model.fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    return round(average_precision_score(yte, p), 3), round(roc_auc_score(yte, p), 3)

print("with duration    (AP, AUC):", score(df))
print("without duration (AP, AUC):", score(df.drop(columns="duration")))
print(df.join(y.rename("y")).groupby("y").duration.median().rename("median call seconds"))
