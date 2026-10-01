"""Head-to-head leaderboard: 13 classifiers, one split, one tuning budget.

Run:  python series/classification/scripts/run_leaderboard.py
Writes artifacts/leaderboard*.csv|json and the figures used in chapters 12-14.
"""
from __future__ import annotations

import json
import time
import warnings

import catboost
import lightgbm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import xgboost
from lightgbm import LGBMClassifier
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, log_loss,
                             precision_recall_curve, roc_auc_score, roc_curve)
from sklearn.model_selection import RandomizedSearchCV, cross_val_predict
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from common import (ART, CatBoostSK, COLORS, COST_PER_CALL, FIG, SEED, VALUE_PER_SUBSCRIPTION, best_profit_threshold,
                    cv, expected_calibration_error, linear_prep, profit, split, tree_prep, views)

warnings.filterwarnings("ignore")
N_ITER = 8          # the same random-search budget for every model that has a search space
np.random.seed(SEED)

X, y, tr, te = split()
V = views(X)


def specs():
    """(name, family, view, estimator, search space). One entry per contender."""
    lin, tre = linear_prep(X), tree_prep(X)
    return [
        ("Prior (no model)", "baseline", "raw", DummyClassifier(strategy="prior"), {}),
        ("Logistic regression", "linear", "raw",
         Pipeline([("prep", lin), ("m", LogisticRegression(max_iter=2000, solver="liblinear"))]),
         {"m__C": [0.01, 0.03, 0.1, 0.3, 1, 3]}),
        ("Linear SVM (calibrated)", "linear", "raw",
         Pipeline([("prep", lin), ("m", CalibratedClassifierCV(LinearSVC(dual=False), cv=3))]),
         {"m__estimator__C": [0.01, 0.03, 0.1, 0.3, 1]}),
        ("Gaussian Naive Bayes", "probabilistic", "raw",
         Pipeline([("prep", linear_prep(X, sparse=False)), ("m", GaussianNB())]),
         {"m__var_smoothing": [1e-9, 1e-7, 1e-5, 1e-3, 1e-1]}),
        ("k-nearest neighbors", "instance", "raw",
         Pipeline([("prep", linear_prep(X, sparse=False)), ("m", KNeighborsClassifier(n_jobs=-1))]),
         {"m__n_neighbors": [15, 30, 60, 120], "m__weights": ["uniform", "distance"]}),
        ("Small neural net (MLP)", "neural", "raw",
         Pipeline([("prep", lin), ("m", MLPClassifier(hidden_layer_sizes=(64, 32), early_stopping=True,
                                                     max_iter=200, random_state=SEED))]),
         {"m__alpha": [1e-4, 1e-3, 1e-2, 1e-1], "m__learning_rate_init": [1e-3, 3e-3]}),
        ("Decision tree", "tree", "raw",
         Pipeline([("prep", tre), ("m", DecisionTreeClassifier(random_state=SEED))]),
         {"m__min_samples_leaf": [10, 30, 100, 300], "m__max_depth": [3, 5, 8, None]}),
        ("Random forest", "bagging", "raw",
         Pipeline([("prep", tre), ("m", RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=SEED))]),
         {"m__min_samples_leaf": [3, 10, 30], "m__max_features": ["sqrt", 0.3]}),
        ("Extra trees", "bagging", "raw",
         Pipeline([("prep", tre), ("m", ExtraTreesClassifier(n_estimators=300, n_jobs=-1, random_state=SEED))]),
         {"m__min_samples_leaf": [3, 10, 30], "m__max_features": ["sqrt", 0.3]}),
        ("sklearn HistGradientBoosting", "boosting", "category",
         HistGradientBoostingClassifier(categorical_features="from_dtype", early_stopping=True, random_state=SEED),
         {"learning_rate": [0.03, 0.06, 0.1], "max_leaf_nodes": [8, 15, 31], "l2_regularization": [0, 1, 10]}),
        ("XGBoost", "boosting", "category",
         XGBClassifier(n_estimators=400, tree_method="hist", enable_categorical=True, n_jobs=-1,
                       eval_metric="logloss", random_state=SEED),
         {"learning_rate": [0.02, 0.05, 0.1], "max_depth": [3, 4, 6], "subsample": [0.7, 1.0],
          "colsample_bytree": [0.6, 1.0], "min_child_weight": [1, 10]}),
        ("LightGBM", "boosting", "category",
         LGBMClassifier(n_estimators=400, n_jobs=-1, random_state=SEED, verbose=-1),
         {"learning_rate": [0.02, 0.05, 0.1], "num_leaves": [7, 15, 31], "subsample": [0.7, 1.0],
          "subsample_freq": [1], "colsample_bytree": [0.6, 1.0], "min_child_samples": [20, 100]}),
        ("CatBoost", "boosting", "raw",
         CatBoostSK(iterations=400),
         {"learning_rate": [0.03, 0.06, 0.1], "depth": [4, 6, 8], "l2_leaf_reg": [1, 3, 10]}),
    ]


def proba(est, Xf) -> np.ndarray:
    return est.predict_proba(Xf)[:, 1]


def main() -> None:
    rows, preds, best_est = [], {}, {}
    for name, family, view, est, space in specs():
        Xf = V[view]
        Xtr, Xte = Xf.iloc[tr], Xf.iloc[te]
        t0 = time.perf_counter()
        if space:
            n_cand = min(N_ITER, int(np.prod([len(v) for v in space.values()])))
            search = RandomizedSearchCV(est, space, n_iter=n_cand, scoring="average_precision", cv=cv(),
                                        random_state=SEED, n_jobs=1, refit=False)
            search.fit(Xtr, y[tr])
            params, cv_ap = search.best_params_, float(search.best_score_)
            final = clone(est).set_params(**params)
        else:
            params, cv_ap, n_cand, final = {}, float("nan"), 0, clone(est)
        tune_s = time.perf_counter() - t0
        t0 = time.perf_counter(); final.fit(Xtr, y[tr]); fit_s = time.perf_counter() - t0
        t0 = time.perf_counter(); p = proba(final, Xte); pred_us = (time.perf_counter() - t0) / len(te) * 1e6
        # out-of-fold scores on the TRAIN part only -> pick the decision threshold without touching test
        p_oof = cross_val_predict(clone(final), Xtr, y[tr], cv=cv(), method="predict_proba")[:, 1]
        thr = best_profit_threshold(y[tr], p_oof)
        top10 = np.argsort(-p)[: len(p) // 10]
        rows.append({
            "model": name, "family": family, "params": json.dumps(params, default=str), "candidates": n_cand,
            "cv_average_precision": cv_ap,
            "roc_auc": roc_auc_score(y[te], p), "average_precision": average_precision_score(y[te], p),
            "log_loss": log_loss(y[te], np.clip(p, 1e-6, 1 - 1e-6)), "brier": brier_score_loss(y[te], p),
            "ece": expected_calibration_error(y[te], p),
            "precision_at_top10pct": float(y[te][top10].mean()),
            "recall_at_top10pct": float(y[te][top10].sum() / y[te].sum()),
            "profit_threshold": thr, "profit": profit(y[te], p, thr),
            "calls": int((p >= thr).sum()), "tune_seconds": tune_s, "fit_seconds": fit_s,
            "predict_microsec_per_row": pred_us,
        })
        preds[name], best_est[name] = p, (final, view)
        print(f"{name:32s} AP={rows[-1]['average_precision']:.3f} AUC={rows[-1]['roc_auc']:.3f} "
              f"profit={rows[-1]['profit']:.0f} tune={tune_s:.0f}s", flush=True)

    board = pd.DataFrame(rows).sort_values("average_precision", ascending=False)
    board.to_csv(ART / "leaderboard.csv", index=False)
    pd.DataFrame({"row": te, "y": y[te], **preds}).to_csv(ART / "leaderboard_predictions.csv", index=False)
    top = board.iloc[0]["model"]
    yt = y[te]

    # ---- uncertainty: paired bootstrap of the AP difference against the best model
    rng = np.random.default_rng(SEED)
    boots = rng.integers(0, len(te), size=(300, len(te)))
    top_aps = np.array([average_precision_score(yt[b], preds[top][b]) for b in boots])
    unc = []
    for name, p in preds.items():
        aps = np.array([average_precision_score(yt[b], p[b]) for b in boots])
        diff = aps - top_aps
        unc.append({"model": name, "ap": average_precision_score(yt, p), "ap_lo": np.quantile(aps, .025),
                    "ap_hi": np.quantile(aps, .975), "diff_vs_best_mean": diff.mean(),
                    "diff_vs_best_lo": np.quantile(diff, .025), "diff_vs_best_hi": np.quantile(diff, .975)})
    pd.DataFrame(unc).to_csv(ART / "leaderboard_uncertainty.csv", index=False)

    # ---- stability: refit each model's chosen params on 5 other random splits
    stab = []
    for seed in range(5):
        _, _, tr2, te2 = split(seed=100 + seed)
        for name, (final, view) in best_est.items():
            if name == "Prior (no model)":
                continue
            m = clone(final).fit(V[view].iloc[tr2], y[tr2])
            p2 = proba(m, V[view].iloc[te2])
            stab.append({"model": name, "seed": seed, "average_precision": average_precision_score(y[te2], p2),
                         "roc_auc": roc_auc_score(y[te2], p2)})
    stab = pd.DataFrame(stab)
    stab.to_csv(ART / "leaderboard_stability.csv", index=False)

    # ---- error analysis on the winner
    seg = X.iloc[te].assign(y=yt, p=preds[top])
    seg["called"] = seg.p >= float(board.set_index("model").loc[top, "profit_threshold"])
    by = []
    for col in ["contact", "poutcome", "month", "job"]:
        g = seg.groupby(col).agg(rows=("y", "size"), base_rate=("y", "mean"), mean_score=("p", "mean"),
                                 called=("called", "mean")).reset_index().rename(columns={col: "value"})
        g.insert(0, "feature", col); by.append(g)
    pd.concat(by).to_csv(ART / "leaderboard_segments.csv", index=False)

    # ---- permutation importance (test split, winner only)
    final, view = best_est[top]
    imp = permutation_importance(final, V[view].iloc[te], yt, scoring="average_precision",
                                 n_repeats=5, random_state=SEED, n_jobs=1)
    pd.DataFrame({"feature": X.columns, "importance": imp.importances_mean, "std": imp.importances_std}) \
        .sort_values("importance", ascending=False).to_csv(ART / "leaderboard_importance.csv", index=False)

    make_figures(board, pd.DataFrame(unc), stab, preds, yt, top)

    (ART / "leaderboard_summary.json").write_text(json.dumps({
        "winner_by_average_precision": top, "test_rows": int(len(te)), "train_rows": int(len(tr)),
        "prevalence": float(y.mean()), "random_search_candidates_per_model": N_ITER, "cv_folds": 3,
        "call_everyone_profit": profit(yt, np.ones(len(yt)), 0.5),
        "cost_per_call": COST_PER_CALL, "value_per_subscription": VALUE_PER_SUBSCRIPTION,
        "versions": {"scikit-learn": sklearn.__version__, "xgboost": xgboost.__version__,
                     "lightgbm": lightgbm.__version__, "catboost": catboost.__version__},
    }, indent=2))


def make_figures(board, unc, stab, preds, yt, top) -> None:
    plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 180, "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": .18, "axes.facecolor": "#fbfcfd"})
    fam_col = {"baseline": COLORS["gray"], "linear": COLORS["blue"], "probabilistic": COLORS["violet"],
               "instance": COLORS["gold"], "neural": COLORS["coral"], "tree": COLORS["teal"],
               "bagging": "#3f9d5a", "boosting": COLORS["navy"]}
    fam = board.set_index("model").family

    def save(name):
        plt.tight_layout(); plt.savefig(FIG / name, bbox_inches="tight"); plt.close()

    u = unc.sort_values("ap")
    fig, ax = plt.subplots(figsize=(8, 5.6))
    ax.barh(u.model, u.ap, color=[fam_col[fam[m]] for m in u.model])
    ax.errorbar(u.ap, u.model, xerr=[u.ap - u.ap_lo, u.ap_hi - u.ap], fmt="none", ecolor="#222", capsize=3, lw=1)
    ax.set_xlabel("Average precision on the test split (whiskers: 95% bootstrap interval)")
    ax.set_title("Thirteen models, one split, one tuning budget")
    save("leaderboard-ap.png")

    hi = ["XGBoost", "LightGBM", "CatBoost", "Logistic regression", "Random forest", "Decision tree", "k-nearest neighbors"]
    cc = [COLORS["navy"], COLORS["blue"], COLORS["teal"], COLORS["coral"], "#3f9d5a", COLORS["gold"], COLORS["gray"]]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    for m, c in zip(hi, cc):
        fpr, tpr, _ = roc_curve(yt, preds[m]); axs[0].plot(fpr, tpr, color=c, lw=1.6, label=m)
        pr, rc, _ = precision_recall_curve(yt, preds[m]); axs[1].plot(rc, pr, color=c, lw=1.6, label=m)
    axs[0].plot([0, 1], [0, 1], "--", color="#999")
    axs[0].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC")
    axs[1].axhline(yt.mean(), ls="--", color="#999")
    axs[1].set(xlabel="Recall", ylabel="Precision", title="Precision-recall")
    axs[1].legend(fontsize=8, frameon=False)
    save("leaderboard-curves.png")

    fig, ax = plt.subplots(figsize=(7.6, 5))
    for _, r in board.iterrows():
        if r.model.startswith("Prior"):
            continue
        ax.scatter(r.fit_seconds, r.average_precision, s=90, color=fam_col[r.family], zorder=3)
        ax.annotate(r.model.replace("sklearn ", ""), (r.fit_seconds, r.average_precision), fontsize=8,
                    xytext=(5, 4), textcoords="offset points")
    ax.set_xscale("log"); ax.set_xlabel("Final fit time, seconds (log scale)"); ax.set_ylabel("Test average precision")
    ax.set_title("Is the extra accuracy worth the extra seconds?")
    save("leaderboard-cost-vs-quality.png")

    fig, ax = plt.subplots(figsize=(7.2, 5))
    for m, c in zip(hi[:4], cc[:4]):
        order = np.argsort(-preds[m]); gain = np.cumsum(yt[order]) / yt.sum()
        ax.plot(np.arange(1, len(yt) + 1) / len(yt), gain, color=c, lw=1.8, label=m)
    ax.plot([0, 1], [0, 1], "--", color="#999", label="random calls")
    ax.set(xlabel="Share of customers called (highest score first)",
           ylabel="Share of all subscribers reached", title="Cumulative gains")
    ax.legend(frameon=False)
    save("leaderboard-gains.png")

    fig, ax = plt.subplots(figsize=(6.4, 5))
    for m, c in zip(hi[:4], cc[:4]):
        g = pd.DataFrame({"p": preds[m], "y": yt}).groupby(pd.qcut(preds[m], 10, duplicates="drop"), observed=True).mean()
        ax.plot(g.p, g.y, "o-", color=c, label=m)
    ax.plot([0, 1], [0, 1], "--", color="#999")
    ax.set(xlabel="Predicted probability", ylabel="Observed subscription rate", title="Reliability (deciles)")
    ax.legend(frameon=False)
    save("leaderboard-calibration.png")

    s = stab.groupby("model").average_precision.agg(["mean", "std"]).sort_values("mean")
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    ax.barh(s.index, s["mean"], xerr=s["std"], color=[fam_col[fam[m]] for m in s.index], capsize=3)
    ax.set_xlabel("Average precision over 5 different random splits (mean ± std)")
    ax.set_title("Does the ranking survive a different split?")
    save("leaderboard-stability.png")

    imp = pd.read_csv(ART / "leaderboard_importance.csv").head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.barh(imp.feature, imp.importance, xerr=imp["std"], color=COLORS["teal"], capsize=3)
    ax.set_xlabel(f"Drop in average precision when the column is shuffled ({top})")
    ax.set_title("What the winning model actually uses")
    save("leaderboard-importance.png")

    pb = board[~board.model.str.startswith("Prior")].sort_values("profit")
    fig, ax = plt.subplots(figsize=(7.4, 5))
    ax.barh(pb.model, pb.profit, color=[fam_col[f] for f in pb.family])
    ax.set_xlabel(f"Profit on the test split (call = {COST_PER_CALL:g}, subscription = {VALUE_PER_SUBSCRIPTION:g})")
    ax.set_title("Same models, priced in money")
    save("leaderboard-profit.png")


if __name__ == "__main__":
    main()
