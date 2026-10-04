"""Every figure of the series, drawn from the files in ../artifacts and nothing else.

    python make_figures.py            # all figures whose inputs exist
    python make_figures.py ch06 ch12  # selected figures

A figure never recomputes a model. If its input artifact is missing it is skipped with a message, so a figure can
only show numbers that an experiment script wrote down.
"""
from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve

import metrics as K
import protocol as P

ART, FIG = P.ART, P.FIG
C = {"navy": "#17324d", "blue": "#2a6fbb", "teal": "#168c84", "gold": "#e1a72f", "coral": "#d95f59",
     "gray": "#75808a", "violet": "#7b5ea7", "green": "#3f9d5a"}
FAMILY = {"baseline": C["gray"], "linear": C["blue"], "probabilistic": C["violet"], "instance": C["gold"],
          "neural": C["coral"], "tree": C["teal"], "bagging": C["green"], "boosting": C["navy"]}
plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 180, "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .18, "axes.facecolor": "#fbfcfd"})


def save(name):
    plt.tight_layout()
    plt.savefig(FIG / name, bbox_inches="tight")
    plt.close()
    print("wrote", name)


def csv(name):
    return pd.read_csv(ART / name)


def js(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def short(m):
    return m.replace("sklearn ", "").replace(" (Platt scaled)", "").replace("Small neural net (MLP)", "Neural net (MLP)")


# --------------------------------------------------------------------------------------------- chapters 1-3
def ch01():
    seg = csv("data_segment_rates.csv")
    prev = js("data_profile.json")["prevalence"] * 100
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.9), gridspec_kw={"width_ratios": [1, 1.1, 1.6]})
    for ax, col, title in zip(axs, ["contact", "poutcome", "month"], ["Contact channel", "Previous campaign outcome", "Month of the last contact"]):
        g = seg[seg["column"] == col].sort_values("rate")
        ax.barh(g.level, g.rate * 100, color=C["teal"], xerr=[(g.rate - g.rate_lo) * 100, (g.rate_hi - g.rate) * 100], error_kw={"lw": 1, "capsize": 2})
        for y_, (r, n) in enumerate(zip(g.rate, g.records)):
            ax.text(r * 100 + 1.5, y_, f"n={n:,}", va="center", fontsize=7, color="#555")
        ax.axvline(prev, color=C["coral"], ls="--", lw=1.2)
        ax.set_title(title); ax.set_xlabel("% of records ending in a subscription (95% interval)")
    save("ch01-segments.png")


def ch02():
    d = csv("data_feature_sets.csv")
    sets = ["main", "main + campaign", "no schedule (profile, history, macro)", "profile + history only", "main + duration (not eligible; benchmark only)"]
    labels = ["main set", "+ campaign", "no schedule\ncolumns", "profile +\nhistory only", "+ duration\n(not eligible)"]
    fig, ax = plt.subplots(figsize=(8.2, 4))
    x = np.arange(len(sets)); w = 0.38
    for i, (model, col) in enumerate((("Logistic regression", C["blue"]), ("LightGBM", C["navy"]))):
        g = d[d.model == model].set_index("feature_set").loc[sets]
        ax.bar(x + (i - .5) * w, g.cv_ap_mean, w, yerr=g.cv_ap_sd, capsize=2, color=col, label=model)
    ax.axhline(js("data_profile.json")["prevalence"], color=C["coral"], ls="--", lw=1.2)
    ax.text(len(sets) - .5, js("data_profile.json")["prevalence"] + .01, "random ranking", color=C["coral"], ha="right", fontsize=8)
    ax.set_xticks(x, labels, fontsize=8); ax.set_ylabel("Average precision, 5-fold CV on development rows")
    ax.legend(frameon=False); ax.set_title("What each feature choice is worth")
    save("ch02-duration-leak.png")


def ch02_drift():
    p = js("data_profile.json")
    rate, eur = np.array(p["rate_by_chunk"]) * 100, np.array(p["euribor3m_by_chunk"])
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(np.arange(1, 11), rate, color=C["teal"]); ax.set_xticks(np.arange(1, 11))
    ax.set_xlabel(f"Chunk of {p['chunk_size']:,} records in file order, earliest to latest"); ax.set_ylabel("% ending in a subscription")
    ax2 = ax.twinx(); ax2.plot(np.arange(1, 11), eur, color=C["coral"], marker="o", lw=2); ax2.grid(False)
    ax2.spines["right"].set_visible(True); ax2.set_ylabel("Mean euribor3m (%)", color=C["coral"])
    ax.set_title("The outcome rate rises through the file as the interest rate falls")
    save("ch02-drift.png")


def ch03():
    s = csv("metrics_scores.csv"); y, p = s.y.to_numpy(), s.p.to_numpy()
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.9))
    ts = np.linspace(0.01, 0.9, 90)
    prec = [K.precision_recall_at(y, p >= t)[0] for t in ts]; rec = [K.precision_recall_at(y, p >= t)[1] for t in ts]
    axs[0].plot(ts, prec, color=C["teal"], label="precision"); axs[0].plot(ts, rec, color=C["coral"], label="recall")
    for t in (0.125, 0.5):
        axs[0].axvline(t, color="#999", ls=":"); axs[0].text(t + .01, .93, f"{t}", fontsize=8)
    axs[0].set(xlabel="Threshold", ylabel="Value", title="Precision and recall vs threshold"); axs[0].legend(frameon=False)
    fpr, tpr, _ = roc_curve(y, p); axs[1].plot(fpr, tpr, color=C["blue"]); axs[1].plot([0, 1], [0, 1], "--", color="#999")
    axs[1].set(xlabel="False positive rate", ylabel="Recall", title=f"ROC curve (AUC {K.auc_roc(y, p):.3f})")
    pr, rc, _ = precision_recall_curve(y, p); axs[2].plot(rc, pr, color=C["navy"]); axs[2].axhline(y.mean(), ls="--", color="#999")
    axs[2].set(xlabel="Recall", ylabel="Precision", title=f"Precision-recall curve (AP {K.ap(y, p):.3f})")
    save("ch03-threshold-roc-pr.png")


# --------------------------------------------------------------------------------------------- chapters 4-6
def ch04():
    m = np.linspace(-3, 3, 400); p = np.linspace(0.001, 0.999, 400)
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.9))
    axs[0].plot(m, np.logaddexp(0, -m), color=C["blue"], label="log loss"); axs[0].plot(m, np.maximum(0, 1 - m) ** 2, color=C["coral"], label="squared hinge")
    axs[0].plot(m, np.maximum(0, 1 - m), color=C["gold"], label="hinge"); axs[0].plot(m, np.exp(-m), color=C["navy"], label="exponential")
    axs[0].set(ylim=(0, 6), xlabel="margin m = y · f(x), y in {-1, +1}", ylabel="loss", title="Margin losses (positive record)"); axs[0].legend(frameon=False)
    axs[1].plot(p, -np.log(p), color=C["blue"], label="log loss"); axs[1].plot(p, (1 - p) ** 2, color=C["teal"], label="Brier")
    axs[1].plot(p, -((1 - p) ** 2) * np.log(p), color=C["violet"], label="focal (γ = 2)")
    axs[1].set(ylim=(0, 5), xlabel="predicted probability of the true class", ylabel="loss", title="Probability losses"); axs[1].legend(frameon=False)
    save("loss-and-impurity.png")


def ch05():
    t = csv("linear_odds_ratios.csv")
    names = ["emp.var.rate", "cons.price.idx", "euribor3m", "nr.employed", "pdays", "previous", "age"]
    t2 = pd.concat([t[t.term.isin(names)], t[~t.term.isin(names)].assign(a=lambda d: (d.odds_ratio.apply(np.log)).abs()).sort_values("a", ascending=False).head(10)]).drop_duplicates("term")
    t2 = t2.sort_values("odds_ratio")
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.errorbar(t2.odds_ratio, np.arange(len(t2)), xerr=[t2.odds_ratio - t2.or_lo, t2.or_hi - t2.odds_ratio], fmt="o", color=C["navy"], ecolor=C["gray"], capsize=2)
    ax.set_yticks(np.arange(len(t2)), t2.term, fontsize=8); ax.axvline(1, color=C["coral"], ls="--"); ax.set_xscale("log")
    ax.set_xlabel("Odds ratio (log scale); bars: middle 95% of 100 bootstrap refits")
    ax.set_title("Odds ratios against the most frequent level (categorical) or per SD (numeric)")
    save("ch05-odds-ratios.png")


def ch06():
    d = csv("trees_sweeps.csv")
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.9))
    for ax, setting, xl in ((axs[0], "max_depth", "max_depth"), (axs[1], "min_samples_leaf", "min_samples_leaf")):
        g = d[d.setting == setting].reset_index(drop=True)
        x = np.arange(len(g))
        ax.plot(x, g.train_ap, "o-", color=C["coral"], label="rows the tree was fitted on")
        ax.errorbar(x, g.cv_ap_mean, yerr=g.cv_ap_sd, fmt="o-", color=C["teal"], capsize=3, label="held-out (5-fold CV)")
        ax.set_xticks(x, g.value); ax.set_xlabel(xl); ax.set_ylabel("Average precision"); ax.set_ylim(0, 1)
    axs[0].legend(frameon=False); axs[0].set_title("Depth: the gap opens as the tree grows"); axs[1].set_title("Smallest leaf: larger leaves close the gap")
    save("ch06-tree-overfit.png")


# --------------------------------------------------------------------------------------------- chapters 7-10
def ch07():
    d = csv("bagging_curve.csv")
    g = d.groupby("trees").val_ap.agg(["mean", "std", "min", "max"]).reset_index()
    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax.fill_between(g.trees, g["min"], g["max"], color=C["green"], alpha=.18, label="range over 5 bootstrap seeds")
    ax.plot(g.trees, g["mean"], "o-", color=C["green"], label="mean")
    ax.set_xscale("log"); ax.set_xlabel("Trees averaged"); ax.set_ylabel("Average precision on inner validation rows")
    ax.legend(frameon=False); ax.set_title("Bagging: most of the gain comes early")
    save("ch07-bagging.png")


def ch08():
    d = csv("boosting_scratch_curve.csv")
    fig, ax = plt.subplots(figsize=(7.4, 4))
    for lr, col in ((0.5, C["coral"]), (0.1, C["blue"]), (0.02, C["teal"])):
        g = d[d.learning_rate == lr]
        ax.plot(g.stages, g.val_ap, "o-", color=col, label=f"learning rate {lr}")
    ax.set_xscale("log"); ax.set_xlabel("Boosting stages (trees)"); ax.set_ylabel("Average precision on inner validation rows")
    ax.legend(frameon=False); ax.set_title("Learning rate trades speed against how long you can run")
    save("ch08-boosting-lr.png")


def ch09():
    t = csv("families_svm_timing.csv")
    fig, ax = plt.subplots(figsize=(6.4, 4))
    ax.plot(t.rows, t.fit_seconds_min, "o-", color=C["coral"], label="RBF SVM, measured")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("Training records"); ax.set_ylabel("Fit time, seconds (best of repetitions)")
    slope = js("families_notes.json")["svm_loglog_slope_up_to_16000_rows"]
    ax.set_title(f"RBF-SVM fit time (log-log slope about {slope:.1f} up to 16,000 records)"); ax.legend(frameon=False)
    save("ch09-svm-scaling.png")


def ch10():
    d = csv("budget_curve.csv")
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    for (m, g), col in zip(d.groupby("model"), (C["navy"], C["blue"], C["green"])):
        ax.errorbar(g.budget, g.val_ap_of_winner, yerr=g.val_ap_sd_across_draws, fmt="o-", capsize=3, color=col, label=m)
        ax.axhline(g.default_val_ap.iloc[0], color=col, ls=":", lw=1)
    ax.set_xscale("log"); ax.set_xlabel("Search budget (candidates)"); ax.set_ylabel("Average precision of the winner on rows outside the search")
    ax.set_title("What a bigger search buys (dotted: library defaults)"); ax.legend(frameon=False, fontsize=8)
    save("ch10-budget.png")


def ch11():
    r = csv("calibration_reliability.csv")
    sel = [("Logistic regression", "none (raw)"), ("Random forest (library default)", "none (raw)"), ("Random forest (min_samples_leaf=10)", "none (raw)"),
           ("Gaussian Naive Bayes", "none (raw)"), ("Gaussian Naive Bayes", "sigmoid (5-fold ensemble)")]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, zoom in zip(axs, (False, True)):
        for (m, c), col in zip(sel, (C["blue"], C["coral"], C["green"], C["violet"], C["gold"])):
            g = r[(r.model == m) & (r.calibration == c)]
            ax.errorbar(g.mean_score, g.rate, yerr=[g.rate - g.rate_lo, g.rate_hi - g.rate], fmt="o-", ms=4, lw=1, capsize=2, color=col, label=f"{m} ({c})" if not zoom else None)
        lim = 0.4 if zoom else 1.0
        ax.plot([0, lim], [0, lim], "--", color="#999"); ax.set_xlim(0, lim); ax.set_ylim(0, lim)
        ax.axvline(P.BREAK_EVEN, color="#bbb", ls=":"); ax.set_xlabel("Mean predicted probability in the bin"); ax.set_ylabel("Observed rate (Wilson 95%)")
        ax.set_title("Zoom to scores up to 0.4 (dotted line: break-even 1/8)" if zoom else "Reliability by decile of score")
    axs[0].legend(frameon=False, fontsize=6.5)
    save("ch11-calibration.png")


# --------------------------------------------------------------------------------------------- chapters 12-14
def leaderboard_frames():
    sel = csv("leaderboard_selected.csv"); pred = csv("leaderboard_predictions.csv")
    return sel, pred, sel.set_index("model").family


def ch12():
    sel, pred, fam = leaderboard_frames()
    u = csv("uncertainty_single_ap.csv").sort_values("ap")
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    y_ = np.arange(len(u))
    for i, (_, r) in enumerate(u.iterrows()):
        ax.errorbar(r.ap, i, xerr=[[r.ap - r.ap_lo], [r.ap_hi - r.ap]], fmt="o", color=FAMILY[fam[r.model]], ecolor="#888", capsize=3, ms=8)
    ax.set_yticks(y_, u.model.map(short)); ax.set_xlim(0.35, 0.56)
    ax.set_xlabel("Average precision, comparison split (bars: 95% bootstrap interval)")
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k) for k, c in FAMILY.items() if k != "baseline"]
    ax.legend(handles=handles, frameon=False, fontsize=7, loc="lower right", title="family", title_fontsize=7)
    ax.set_title("Twelve models under one search protocol (random ranking would score 0.113)")
    save("leaderboard-ap.png")


def ch12_curves():
    sel, pred, fam = leaderboard_frames()
    y = pred.y.to_numpy()
    show = ["LightGBM", "Random forest", "Logistic regression", "Decision tree", "k-nearest neighbours"]
    cols = [C["navy"], C["green"], C["coral"], C["teal"], C["gold"]]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    for m, c in zip(show, cols):
        f, t, _ = roc_curve(y, pred[m]); axs[0].plot(f, t, color=c, lw=1.5, label=m)
        pr, rc, _ = precision_recall_curve(y, pred[m]); axs[1].plot(rc, pr, color=c, lw=1.5, label=m)
    axs[0].plot([0, 1], [0, 1], "--", color="#999"); axs[0].set(xlabel="False positive rate", ylabel="Recall", title="ROC")
    axs[1].axhline(y.mean(), ls="--", color="#999"); axs[1].set(xlabel="Recall", ylabel="Precision", title="Precision-recall"); axs[1].legend(frameon=False, fontsize=8)
    save("leaderboard-curves.png")


def ch12_cost():
    sel, pred, fam = leaderboard_frames()
    t = csv("timing.csv")
    d = t.merge(sel[["model", "cmp_average_precision"]], on="model")
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    for _, r in d.iterrows():
        axs[0].scatter(r.fit_seconds_best, r.cmp_average_precision, s=70, color=FAMILY[r.family], zorder=3)
        axs[0].annotate(short(r.model), (r.fit_seconds_best, r.cmp_average_precision), fontsize=7, xytext=(4, 3), textcoords="offset points")
        axs[1].scatter(r.batch_records_per_second, r.cmp_average_precision, s=70, color=FAMILY[r.family], zorder=3)
        axs[1].annotate(short(r.model), (r.batch_records_per_second, r.cmp_average_precision), fontsize=7, xytext=(4, 3), textcoords="offset points")
    axs[0].set(xscale="log", xlabel="Final fit time on development rows, seconds (log)", ylabel="Comparison-split AP", title="Training cost")
    axs[1].set(xscale="log", xlabel="Batch scoring, records per second including preprocessing (log)", title="Scoring throughput")
    save("leaderboard-cost-vs-quality.png")


def ch13():
    t = csv("uncertainty_paired_ap.csv")
    g = t[(t.resampling == "rows") & (t.reference == "Logistic regression")].sort_values("diff")
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    y_ = np.arange(len(g))
    ax.errorbar(g["diff"], y_ + .12, xerr=[g["diff"] - g.simultaneous95_lo, g.simultaneous95_hi - g["diff"]], fmt="none", ecolor=C["gold"], lw=3, label="simultaneous 95%")
    ax.errorbar(g["diff"], y_ - .12, xerr=[g["diff"] - g.ci95_lo, g.ci95_hi - g["diff"]], fmt="o", color=C["navy"], capsize=3, label="marginal 95%")
    ax.axvline(0, color=C["coral"], ls="--"); ax.set_yticks(y_, g.model.map(short))
    ax.set_xlabel("AP difference from logistic regression (same resampled records)"); ax.legend(frameon=False)
    ax.set_title("Paired differences against the simple baseline")
    save("leaderboard-paired.png")
    s = csv("stability_runs.csv")
    if len(s):
        m = s.groupby("model").ap.agg(["mean", "std"]).sort_values("mean")
        fig, ax = plt.subplots(figsize=(8, 5.2))
        sel, _, fam = leaderboard_frames()
        ax.barh(m.index.map(short), m["mean"], xerr=m["std"], color=[FAMILY[fam[i]] for i in m.index], capsize=3, alpha=.85)
        for i, name in enumerate(m.index):
            ax.scatter(s[s.model == name].ap, [i] * (s.model == name).sum(), color="#222", s=10, zorder=3)
        ax.set_xlabel("AP over other random splits, each model re-tuned on its split (dots: single splits)")
        ax.set_title("Variation when training sample, test sample and search all change")
        save("leaderboard-stability.png")


def ch14():
    p = csv("policy_by_model.csv"); b = csv("policy_baselines.csv").set_index("policy").contribution
    q = p[p.policy.str.startswith("break")].sort_values("contribution")
    sel, _, fam = leaderboard_frames()
    fig, ax = plt.subplots(figsize=(8.4, 5))
    ax.barh(q.model.map(short), q.contribution, color=[FAMILY[fam[m]] for m in q.model])
    for lab, col in (("call everyone", C["coral"]), ("prior-success rule", C["gold"])):
        ax.axvline(b[lab], color=col, ls="--"); ax.text(b[lab], len(q) - .4, lab, color=col, fontsize=8, rotation=90, va="top", ha="right")
    ax.set_xlabel("Simulated contribution at break-even 1/8 on the comparison split (cost 1, value 8; illustrative)")
    ax.set_title("Same frozen scores, one illustrative price list")
    save("leaderboard-profit.png")
    c = csv("policy_capacity.csv")
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for m, col in (("LightGBM", C["navy"]), ("Logistic regression", C["coral"]), ("Random forest", C["green"])):
        g = c[(c.model == m) & (c.break_even_guard == True)]
        ax.plot(g.capacity, g.contribution, "o-", color=col, label=f"{m}, capped at k, never below 1/8")
        g2 = c[(c.model == m) & (c.break_even_guard == False)]
        ax.plot(g2.capacity, g2.contribution, "x--", color=col, alpha=.6)
    ax.axhline(b["prior-success rule"], color=C["gold"], ls="--", label="prior-success rule"); ax.axhline(0, color="#999", lw=.8)
    ax.set_xlabel("Capacity k (contacts per list)"); ax.set_ylabel("Simulated contribution"); ax.legend(frameon=False, fontsize=7)
    ax.set_title("Capacity is a ceiling: dashed crosses ignore the break-even guard")
    save("ch14-capacity.png")


# --------------------------------------------------------------------------------------------- chapters 15-16
def ch15():
    pm = csv("importance_permutation.csv").head(10).iloc[::-1]
    g = csv("importance_groups.csv")
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    axs[0].barh(pm.feature, pm.ap_drop_mean, xerr=pm.ap_drop_sd, color=C["teal"], capsize=3)
    axs[0].set_xlabel("AP drop when one column is shuffled (10 repeats)"); axs[0].set_title("Single-column permutation")
    y_ = np.arange(len(g)); w = .27
    axs[1].barh(y_ + w, g.sum_of_single_column_drops, w, color=C["gray"], label="sum of single-column drops")
    axs[1].barh(y_, g.grouped_ap_drop_mean, w, color=C["gold"], label="group shuffled together")
    axs[1].barh(y_ - w, g.ap_drop_vs_full, w, color=C["navy"], label="retrained without the group")
    axs[1].set_yticks(y_, g.group.str.replace(r" \(.*\)", "", regex=True)); axs[1].legend(frameon=False, fontsize=8)
    axs[1].set_xlabel("AP drop"); axs[1].set_title("Groups: three different questions")
    save("leaderboard-importance.png")


def ch16():
    pol = csv("temporal_policies.csv")
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
    base = pol[(pol.policy == "break-even (1/8)")]
    for ax, metric, ttl in ((axs[0], "ap", "Average precision on the future records"), (axs[1], "contribution", "Simulated contribution at break-even 1/8")):
        pivot = base.pivot(index="model", columns="correction", values=metric)
        order = pivot["none"].sort_values().index if metric == "ap" else pivot["none"].sort_values().index
        for k, (c, col) in enumerate((("none", C["coral"]), ("EM on unlabelled scores", C["gold"]), ("oracle prevalence (diagnostic)", C["teal"]))):
            if metric == "ap" and c != "none":
                continue
            ax.barh(np.arange(len(order)) + (k - 1) * .27, pivot.loc[order, c], .27, color=col, label=c)
        ax.set_yticks(np.arange(len(order)), [short(m) for m in order], fontsize=8); ax.set_title(ttl)
    ev = pol.call_everyone.iloc[0]
    axs[1].axvline(ev, color="k", ls="--"); axs[1].text(ev, -.6, "call everyone", fontsize=8, rotation=90, va="bottom", ha="right")
    axs[0].axvline(P.build_manifest()["blocks"][3]["prevalence"], color="#999", ls=":"); axs[0].set_xlabel("AP (dotted: prevalence of the future block)")
    axs[1].legend(frameon=False, fontsize=7)
    save("ch16-time-shift.png")
    f = pd.DataFrame(P.build_manifest()["blocks"])
    f = f[f.block.str.contains("fold|future|development \\(first", regex=True)] if False else f
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    t = f[f.block.str.startswith("temporal fold") & f.block.str.endswith("validate")].reset_index(drop=True)
    parts = [("training window", f[f.block == "temporal development (first 80% of rows)"].iloc[0]), ("future", f[f.block == "future (last 20% of rows)"].iloc[0])]
    labels = [b.split(": ")[0] for b in t.block] + ["future"]
    prev = list(t.prevalence) + [parts[1][1].prevalence]
    ax.bar(labels, np.array(prev) * 100, color=[C["teal"]] * len(t) + [C["coral"]])
    for i, (b, pr) in enumerate(zip(list(t.records) + [parts[1][1].records], prev)):
        ax.text(i, pr * 100 + .8, f"{int(b):,} records", ha="center", fontsize=8)
    ax.set_ylabel("% subscribed in the validation block"); ax.set_title("Prevalence of the temporal validation blocks and of the future")
    save("ch16-folds.png")


ALL = {"ch01": ch01, "ch02": ch02, "ch02_drift": ch02_drift, "ch03": ch03, "ch04": ch04, "ch05": ch05, "ch06": ch06, "ch07": ch07,
       "ch08": ch08, "ch09": ch09, "ch10": ch10, "ch11": ch11, "ch12": ch12, "ch12_curves": ch12_curves, "ch12_cost": ch12_cost,
       "ch13": ch13, "ch14": ch14, "ch15": ch15, "ch16": ch16}

if __name__ == "__main__":
    for name in sys.argv[1:] or list(ALL):
        try:
            ALL[name]()
        except FileNotFoundError as e:
            print(f"skipped {name}: missing {e.filename}")
