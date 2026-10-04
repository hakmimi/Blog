"""Chapter 14: what the frozen scores are worth under the illustrative price list.

Everything here is a retrospective policy simulation on the comparison split:
    contribution = value * (subscriptions among selected records) - cost * (selected records)
It is not an estimate of profit *caused* by contacting. Records that would have subscribed without a call
still count as wins, and the file only contains contacts the bank chose to make. The chapter explains the
extra assumptions needed to read it as incremental value.

Policies compared (all frozen before the comparison split is scored):
  break-even   select records with score >= cost/value. Sensible only when scores behave like probabilities.
  out-of-fold  threshold chosen on development out-of-fold scores to maximise simulated contribution.
  capacity k   at most k records, highest scores first, and never one below the break-even threshold.
Baselines: call nobody, call everyone, random selection at the same number of records as the policy it is
compared with, and the one-line rule "previous campaign succeeded".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import metrics as K
import protocol as P

B = 2000
CAPACITIES = [200, 500, 1000, 1500, 2500]
VALUES = [4, 8, 16]


def run() -> None:
    pred = pd.read_csv(P.ART / "leaderboard_predictions.csv")
    sel = pd.read_csv(P.ART / "leaderboard_selected.csv").set_index("model")
    X, y_all = P.load()
    pred = pred.sort_values("row").reset_index(drop=True)
    y = pred["y"].to_numpy()
    rows_idx = pred["row"].to_numpy()
    models = [c for c in pred.columns if c not in ("row", "y") and not c.startswith("Prior")]
    rng = np.random.default_rng(P.SEED)
    n = len(y)
    prior_rule = (X["poutcome"].to_numpy()[rows_idx] == "success")

    def random_mean(count: int, reps: int = 400) -> float:
        return float(np.mean([K.contribution(y, K.random_policy(n, count, rng)) for _ in range(reps)]))

    baseline = {
        "call nobody": 0.0,
        "call everyone": K.contribution(y, np.ones(n, dtype=bool)),
        "prior-success rule": K.contribution(y, prior_rule),
    }
    base_rows = [{"policy": k, "records_selected": {"call nobody": 0, "call everyone": n,
                                                   "prior-success rule": int(prior_rule.sum())}[k],
                  "contribution": v} for k, v in baseline.items()]
    pd.DataFrame(base_rows).to_csv(P.ART / "policy_baselines.csv", index=False)

    rows = []
    for m in models:
        s = pred[m].to_numpy()
        thr_oof = float(sel.loc[m, "threshold_oof"])
        for policy, selected in (("break-even (1/8)", K.threshold_policy(s, P.BREAK_EVEN)),
                                 ("out-of-fold threshold", K.threshold_policy(s, thr_oof)),
                                 ("default cut-off 0.5", K.threshold_policy(s, 0.5))):
            prec, rec, count = K.precision_recall_at(y, selected)
            c = K.contribution(y, selected)
            rows.append({"model": m, "policy": policy, "threshold": P.BREAK_EVEN if policy.startswith("break") else (0.5 if policy.startswith("default") else thr_oof),
                         "records_selected": count, "share_selected": count / n, "precision": prec, "recall": rec,
                         "contribution": c, "random_same_size": random_mean(count),
                         "gain_vs_everyone": c - baseline["call everyone"], "gain_vs_prior_rule": c - baseline["prior-success rule"]})
    pol = pd.DataFrame(rows)
    pol.to_csv(P.ART / "policy_by_model.csv", index=False, float_format="%.4f")

    # ---- capacity: a ceiling, with and without the break-even guard
    cap = []
    for m in models:
        s = pred[m].to_numpy()
        for k in CAPACITIES:
            for guard in (False, True):
                selected = K.capacity_policy(s, k, P.BREAK_EVEN if guard else None)
                prec, rec, count = K.precision_recall_at(y, selected)
                cap.append({"model": m, "capacity": k, "break_even_guard": guard, "records_selected": count,
                            "precision": prec, "recall": rec, "contribution": K.contribution(y, selected),
                            "random_same_size": random_mean(count, 100)})
    pd.DataFrame(cap).to_csv(P.ART / "policy_capacity.csv", index=False, float_format="%.4f")

    # ---- sensitivity to the value of a subscription (threshold = cost/value on the raw scores)
    sens = []
    for m in models:
        s = pred[m].to_numpy()
        for v in VALUES:
            selected = K.threshold_policy(s, P.COST_PER_CONTACT / v)
            sens.append({"model": m, "value": v, "threshold": P.COST_PER_CONTACT / v, "records_selected": int(selected.sum()),
                         "contribution": K.contribution(y, selected, value=v),
                         "call_everyone": K.contribution(y, np.ones(n, dtype=bool), value=v)})
    pd.DataFrame(sens).to_csv(P.ART / "policy_value_sensitivity.csv", index=False, float_format="%.4f")

    # ---- paired bootstrap of contribution differences against logistic regression (both frozen policies)
    ref = "Logistic regression"
    idx = rng.integers(0, n, size=(B, n))
    boot = []
    for policy in ("break-even (1/8)", "out-of-fold threshold"):
        def sel_of(m):
            thr = P.BREAK_EVEN if policy.startswith("break") else float(sel.loc[m, "threshold_oof"])
            return K.threshold_policy(pred[m].to_numpy(), thr)
        gains = {m: np.where(sel_of(m), P.VALUE_PER_SUBSCRIPTION * y - P.COST_PER_CONTACT, 0.0) for m in models}
        base = gains[ref]
        diffs = {m: (gains[m][idx] - base[idx]).sum(axis=1) for m in models if m != ref}
        obs = {m: gains[m].sum() - base.sum() for m in diffs}
        sd = {m: diffs[m].std(ddof=1) for m in diffs}
        crit = float(np.quantile(np.max([np.abs(diffs[m] - obs[m]) / sd[m] for m in diffs], axis=0), 0.95))
        for m in diffs:
            boot.append({"policy": policy, "model": m, "contribution": gains[m].sum(), "reference": ref,
                         "reference_contribution": base.sum(), "diff": obs[m],
                         "ci95_lo": float(np.quantile(diffs[m], .025)), "ci95_hi": float(np.quantile(diffs[m], .975)),
                         "simultaneous95_lo": obs[m] - crit * sd[m], "simultaneous95_hi": obs[m] + crit * sd[m]})
    pd.DataFrame(boot).to_csv(P.ART / "policy_paired_bootstrap.csv", index=False, float_format="%.3f")

    pd.set_option("display.width", 220)
    print(pd.DataFrame(base_rows).to_string(index=False))
    print(pol[pol.policy.str.startswith("break")].sort_values("contribution", ascending=False).round(3).to_string(index=False))
    spread = pol.groupby("policy").contribution.agg(["max", "min"])
    print((spread["max"] - spread["min"]).rename("max - min across the learned models"))


if __name__ == "__main__":
    run()
