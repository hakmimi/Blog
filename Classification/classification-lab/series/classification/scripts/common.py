"""Shared loading, splitting and preprocessing for the head-to-head chapters.

Every model in the leaderboard sees exactly the same rows, the same features
and the same folds. Only the *encoding* differs, because that is part of what
each algorithm family needs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "bank-additional-full.csv"
ART = ROOT / "artifacts"
FIG = ROOT / "figures"
SEED = 42
COLORS = {"navy": "#17324d", "blue": "#2a6fbb", "teal": "#168c84",
          "gold": "#e1a72f", "coral": "#d95f59", "gray": "#75808a", "violet": "#7b5ea7"}

# Business assumptions used for the cost chapter. They are assumptions, not data.
COST_PER_CALL = 1.0
VALUE_PER_SUBSCRIPTION = 8.0


def load_bank() -> tuple[pd.DataFrame, np.ndarray]:
    """Return features (without `duration`) and a 0/1 target."""
    df = pd.read_csv(DATA, sep=";")
    y = (df.pop("y") == "yes").astype(int).to_numpy()
    # `duration` is only known after the call ends, so it cannot be used to
    # decide whether to place the call. See chapter 2.
    df = df.drop(columns="duration")
    return df, y


def split(seed: int = SEED, test_size: float = 0.2):
    """Stratified 80/20 split. Returns index arrays so any encoding can be sliced."""
    X, y = load_bank()
    idx = np.arange(len(X))
    train, test = train_test_split(idx, test_size=test_size, stratify=y, random_state=seed)
    return X, y, train, test


def cv(n_splits: int = 3, seed: int = SEED) -> StratifiedKFold:
    return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)


def column_types(X: pd.DataFrame) -> tuple[list[str], list[str]]:
    cat = X.select_dtypes(include="object").columns.tolist()
    num = [c for c in X.columns if c not in cat]
    return cat, num


def views(X: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Three encodings of the same table.

    raw      - strings, for CatBoost (it does its own ordered target encoding)
    category - pandas `category` dtype, for LightGBM / XGBoost native splits
    (one-hot and scaling live inside sklearn pipelines so they are fit per fold)
    """
    cat, _ = column_types(X)
    as_cat = X.copy()
    for c in cat:
        as_cat[c] = pd.Categorical(as_cat[c], categories=sorted(X[c].unique()))
    return {"raw": X, "category": as_cat, "onehot": X}


def linear_prep(X: pd.DataFrame, sparse: bool = True) -> ColumnTransformer:
    """One-hot + standardise. Fit inside a Pipeline so it only ever sees train folds."""
    cat, num = column_types(X)
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=sparse), cat),
        ("num", Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]), num),
    ])


def tree_prep(X: pd.DataFrame) -> ColumnTransformer:
    """One-hot only: trees do not care about feature scale."""
    cat, num = column_types(X)
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
        ("num", "passthrough", num),
    ])


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    which = np.digitize(p, edges[1:-1])
    ece = 0.0
    for b in range(bins):
        m = which == b
        if m.any():
            ece += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(ece)


def profit(y: np.ndarray, p: np.ndarray, threshold: float) -> float:
    call = p >= threshold
    return float(VALUE_PER_SUBSCRIPTION * y[call].sum() - COST_PER_CALL * call.sum())


def best_profit_threshold(y: np.ndarray, p: np.ndarray) -> float:
    grid = np.unique(np.quantile(p, np.linspace(0.0, 0.995, 200)))
    return float(grid[int(np.argmax([profit(y, p, t) for t in grid]))])


class CatBoostSK:
    """Thin sklearn-compatible wrapper so CatBoost can be cloned / tuned / cross-validated.

    CatBoost's own estimator refuses sklearn.clone() when `cat_features` is set, so we
    detect string columns at fit time instead.
    """
    _est_type = "classifier"

    def __init__(self, iterations=400, learning_rate=0.06, depth=6, l2_leaf_reg=3, random_seed=SEED, verbose=0):
        self.iterations, self.learning_rate, self.depth = iterations, learning_rate, depth
        self.l2_leaf_reg, self.random_seed, self.verbose = l2_leaf_reg, random_seed, verbose

    def get_params(self, deep=True):
        return dict(iterations=self.iterations, learning_rate=self.learning_rate, depth=self.depth,
                    l2_leaf_reg=self.l2_leaf_reg, random_seed=self.random_seed, verbose=self.verbose)

    def set_params(self, **params):
        for k, v in params.items():
            setattr(self, k, v)
        return self

    def fit(self, X, y):
        from catboost import CatBoostClassifier
        cats = [c for c in X.columns if X[c].dtype == object]
        self.model_ = CatBoostClassifier(cat_features=cats, thread_count=-1, **self.get_params())
        self.model_.fit(X, y)
        self.classes_ = self.model_.classes_
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(X)

    def predict(self, X):
        return self.model_.predict(X).ravel()

    def __sklearn_tags__(self):
        from sklearn.utils import Tags, ClassifierTags, TargetTags, InputTags
        return Tags(estimator_type="classifier", target_tags=TargetTags(required=True),
                    classifier_tags=ClassifierTags(), input_tags=InputTags())
