import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

# test-set scores of every model, saved by run_leaderboard.py (no retraining needed)
pred = pd.read_csv("../../artifacts/leaderboard_predictions.csv")
y = pred["y"].to_numpy()
print(len(y), "test customers,", y.sum(), "subscribers")

rng = np.random.default_rng(42)
boots = rng.integers(0, len(y), size=(1000, len(y)))               # 1000 resamples of the customers

def ap_samples(model):
    p = pred[model].to_numpy()
    return np.array([average_precision_score(y[b], p[b]) for b in boots])

lgbm = ap_samples("LightGBM")
print(f"\nLightGBM alone: AP = {average_precision_score(y, pred['LightGBM']):.3f}, "
      f"95% interval {np.quantile(lgbm, .025):.3f} to {np.quantile(lgbm, .975):.3f}  (width {np.quantile(lgbm, .975) - np.quantile(lgbm, .025):.3f})")

print("\nPAIRED difference vs LightGBM (same resample for both models)")
for m in ["sklearn HistGradientBoosting", "Random forest", "XGBoost", "CatBoost", "Extra trees",
          "Small neural net (MLP)", "Logistic regression", "Gaussian Naive Bayes"]:
    d = ap_samples(m) - lgbm
    lo, hi = np.quantile(d, [.025, .975])
    verdict = "indistinguishable" if lo <= 0 <= hi else "LightGBM better"
    print(f"{m:<30} {d.mean():+.3f}   [{lo:+.3f}, {hi:+.3f}]   P(LightGBM worse) = {(d > 0).mean():.2f}   {verdict}")
