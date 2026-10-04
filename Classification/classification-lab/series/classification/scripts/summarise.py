"""Small summary tables derived from the raw experiment outputs, so articles can cite them with one token.
Safe to re-run; each table is a pure function of files in ../artifacts."""
from __future__ import annotations

import pandas as pd

import protocol as P

A = P.ART


def main() -> None:
    if (A / "bagging_curve.csv").exists():
        c = pd.read_csv(A / "bagging_curve.csv")
        c.groupby("trees").val_ap.agg(["mean", "std", "min", "max"]).reset_index().to_csv(A / "bagging_curve_summary.csv", index=False, float_format="%.5f")
    if (A / "bagging_forest_variants.csv").exists():
        f = pd.read_csv(A / "bagging_forest_variants.csv")
        g = f.groupby("model").agg(val_ap_mean=("val_ap", "mean"), val_ap_sd=("val_ap", "std"), fit_seconds_mean=("fit_seconds", "mean")).reset_index()
        g.to_csv(A / "bagging_forest_summary.csv", index=False, float_format="%.5f")
    if (A / "bagging_n_estimators.csv").exists():
        n = pd.read_csv(A / "bagging_n_estimators.csv")
        n.groupby("n_estimators").val_ap.agg(["mean", "std", "min", "max"]).reset_index().to_csv(A / "bagging_n_estimators_summary.csv", index=False, float_format="%.5f")
    if (A / "boosting_scratch_curve.csv").exists():
        b = pd.read_csv(A / "boosting_scratch_curve.csv")
        peak = b.loc[b.groupby("learning_rate").val_ap.idxmax()][["learning_rate", "stages", "val_ap"]].rename(columns={"stages": "best_stages", "val_ap": "best_val_ap"})
        last = b[b.stages == b.stages.max()][["learning_rate", "val_ap"]].rename(columns={"val_ap": "val_ap_at_1000"})
        peak.merge(last, on="learning_rate").to_csv(A / "boosting_scratch_peaks.csv", index=False, float_format="%.5f")
    if (A / "families_notes.json").exists():
        import json
        n = json.loads((A / "families_notes.json").read_text(encoding="utf-8"))
        pd.DataFrame({"feature": list(n["feature_std"]), "std": list(n["feature_std"].values())}).to_csv(A / "families_notes_std.csv", index=False, float_format="%.2f")
    if (A / "stability_runs.csv").exists():
        s = pd.read_csv(A / "stability_runs.csv")
        agg = s.groupby("model").agg(ap_mean=("ap", "mean"), ap_sd=("ap", "std"), ap_min=("ap", "min"), ap_max=("ap", "max"),
                                     ap_default_mean=("ap_default", "mean"), splits=("seed", "nunique")).reset_index()
        s["rank"] = s.groupby("seed").ap.rank(ascending=False)
        agg = agg.merge(s.groupby("model")["rank"].agg(rank_mean="mean", rank_best="min", rank_worst="max").reset_index(), on="model")
        agg.sort_values("ap_mean", ascending=False).to_csv(A / "stability_summary.csv", index=False, float_format="%.5f")


if __name__ == "__main__":
    main()
