import numpy as np
import pandas as pd

COST, VALUE = 1.0, 8.0
pred = pd.read_csv("../../artifacts/leaderboard_predictions.csv")
board = pd.read_csv("../../artifacts/leaderboard.csv").set_index("model")
y = pred["y"].to_numpy()
models = [m for m in board.sort_values("average_precision", ascending=False).index if not m.startswith("Prior")]

def profit(p, t, value=VALUE):
    call = p >= t
    return value * y[call].sum() - COST * call.sum()

# 1. three policies for the same scores ---------------------------------------------------------
print(f"{'model':<30}{'t=0.5':>8}{'t=1/8':>8}{'t=OOF':>8}   {'calls':>6}{'hit rate':>9}")
for m in models:
    p = pred[m].to_numpy(); t = board.loc[m, "profit_threshold"]; call = p >= t
    print(f"{m:<30}{profit(p, .5):8.0f}{profit(p, 1 / VALUE):8.0f}{profit(p, t):8.0f}   {call.sum():6d}{y[call].mean():9.2f}")
print("call everyone:", profit(np.ones(len(y)), .5))

# 2. capacity view: you can only call the top k -------------------------------------------------
print("\nprofit if the call centre can phone only the top k customers")
print(f"{'k':>6}" + "".join(f"{m[:12]:>14}" for m in ["LightGBM", "XGBoost", "Logistic regression", "Gaussian Naive Bayes"]))
for k in (200, 500, 1000, 1500, 2500):
    row = f"{k:>6}"
    for m in ["LightGBM", "XGBoost", "Logistic regression", "Gaussian Naive Bayes"]:
        top = np.argsort(-pred[m].to_numpy())[:k]
        row += f"{VALUE * y[top].sum() - COST * k:14.0f}"
    print(row)

# 3. how sure are we that the profit ranking is real? paired bootstrap of PROFIT ---------------------
rng = np.random.default_rng(1)
boots = rng.integers(0, len(y), size=(1000, len(y)))
def boot_profit(m):
    p = pred[m].to_numpy(); t = board.loc[m, "profit_threshold"]
    gain = np.where(p >= t, VALUE * y - COST, 0.0)                   # profit contribution of each customer
    return gain[boots].sum(axis=1)
ref = boot_profit("XGBoost")
print("\nprofit difference vs XGBoost, paired bootstrap")
for m in ["LightGBM", "Random forest", "CatBoost", "Logistic regression", "Gaussian Naive Bayes"]:
    d = boot_profit(m) - ref; lo, hi = np.quantile(d, [.025, .975])
    print(f"{m:<26}{d.mean():+8.0f}   [{lo:+6.0f}, {hi:+6.0f}]")

# 4. what if the economics change? (value of a subscription) ------------------------------------------
print("\nprofit when a subscription is worth 4 / 8 / 16 (threshold = 1/value, applied to raw probabilities)")
for m in ["LightGBM", "Logistic regression", "Gaussian Naive Bayes"]:
    p = pred[m].to_numpy()
    print(f"{m:<24}" + "".join(f"  value={v:>2}: {profit(p, 1 / v, v):7.0f} ({(p >= 1 / v).sum():5d} calls)" for v in (4, 8, 16)))
