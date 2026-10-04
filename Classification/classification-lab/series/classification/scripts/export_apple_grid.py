"""Synthetic apples for part 0b and the Grid Lab widget.

Two features (redness of the skin, acidity of the juice), both on 0..1, and a label: 1 = green apple, 0 = red apple.
The data are made up on purpose: the truth is known and the overlap is controllable. They are not agricultural data.
Writes artifacts/apple_grid.json (points, logistic fit, and the grid table the article quotes) and
artifacts/apple_grid_table.csv.

    python export_apple_grid.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ART = Path(__file__).resolve().parents[1] / "artifacts"
SEED = 7
N_TRAIN = N_TEST = 400


def make(rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Green apples sit at low redness and higher acidity, red apples the other way round, with overlap."""
    y = (rng.random(n) < 0.45).astype(int)
    red = np.where(y == 1, rng.normal(0.36, 0.13, n), rng.normal(0.64, 0.13, n))
    acid = np.where(y == 1, rng.normal(0.60, 0.15, n), rng.normal(0.42, 0.15, n))
    return np.clip(np.column_stack([red, acid]), 0.001, 0.999), y


def newton_logistic(X: np.ndarray, y: np.ndarray, steps: int = 25) -> np.ndarray:
    """Plain Newton-Raphson for logistic regression, NumPy only (the same code the article prints)."""
    A = np.column_stack([np.ones(len(X)), X])
    w = np.zeros(A.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-A @ w))
        H = A.T @ (A * (p * (1 - p))[:, None])
        w = w + np.linalg.solve(H, A.T @ (y - p))
    return w


def grid_row(Xtr, ytr, Xte, yte, k: int) -> dict:
    cell = lambda X: np.minimum((X * k).astype(int), k - 1) @ np.array([k, 1])   # cell id = row * k + col
    ctr, cte = cell(Xtr), cell(Xte)
    n_cells = k * k
    count = np.bincount(ctr, minlength=n_cells)
    greens = np.bincount(ctr, weights=ytr, minlength=n_cells)
    default = int(ytr.mean() >= 0.5)                       # an empty cell predicts the overall majority class
    pred_cell = np.where(count > 0, (greens * 2 >= count).astype(int), default)
    return dict(cuts=k, cells=n_cells, empty=int((count == 0).sum()), median_per_cell=float(np.median(count)),
                train_acc=float((pred_cell[ctr] == ytr).mean()), test_acc=float((pred_cell[cte] == yte).mean()))


def main() -> None:
    rng = np.random.default_rng(SEED)
    Xtr, ytr = make(rng, N_TRAIN)
    Xte, yte = make(rng, N_TEST)
    w = newton_logistic(Xtr, ytr)
    prob = lambda X: 1 / (1 + np.exp(-(w[0] + X @ w[1:])))
    rows = [grid_row(Xtr, ytr, Xte, yte, k) for k in range(1, 13)]
    table = pd.DataFrame(rows)
    table.to_csv(ART / "apple_grid_table.csv", index=False)
    r = lambda a: np.round(a, 4).tolist()
    out = {
        "seed": SEED, "label": "1 = green apple, 0 = red apple", "features": ["redness", "acidity"],
        "train": {"x": r(Xtr[:, 0]), "y": r(Xtr[:, 1]), "label": ytr.tolist()},
        "test": {"x": r(Xte[:, 0]), "y": r(Xte[:, 1]), "label": yte.tolist()},
        "logistic": {"intercept": float(w[0]), "coef": w[1:].tolist(),
                     "train_acc": float(((prob(Xtr) >= .5) == ytr).mean()), "test_acc": float(((prob(Xte) >= .5) == yte).mean())},
    }
    (ART / "apple_grid.json").write_text(json.dumps(out), encoding="utf-8")
    print(table.round(3).to_string(index=False))
    print("logistic", out["logistic"])


if __name__ == "__main__":
    main()
