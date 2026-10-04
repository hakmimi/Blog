"""Uncertainty for the comparison-split scores of the frozen pipelines (chapter 13).

What this does and does not condition on
  * The fitted models, their hyperparameters and thresholds are fixed. The bootstrap resamples the 8,238
    comparison records, so intervals describe test-sample uncertainty only. Variation from other training
    samples, seeds and tuning is studied separately in exp_stability.py.
  * Resamples are aligned across models, so differences are paired.
  * Records are resampled independently (rows) and, as a sensitivity check, in blocks of consecutive file
    positions. The block version is a stress test for serial dependence, not a calendar-exact analysis:
    the file has no dates, only an order.
  * Intervals use enough decimals that "touches zero" can be judged. Simultaneous intervals use the
    max-t bootstrap over all comparisons against the reference, so the displayed winner is not cherry-picked.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import metrics as K
import protocol as P

B = 2000
BLOCK = 100
REFERENCE = "Logistic regression"


def load():
    pred = pd.read_csv(P.ART / "leaderboard_predictions.csv")
    sel = pd.read_csv(P.ART / "leaderboard_selected.csv")
    return pred, sel


def boot_indices(n, rng, block=None):
    if block is None:
        return rng.integers(0, n, size=(B, n))
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(B, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
    return idx


def aps(y, s, idx):
    return np.array([K.ap(y[b], s[b]) for b in idx])


def run() -> None:
    pred, sel = load()
    models = [c for c in pred.columns if c not in ("row", "y") and not c.startswith("Prior")]
    order = np.argsort(pred["row"].to_numpy())           # file order within the comparison split
    pred = pred.iloc[order].reset_index(drop=True)
    y = pred["y"].to_numpy()
    rng = np.random.default_rng(P.SEED)
    out = {}
    for label, block in (("rows", None), (f"blocks of {BLOCK}", BLOCK)):
        idx = boot_indices(len(y), rng, block)
        base = {m: aps(y, pred[m].to_numpy(), idx) for m in models}
        point = {m: K.ap(y, pred[m].to_numpy()) for m in models}
        out[label] = (idx, base, point)

    top = max(models, key=lambda m: out["rows"][2][m])
    rows = []
    for label, (idx, base, point) in out.items():
        for ref in (REFERENCE, top):
            diffs = {m: base[m] - base[ref] for m in models if m != ref}
            obs = {m: point[m] - point[ref] for m in diffs}
            sd = {m: diffs[m].std(ddof=1) for m in diffs}
            # max-t over all comparisons: simultaneous (family-wise) interval half-widths
            t = np.max([np.abs(diffs[m] - obs[m]) / sd[m] for m in diffs], axis=0)
            crit = float(np.quantile(t, 0.95))
            for m in diffs:
                d = diffs[m]
                rows.append({"resampling": label, "reference": ref, "model": m, "ap": point[m], "ap_reference": point[ref],
                             "diff": obs[m], "ci95_lo": float(np.quantile(d, .025)), "ci95_hi": float(np.quantile(d, .975)),
                             "simultaneous95_lo": obs[m] - crit * sd[m], "simultaneous95_hi": obs[m] + crit * sd[m],
                             "share_resamples_above_zero": float((d > 0).mean())})
    table = pd.DataFrame(rows)
    table.to_csv(P.ART / "uncertainty_paired_ap.csv", index=False, float_format="%.5f")

    idx, base, point = out["rows"]
    single = pd.DataFrame({"model": models, "ap": [point[m] for m in models],
                           "ap_lo": [np.quantile(base[m], .025) for m in models],
                           "ap_hi": [np.quantile(base[m], .975) for m in models]})
    single["width"] = single.ap_hi - single.ap_lo
    single.to_csv(P.ART / "uncertainty_single_ap.csv", index=False, float_format="%.5f")
    print("reference for 'top':", top)
    print(single.sort_values("ap", ascending=False).round(4).to_string(index=False))
    pd.set_option("display.width", 200)
    print(table[(table.resampling == "rows") & (table.reference == REFERENCE)].round(4).to_string(index=False))


if __name__ == "__main__":
    run()
