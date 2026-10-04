"""Chapter 16: train on the past, decide on the future, using only what the past contains.

The file is in date order but has no dates, so row position is a *proxy* for time. Development is the first
80% of rows. Everything that is chosen (hyperparameters, early-stopping data, threshold) is chosen inside that
prefix: hyperparameters by expanding-window folds, the contribution threshold from the validation predictions
of those same folds. The last 20% of rows (the "future") is scored once, for frozen pipelines.

Prior-odds correction variants for the future scores
  none        the model as trained
  last-window prevalence of the last validation block of the past (a lagged estimate that is feasible)
  EM          Saerens-Latinne-Decaestecker EM on the *unlabelled* future scores (feasible: needs scores, not labels)
  oracle      the future's true prevalence, a diagnostic that is not deployable
EM and prior correction both assume label shift (P(x|y) stable) and well-calibrated base probabilities.

    python exp_temporal.py
"""
from __future__ import annotations

import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import cross_val_score

import metrics as K
import models as M
import protocol as P
from exp_leaderboard import candidate_list

warnings.filterwarnings("ignore")
SKIP = {"Prior (no model)", "Linear SVM (Platt scaled)"}      # the SVM's inner calibration folds would need an ordered design


def odds(p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return p / (1 - p)


def shift_prior(p, pi_train, pi_new):
    o = odds(p) * (pi_new / (1 - pi_new)) / (pi_train / (1 - pi_train))
    return o / (1 + o)


def em_prior(p, pi_train, iters=200, tol=1e-7):
    """Saerens et al. (2002): re-estimate the class prior from unlabelled scores."""
    pi = pi_train
    for _ in range(iters):
        new = shift_prior(p, pi_train, pi).mean()
        if abs(new - pi) < tol:
            break
        pi = float(new)
    return float(pi)


def rolling_cv(folds):
    return [(tr, va) for tr, va in folds]


def run() -> None:
    X, y = P.load()
    dev, fut = P.temporal_split(len(y))
    folds = P.expanding_window_folds(len(dev))
    pi_train, pi_fut = float(y[dev].mean()), float(y[fut].mean())
    pi_last = float(y[folds[-1][1]].mean())
    cands_rows, sel_rows, fut_scores, val_scores = [], [], {}, {}
    val_idx = np.concatenate([va for _, va in folds])
    for spec in M.registry(X):
        if spec.name in SKIP:
            continue
        t0 = time.perf_counter()
        if not spec.space:
            est = spec.build().fit(X.iloc[dev], y[dev])
            fut_scores[spec.name] = est.predict_proba(X.iloc[fut])[:, 1]
            val_scores[spec.name] = np.full(len(val_idx), pi_train)
            continue
        cands = candidate_list(spec.space, P.TUNING_CANDIDATES - 1, P.SEED)
        scored = []
        for i, params in enumerate(cands):
            est = clone(spec.build()).set_params(**params)
            s = cross_val_score(est, X.iloc[dev], y[dev], scoring="average_precision", cv=rolling_cv(folds))
            scored.append(float(s.mean()))
            cands_rows.append({"model": spec.name, "candidate": i, "is_default": i == 0, "cv_ap_mean": float(s.mean()),
                               "fold_ap": json.dumps([round(float(v), 4) for v in s]),
                               "params": json.dumps(params, default=lambda o: float(o))})
        best = int(np.argmax(scored))
        chosen = clone(spec.build()).set_params(**cands[best])
        # validation predictions of the chosen configuration, one expanding-window fold at a time (past only)
        vs = np.concatenate([clone(chosen).fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[va])[:, 1] for tr, va in folds])
        val_scores[spec.name] = vs
        final = clone(chosen).fit(X.iloc[dev], y[dev])
        fut_scores[spec.name] = final.predict_proba(X.iloc[fut])[:, 1]
        sel_rows.append({"model": spec.name, "candidates": len(cands), "selected": "default" if best == 0 else f"candidate {best}",
                         "cv_ap_expanding": scored[best], "cv_ap_default": scored[0], "params": json.dumps(cands[best], default=lambda o: float(o)),
                         "seconds": time.perf_counter() - t0})
        print(f"{spec.name:32s} sel={sel_rows[-1]['selected']:<12s} cvAP={scored[best]:.3f} futureAP={K.ap(y[fut], fut_scores[spec.name]):.3f} "
              f"{time.perf_counter() - t0:.0f}s", flush=True)

    pd.DataFrame(cands_rows).to_csv(P.ART / "temporal_candidates.csv", index=False)
    pd.DataFrame(sel_rows).to_csv(P.ART / "temporal_selected.csv", index=False)
    yf, yvv = y[fut], y[val_idx]
    pd.DataFrame({"row": fut, "y": yf, **fut_scores}).to_csv(P.ART / "temporal_future_scores.csv", index=False)
    pd.DataFrame({"row": val_idx, "y": yvv, **val_scores}).to_csv(P.ART / "temporal_validation_scores.csv", index=False)

    everyone = K.contribution(yf, np.ones(len(yf), dtype=bool))
    pol = []
    for name, raw in fut_scores.items():
        if name.startswith("Prior"):
            continue
        thr_val = K.best_observed_threshold(yvv, val_scores[name])        # from past-only validation scores
        em = em_prior(raw, pi_train)
        variants = {"none": raw, "last-window prevalence": shift_prior(raw, pi_train, pi_last),
                    "EM on unlabelled scores": shift_prior(raw, pi_train, em), "oracle prevalence (diagnostic)": shift_prior(raw, pi_train, pi_fut)}
        for vname, p in variants.items():
            for pname, selected in (("break-even (1/8)", p >= P.BREAK_EVEN),
                                    ("past-only validation threshold", (raw >= thr_val) if vname == "none" else (p >= P.BREAK_EVEN))):
                if pname.startswith("past") and vname != "none":
                    continue
                prec, rec, count = K.precision_recall_at(yf, selected)
                pol.append({"model": name, "correction": vname, "policy": pname,
                            "estimated_prevalence": {"none": pi_train, "last-window prevalence": pi_last, "EM on unlabelled scores": em,
                                                     "oracle prevalence (diagnostic)": pi_fut}[vname],
                            "ap": K.ap(yf, p), "roc_auc": K.auc_roc(yf, p), "mean_score": float(p.mean()),
                            "ece_10_quantile": K.ece(yf, p), "records_selected": count, "share_selected": count / len(yf),
                            "precision": prec, "recall": rec, "contribution": K.contribution(yf, selected),
                            "call_everyone": everyone, "gain_vs_call_everyone": K.contribution(yf, selected) - everyone})
    pd.DataFrame(pol).to_csv(P.ART / "temporal_policies.csv", index=False, float_format="%.5f")

    # ---- what shifted? prevalence, covariates, and the conditional relationship
    from sklearn.ensemble import HistGradientBoostingClassifier
    domain_X = pd.concat([X.iloc[dev], X.iloc[fut]])
    domain_y = np.r_[np.zeros(len(dev)), np.ones(len(fut))]
    rng = np.random.default_rng(P.SEED)
    take = rng.permutation(len(domain_y))
    half = len(take) // 2
    prep = M.CategoryCaster().fit(domain_X)
    dm = HistGradientBoostingClassifier(categorical_features="from_dtype", random_state=P.SEED).fit(prep.transform(domain_X.iloc[take[:half]]), domain_y[take[:half]])
    dom_auc = float(roc_auc_score(domain_y[take[half:]], dm.predict_proba(prep.transform(domain_X.iloc[take[half:]]))[:, 1]))
    num = [c for c in X.columns if X[c].dtype != object]
    smd = {c: float((X.iloc[fut][c].mean() - X.iloc[dev][c].mean()) / np.sqrt((X.iloc[fut][c].var() + X.iloc[dev][c].var()) / 2)) for c in num}
    drift_cat = {}
    for c in ("contact", "month", "poutcome"):
        drift_cat[c] = pd.concat([X.iloc[dev][c].value_counts(normalize=True).rename("past"),
                                  X.iloc[fut][c].value_counts(normalize=True).rename("future")], axis=1).fillna(0).round(4).to_dict()
    # does a pure prior correction restore calibration? (label shift would say yes; a changed relationship would not)
    lgb = fut_scores["LightGBM"]; lr = fut_scores["Logistic regression"]
    cal = {m: {"ece_before": K.ece(yf, s), "ece_after_oracle_prior_correction": K.ece(yf, shift_prior(s, pi_train, pi_fut)),
               "mean_score_before": float(s.mean()), "mean_score_after": float(shift_prior(s, pi_train, pi_fut).mean())}
           for m, s in (("LightGBM", lgb), ("Logistic regression", lr))}
    rel = K.reliability(yf, shift_prior(lgb, pi_train, pi_fut), 10).assign(model="LightGBM + oracle correction")
    rel = pd.concat([rel, K.reliability(yf, lgb, 10).assign(model="LightGBM raw"),
                     K.reliability(yf, lr, 10).assign(model="Logistic regression raw")])
    rel.to_csv(P.ART / "temporal_reliability.csv", index=False, float_format="%.5f")
    P.write_json("temporal_shift.json", {"prevalence_past": pi_train, "prevalence_last_validation_block": pi_last, "prevalence_future": pi_fut,
                                          "em_estimate_by_model": {m: em_prior(s, pi_train) for m, s in fut_scores.items() if not m.startswith("Prior")},
                                          "domain_classifier_auc_past_vs_future": dom_auc, "standardised_mean_difference_numeric": smd,
                                          "category_shares": drift_cat, "calibration_effect_of_prior_correction": cal})

    # ---- hypotheses about boosters vs logistic regression, tested by ablation (same chosen configuration)
    sel = pd.DataFrame(sel_rows).set_index("model")
    abl = []
    macro = ["emp.var.rate", "cons.price.idx", "cons.conf.idx", "euribor3m", "nr.employed"]
    for name in ("Logistic regression", "LightGBM", "Random forest"):
        spec = [s for s in M.registry(X) if s.name == name][0]
        params = json.loads(sel.loc[name, "params"])
        for label, cols, rows in (("as trained", list(X.columns), dev), ("without the five macro columns", [c for c in X.columns if c not in macro], dev),
                                  ("trained on the more recent half of the past", list(X.columns), dev[len(dev) // 2:])):
            Xs = X[cols]
            est = [s for s in M.registry(Xs) if s.name == name][0].build()
            est = clone(est).set_params(**params).fit(Xs.iloc[rows], y[rows])
            p = est.predict_proba(Xs.iloc[fut])[:, 1]
            abl.append({"model": name, "variant": label, "ap": K.ap(yf, p), "roc_auc": K.auc_roc(yf, p), "mean_score": float(p.mean()),
                        "contribution_break_even": K.contribution(yf, p >= P.BREAK_EVEN), "selected": int((p >= P.BREAK_EVEN).sum())})
    pd.DataFrame(abl).to_csv(P.ART / "temporal_ablations.csv", index=False, float_format="%.5f")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(pd.DataFrame(pol)[lambda d: d.policy.str.startswith("break")].round(3).to_string(index=False))
    print(json.dumps({"prevalence_past": pi_train, "last_block": pi_last, "future": pi_fut, "call_everyone": everyone, "domain_auc": dom_auc}, indent=1))
    print(pd.DataFrame(abl).round(3).to_string(index=False))


if __name__ == "__main__":
    run()
