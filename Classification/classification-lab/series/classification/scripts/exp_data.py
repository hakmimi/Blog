"""Chapters 1-2: what the file contains, which columns are eligible, and what the eligibility choices cost.

All model scores come from 5-fold cross-validation inside the development rows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

import metrics as K
import models as M
import protocol as P

CV5 = StratifiedKFold(5, shuffle=True, random_state=P.SEED)


def profile() -> dict:
    df = P.load_frame()
    y = (df["y"] == "yes").astype(int)
    X = df.drop(columns="y")
    chunk = np.arange(len(df)) // 4119
    out = {
        "rows": len(df), "positives": int(y.sum()), "prevalence": float(y.mean()),
        "always_no_accuracy": float(1 - y.mean()), "max_possible_accuracy_gain_points": float(100 * y.mean()),
        "exact_duplicate_rows": int(X.duplicated().sum()),
        "pdays_999_share": float((X.pdays == 999).mean()), "previous_gt0_share": float((X.previous > 0).mean()),
        "campaign_gt1_share": float((X.campaign > 1).mean()), "campaign_max": int(X.campaign.max()),
        "rows_with_unknown_label": float((X == "unknown").any(axis=1).mean()),
        "unknown_share_by_column": {c: float((X[c] == "unknown").mean()) for c in X.columns if (X[c] == "unknown").any()},
        "poutcome_levels": sorted(X.poutcome.unique()),
        "rate_by_chunk": y.groupby(chunk).mean().round(4).tolist(),
        "euribor3m_by_chunk": X.euribor3m.groupby(chunk).mean().round(3).tolist(),
        "chunk_size": 4119,
    }
    # campaign: how does the success rate depend on the recorded contact count? (selection into being the last contact)
    out["rate_by_campaign"] = y.groupby(X.campaign.clip(upper=8)).agg(["mean", "size"]).round(4).reset_index().to_dict(orient="records")
    pd.DataFrame(out["rate_by_campaign"]).rename(columns={"mean": "rate", "size": "records"}).to_csv(P.ART / "data_campaign_rates.csv", index=False)
    seg = []
    for col in ("contact", "poutcome", "month", "job", "education", "default"):
        g = y.groupby(X[col]).agg(rate="mean", records="size").reset_index().rename(columns={col: "level"})
        g.insert(0, "column", col)
        lo_hi = [K.wilson(int(r * n), int(n)) for r, n in zip(g.rate, g.records)]
        g["rate_lo"], g["rate_hi"] = [a for a, _ in lo_hi], [b for _, b in lo_hi]
        seg.append(g)
    pd.concat(seg).to_csv(P.ART / "data_segment_rates.csv", index=False, float_format="%.4f")
    return out


def feature_set_study() -> pd.DataFrame:
    X_all, y = P.load("main + campaign")
    df = P.load_frame()
    dev, _ = P.random_split(y)
    rows = []
    for fs, cols in P.FEATURE_SETS.items():
        X = df[cols]
        for model in ("Logistic regression", "LightGBM"):
            spec = [s for s in M.registry(X) if s.name == model][0]
            est = clone(spec.build())
            sc = cross_val_score(est, X.iloc[dev], y[dev], scoring="average_precision", cv=CV5)
            auc = cross_val_score(clone(spec.build()), X.iloc[dev], y[dev], scoring="roc_auc", cv=CV5)
            rows.append({"feature_set": fs, "n_features": len(cols), "model": model, "cv_ap_mean": sc.mean(), "cv_ap_sd": sc.std(ddof=1),
                         "cv_auc_mean": auc.mean()})
            print(rows[-1], flush=True)
    return pd.DataFrame(rows)


def sentinel_study() -> pd.DataFrame:
    X, y = P.load()
    dev, _ = P.random_split(y)
    rows = []
    for rep in ("raw", "flag"):
        for model in ("Logistic regression", "k-nearest neighbours", "LightGBM"):
            spec = [s for s in M.registry(X, pdays=rep) if s.name == model][0]
            # trees/boosters consume the raw columns; only the preprocessing of linear/distance models changes
            est = clone(spec.build())
            if model == "LightGBM" and rep == "flag":
                from sklearn.preprocessing import FunctionTransformer
                est = Pipeline([("flag", FunctionTransformer(M.pdays_flag))] + list(est.steps))
            sc = cross_val_score(est, X.iloc[dev], y[dev], scoring="average_precision", cv=CV5)
            rows.append({"pdays_representation": "raw value (999 = never contacted)" if rep == "raw" else "flag + recency",
                         "model": model, "cv_ap_mean": sc.mean(), "cv_ap_sd": sc.std(ddof=1)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    P.write_json("data_profile.json", profile())
    fs = feature_set_study(); fs.to_csv(P.ART / "data_feature_sets.csv", index=False, float_format="%.5f")
    st = sentinel_study(); st.to_csv(P.ART / "data_sentinel.csv", index=False, float_format="%.5f")
    pd.set_option("display.width", 200)
    print(fs.round(4).to_string(index=False)); print(st.round(4).to_string(index=False))
