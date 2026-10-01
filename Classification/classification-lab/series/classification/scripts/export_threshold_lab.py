"""Export test-set scores for a few models as compact JSON for the in-browser threshold lab."""
import json
from pathlib import Path
import pandas as pd

ART = Path(__file__).resolve().parents[1] / "artifacts"
MODELS = ["LightGBM", "XGBoost", "Random forest", "Logistic regression", "Gaussian Naive Bayes"]

pred = pd.read_csv(ART / "leaderboard_predictions.csv")
out = {"y": pred["y"].astype(int).tolist(),
       "models": {m: [round(float(p), 4) for p in pred[m]] for m in MODELS}}
(ART / "threshold_lab.json").write_text(json.dumps(out, separators=(",", ":")))
print(f"{len(pred)} rows, {len(MODELS)} models ->", (ART / "threshold_lab.json").stat().st_size // 1024, "KB")
