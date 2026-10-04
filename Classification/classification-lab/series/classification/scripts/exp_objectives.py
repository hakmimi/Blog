"""Chapter 4: what a loss does, with solutions that have actually converged.

Everything is fitted on 80% of the development rows and scored on the other 20% (an inner validation split);
the comparison split is not used. The design matrix is the full one-hot encoding plus scaled numerics and an
intercept, as in the hand-written version in the chapter, so the rank deficiency of full one-hot encoding is
part of the problem and is measured, not ignored.

Part A  the 0.201 discrepancy: hand-written gradient descent vs scikit-learn with no penalty.
Part B  one controlled comparison of objectives, each fitted to a small gradient tolerance with the same weak
        L2 penalty so every problem has a unique answer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

import metrics as K
import models as M
import protocol as P

LAMBDA = 1e-3        # weak L2 on non-intercept weights, applied to every objective in part B
sigmoid = lambda z: 1 / (1 + np.exp(-np.clip(z, -35, 35)))


def design():
    X, y = P.load()
    dev, _ = P.random_split(y)
    tr, va = train_test_split(dev, test_size=0.2, stratify=y[dev], random_state=P.SEED)
    prep = M.make_prep(X, "dense")
    A = prep.fit_transform(X.iloc[tr])
    B = prep.transform(X.iloc[va])
    names = list(prep.named_steps["encode"].get_feature_names_out())
    A, B = np.c_[np.ones(len(tr)), A], np.c_[np.ones(len(va)), B]
    return A, y[tr], B, y[va], names


# ----------------------------------------------------------------------------------------- losses (per record)
def make_objective(kind: str, A, yy, lam=LAMBDA, pos_weight=1.0, gamma=2.0):
    n = len(yy)
    sgn = 2 * yy - 1
    w = np.where(yy == 1, pos_weight, 1.0)

    def f(wv):
        z = A @ wv
        p = sigmoid(z)
        if kind in ("log", "weighted log"):
            per = np.logaddexp(0, -sgn * z)
            dz = (p - yy)
        elif kind == "brier (on sigmoid)":
            per = (p - yy) ** 2
            dz = 2 * (p - yy) * p * (1 - p)
        elif kind == "squared hinge":
            m = np.maximum(0, 1 - sgn * z)
            per, dz = m ** 2, -2 * sgn * m
        elif kind == "exponential":
            per = np.exp(np.clip(-sgn * z, -50, 50))
            dz = -sgn * per
        elif kind == "focal":
            pt = np.where(yy == 1, p, 1 - p)
            pt = np.clip(pt, 1e-12, 1)
            per = -((1 - pt) ** gamma) * np.log(pt)
            dldpt = gamma * (1 - pt) ** (gamma - 1) * np.log(pt) - (1 - pt) ** gamma / pt
            dz = dldpt * pt * (1 - pt) * np.where(yy == 1, 1, -1)
        else:
            raise ValueError(kind)
        value = (w * per).sum() / w.sum() + 0.5 * lam * (wv[1:] ** 2).sum()
        grad = A.T @ (w * dz) / w.sum()
        grad[1:] += lam * wv[1:]
        return value, grad

    return f


def fit(kind, A, yy, x0=None, **kw):
    f = make_objective(kind, A, yy, **kw)
    x0 = np.zeros(A.shape[1]) if x0 is None else x0
    res = minimize(f, x0, jac=True, method="L-BFGS-B", options={"maxiter": 5000, "maxfun": 20000, "ftol": 1e-14, "gtol": 1e-9})
    val, g = f(res.x)
    return res.x, {"objective": float(val), "grad_inf_norm": float(np.abs(g).max()), "iterations": int(res.nit),
                   "converged": bool(res.success)}


def gd(A, yy, steps, lr):
    """The hand-written version from the chapter: plain gradient descent on mean log loss from zero, no penalty."""
    w = np.zeros(A.shape[1])
    f = make_objective("log", A, yy, lam=0.0)
    for _ in range(steps):
        w -= lr * f(w)[1]
    return w


# ----------------------------------------------------------------------------------------------------- part A
def part_a(A, ytr, B, yva, names):
    rank = np.linalg.matrix_rank(A)
    f0 = make_objective("log", A, ytr, lam=0.0)
    rows = []
    ref = LogisticRegression(penalty=None, max_iter=20000, tol=1e-10).fit(A[:, 1:], ytr)
    w_ref = np.r_[ref.intercept_, ref.coef_[0]]
    p_ref = sigmoid(B @ w_ref)
    for label, steps in (("gradient descent, 1,500 steps (the chapter's version)", 1500),
                         ("gradient descent, 20,000 steps", 20000)):
        w = gd(A, ytr, steps, 0.5)
        p = sigmoid(B @ w)
        rows.append(_cmp(label, w, p, p_ref, f0, A, ytr, yva))
    w_l, info = fit("log", A, ytr, lam=0.0)
    rows.append(_cmp("L-BFGS on our own objective, no penalty", w_l, sigmoid(B @ w_l), p_ref, f0, A, ytr, yva))
    rows.append(_cmp("scikit-learn, penalty=None, tol 1e-10 (reference)", w_ref, p_ref, p_ref, f0, A, ytr, yva))
    # the same problem with a unique answer: drop one level per categorical (full-rank design) and a tiny ridge
    keep = [0] + [j + 1 for j, nme in enumerate(names) if not _is_reference_level(nme, names)]
    A2, B2 = A[:, keep], B[:, keep]
    ref2 = LogisticRegression(penalty=None, max_iter=20000, tol=1e-10).fit(A2[:, 1:], ytr)
    w2 = np.r_[ref2.intercept_, ref2.coef_[0]]
    f2 = make_objective("log", A2, ytr, lam=0.0)
    wl2, _ = fit("log", A2, ytr, lam=0.0)
    p2 = sigmoid(B2 @ w2)
    rows.append(_cmp("full-rank design (one level dropped per variable): L-BFGS vs scikit-learn",
                     wl2, sigmoid(B2 @ wl2), p2, f2, A2, ytr, yva))
    # which records carry the largest disagreement, and which coefficients are large
    w_gd = gd(A, ytr, 1500, 0.5)
    d = np.abs(sigmoid(B @ w_gd) - p_ref)
    worst = np.argsort(-d)[:5]
    detail = []
    for r in worst:
        active = [names[j - 1] for j in np.flatnonzero(B[r, 1:] != 0) if names[j].startswith("encode__cat") or True][:0]
        detail.append({"record": int(r), "abs_prob_diff": float(d[r]), "p_gd": float(sigmoid(B[r] @ w_gd)),
                       "p_reference": float(p_ref[r])})
    big = pd.DataFrame({"feature": names, "gd_1500": w_gd[1:], "reference": w_ref[1:]})
    big["abs_ref"] = big.reference.abs()
    return pd.DataFrame(rows), pd.DataFrame(detail), big.sort_values("abs_ref", ascending=False).head(12), {
        "design_columns": int(A.shape[1]), "design_rank": int(rank), "rank_deficiency": int(A.shape[1] - rank)}


def _is_reference_level(name: str, names: list[str]) -> bool:
    """Drop the first level of each one-hot variable (alphabetical), keep numeric columns."""
    if not name.startswith("cat__"):
        return False
    var = name.split("__")[1].rsplit("_", 1)[0]
    group = [n for n in names if n.startswith(f"cat__{var}_")]
    return name == sorted(group)[0]


def _cmp(label, w, p, p_ref, f0, A, ytr, yva):
    val, g = f0(w)
    return {"fit": label, "train_mean_log_loss": float(val), "grad_inf_norm": float(np.abs(g).max()),
            "max_abs_prob_diff_vs_reference": float(np.abs(p - p_ref).max()),
            "mean_abs_prob_diff": float(np.abs(p - p_ref).mean()),
            "spearman_with_reference": float(spearmanr(p, p_ref)[0]),
            "pearson_with_reference": float(np.corrcoef(p, p_ref)[0, 1]),
            "validation_ap": K.ap(yva, p), "validation_log_loss": K.safe_log_loss(yva, p)}


# ----------------------------------------------------------------------------------------------------- part B
def part_b(A, ytr, B, yva):
    pos_w = (ytr == 0).sum() / (ytr == 1).sum()
    fits = {}
    for kind, kw in (("log", {}), ("weighted log", {"pos_weight": pos_w}), ("brier (on sigmoid)", {}),
                     ("squared hinge", {}), ("exponential", {}), ("focal", {"gamma": 2.0})):
        w, info = fit(kind, A, ytr, **kw)
        fits[kind] = (w, info)
    # brier is not convex on a sigmoid: also start from the log-loss solution and keep the better objective
    w_b, info_b = fit("brier (on sigmoid)", A, ytr, x0=fits["log"][0])
    if info_b["objective"] < fits["brier (on sigmoid)"][1]["objective"] - 1e-12:
        fits["brier (on sigmoid)"] = (w_b, info_b)
    base_scores = B @ fits["log"][0]
    rows = []
    for kind, (w, info) in fits.items():
        z = B @ w
        # squared hinge and exponential produce margins, not probabilities: map by a one-parameter sigmoid fitted on train
        if kind in ("squared hinge", "exponential"):
            zt = A @ w
            lr = LogisticRegression(C=1e6, max_iter=1000).fit(zt[:, None], ytr)
            p = lr.predict_proba(z[:, None])[:, 1]
            out = "margin score (Platt-scaled for the probability columns)"
        else:
            p = sigmoid(z)
            out = "probability" if kind != "weighted log" else "probability under re-weighted classes"
        top = np.argsort(-z)[: len(z) // 10]
        top0 = set(np.argsort(-base_scores)[: len(z) // 10])
        rows.append({"loss": kind, "output": out, **info, "validation_ap": K.ap(yva, z), "validation_auc": K.auc_roc(yva, z),
                     "spearman_with_log_loss_scores": float(spearmanr(z, base_scores)[0]),
                     "top10pct_overlap_with_log_loss": len(set(top) & top0) / len(top),
                     "mean_probability": float(p.mean()), "log_loss_of_probabilities": K.safe_log_loss(yva, p),
                     "brier_of_probabilities": K.brier(yva, p), "ece": K.ece(yva, p),
                     "records_flagged_at_0.5": int((p >= 0.5).sum()),
                     "records_flagged_at_break_even": int((p >= P.BREAK_EVEN).sum()),
                     "contribution_at_break_even": K.contribution(yva, p >= P.BREAK_EVEN)})
    # weighting vs shifting the intercept: is the weighted solution the log-loss solution plus log(weight)?
    w_log, w_wt = fits["log"][0], fits["weighted log"][0]
    shifted = w_log.copy(); shifted[0] += np.log(pos_w)
    p_shift, p_wt = sigmoid(B @ shifted), sigmoid(B @ w_wt)
    shift = {"weight": float(pos_w), "max_abs_prob_diff_weighted_vs_shifted_intercept": float(np.abs(p_shift - p_wt).max()),
             "spearman_weighted_vs_log": float(spearmanr(B @ w_wt, B @ w_log)[0])}
    return pd.DataFrame(rows), shift


def main() -> None:
    A, ytr, B, yva, names = design()
    a, worst, big, info = part_a(A, ytr, B, yva, names)
    b, shift = part_b(A, ytr, B, yva)
    a.to_csv(P.ART / "objectives_discrepancy.csv", index=False, float_format="%.6g")
    worst.to_csv(P.ART / "objectives_discrepancy_worst_records.csv", index=False, float_format="%.5f")
    big.to_csv(P.ART / "objectives_discrepancy_coefficients.csv", index=False, float_format="%.4f")
    b.to_csv(P.ART / "objectives_comparison.csv", index=False, float_format="%.5g")
    P.write_json("objectives_notes.json", {**info, "weight_vs_intercept_shift": shift, "lambda_part_b": LAMBDA,
                                           "train_rows": int(len(ytr)), "validation_rows": int(len(yva)), "validation_prevalence": float(yva.mean())})
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(info); print(a.round(5).to_string(index=False)); print(worst.round(4)); print(big.round(3).to_string(index=False))
    print(b.round(4).T.to_string()); print(shift)


if __name__ == "__main__":
    main()
