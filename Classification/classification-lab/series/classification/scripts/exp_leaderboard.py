"""Chapter 10-14 backbone: tune on development data only, freeze, then score the comparison split once.

Protocol (see protocol.py):
  1. Candidates per model: the library default plus up to 7 distinct random draws from its search space.
     The default is a real candidate, not a discarded baseline.
  2. Every candidate is scored by 3-fold stratified (shuffled) cross-validation on the development rows,
     with average precision. The best mean wins. Ties go to the earlier (simpler: default first) candidate.
  3. The chosen configuration is refit on all development rows, out-of-fold development scores pick the
     contribution-maximising threshold, and the comparison split is scored for the frozen pipeline.
  4. The default configuration is also scored on the comparison split, so tuning gain can be read directly.

    python exp_leaderboard.py [model name ...]
"""
from __future__ import annotations

import json
import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import ParameterSampler, cross_val_predict, cross_val_score

import metrics as K
import models as M
import protocol as P

warnings.filterwarnings("ignore")


def candidate_list(space: dict, n_random: int, seed: int) -> list[dict]:
    """Default first, then distinct random draws. A finite space yields fewer than n_random if it is exhausted."""
    out, seen = [{}], {json.dumps({}, sort_keys=True)}
    if not space:
        return out
    sampler = ParameterSampler(space, n_iter=n_random * 4, random_state=seed)
    for params in sampler:
        key = json.dumps({k: (round(v, 10) if isinstance(v, float) else v) for k, v in params.items()},
                         sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        out.append(params)
        if len(out) == n_random + 1:
            break
    return out


def run(only: list[str] | None = None) -> None:
    X, y = P.load()
    dev, comp = P.random_split(y)
    cv = P.tuning_cv()
    cand_rows, sel_rows, pred_cols, oof_cols = [], [], {}, {}
    comp_default = {}
    for spec in M.registry(X):
        if only and spec.name not in only:
            continue
        t_search = time.perf_counter()
        if not spec.space:
            est = spec.build()
            est.fit(X.iloc[dev], y[dev])
            p = est.predict_proba(X.iloc[comp])[:, 1]
            pred_cols[spec.name], comp_default[spec.name] = p, p
            oof_cols[spec.name] = np.full(len(dev), y[dev].mean())
            sel_rows.append({"model": spec.name, "family": spec.family, "representation": spec.representation,
                             "candidates_evaluated": 0, "selected": "none (no parameters)", "params": "{}",
                             "cv_ap": np.nan, "cv_ap_default": np.nan, "search_seconds": 0.0,
                             "threshold_oof": 1.0, **{f"cmp_{k}": v for k, v in K.summary(y[comp], p).items()}})
            continue
        cands = candidate_list(spec.space, P.TUNING_CANDIDATES - 1, P.SEED)
        scored = []
        for i, params in enumerate(cands):
            t0 = time.perf_counter()
            est = clone(spec.build()).set_params(**params)
            scores = cross_val_score(est, X.iloc[dev], y[dev], scoring="average_precision", cv=cv, n_jobs=1)
            scored.append(float(scores.mean()))
            cand_rows.append({"model": spec.name, "candidate": i, "is_default": i == 0,
                              "params": json.dumps(params, default=lambda o: float(o)), "cv_ap_mean": float(scores.mean()),
                              "cv_ap_std": float(scores.std(ddof=1)), "seconds": time.perf_counter() - t0})
        best = int(np.argmax(scored))                       # argmax returns the first maximum: default wins ties
        search_s = time.perf_counter() - t_search
        chosen = clone(spec.build()).set_params(**cands[best])
        default = clone(spec.build())
        chosen.fit(X.iloc[dev], y[dev])
        default.fit(X.iloc[dev], y[dev])
        p = chosen.predict_proba(X.iloc[comp])[:, 1]
        p0 = default.predict_proba(X.iloc[comp])[:, 1]
        oof = cross_val_predict(clone(spec.build()).set_params(**cands[best]), X.iloc[dev], y[dev], cv=cv,
                                method="predict_proba", n_jobs=1)[:, 1]
        thr = K.best_observed_threshold(y[dev], oof)
        pred_cols[spec.name], comp_default[spec.name], oof_cols[spec.name] = p, p0, oof
        sel_rows.append({"model": spec.name, "family": spec.family, "representation": spec.representation,
                         "candidates_evaluated": len(cands), "selected": "default" if best == 0 else f"candidate {best}",
                         "params": json.dumps(cands[best], default=lambda o: float(o)),
                         "cv_ap": scored[best], "cv_ap_default": scored[0], "search_seconds": search_s,
                         "threshold_oof": thr, "n_trees": getattr(getattr(chosen, "steps", [[None, None]])[-1][1], "n_trees_", np.nan),
                         **{f"cmp_{k}": v for k, v in K.summary(y[comp], p).items()},
                         "cmp_ap_default": K.ap(y[comp], p0)})
        print(f"{spec.name:32s} cands={len(cands)} sel={sel_rows[-1]['selected']:<12s} cvAP={scored[best]:.3f} "
              f"cmpAP={sel_rows[-1]['cmp_average_precision']:.3f} (default {sel_rows[-1]['cmp_ap_default']:.3f}) "
              f"search={search_s:.0f}s", flush=True)

    outputs = {
        "leaderboard_candidates.csv": (pd.DataFrame(cand_rows), "model"),
        "leaderboard_selected.csv": (pd.DataFrame(sel_rows), "model"),
    }
    wide = {
        "leaderboard_predictions.csv": ({"row": comp, "y": y[comp], **pred_cols}, comp),
        "leaderboard_predictions_default.csv": ({"row": comp, "y": y[comp], **comp_default}, comp),
        "leaderboard_oof.csv": ({"row": dev, "y": y[dev], **oof_cols}, dev),
    }
    for name, (df, key) in outputs.items():
        path = P.ART / name
        if only and path.exists():                       # re-run of a few models: replace just their rows
            old = pd.read_csv(path)
            df = pd.concat([old[~old[key].isin(df[key].unique())], df], ignore_index=True)
        df.to_csv(path, index=False)
    for name, (cols, _) in wide.items():
        path = P.ART / name
        df = pd.DataFrame(cols)
        if only and path.exists():
            old = pd.read_csv(path)
            for c in df.columns:
                old[c] = df[c].to_numpy()
            df = old
        df.to_csv(path, index=False)
    P.write_json("leaderboard_environment.json", P.environment())


if __name__ == "__main__":
    run(sys.argv[1:] or None)
