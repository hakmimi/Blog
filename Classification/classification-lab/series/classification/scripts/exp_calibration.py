"""Chapter 11: are the scores probabilities, and what does repairing them cost?

Data roles: development rows are split 75/25 into a fitting part and an inner validation part. Calibrators are
fitted with cross-validation *inside the fitting part* and wrapped around the whole preprocessing + model
pipeline, so no step ever sees a record it is later scored on. The comparison split is not used.

Ranking metrics (AP, AUC) come from the unclipped scores. Clipping to [1e-12, 1-1e-12] is applied to the copy
used for log loss only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, train_test_split

import metrics as K
import models as M
import protocol as P

MODELS = [("Logistic regression", "Logistic regression", {}),
          ("Random forest (library default)", "Random forest", {}),
          ("Random forest (min_samples_leaf=10)", "Random forest", {"m__min_samples_leaf": 10}),
          ("Gaussian Naive Bayes", "Gaussian Naive Bayes", {}),
          ("LightGBM (library default)", "LightGBM", {})]


def row(name, method, y, p, extra=None):
    r = {"model": name, "calibration": method, **K.summary(y, p),
         "distinct_scores": int(len(np.unique(p))), "ece_10_uniform": K.ece(y, p, 10, "uniform"),
         "records_at_or_above_break_even": int((p >= P.BREAK_EVEN).sum()),
         "contribution_at_break_even": K.contribution(y, p >= P.BREAK_EVEN)}
    r.update(extra or {})
    return r


def run() -> None:
    X, y = P.load()
    dev, _ = P.random_split(y)
    fit_idx, val_idx = train_test_split(dev, test_size=0.25, stratify=y[dev], random_state=P.SEED)
    yv = y[val_idx]
    specs = {s.name: s for s in M.registry(X)}
    rows, rel_rows, window_rows, check = [], [], [], []
    for name, spec_name, override in MODELS:
        spec = specs[spec_name]
        build = lambda: clone(spec.build()).set_params(**override)
        est = build().fit(X.iloc[fit_idx], y[fit_idx])
        raw = est.predict_proba(X.iloc[val_idx])[:, 1]
        rows.append(row(name, "none (raw)", yv, raw))
        rel_rows.append(K.reliability(yv, raw, 10).assign(model=name, calibration="none (raw)"))
        for method in ("sigmoid", "isotonic"):
            # (1) the pipeline itself is the calibrated estimator: preprocessing + model are refit in each fold
            cal = CalibratedClassifierCV(build(), method=method,
                                         cv=StratifiedKFold(5, shuffle=True, random_state=P.SEED)).fit(X.iloc[fit_idx], y[fit_idx])
            p = cal.predict_proba(X.iloc[val_idx])[:, 1]
            rows.append(row(name, f"{method}, 5-fold ensemble around the pipeline", yv, p))
            rel_rows.append(K.reliability(yv, p, 10).assign(model=name, calibration=f"{method} (5-fold ensemble)"))
            # (2) a monotone map fitted on a *fixed* score vector (out-of-fold scores of the fitting part)
            oof = np.zeros(len(fit_idx))
            for a, b in StratifiedKFold(5, shuffle=True, random_state=P.SEED).split(fit_idx, y[fit_idx]):
                m = build().fit(X.iloc[fit_idx[a]], y[fit_idx[a]])
                oof[b] = m.predict_proba(X.iloc[fit_idx[b]])[:, 1]
            if method == "sigmoid":
                lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit(np.clip(oof, 1e-15, 1 - 1e-15))[:, None], y[fit_idx])
                mapped = lr.predict_proba(logit(np.clip(raw, 1e-15, 1 - 1e-15))[:, None])[:, 1]
            else:
                iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(oof, y[fit_idx])
                mapped = iso.predict(raw)
            rows.append(row(name, f"{method}, map fitted on out-of-fold scores, applied to one fixed score vector", yv, mapped))
            check.append({"model": name, "map": method, "ap_raw": K.ap(yv, raw), "ap_after_map": K.ap(yv, mapped),
                          "auc_raw": K.auc_roc(yv, raw), "auc_after_map": K.auc_roc(yv, mapped),
                          "distinct_scores_raw": int(len(np.unique(raw))), "distinct_scores_after_map": int(len(np.unique(mapped))),
                          "strictly_increasing_map": bool(np.all(np.diff(mapped[np.argsort(raw)]) >= -1e-15)) and method == "sigmoid"})
        # reliability close to the decision threshold: windows around 1/8
        for lo, hi in ((0.05, 0.10), (0.10, 0.15), (0.15, 0.25)):
            m = (raw >= lo) & (raw < hi)
            k, n = int(yv[m].sum()), int(m.sum())
            ci = K.wilson(k, n)
            window_rows.append({"model": name, "score_window": f"[{lo:.2f}, {hi:.2f})", "records": n,
                                "mean_score": float(raw[m].mean()) if n else np.nan, "observed_rate": k / n if n else np.nan,
                                "rate_lo": ci[0], "rate_hi": ci[1]})
    out = pd.DataFrame(rows)
    out.to_csv(P.ART / "calibration_summary.csv", index=False, float_format="%.5f")
    pd.concat(rel_rows).to_csv(P.ART / "calibration_reliability.csv", index=False, float_format="%.5f")
    pd.DataFrame(window_rows).to_csv(P.ART / "calibration_threshold_windows.csv", index=False, float_format="%.5f")
    pd.DataFrame(check).to_csv(P.ART / "calibration_rank_checks.csv", index=False, float_format="%.5f")
    # a strictly increasing transform of a fixed vector cannot change AP or AUC: assert it on the real scores
    z = np.random.default_rng(0).normal(size=2000); yy = (np.random.default_rng(1).random(2000) < expit(z)).astype(int)
    assert K.ap(yy, z) == K.ap(yy, expit(3 * z + 1)) and K.auc_roc(yy, z) == K.auc_roc(yy, expit(3 * z + 1))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(out[["model", "calibration", "average_precision", "roc_auc", "log_loss", "brier", "ece_10_quantile",
               "distinct_scores", "mean_score", "contribution_at_break_even"]].round(4).to_string(index=False))
    print(pd.DataFrame(check).round(4).to_string(index=False))
    print(pd.DataFrame(window_rows).round(3).to_string(index=False))
    P.write_json("calibration_notes.json", {"fitting_rows": int(len(fit_idx)), "validation_rows": int(len(val_idx)),
                                            "validation_prevalence": float(yv.mean())})


if __name__ == "__main__":
    run()
