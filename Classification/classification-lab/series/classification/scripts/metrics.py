"""Metrics and policies. Ranking metrics always use the original scores; clipping is only for probability losses."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (auc, average_precision_score, brier_score_loss, log_loss, precision_recall_curve,
                             roc_auc_score)

from protocol import BREAK_EVEN, COST_PER_CONTACT, VALUE_PER_SUBSCRIPTION

EPS = 1e-12


def ap(y, p) -> float:
    """Average precision as scikit-learn defines it: the step-wise sum of (R_n - R_{n-1}) * P_n. Not the trapezoid."""
    return float(average_precision_score(y, p))


def pr_auc_trapezoid(y, p) -> float:
    precision, recall, _ = precision_recall_curve(y, p)
    return float(auc(recall, precision))


def auc_roc(y, p) -> float:
    return float(roc_auc_score(y, p))


def safe_log_loss(y, p) -> float:
    """Log loss with probabilities clipped to [EPS, 1 - EPS] so a hard 0 or 1 cannot give infinity.
    The clipped copy is used for this loss only; AP and AUC are computed from the unclipped scores."""
    return float(log_loss(y, np.clip(p, EPS, 1 - EPS), labels=[0, 1]))


def brier(y, p) -> float:
    return float(brier_score_loss(y, p))


def ece(y, p, bins: int = 10, strategy: str = "quantile") -> float:
    r = reliability(y, p, bins, strategy)
    return float((r["weight"] * (r["mean_score"] - r["rate"]).abs()).sum())


def reliability(y, p, bins: int = 10, strategy: str = "quantile") -> pd.DataFrame:
    """Reliability table: mean score, observed rate, count and a Wilson 95% interval for the rate, per bin."""
    y, p = np.asarray(y), np.asarray(p)
    if strategy == "quantile":
        edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    else:
        edges = np.linspace(0, 1, bins + 1)
    edges = np.unique(edges)
    if len(edges) < 2:                       # constant scores: one bin
        edges = np.array([edges[0] - 1, edges[0] + 1])
    which = np.clip(np.digitize(p, edges[1:-1], right=False), 0, len(edges) - 2)
    rows = []
    for b in range(len(edges) - 1):
        m = which == b
        n = int(m.sum())
        if n == 0:
            continue
        k = int(y[m].sum())
        lo, hi = wilson(k, n)
        rows.append({"bin": b, "low": float(p[m].min()), "high": float(p[m].max()), "count": n,
                     "weight": n / len(y), "mean_score": float(p[m].mean()), "rate": k / n,
                     "rate_lo": lo, "rate_hi": hi})
    return pd.DataFrame(rows)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return float(c - h), float(c + h)


# ---- cost policy -----------------------------------------------------------------------------------------
def contribution(y, selected, cost: float = COST_PER_CONTACT, value: float = VALUE_PER_SUBSCRIPTION) -> float:
    """Retrospective policy simulation: value * (positives among selected records) - cost * (selected records).
    It is NOT an estimate of profit caused by contacting: some of those clients might have subscribed anyway."""
    selected = np.asarray(selected, dtype=bool)
    return float(value * np.asarray(y)[selected].sum() - cost * selected.sum())


def threshold_policy(p, threshold: float):
    return np.asarray(p) >= threshold


def capacity_policy(p, capacity: int, threshold: float | None = None):
    """Select at most `capacity` records in descending score order, and (if a threshold is given) never one below it.
    Capacity is a ceiling, not an obligation."""
    p = np.asarray(p)
    order = np.argsort(-p, kind="stable")[:capacity]
    sel = np.zeros(len(p), dtype=bool)
    sel[order] = True
    if threshold is not None:
        sel &= p >= threshold
    return sel


def random_policy(n: int, capacity: int, rng: np.random.Generator):
    sel = np.zeros(n, dtype=bool)
    sel[rng.choice(n, size=min(capacity, n), replace=False)] = True
    return sel


def best_observed_threshold(y, p, grid: int = 400) -> float:
    """The threshold that maximises simulated contribution on THESE scores. A description of a sample, not a
    population-level optimum; select it on out-of-fold development scores only."""
    p = np.asarray(p)
    qs = np.unique(np.quantile(p, np.linspace(0, 0.9975, grid)))
    vals = [contribution(y, p >= t) for t in qs]
    return float(qs[int(np.argmax(vals))])


def summary(y, p) -> dict:
    return {"average_precision": ap(y, p), "roc_auc": auc_roc(y, p), "pr_auc_trapezoid": pr_auc_trapezoid(y, p),
            "log_loss": safe_log_loss(y, p), "brier": brier(y, p), "ece_10_quantile": ece(y, p),
            "prevalence": float(np.mean(y)), "mean_score": float(np.mean(p))}


def precision_recall_at(y, selected) -> tuple[float, float, int]:
    selected = np.asarray(selected, dtype=bool)
    n = int(selected.sum())
    tp = int(np.asarray(y)[selected].sum())
    return (tp / n if n else float("nan")), tp / max(int(np.sum(y)), 1), n
