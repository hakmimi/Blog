"""Chapter 15: what does the chosen model rely on, and who does it miss?

The model audited is the one a reader would have chosen from *development* evidence: the highest mean
cross-validated AP in leaderboard_selected.csv. Scores come from the frozen pipeline on the comparison split.

Four different questions, four different tools (they must not be read as one):
  gain importance          how much a boosted model's training loss fell at splits on a column (training usage)
  permutation importance   how much the frozen model's AP drops when a column's values are shuffled across records
                           (reliance of this fitted model; can create combinations that never occur)
  grouped permutation      the same, shuffling a group of columns together so relationships *inside* the group survive
  drop-group retraining    how much AP drops when a model with the same settings is refit without the group
                           (what the remaining columns can substitute for; settings were not re-tuned)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.base import clone

import metrics as K
import models as M
import protocol as P

GROUPS = {
    "macro (5 columns)": ["emp.var.rate", "cons.price.idx", "cons.conf.idx", "euribor3m", "nr.employed"],
    "history (pdays, previous, poutcome)": ["pdays", "previous", "poutcome"],
    "schedule (contact, month, day_of_week)": ["contact", "month", "day_of_week"],
    "customer profile (7 columns)": ["age", "job", "marital", "education", "default", "housing", "loan"],
}


def permute(Xc: pd.DataFrame, cols, rng):
    Xp = Xc.copy()
    order = rng.permutation(len(Xp))
    for c in cols:                               # one column at a time so each keeps its dtype
        Xp[c] = Xc[c].iloc[order].to_numpy()
    return Xp


def run() -> None:
    X, y = P.load()
    dev, comp = P.random_split(y)
    sel = pd.read_csv(P.ART / "leaderboard_selected.csv").dropna(subset=["cv_ap"])
    ref = sel.sort_values("cv_ap", ascending=False).iloc[0]
    name, params, thr = ref["model"], json.loads(ref["params"]), float(ref["threshold_oof"])
    spec = [s for s in M.registry(X) if s.name == name][0]
    model = clone(spec.build()).set_params(**params).fit(X.iloc[dev], y[dev])
    yc, Xc = y[comp], X.iloc[comp]
    base = model.predict_proba(Xc)[:, 1]
    base_ap = K.ap(yc, base)
    rng = np.random.default_rng(P.SEED)

    perm = []
    for col in X.columns:
        drops = [base_ap - K.ap(yc, model.predict_proba(permute(Xc, [col], rng))[:, 1]) for _ in range(10)]
        perm.append({"feature": col, "ap_drop_mean": np.mean(drops), "ap_drop_sd": np.std(drops, ddof=1)})
    perm = pd.DataFrame(perm).sort_values("ap_drop_mean", ascending=False)
    perm.to_csv(P.ART / "importance_permutation.csv", index=False, float_format="%.5f")

    grouped = []
    for g, cols in GROUPS.items():
        drops_joint = [base_ap - K.ap(yc, model.predict_proba(permute(Xc, cols, rng))[:, 1]) for _ in range(10)]
        indiv = perm.set_index("feature").loc[cols, "ap_drop_mean"].sum()
        grouped.append({"group": g, "grouped_ap_drop_mean": np.mean(drops_joint), "grouped_ap_drop_sd": np.std(drops_joint, ddof=1),
                        "sum_of_single_column_drops": indiv})
    # drop-group retraining: same settings, columns removed, three fitting seeds where the model has a seed
    drops = []
    for g, cols in GROUPS.items():
        keep = [c for c in X.columns if c not in cols]
        aps = []
        for seed in range(3):
            est = clone([s for s in M.registry(X[keep]) if s.name == name][0].build()).set_params(**params)
            for k in est.get_params():
                if k.endswith("random_state"):
                    est.set_params(**{k: P.SEED + seed})
            est.fit(X[keep].iloc[dev], y[dev])
            aps.append(K.ap(yc, est.predict_proba(X[keep].iloc[comp])[:, 1]))
        drops.append({"group": g, "retrained_ap_mean": np.mean(aps), "retrained_ap_sd": np.std(aps, ddof=1),
                      "ap_drop_vs_full": base_ap - np.mean(aps)})
    g_tbl = pd.DataFrame(grouped).merge(pd.DataFrame(drops), on="group")
    g_tbl.to_csv(P.ART / "importance_groups.csv", index=False, float_format="%.5f")

    # gain importance of a boosted model (LightGBM at its selected settings): usage during training
    lg = sel[sel.model == "LightGBM"].iloc[0]
    gm = clone([s for s in M.registry(X) if s.name == "LightGBM"][0].build()).set_params(**json.loads(lg["params"])).fit(X.iloc[dev], y[dev])
    booster = gm[-1].model_
    gain = pd.Series(booster.booster_.feature_importance(importance_type="gain"), index=booster.booster_.feature_name())
    gain = (gain / gain.sum()).sort_values(ascending=False).rename("gain_share").reset_index().rename(columns={"index": "feature"})
    gain.to_csv(P.ART / "importance_gain_lightgbm.csv", index=False, float_format="%.5f")

    # ---- errors under the frozen policy -----------------------------------------------------------------
    selected = base >= thr
    frame = X.iloc[comp].assign(y=yc, score=base, selected=selected)
    pos = frame[frame.y == 1].copy()
    q50, q90 = np.quantile(base, 0.5), np.quantile(base, 0.9)
    pos["rank_group"] = np.where(pos.score >= q90, "high-ranked (top 10% of scores)",
                                 np.where(pos.score < q50, "low-ranked (below the median score)", "middle"))
    groups = pos.rank_group.value_counts().rename_axis("positives_group").rename("positives").reset_index()
    groups["share_of_positives"] = groups.positives / len(pos)
    groups.to_csv(P.ART / "errors_positive_rank_groups.csv", index=False, float_format="%.4f")
    policy = pd.DataFrame([{"policy": f"{name}, out-of-fold threshold {thr:.3f}", "records_selected": int(selected.sum()),
                            "true_positives": int((selected & (frame.y == 1)).sum()),
                            "false_negatives": int((~selected & (frame.y == 1)).sum()), "positives": int(frame.y.sum())}])
    policy.to_csv(P.ART / "errors_policy_counts.csv", index=False)

    seg = []
    for col in ("contact", "poutcome", "month", "job"):
        for lvl, g in frame.groupby(col):
            n, k = len(g), int(g.y.sum())
            fn = int(((~g.selected) & (g.y == 1)).sum())
            lo, hi = K.wilson(k, n)
            fo, fh = K.wilson(fn, k) if k else (np.nan, np.nan)
            seg.append({"column": col, "level": lvl, "records": n, "positives": k, "observed_rate": k / n, "rate_lo": lo, "rate_hi": hi,
                        "mean_score": float(g.score.mean()), "mean_score_inside_rate_interval": bool(lo <= g.score.mean() <= hi),
                        "false_negatives": fn, "false_negative_rate_among_positives": fn / k if k else np.nan, "fn_rate_lo": fo, "fn_rate_hi": fh,
                        "share_selected": float(g.selected.mean())})
    pd.DataFrame(seg).to_csv(P.ART / "errors_segments.csv", index=False, float_format="%.4f")
    P.write_json("importance_notes.json", {"audited_model": name, "selection_rule": "highest mean cross-validated AP on development data",
                                           "cv_ap": float(ref["cv_ap"]), "comparison_ap": base_ap, "threshold_oof": thr,
                                           "rank_cutoffs": {"median_score": float(q50), "top10pct_score": float(q90)}})
    pd.set_option("display.width", 220)
    print(name, base_ap); print(perm.head(8).round(4)); print(g_tbl.round(4).to_string(index=False)); print(gain.head(8).round(3))
    print(groups); print(policy)


if __name__ == "__main__":
    run()
