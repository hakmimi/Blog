"""Chapter 13, part C: how much does a model's score move when the whole procedure is repeated?

For each of five other random 80/20 splits (seeds 100-104) every model is *re-tuned from scratch* on that split's
development part (the same default + 7 random candidates protocol), refit, and scored on that split's comparison
part. Hyperparameters chosen on one split are never reused on another, so the comparison part of each split took
no part in choosing anything for that split.

What varies between rows of the output: the training sample, the comparison sample, and the random draws of the
search. The bootstrap in exp_uncertainty.py varies only the comparison sample for one frozen fit.

    python exp_stability.py [seed ...]
"""
from __future__ import annotations

import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import cross_val_score

import metrics as K
import models as M
import protocol as P
from exp_leaderboard import candidate_list

warnings.filterwarnings("ignore")
SEEDS = [100, 101, 102, 103, 104]


def run(seeds: list[int]) -> None:
    X, y = P.load()
    path = P.ART / "stability_runs.csv"
    done = pd.read_csv(path) if path.exists() else pd.DataFrame()
    rows = done.to_dict("records") if len(done) else []
    for seed in seeds:
        dev, comp = P.random_split(y, seed=seed)
        cv = P.tuning_cv(seed=seed)
        for spec in M.registry(X):
            if any(r["seed"] == seed and r["model"] == spec.name for r in rows):
                continue
            t0 = time.perf_counter()
            if not spec.space:
                est = spec.build().fit(X.iloc[dev], y[dev]); p = est.predict_proba(X.iloc[comp])[:, 1]
                rows.append({"seed": seed, "model": spec.name, "selected": "none", "candidates": 0, "ap": K.ap(y[comp], p),
                             "ap_default": K.ap(y[comp], p), "roc_auc": K.auc_roc(y[comp], p), "prevalence": float(y[comp].mean())})
                continue
            cands = candidate_list(spec.space, P.TUNING_CANDIDATES - 1, seed)
            scores = [cross_val_score(clone(spec.build()).set_params(**c), X.iloc[dev], y[dev], scoring="average_precision",
                                      cv=cv, n_jobs=1).mean() for c in cands]
            best = int(np.argmax(scores))
            chosen = clone(spec.build()).set_params(**cands[best]).fit(X.iloc[dev], y[dev])
            default = clone(spec.build()).fit(X.iloc[dev], y[dev])
            p, p0 = chosen.predict_proba(X.iloc[comp])[:, 1], default.predict_proba(X.iloc[comp])[:, 1]
            rows.append({"seed": seed, "model": spec.name, "selected": "default" if best == 0 else f"candidate {best}",
                         "candidates": len(cands), "cv_ap": scores[best], "ap": K.ap(y[comp], p), "ap_default": K.ap(y[comp], p0),
                         "roc_auc": K.auc_roc(y[comp], p), "prevalence": float(y[comp].mean()), "seconds": time.perf_counter() - t0})
            print(seed, spec.name, round(rows[-1]["ap"], 3), rows[-1]["selected"], f"{time.perf_counter() - t0:.0f}s", flush=True)
            pd.DataFrame(rows).to_csv(path, index=False)
    pd.DataFrame(rows).to_csv(path, index=False)


if __name__ == "__main__":
    run([int(a) for a in sys.argv[1:]] or SEEDS)
