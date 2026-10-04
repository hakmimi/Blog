"""Chapters 6-10: studies that choose or explain settings, using development data only.

Two inner designs are used, both inside the development rows (the comparison split is never read):
  cv     5-fold stratified cross-validation, for sweeps where a single number per setting is wanted.
  inner  a 75/25 stratified split of the development rows (`fit` / `val`). Used where a curve over trees or
         stages is plotted: the curve is scored on `val`, never on the rows that fitted the model.

    python exp_dev_studies.py trees bagging boosting families budget
"""
from __future__ import annotations

import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor, export_text

import metrics as K
import models as M
import protocol as P

warnings.filterwarnings("ignore")
CV5 = StratifiedKFold(5, shuffle=True, random_state=P.SEED)


def setup():
    X, y = P.load()
    dev, _ = P.random_split(y)
    fit, val = train_test_split(dev, test_size=0.25, stratify=y[dev], random_state=P.SEED)
    return X, y, dev, fit, val


def tree_matrix(X, fit, val):
    prep = M.make_prep(X, "tree")
    return prep.fit_transform(X.iloc[fit]), prep.transform(X.iloc[val]), prep


# --------------------------------------------------------------------------------------------- chapter 6
def trees():
    X, y, dev, fit, val = setup()
    Xd, yd = X.iloc[dev], y[dev]
    # hand-computed Gini on development data
    gini = lambda lab: 2 * np.mean(lab) * (1 - np.mean(lab))
    root = gini(yd)
    rows = [{"split": "root (no split)", "gain": 0.0, "impurity": root}]
    for col, ts in (("euribor3m", (1.0, 3.0, 5.0)), ("nr.employed", (5087.65,)), ("pdays", (16.5,))):
        for t in ts:
            m = Xd[col].to_numpy() <= t
            child = (m.sum() * gini(yd[m]) + (~m).sum() * gini(yd[~m])) / len(yd)
            rows.append({"split": f"{col} <= {t}", "gain": root - child, "impurity": child})
    pd.DataFrame(rows).to_csv(P.ART / "trees_gini_by_hand.csv", index=False, float_format="%.5f")

    prep = M.make_prep(X, "tree")
    out = []
    for depth in (2, 3, 5, 8, 12, None):
        est = Pipeline([("prep", clone(prep)), ("m", DecisionTreeClassifier(max_depth=depth, random_state=P.SEED))])
        est.fit(Xd, yd)
        train_ap = K.ap(yd, est.predict_proba(Xd)[:, 1])
        cvs = cross_val_score(est, Xd, yd, scoring="average_precision", cv=CV5)
        out.append({"setting": "max_depth", "value": str(depth), "leaves": est[-1].get_n_leaves(), "train_ap": train_ap,
                    "cv_ap_mean": cvs.mean(), "cv_ap_sd": cvs.std(ddof=1)})
    for leaf in (1, 5, 10, 25, 50, 100, 200, 500):
        est = Pipeline([("prep", clone(prep)), ("m", DecisionTreeClassifier(min_samples_leaf=leaf, random_state=P.SEED))])
        est.fit(Xd, yd)
        cvs = cross_val_score(est, Xd, yd, scoring="average_precision", cv=CV5)
        out.append({"setting": "min_samples_leaf", "value": str(leaf), "leaves": est[-1].get_n_leaves(),
                    "train_ap": K.ap(yd, est.predict_proba(Xd)[:, 1]), "cv_ap_mean": cvs.mean(), "cv_ap_sd": cvs.std(ddof=1)})
    pd.DataFrame(out).to_csv(P.ART / "trees_sweeps.csv", index=False, float_format="%.5f")
    small = Pipeline([("prep", clone(prep)), ("m", DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, random_state=P.SEED))]).fit(Xd, yd)
    text = export_text(small[-1], feature_names=list(small[0].get_feature_names_out()), show_weights=True)
    (P.ART / "trees_small_tree.txt").write_text(text, encoding="utf-8")
    # is nr.employed a stand-in for time? (row order is the only time information in the file)
    pos = np.arange(len(X))
    P.write_json("trees_notes.json", {"spearman_row_position_vs_nr_employed": float(spearmanr(pos, X["nr.employed"])[0]),
                                      "spearman_row_position_vs_euribor3m": float(spearmanr(pos, X["euribor3m"])[0]),
                                      "development_rows": int(len(dev)), "development_prevalence": float(yd.mean())})
    print(pd.DataFrame(out).round(3).to_string(index=False))


# --------------------------------------------------------------------------------------------- chapter 7
def bagging():
    X, y, dev, fit, val = setup()
    A, B, prep = tree_matrix(X, fit, val)
    yf, yv = y[fit], y[val]
    rng_all = [np.random.default_rng(s) for s in range(5)]
    curves, corr, single = [], [], []
    for seed, rng in enumerate(rng_all):
        votes = []
        for i in range(200):
            rows = rng.integers(0, len(A), len(A))
            t = DecisionTreeClassifier(min_samples_leaf=20, random_state=seed * 1000 + i).fit(A[rows], yf[rows])
            votes.append(t.predict_proba(B)[:, 1])
        votes = np.array(votes)
        single.append(np.mean([K.ap(yv, v) for v in votes[:50]]))
        for n in (1, 5, 10, 25, 50, 100, 200):
            curves.append({"seed": seed, "trees": n, "val_ap": K.ap(yv, votes[:n].mean(axis=0))})
        c = np.corrcoef(votes[:20]); corr.append(float(c[np.triu_indices(20, 1)].mean()))
    pd.DataFrame(curves).to_csv(P.ART / "bagging_curve.csv", index=False, float_format="%.5f")
    rf_rows = []
    for name, make in (("RF max_features=sqrt", lambda s: RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", n_jobs=P.N_JOBS, random_state=s)),
                       ("RF max_features=0.5", lambda s: RandomForestClassifier(300, min_samples_leaf=10, max_features=0.5, n_jobs=P.N_JOBS, random_state=s)),
                       ("RF max_features=1.0 (bagging)", lambda s: RandomForestClassifier(300, min_samples_leaf=10, max_features=1.0, n_jobs=P.N_JOBS, random_state=s)),
                       ("Extra trees sqrt", lambda s: ExtraTreesClassifier(300, min_samples_leaf=10, max_features="sqrt", n_jobs=P.N_JOBS, random_state=s))):
        for seed in range(3):
            t0 = time.perf_counter(); m = make(seed).fit(A, yf); sec = time.perf_counter() - t0
            rf_rows.append({"model": name, "seed": seed, "val_ap": K.ap(yv, m.predict_proba(B)[:, 1]), "fit_seconds": sec})
    pd.DataFrame(rf_rows).to_csv(P.ART / "bagging_forest_variants.csv", index=False, float_format="%.5f")
    ne = []
    for n in (10, 50, 100, 300, 600):
        for seed in range(5):
            m = RandomForestClassifier(n, min_samples_leaf=10, max_features="sqrt", n_jobs=P.N_JOBS, random_state=seed).fit(A, yf)
            ne.append({"n_estimators": n, "seed": seed, "val_ap": K.ap(yv, m.predict_proba(B)[:, 1])})
    pd.DataFrame(ne).to_csv(P.ART / "bagging_n_estimators.csv", index=False, float_format="%.5f")
    # OOB: what it estimates, and a direct test of the "fewer trees per row" explanation of its gap to the validation score
    rf = RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", oob_score=True, n_jobs=P.N_JOBS, random_state=0).fit(A, yf)
    oob_ap = K.ap(yf, rf.oob_decision_function_[:, 1])
    val_all = K.ap(yv, rf.predict_proba(B)[:, 1])
    rng = np.random.default_rng(0)
    subset = []
    for _ in range(20):
        pick = rng.choice(300, size=100, replace=False)
        p = np.mean([rf.estimators_[i].predict_proba(B)[:, 1] for i in pick], axis=0)
        subset.append(K.ap(yv, p))
    P.write_json("bagging_oob.json", {"oob_ap": oob_ap, "val_ap_300_trees": val_all, "val_ap_random_100_of_300_mean": float(np.mean(subset)),
                                      "val_ap_random_100_of_300_sd": float(np.std(subset, ddof=1)),
                                      "mean_pairwise_tree_correlation_by_seed": corr, "single_tree_val_ap_mean_by_seed": single})
    print(pd.DataFrame(curves).groupby("trees").val_ap.agg(["mean", "std"]).round(4))
    print(pd.DataFrame(rf_rows).groupby("model")[["val_ap", "fit_seconds"]].mean().round(3))
    print(pd.DataFrame(ne).groupby("n_estimators").val_ap.agg(["mean", "std", "min", "max"]).round(4))
    print({"oob_ap": oob_ap, "val_ap": val_all, "subset100": float(np.mean(subset))})


# --------------------------------------------------------------------------------------------- chapter 8
def boosting():
    X, y, dev, fit, val = setup()
    A, B, prep = tree_matrix(X, fit, val)
    yf, yv = y[fit], y[val]
    sig = lambda z: 1 / (1 + np.exp(-z))
    rows = []
    for lr in (0.5, 0.1, 0.02):
        base = np.log(yf.mean() / (1 - yf.mean()))
        Ff, Fv = np.full(len(A), base), np.full(len(B), base)
        for m in range(1, 1001):
            res = yf - sig(Ff)
            t = DecisionTreeRegressor(max_depth=3, min_samples_leaf=20).fit(A, res)
            Ff += lr * t.predict(A); Fv += lr * t.predict(B)
            if m in (1, 10, 25, 50, 100, 200, 300, 500, 1000):
                rows.append({"learning_rate": lr, "stages": m, "val_ap": K.ap(yv, Fv), "val_log_loss": K.safe_log_loss(yv, sig(Fv)),
                             "fit_ap": K.ap(yf, Ff)})
    pd.DataFrame(rows).to_csv(P.ART / "boosting_scratch_curve.csv", index=False, float_format="%.5f")
    Xc = M.CategoryCaster().fit(X.iloc[fit])
    Xf, Xv = Xc.transform(X.iloc[fit]), Xc.transform(X.iloc[val])
    es = []
    for lr in (0.3, 0.1, 0.03):
        h = HistGradientBoostingClassifier(learning_rate=lr, max_iter=2000, early_stopping=True, validation_fraction=0.15,
                                           n_iter_no_change=30, categorical_features="from_dtype", random_state=P.SEED).fit(Xf, yf)
        p = h.predict_proba(Xv)[:, 1]
        es.append({"learning_rate": lr, "stopped_at_trees": int(h.n_iter_), "val_ap": K.ap(yv, p), "val_log_loss": K.safe_log_loss(yv, p)})
    pd.DataFrame(es).to_csv(P.ART / "boosting_early_stopping.csv", index=False, float_format="%.5f")
    print(pd.DataFrame(rows).pivot(index="stages", columns="learning_rate", values="val_ap").round(3)); print(pd.DataFrame(es).round(3))


# --------------------------------------------------------------------------------------------- chapter 9
def families():
    X, y, dev, fit, val = setup()
    yf, yv = y[fit], y[val]
    scaled = M.make_prep(X, "dense")
    # which columns dominate Euclidean distance before and after scaling?
    A_raw = pd.get_dummies(X.iloc[fit], dtype=float)
    var_share = (A_raw.var() / A_raw.var().sum()).sort_values(ascending=False).head(6)
    A_scaled = scaled.fit_transform(X.iloc[fit]); B_scaled = scaled.transform(X.iloc[val])
    rows = []
    for k in (5, 15, 50, 150, 400):
        m = KNeighborsClassifier(k, n_jobs=P.N_JOBS).fit(A_scaled, yf)
        rows.append({"model": "kNN scaled", "setting": f"k={k}", "val_ap": K.ap(yv, m.predict_proba(B_scaled)[:, 1])})
    raw_prep = M.make_prep(X, "tree")
    A_r = raw_prep.fit_transform(X.iloc[fit]); B_r = raw_prep.transform(X.iloc[val])
    for k in (50,):
        m = KNeighborsClassifier(k, n_jobs=P.N_JOBS).fit(A_r, yf)
        rows.append({"model": "kNN unscaled", "setting": f"k={k}", "val_ap": K.ap(yv, m.predict_proba(B_r)[:, 1])})
    # kNN with the pdays sentinel recoded as flag + recency
    flag = M.make_prep(X, "dense", pdays="flag")
    Af, Bf = flag.fit_transform(X.iloc[fit]), flag.transform(X.iloc[val])
    m = KNeighborsClassifier(50, n_jobs=P.N_JOBS).fit(Af, yf)
    rows.append({"model": "kNN scaled, pdays as flag + recency", "setting": "k=50", "val_ap": K.ap(yv, m.predict_proba(Bf)[:, 1])})
    # RBF SVM cost, measured on this machine
    timing = []
    Atr = A_scaled
    for n in (2000, 4000, 8000, 16000, len(Atr)):
        reps = 1 if n > 8000 else 2
        secs = []
        for _ in range(reps):
            t0 = time.perf_counter(); SVC(C=1, gamma="scale").fit(Atr[:n], yf[:n]); secs.append(time.perf_counter() - t0)
        timing.append({"rows": n, "fit_seconds_min": min(secs), "repetitions": reps})
        print("svc", n, min(secs), flush=True)
    t = pd.DataFrame(timing)
    slope = np.polyfit(np.log(t.rows[:-1]), np.log(t.fit_seconds_min[:-1]), 1)[0]
    t.to_csv(P.ART / "families_svm_timing.csv", index=False, float_format="%.3f")
    seeds = []
    for seed in range(5):
        m = MLPClassifier((64, 32), early_stopping=True, max_iter=200, random_state=seed).fit(A_scaled, yf)
        seeds.append({"seed": seed, "val_ap": K.ap(yv, m.predict_proba(B_scaled)[:, 1]), "epochs": int(m.n_iter_)})
    pd.DataFrame(rows).to_csv(P.ART / "families_knn.csv", index=False, float_format="%.5f")
    pd.DataFrame(seeds).to_csv(P.ART / "families_mlp_seeds.csv", index=False, float_format="%.5f")
    P.write_json("families_notes.json", {"distance_variance_share_unscaled_top": var_share.round(4).to_dict(),
                                         "svm_loglog_slope_up_to_16000_rows": float(slope), "svm_full_development_rows": int(len(Atr)),
                                         "feature_std": {c: float(X[c].std()) for c in ("age", "pdays", "previous", "nr.employed", "euribor3m")}})
    print(pd.DataFrame(rows).round(4)); print(t); print(slope); print(pd.DataFrame(seeds).round(4)); print(var_share)


# -------------------------------------------------------------------------------------------- chapter 10
def budget(n_candidates: int = 40):
    """How much does a bigger search budget buy, scored on rows that took no part in the search?"""
    X, y, dev, fit, val = setup()
    yf, yv = y[fit], y[val]
    specs = {s.name: s for s in M.registry(X)}
    from sklearn.model_selection import ParameterSampler
    cv = P.tuning_cv()
    all_rows = []
    for name, n in (("sklearn HistGradientBoosting", n_candidates), ("LightGBM", n_candidates), ("Random forest", 24)):
        spec = specs[name]
        cands = [{}] + list(ParameterSampler(spec.space, n - 1, random_state=P.SEED))
        rec = []
        for i, params in enumerate(cands):
            est = clone(spec.build()).set_params(**params)
            cvs = cross_val_score(est, X.iloc[fit], yf, scoring="average_precision", cv=cv)
            est.fit(X.iloc[fit], yf)
            rec.append({"model": name, "candidate": i, "cv_ap": cvs.mean(), "val_ap": K.ap(yv, est.predict_proba(X.iloc[val])[:, 1])})
            print(name, i, round(cvs.mean(), 3), round(rec[-1]["val_ap"], 3), flush=True)
        all_rows += rec
    cand = pd.DataFrame(all_rows)
    cand.to_csv(P.ART / "budget_candidates.csv", index=False, float_format="%.5f")
    rng = np.random.default_rng(P.SEED)
    out = []
    for name, g in cand.groupby("model"):
        g = g.reset_index(drop=True)
        for b in (1, 2, 4, 8, 16, len(g)):
            cvs, vals = [], []
            for _ in range(300):
                pick = g.iloc[rng.permutation(len(g))[:b]]
                w = pick.loc[pick.cv_ap.idxmax()]
                cvs.append(w.cv_ap); vals.append(w.val_ap)
            out.append({"model": name, "budget": b, "best_cv_ap": np.mean(cvs), "val_ap_of_winner": np.mean(vals),
                        "val_ap_sd_across_draws": np.std(vals), "default_val_ap": g.val_ap[0]})
    pd.DataFrame(out).to_csv(P.ART / "budget_curve.csv", index=False, float_format="%.5f")
    print(pd.DataFrame(out).round(4).to_string(index=False))


if __name__ == "__main__":
    for name in sys.argv[1:] or ["trees", "bagging", "boosting", "families", "budget"]:
        print("=" * 20, name, flush=True)
        globals()[name]()
