"""Figures for chapters 1-11. Each function is independent; run all with no arguments.

    python chapter_figures.py            # everything
    python chapter_figures.py ch03 ch06  # selected chapters
"""
from __future__ import annotations

import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve
from sklearn.pipeline import make_pipeline
from sklearn.tree import DecisionTreeClassifier

from common import COLORS, FIG, SEED, linear_prep, load_bank, split, tree_prep

warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 180, "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .18, "axes.facecolor": "#fbfcfd"})


def save(name: str) -> None:
    plt.tight_layout(); plt.savefig(FIG / name, bbox_inches="tight"); plt.close()


def ch01() -> None:
    X, y = load_bank()
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), gridspec_kw={"width_ratios": [1, 1, 1.6]})
    for ax, col, title in zip(axs, ["contact", "poutcome", "month"], ["Contact channel", "Outcome of previous campaign", "Month of call"]):
        r = pd.Series(y).groupby(X[col].to_numpy()).mean().sort_values()
        ax.barh(r.index, r.values * 100, color=COLORS["teal"])
        ax.axvline(y.mean() * 100, color=COLORS["coral"], ls="--", lw=1.2)
        ax.set_title(title); ax.set_xlabel("% who subscribed")
    axs[0].text(y.mean() * 100 + .4, -0.45, "average 11.3%", color=COLORS["coral"], fontsize=8)
    save("ch01-segments.png")


def ch02() -> None:
    X, y, tr, te = split()
    Xd = X.copy(); Xd["duration"] = pd.read_csv(str(FIG.parent / "data/raw/bank-additional-full.csv"), sep=";")["duration"]
    out = {}
    for label, frame in [("without duration", X), ("with duration", Xd)]:
        m = make_pipeline(linear_prep(frame), LogisticRegression(max_iter=2000))
        p = m.fit(frame.iloc[tr], y[tr]).predict_proba(frame.iloc[te])[:, 1]
        out[label] = (roc_auc_score(y[te], p), average_precision_score(y[te], p))
    fig, ax = plt.subplots(figsize=(6, 3.6))
    xs = np.arange(2); w = .35
    ax.bar(xs - w / 2, [out[k][0] for k in out], w, label="ROC-AUC", color=COLORS["blue"])
    ax.bar(xs + w / 2, [out[k][1] for k in out], w, label="Average precision", color=COLORS["coral"])
    for i, k in enumerate(out):
        ax.text(i - w / 2, out[k][0] + .01, f"{out[k][0]:.2f}", ha="center"); ax.text(i + w / 2, out[k][1] + .01, f"{out[k][1]:.2f}", ha="center")
    ax.set_xticks(xs, list(out)); ax.set_ylim(0, 1.05); ax.legend(frameon=False)
    ax.set_title("Same model; one column that does not exist before the call")
    save("ch02-duration-leak.png")


def ch02_drift() -> None:
    X, y = load_bank()
    chunk = np.arange(len(X)) // 4119
    rate = pd.Series(y).groupby(chunk).mean() * 100
    euribor = X["euribor3m"].groupby(chunk).mean()
    print("rate %:", rate.round(1).tolist()); print("euribor3m:", euribor.round(2).tolist())
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(rate.index + 1, rate.values, color=COLORS["teal"])
    ax.set_xticks(rate.index + 1); ax.set_xlabel("Chunk of 4,119 calls, oldest to newest"); ax.set_ylabel("% who subscribed")
    ax2 = ax.twinx(); ax2.plot(euribor.index + 1, euribor.values, color=COLORS["coral"], marker="o", lw=2)
    ax2.set_ylabel("Mean euribor3m (%)", color=COLORS["coral"]); ax2.grid(False); ax2.spines["right"].set_visible(True)
    ax.set_title("The subscription rate climbs as the interest rate falls")
    save("ch02-drift.png")


def ch03() -> None:
    X, y, tr, te = split()
    m = make_pipeline(linear_prep(X), LogisticRegression(max_iter=2000)).fit(X.iloc[tr], y[tr])
    p = m.predict_proba(X.iloc[te])[:, 1]; yt = y[te]
    pr, rc, th = precision_recall_curve(yt, p)
    fpr, tpr, _ = roc_curve(yt, p)
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.9))
    axs[0].plot(th, pr[:-1], color=COLORS["coral"], label="precision"); axs[0].plot(th, rc[:-1], color=COLORS["blue"], label="recall")
    axs[0].axvline(.5, color="#999", ls=":"); axs[0].set(xlabel="Decision threshold", title="Moving the threshold trades one for the other"); axs[0].legend(frameon=False)
    axs[1].plot(fpr, tpr, color=COLORS["navy"]); axs[1].plot([0, 1], [0, 1], "--", color="#999")
    axs[1].set(xlabel="False positive rate", ylabel="True positive rate", title=f"ROC (AUC {roc_auc_score(yt, p):.2f})")
    axs[2].plot(rc, pr, color=COLORS["teal"]); axs[2].axhline(yt.mean(), ls="--", color="#999")
    axs[2].set(xlabel="Recall", ylabel="Precision", title=f"Precision-recall (AP {average_precision_score(yt, p):.2f})")
    save("ch03-threshold-roc-pr.png")


def _enc():
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder
    X, y, tr, te = split()
    cat = X.select_dtypes(include="object").columns.tolist()
    prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)], remainder="passthrough")
    return X, y, tr, te, prep.fit_transform(X.iloc[tr]), prep.transform(X.iloc[te])


def ch05() -> None:
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    X, y, tr, te = split()
    cat = X.select_dtypes(include="object").columns.tolist()
    prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), cat)], remainder=StandardScaler())
    m = make_pipeline(prep, LogisticRegression(C=0.1, max_iter=2000)).fit(X.iloc[tr], y[tr])
    coef = pd.Series(m[-1].coef_[0], index=[n.split("__", 1)[1] for n in m[0].get_feature_names_out()])
    odds = np.exp(coef).sort_values()
    show = pd.concat([odds.head(8), odds.tail(8)])
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.barh(show.index, show.values - 1, left=1, color=[COLORS["coral"] if v < 1 else COLORS["teal"] for v in show.values])
    ax.axvline(1, color="#333", lw=1); ax.set_xscale("log")
    ax.set_xlabel("Odds ratio (log scale; 1 = no effect)"); ax.set_title("Logistic regression: strongest effects (C = 0.1)")
    save("ch05-odds-ratios.png")


def ch06() -> None:
    from sklearn.model_selection import cross_val_score
    X, y, tr, te, A, B = _enc()
    depths = [2, 3, 4, 5, 6, 8, 10, 12, 16, None]
    tr_ap, cv_ap = [], []
    for d in depths:
        t = DecisionTreeClassifier(max_depth=d, random_state=SEED).fit(A, y[tr])
        tr_ap.append(average_precision_score(y[tr], t.predict_proba(A)[:, 1]))
        cv_ap.append(cross_val_score(DecisionTreeClassifier(max_depth=d, random_state=SEED), A, y[tr], cv=3, scoring="average_precision").mean())
    xs = [d if d else 40 for d in depths]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(xs, tr_ap, "o-", color=COLORS["coral"], label="training data")
    ax.plot(xs, cv_ap, "o-", color=COLORS["teal"], label="cross-validation")
    ax.set_xscale("log"); ax.set_xticks(xs, [str(d) if d else "none" for d in depths]); ax.minorticks_off()
    ax.set(xlabel="max_depth", ylabel="Average precision", title="The overfitting gap opens as the tree grows"); ax.legend(frameon=False)
    save("ch06-tree-overfit.png")


def ch07() -> None:
    X, y, tr, te, A, B = _enc()
    rng = np.random.default_rng(0); votes = []
    for i in range(100):
        rows = rng.integers(0, len(A), len(A))
        votes.append(DecisionTreeClassifier(min_samples_leaf=20, random_state=i).fit(A[rows], y[tr][rows]).predict_proba(B)[:, 1])
    votes = np.array(votes); ns = [1, 2, 3, 5, 8, 12, 18, 25, 40, 60, 100]
    ap = [average_precision_score(y[te], votes[:n].mean(axis=0)) for n in ns]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(ns, ap, "o-", color=COLORS["navy"]); ax.axhline(ap[0], ls="--", color="#999")
    ax.text(ns[-1], ap[0] + .004, "a single tree", ha="right", color="#666")
    ax.set(xlabel="Trees averaged (bootstrap bagging)", ylabel="Test average precision", title="Averaging noisy trees"); ax.set_xscale("log")
    save("ch07-bagging.png")


def ch08() -> None:
    from sklearn.tree import DecisionTreeRegressor
    X, y, tr, te, A, B = _enc()
    sig = lambda z: 1 / (1 + np.exp(-z)); ytr = y[tr]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for lr, c in [(0.5, COLORS["coral"]), (0.1, COLORS["blue"]), (0.02, COLORS["teal"])]:
        base = np.log(ytr.mean() / (1 - ytr.mean())); Ft, Fe = np.full(len(A), base), np.full(len(B), base); xs, ys = [], []
        for m in range(1, 301):
            t = DecisionTreeRegressor(max_depth=3, min_samples_leaf=20).fit(A, ytr - sig(Ft))
            Ft += lr * t.predict(A); Fe += lr * t.predict(B)
            if m % 10 == 0 or m == 1:
                xs.append(m); ys.append(average_precision_score(y[te], sig(Fe)))
        ax.plot(xs, ys, color=c, lw=2, label=f"learning rate {lr}")
    ax.set(xlabel="Boosting stages (trees)", ylabel="Test average precision", title="Smaller steps need more trees"); ax.legend(frameon=False)
    save("ch08-boosting-lr.png")


def ch09() -> None:
    import time
    from sklearn.svm import SVC, LinearSVC
    X, y, tr, te = split()
    A = linear_prep(X, sparse=False).fit_transform(X.iloc[tr])
    ns = [1000, 2000, 4000, 8000, 16000]; rbf, lin = [], []
    for n in ns:
        t0 = time.perf_counter(); SVC(C=1, gamma="scale").fit(A[:n], y[tr][:n]); rbf.append(time.perf_counter() - t0)
        t0 = time.perf_counter(); LinearSVC(C=0.1, dual=False).fit(A[:n], y[tr][:n]); lin.append(time.perf_counter() - t0)
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ax.plot(ns, rbf, "o-", color=COLORS["coral"], label="RBF SVM"); ax.plot(ns, lin, "o-", color=COLORS["blue"], label="Linear SVM")
    ax.set(xscale="log", yscale="log", xlabel="Training rows", ylabel="Fit time (seconds)", title="Kernel SVMs scale roughly quadratically"); ax.legend(frameon=False)
    save("ch09-svm-scaling.png")


def ch10() -> None:
    t = pd.read_csv(FIG.parent / "artifacts" / "ch10_candidates.csv"); rng = np.random.default_rng(0)
    budgets = [1, 2, 3, 4, 6, 8, 12, 16, 24, 40]; mean, lo, hi = [], [], []
    for b in budgets:
        tes = []
        for _ in range(300):
            pick = t.iloc[rng.permutation(len(t))[:b]]; tes.append(pick.loc[pick.cv_ap.idxmax(), "test_ap"])
        mean.append(np.mean(tes)); lo.append(np.quantile(tes, .1)); hi.append(np.quantile(tes, .9))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.fill_between(budgets, lo, hi, color=COLORS["teal"], alpha=.2, label="10th-90th percentile over 300 searches")
    ax.plot(budgets, mean, "o-", color=COLORS["teal"], label="mean test AP of the CV winner")
    ax.set(xscale="log", xlabel="Random candidates evaluated", ylabel="Test average precision", title="What a bigger tuning budget buys"); ax.legend(frameon=False)
    save("ch10-budget.png")


def ch11() -> None:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.naive_bayes import GaussianNB
    X, y, tr, te = split()
    Xf, Xc, yf, yc = train_test_split(X.iloc[tr], y[tr], test_size=0.25, stratify=y[tr], random_state=1)
    models = {"Logistic regression": LogisticRegression(C=0.1, max_iter=2000),
              "Random forest": RandomForestClassifier(300, min_samples_leaf=10, n_jobs=-1, random_state=0),
              "Naive Bayes": GaussianNB(var_smoothing=1e-3)}
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    for (name, est), c in zip(models.items(), [COLORS["blue"], "#3f9d5a", COLORS["coral"]]):
        p = make_pipeline(linear_prep(X, sparse=False), est).fit(Xf, yf).predict_proba(X.iloc[te])[:, 1]
        g = pd.DataFrame({"p": p, "y": y[te]}).groupby(pd.qcut(p, 10, duplicates="drop"), observed=True).mean()
        ax.plot(g.p, g.y, "o-", color=c, label=name)
    ax.plot([0, 1], [0, 1], "--", color="#999")
    ax.set(xlabel="Mean predicted probability (decile)", ylabel="Observed subscription rate", title="Reliability diagram"); ax.legend(frameon=False)
    save("ch11-calibration.png")


def ch16() -> None:
    art = FIG.parent / "artifacts"
    rnd = pd.read_csv(art / "leaderboard.csv").set_index("model")
    chrono = pd.read_csv(art / "chronological_leaderboard.csv").set_index("model")
    order = chrono.sort_values("average_precision").index
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.15, 1]})
    ys = np.arange(len(order)); h = .38
    axs[0].barh(ys + h / 2, [rnd.loc[m, "average_precision"] for m in order], h, color=COLORS["gray"], label="random split")
    axs[0].barh(ys - h / 2, chrono.loc[order, "average_precision"], h, color=COLORS["coral"], label="train on past, test on future")
    axs[0].set_yticks(ys, order); axs[0].set_xlabel("Average precision"); axs[0].set_title("The ranking changes"); axs[0].legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    prof = chrono.profit_at_eighth.sort_values()
    axs[1].barh(prof.index, prof.values, color=[COLORS["teal"] if v > 12000 else COLORS["navy"] for v in prof.values])
    axs[1].axvline(12082, color=COLORS["coral"], ls="--"); axs[1].text(11900, len(prof) - 0.45, "call everyone: 12,082 ", color=COLORS["coral"], fontsize=8, ha="right", va="bottom")
    axs[1].set_xlabel("Profit at threshold 1/8 on the future test set"); axs[1].set_title("...and so does the money")
    save("ch16-time-shift.png")


ALL = {"ch01": ch01, "ch02": ch02, "ch02_drift": ch02_drift, "ch03": ch03, "ch05": ch05, "ch06": ch06, "ch07": ch07,
       "ch08": ch08, "ch09": ch09, "ch10": ch10, "ch11": ch11, "ch16": ch16}

if __name__ == "__main__":
    for name in (sys.argv[1:] or ALL):
        print("figure", name); ALL[name]()
