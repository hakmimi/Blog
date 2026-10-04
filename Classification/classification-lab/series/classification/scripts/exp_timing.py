"""Timing for the selected pipelines, measured separately and on an otherwise idle machine.

  final fit      refit on all development rows; best and median of 3 runs after one warm-up run
  batch scoring  predict_proba on all comparison records, preprocessing included; best and median of 5 runs
  single record  predict_proba on one record at a time (a one-row DataFrame), median and 95th percentile of 300 calls
  search cost    total wall-clock seconds of the candidate search, copied from the leaderboard run
Numbers describe this machine, these library versions and these thread settings (see leaderboard_environment.json).
Run it when nothing else is using the CPU. Do not read the single-record column as a production latency.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.base import clone

import models as M
import protocol as P


def run() -> None:
    X, y = P.load()
    dev, comp = P.random_split(y)
    sel = pd.read_csv(P.ART / "leaderboard_selected.csv").set_index("model")
    rows = []
    for spec in M.registry(X):
        if spec.name.startswith("Prior"):
            continue
        params = json.loads(sel.loc[spec.name, "params"])
        est = clone(spec.build()).set_params(**params)
        est.fit(X.iloc[dev], y[dev])                                        # warm-up
        fit_times = []
        for _ in range(3):
            e = clone(spec.build()).set_params(**params)
            t = time.perf_counter(); e.fit(X.iloc[dev], y[dev]); fit_times.append(time.perf_counter() - t)
        Xc = X.iloc[comp]
        est.predict_proba(Xc.iloc[:100])
        batch = []
        for _ in range(5):
            t = time.perf_counter(); est.predict_proba(Xc); batch.append(time.perf_counter() - t)
        single = []
        for i in range(300):
            one = Xc.iloc[[i]]
            t = time.perf_counter(); est.predict_proba(one); single.append(time.perf_counter() - t)
        rows.append({"model": spec.name, "family": spec.family, "fit_seconds_best": min(fit_times), "fit_seconds_median": float(np.median(fit_times)),
                     "batch_records": len(Xc), "batch_seconds_best": min(batch), "batch_records_per_second": len(Xc) / min(batch),
                     "single_record_ms_median": float(np.median(single) * 1e3), "single_record_ms_p95": float(np.quantile(single, .95) * 1e3),
                     "search_seconds_total": float(sel.loc[spec.name, "search_seconds"]),
                     "search_candidates": int(sel.loc[spec.name, "candidates_evaluated"])})
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(P.ART / "timing.csv", index=False, float_format="%.5g")
    P.write_json("timing_environment.json", {**P.environment(), "timing_note": "run on an otherwise idle machine; see module docstring"})


if __name__ == "__main__":
    run()
