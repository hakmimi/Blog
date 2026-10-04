"""Chapter 5: logistic regression and Naive Bayes on development data (5-fold cross-validation).

  C sweep           mean/sd of fold AP for the L2 strength
  odds ratios       relative to the most frequent level of each categorical variable (a full-rank encoding), numeric
                    columns per one standard deviation; plus a bootstrap of the refit to show how stable each one is
  pipeline          scaling fitted on all development rows before cross-validation versus inside each fold
  naive Bayes       Gaussian NB on one-hot columns (a deliberately imperfect representation) against a categorical NB
                    on binned numerics, scored with out-of-fold probabilities
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.naive_bayes import CategoricalNB, GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import KBinsDiscretizer, OneHotEncoder, OrdinalEncoder, StandardScaler

import metrics as K
import models as M
import protocol as P

CV5 = StratifiedKFold(5, shuffle=True, random_state=P.SEED)


def main() -> None:
    X, y = P.load()
    dev, _ = P.random_split(y)
    Xd, yd = X.iloc[dev], y[dev]
    cat = [c for c in X.columns if X[c].dtype == object]
    num = [c for c in X.columns if c not in cat]

    # C sweep
    rows = []
    for C in (0.001, 0.01, 0.1, 1, 10):
        est = Pipeline([("prep", M.make_prep(X, "linear")), ("m", LogisticRegression(C=C, max_iter=5000))])
        s = cross_val_score(est, Xd, yd, scoring="average_precision", cv=CV5)
        rows.append({"C": C, "cv_ap_mean": s.mean(), "cv_ap_sd": s.std(ddof=1)})
    pd.DataFrame(rows).to_csv(P.ART / "linear_c_sweep.csv", index=False, float_format="%.5f")

    # odds ratios against the most frequent level
    ref_levels = [Xd[c].value_counts().index[0] for c in cat]
    ohe = OneHotEncoder(drop=ref_levels, handle_unknown="ignore", sparse_output=False)
    ct = ColumnTransformer([("cat", ohe, cat), ("num", StandardScaler(), num)])
    A = ct.fit_transform(Xd)
    names = list(ct.get_feature_names_out())
    fit = LogisticRegression(C=1.0, max_iter=5000).fit(A, yd)
    rng = np.random.default_rng(P.SEED)
    boots = []
    for _ in range(100):
        i = rng.integers(0, len(yd), len(yd))
        boots.append(LogisticRegression(C=1.0, max_iter=5000).fit(A[i], yd[i]).coef_[0])
    boots = np.array(boots)
    tbl = pd.DataFrame({"term": names, "coef": fit.coef_[0], "odds_ratio": np.exp(fit.coef_[0]),
                        "or_lo": np.exp(np.quantile(boots, .025, axis=0)), "or_hi": np.exp(np.quantile(boots, .975, axis=0)),
                        "share_boot_same_sign": [(np.sign(boots[:, j]) == np.sign(fit.coef_[0][j])).mean() for j in range(len(names))]})
    tbl["term"] = tbl.term.str.replace("cat__", "").str.replace("num__", "")
    tbl.to_csv(P.ART / "linear_odds_ratios.csv", index=False, float_format="%.4f")
    macro = ["emp.var.rate", "cons.price.idx", "cons.conf.idx", "euribor3m", "nr.employed"]
    X[macro].corr().to_csv(P.ART / "linear_macro_correlation.csv", float_format="%.3f", index_label="column")
    P.write_json("linear_notes.json", {"reference_levels": dict(zip(cat, ref_levels)), "bootstrap_refits": 100,
                                       "intercept": float(fit.intercept_[0])})

    # does fitting the scaler before cross-validation matter?
    both = []
    for name, model in (("Logistic regression", LogisticRegression(C=0.1, max_iter=5000)), ("k-nearest neighbours (k=50)", KNeighborsClassifier(50, n_jobs=P.N_JOBS))):
        inside = Pipeline([("prep", M.make_prep(X, "dense")), ("m", clone(model))])
        a = cross_val_score(inside, Xd, yd, scoring="average_precision", cv=CV5)
        pre = M.make_prep(X, "dense").fit(Xd)                         # fitted on ALL development rows, then cross-validated
        Aall = pre.transform(Xd)
        b = cross_val_score(clone(model), Aall, yd, scoring="average_precision", cv=CV5)
        both.append({"model": name, "inside_each_fold": a.mean(), "fitted_on_all_rows_first": b.mean(), "difference": b.mean() - a.mean()})
    pd.DataFrame(both).to_csv(P.ART / "linear_pipeline_isolation.csv", index=False, float_format="%.5f")

    # naive Bayes variants, out-of-fold probabilities
    nb_rows = []
    binned = Pipeline([("prep", ColumnTransformer([("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), cat),
                                                   ("num", KBinsDiscretizer(10, encode="ordinal", strategy="quantile"), num)])),
                       ("m", CategoricalNB(min_categories=12))])
    specs = {"Logistic regression (C=0.1)": Pipeline([("prep", M.make_prep(X, "linear")), ("m", LogisticRegression(C=0.1, max_iter=5000))]),
             "Gaussian NB on one-hot columns": Pipeline([("prep", M.make_prep(X, "dense")), ("m", GaussianNB(var_smoothing=1e-3))]),
             "Categorical NB on binned numerics": binned}
    for name, est in specs.items():
        oof = cross_val_predict(est, Xd, yd, cv=CV5, method="predict_proba")[:, 1]
        nb_rows.append({"model": name, **K.summary(yd, oof), "share_above_0.9": float((oof > 0.9).mean()), "share_below_0.1": float((oof < 0.1).mean())})
    pd.DataFrame(nb_rows).to_csv(P.ART / "linear_naive_bayes.csv", index=False, float_format="%.5f")
    pd.set_option("display.width", 220)
    print(pd.DataFrame(rows).round(4)); print(tbl.sort_values("odds_ratio").round(3).head(8)); print(tbl.sort_values("odds_ratio").round(3).tail(8))
    print(pd.DataFrame(both).round(4)); print(pd.DataFrame(nb_rows).round(4).to_string(index=False)); print(X[macro].corr().round(2))


if __name__ == "__main__":
    main()
