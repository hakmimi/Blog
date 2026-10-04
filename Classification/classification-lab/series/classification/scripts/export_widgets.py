"""Write the JSON that feeds the two browser widgets, from frozen experiment outputs only.

  threshold_lab.json    comparison-split scores of five models (chapters 3 and 14)
  prior_shift_lab.json  future-block scores for the temporal chapter (chapter 16), with the lagged and EM prevalence
                        estimates, so the widget can show feasible and oracle corrections side by side
"""
from __future__ import annotations

import json

import pandas as pd

import protocol as P

THRESHOLD_MODELS = ["LightGBM", "XGBoost", "Random forest", "Logistic regression", "Gaussian Naive Bayes"]
SHIFT_MODELS = ["LightGBM", "Logistic regression", "Random forest"]


def main() -> None:
    pred = pd.read_csv(P.ART / "leaderboard_predictions.csv").sort_values("row")
    out = {"y": pred["y"].astype(int).tolist(), "models": {m: [round(float(p), 4) for p in pred[m]] for m in THRESHOLD_MODELS}}
    (P.ART / "threshold_lab.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("threshold_lab.json", len(pred), "rows")
    path = P.ART / "temporal_future_scores.csv"
    if path.exists():
        fut = pd.read_csv(path)
        shift = json.loads((P.ART / "temporal_shift.json").read_text(encoding="utf-8"))
        out = {"y": fut["y"].astype(int).tolist(), "train_rate": shift["prevalence_past"],
               "last_block_rate": shift["prevalence_last_validation_block"], "test_rate": shift["prevalence_future"],
               "em_rate": {m: round(shift["em_estimate_by_model"][m], 4) for m in SHIFT_MODELS},
               "models": {m: [round(float(p), 5) for p in fut[m]] for m in SHIFT_MODELS}}
        (P.ART / "prior_shift_lab.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
        print("prior_shift_lab.json", len(fut), "rows")


if __name__ == "__main__":
    main()
