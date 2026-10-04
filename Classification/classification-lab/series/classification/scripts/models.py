"""The contenders: twelve predictive models plus one no-model baseline.

Each entry says how the model sees the data (its representation), its library default, and the space we
sample candidates from. Preprocessing lives inside the estimator so it is fitted on training folds only.

Early stopping is the same for the four boosting libraries: the wrapper holds out 10% of whatever training
data it receives, stops after 30 rounds without improvement in validation log loss (at most 2000 trees),
and predicts with the best round. `n_estimators` is therefore not a search dimension for boosters.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
from scipy.stats import loguniform, randint, uniform

from protocol import N_JOBS, SEED

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------------------- representations
def _split_columns(X: pd.DataFrame):
    cat = X.select_dtypes(include=["object", "category"]).columns.tolist()
    return cat, [c for c in X.columns if c not in cat]


def pdays_flag(X: pd.DataFrame) -> pd.DataFrame:
    """pdays == 999 is a code for 'not previously contacted', not a number of days.
    Replace it by a flag plus a recency that is only meaningful when the flag is set."""
    X = X.copy()
    if "pdays" in X:
        contacted = (X["pdays"] != 999)
        X["previously_contacted"] = contacted.astype(int)
        X["pdays"] = np.where(contacted, X["pdays"], 0)
    return X


def make_prep(X: pd.DataFrame, kind: str, pdays: str = "raw") -> Pipeline:
    """kind: 'linear' (one-hot + scale, sparse), 'dense' (one-hot + scale, dense), 'tree' (one-hot only)."""
    X0 = pdays_flag(X) if pdays == "flag" else X
    cat, num = _split_columns(X0)
    if kind == "tree":
        ct = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
                                ("num", "passthrough", num)])
    else:
        sparse = kind == "linear"
        ct = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=sparse), cat),
                                ("num", Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]), num)])
    steps = ([("flag", FunctionTransformer(pdays_flag))] if pdays == "flag" else []) + [("encode", ct)]
    return Pipeline(steps)


class CategoryCaster(BaseEstimator, TransformerMixin):
    """Cast string columns to pandas 'category' with the categories seen in training (for XGBoost, LightGBM, HGB)."""

    def fit(self, X, y=None):
        self.cats_ = {c: sorted(X[c].dropna().unique()) for c in X.select_dtypes(include=["object", "category"])}
        return self

    def transform(self, X):
        X = X.copy()
        for c, cats in self.cats_.items():
            X[c] = pd.Categorical(X[c], categories=cats)
        return X


class StringCaster(BaseEstimator, TransformerMixin):
    """Keep string columns as plain strings (CatBoost does its own ordered target statistics)."""

    def fit(self, X, y=None):
        self.cat_columns_ = X.select_dtypes(include=["object", "category"]).columns.tolist()
        return self

    def transform(self, X):
        X = X.copy()
        for c in self.cat_columns_:
            X[c] = X[c].astype(str)
        return X


# ---------------------------------------------------------------------------------------- boosting wrappers
class _EarlyStopped(ClassifierMixin, BaseEstimator):
    """Shared behaviour: hold out a validation slice, stop on validation log loss, remember the stopping round."""
    max_trees = 2000
    patience = 30
    val_fraction = 0.10

    def _split(self, X, y):
        return train_test_split(X, y, test_size=self.val_fraction, stratify=y, random_state=self.random_state)

    @property
    def classes_(self):
        return np.array([0, 1])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


class XGBES(_EarlyStopped):
    def __init__(self, learning_rate=0.05, max_depth=6, subsample=1.0, colsample_bytree=1.0,
                 min_child_weight=1, reg_lambda=1.0, random_state=SEED, n_jobs=N_JOBS):
        self.learning_rate, self.max_depth, self.subsample = learning_rate, max_depth, subsample
        self.colsample_bytree, self.min_child_weight, self.reg_lambda = colsample_bytree, min_child_weight, reg_lambda
        self.random_state, self.n_jobs = random_state, n_jobs

    def fit(self, X, y):
        from xgboost import XGBClassifier
        Xa, Xb, ya, yb = self._split(X, y)
        self.model_ = XGBClassifier(
            n_estimators=self.max_trees, learning_rate=self.learning_rate, max_depth=self.max_depth,
            subsample=self.subsample, colsample_bytree=self.colsample_bytree, min_child_weight=self.min_child_weight,
            reg_lambda=self.reg_lambda, tree_method="hist", enable_categorical=True, eval_metric="logloss",
            early_stopping_rounds=self.patience, random_state=self.random_state, n_jobs=self.n_jobs, verbosity=0)
        self.model_.fit(Xa, ya, eval_set=[(Xb, yb)], verbose=False)
        self.n_trees_ = int(self.model_.best_iteration) + 1
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(X, iteration_range=(0, self.n_trees_))


class LGBMES(_EarlyStopped):
    def __init__(self, learning_rate=0.1, num_leaves=31, subsample=1.0, colsample_bytree=1.0,
                 min_child_samples=20, reg_lambda=0.0, random_state=SEED, n_jobs=N_JOBS):
        self.learning_rate, self.num_leaves, self.subsample = learning_rate, num_leaves, subsample
        self.colsample_bytree, self.min_child_samples, self.reg_lambda = colsample_bytree, min_child_samples, reg_lambda
        self.random_state, self.n_jobs = random_state, n_jobs

    def fit(self, X, y):
        import lightgbm as lgb
        Xa, Xb, ya, yb = self._split(X, y)
        self.model_ = lgb.LGBMClassifier(
            n_estimators=self.max_trees, learning_rate=self.learning_rate, num_leaves=self.num_leaves,
            subsample=self.subsample, subsample_freq=1 if self.subsample < 1 else 0,
            colsample_bytree=self.colsample_bytree, min_child_samples=self.min_child_samples,
            reg_lambda=self.reg_lambda, random_state=self.random_state, n_jobs=self.n_jobs, verbose=-1)
        self.model_.fit(Xa, ya, eval_set=[(Xb, yb)], eval_metric="binary_logloss",
                        callbacks=[lgb.early_stopping(self.patience, verbose=False)])
        self.n_trees_ = int(self.model_.best_iteration_ or self.max_trees)
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(X, num_iteration=self.n_trees_)


class CatBoostES(_EarlyStopped):
    """CatBoost needs `cat_features` (column names) at fit time. Passing it to the constructor breaks
    `sklearn.clone` (it raises a RuntimeError, tested with CatBoost 1.2.x), so this wrapper finds the string
    columns itself at fit time and keeps the constructor sklearn-clean."""

    def __init__(self, learning_rate=0.08, depth=6, l2_leaf_reg=3.0, random_state=SEED, n_jobs=N_JOBS):
        self.learning_rate, self.depth, self.l2_leaf_reg = learning_rate, depth, l2_leaf_reg
        self.random_state, self.n_jobs = random_state, n_jobs

    def fit(self, X, y):
        from catboost import CatBoostClassifier
        Xa, Xb, ya, yb = self._split(X, y)
        cats = [c for c in X.columns if X[c].dtype == object or str(X[c].dtype) == "category"]
        self.model_ = CatBoostClassifier(
            iterations=self.max_trees, learning_rate=self.learning_rate, depth=self.depth,
            l2_leaf_reg=self.l2_leaf_reg, random_seed=self.random_state, thread_count=self.n_jobs,
            od_type="Iter", od_wait=self.patience, use_best_model=True, loss_function="Logloss",
            cat_features=cats, verbose=0, allow_writing_files=False)
        self.model_.fit(Xa, ya, eval_set=(Xb, yb))
        self.n_trees_ = int(self.model_.get_best_iteration()) + 1
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(X)


# ---------------------------------------------------------------------------------------- the registry
@dataclass
class Spec:
    name: str
    family: str
    representation: str
    build: Any                     # callable(X) -> estimator (sklearn-clonable)
    space: dict = field(default_factory=dict)    # scipy distributions or lists, keys are estimator params
    note: str = ""


def registry(X: pd.DataFrame, pdays: str = "raw", calib_cv=None) -> list[Spec]:
    """calib_cv: folds used inside the Platt-scaled SVM. Default is a shuffled 3-fold split; for time-ordered data pass
    an explicit list of (train, validation) index pairs that respects order."""
    from sklearn.model_selection import StratifiedKFold
    calib_cv = calib_cv if calib_cv is not None else StratifiedKFold(3, shuffle=True, random_state=SEED)
    lin = lambda: make_prep(X, "linear", pdays)
    den = lambda: make_prep(X, "dense", pdays)
    tre = lambda: make_prep(X, "tree", pdays)
    pipe = lambda prep, est: Pipeline([("prep", prep), ("m", est)])
    return [
        Spec("Prior (no model)", "baseline", "none",
             lambda: DummyClassifier(strategy="prior"), {}, "Every record gets the development prevalence."),
        Spec("Logistic regression", "linear", "one-hot + scaled",
             lambda: pipe(lin(), LogisticRegression(max_iter=5000)),
             {"m__C": loguniform(1e-3, 10)}, "L2 penalty; C is the inverse strength."),
        Spec("Linear SVM (Platt scaled)", "linear", "one-hot + scaled",
             lambda: CalibratedClassifierCV(pipe(lin(), LinearSVC(dual=False, max_iter=5000)), method="sigmoid", cv=calib_cv),
             {"estimator__m__C": loguniform(1e-3, 3)},
             "Preprocessing and SVM are both inside the calibration folds."),
        Spec("Gaussian Naive Bayes", "probabilistic", "one-hot + scaled (dense)",
             lambda: pipe(den(), GaussianNB()), {"m__var_smoothing": loguniform(1e-9, 1e-1)},
             "Gaussian densities on one-hot columns: a deliberately imperfect representation."),
        Spec("k-nearest neighbours", "instance", "one-hot + scaled (dense)",
             lambda: pipe(den(), KNeighborsClassifier(n_jobs=N_JOBS)),
             {"m__n_neighbors": randint(5, 201), "m__weights": ["uniform", "distance"]}),
        Spec("Small neural net (MLP)", "neural", "one-hot + scaled",
             lambda: pipe(lin(), MLPClassifier(hidden_layer_sizes=(64, 32), early_stopping=True, max_iter=200,
                                              random_state=SEED)),
             {"m__alpha": loguniform(1e-5, 1e-1), "m__learning_rate_init": loguniform(3e-4, 1e-2)}),
        Spec("Decision tree", "tree", "one-hot",
             lambda: pipe(tre(), DecisionTreeClassifier(random_state=SEED)),
             {"m__min_samples_leaf": randint(5, 301), "m__max_depth": [3, 5, 8, 12, None]},
             "Library default is a fully grown tree."),
        Spec("Random forest", "bagging", "one-hot",
             lambda: pipe(tre(), RandomForestClassifier(n_estimators=300, n_jobs=N_JOBS, random_state=SEED)),
             {"m__min_samples_leaf": randint(1, 41), "m__max_features": uniform(0.1, 0.5)}),
        Spec("Extra trees", "bagging", "one-hot",
             lambda: pipe(tre(), ExtraTreesClassifier(n_estimators=300, n_jobs=N_JOBS, random_state=SEED)),
             {"m__min_samples_leaf": randint(1, 41), "m__max_features": uniform(0.1, 0.5)}),
        Spec("sklearn HistGradientBoosting", "boosting", "native categories",
             lambda: pipe(CategoryCaster(), HistGradientBoostingClassifier(
                 categorical_features="from_dtype", early_stopping=True, validation_fraction=0.1,
                 n_iter_no_change=30, max_iter=2000, random_state=SEED)),
             {"m__learning_rate": loguniform(0.02, 0.3), "m__max_leaf_nodes": randint(6, 64),
              "m__l2_regularization": loguniform(1e-3, 30), "m__min_samples_leaf": randint(10, 200)}),
        Spec("XGBoost", "boosting", "native categories",
             lambda: pipe(CategoryCaster(), XGBES()),
             {"m__learning_rate": loguniform(0.02, 0.3), "m__max_depth": randint(2, 9),
              "m__subsample": uniform(0.6, 0.4), "m__colsample_bytree": uniform(0.5, 0.5),
              "m__min_child_weight": loguniform(1, 50)}),
        Spec("LightGBM", "boosting", "native categories",
             lambda: pipe(CategoryCaster(), LGBMES()),
             {"m__learning_rate": loguniform(0.02, 0.3), "m__num_leaves": randint(4, 64),
              "m__subsample": uniform(0.6, 0.4), "m__colsample_bytree": uniform(0.5, 0.5),
              "m__min_child_samples": randint(10, 200)}),
        Spec("CatBoost", "boosting", "raw strings (own target statistics)",
             lambda: pipe(StringCaster(), CatBoostES()),
             {"m__learning_rate": loguniform(0.03, 0.3), "m__depth": randint(3, 9),
              "m__l2_leaf_reg": loguniform(1, 30)}),
    ]
