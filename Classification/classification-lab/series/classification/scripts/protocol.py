"""The evaluation protocol and the data contract, in one place.

Every experiment in the series imports this module, so a chapter cannot quietly use a different split,
feature set or price list. Nothing here fits a model.

Roles of the data
-----------------
development   the first 80% of a stratified random split (seed 42). All exploration, hyperparameter search,
              early stopping, calibration and threshold selection use only this part (cross-validation inside it).
comparison    the other 20%. It is scored for frozen pipelines and frozen thresholds. It is a teaching benchmark,
              not an untouched test set: earlier drafts of this series looked at it while exploring, and the
              chapters say so. In this edition no choice is made from it.
future        the last 20% of rows in file order (a proxy for later time). Used only by the temporal chapter,
              where development is the first 80% of rows, with expanding-window folds inside it.
"""
from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "bank-additional-full.csv"
ART = ROOT / "artifacts"
FIG = ROOT / "figures"

SEED = 42
N_JOBS = 6                      # worker threads for libraries that parallelise; recorded in the manifest
TEST_SIZE = 0.20
TUNING_FOLDS = 3
TUNING_CANDIDATES = 8           # the *maximum* number of random-search candidates per model

# Illustrative price list. These are teaching assumptions, not figures from the bank.
COST_PER_CONTACT = 1.0
VALUE_PER_SUBSCRIPTION = 8.0
BREAK_EVEN = COST_PER_CONTACT / VALUE_PER_SUBSCRIPTION

# ---------------------------------------------------------------------------------------------------------
# Data contract. Descriptions paraphrase bank-additional-names.txt from the UCI archive (CC BY 4.0).
# "available" says when the value exists relative to a planned contact; "role" separates attributes of the
# customer from attributes of how the bank chooses to contact them, or of the world around them.
# ---------------------------------------------------------------------------------------------------------
FEATURES = [
    # name, group, role, available, main-set decision, note
    ("age", "profile", "customer", "before", True, ""),
    ("job", "profile", "customer", "before", True, "'unknown' is a documented missing-value label"),
    ("marital", "profile", "customer", "before", True, "'unknown' is a documented missing-value label"),
    ("education", "profile", "customer", "before", True, "'unknown' is a documented missing-value label"),
    ("default", "profile", "customer", "before", True, "'unknown' is a documented missing-value label"),
    ("housing", "profile", "customer", "before", True, "'unknown' is a documented missing-value label"),
    ("loan", "profile", "customer", "before", True, "'unknown' is a documented missing-value label"),
    ("contact", "schedule", "policy", "when scheduled", True,
     "documented as an attribute of the last contact; assumed known when the contact is planned"),
    ("month", "schedule", "policy", "when scheduled", True,
     "documented as the month of the last contact; assumed known when the contact is planned"),
    ("day_of_week", "schedule", "policy", "when scheduled", True,
     "documented as the weekday of the last contact; assumed known when the contact is planned"),
    ("duration", "call outcome", "outcome of the contact", "after", False,
     "length of the last contact; documentation says to discard it for any realistic predictive model"),
    ("campaign", "contact count", "policy", "unclear", False,
     "number of contacts in this campaign including the last one; a record is the last contact, so the count "
     "is tied to when the bank stopped calling, which can depend on the outcome. Excluded from the main set and "
     "re-added in a sensitivity run"),
    ("pdays", "history", "customer", "before", True, "999 is a code for 'not previously contacted'"),
    ("previous", "history", "customer", "before", True, "contacts before this campaign"),
    ("poutcome", "history", "customer", "before", True, "outcome of the previous campaign"),
    ("emp.var.rate", "macro", "context", "before (as published)", True, "quarterly indicator"),
    ("cons.price.idx", "macro", "context", "before (as published)", True, "monthly indicator"),
    ("cons.conf.idx", "macro", "context", "before (as published)", True, "monthly indicator"),
    ("euribor3m", "macro", "context", "before (as published)", True, "daily indicator"),
    ("nr.employed", "macro", "context", "before (as published)", True, "quarterly indicator"),
]
FEATURE_TABLE = pd.DataFrame(FEATURES, columns=["feature", "group", "role", "available", "in_main_set", "note"])

# Feature sets used in the sensitivity study (chapter 2). "main" is what every other chapter uses.
_main = [r[0] for r in FEATURES if r[4]]
FEATURE_SETS = {
    "main": _main,
    "main + campaign": _main + ["campaign"],
    "no schedule (profile, history, macro)": [r[0] for r in FEATURES if r[1] in ("profile", "history", "macro")],
    "profile + history only": [r[0] for r in FEATURES if r[1] in ("profile", "history")],
    "main + duration (not eligible; benchmark only)": _main + ["duration"],
}
MAIN = FEATURE_SETS["main"]


def load_frame() -> pd.DataFrame:
    return pd.read_csv(DATA, sep=";")


def load(feature_set: str = "main") -> tuple[pd.DataFrame, np.ndarray]:
    """Features (in file order) and the 0/1 target."""
    df = load_frame()
    y = (df["y"] == "yes").astype(int).to_numpy()
    return df[FEATURE_SETS[feature_set]].copy(), y


def random_split(y: np.ndarray, seed: int = SEED, test_size: float = TEST_SIZE):
    """Stratified random split used for the controlled within-distribution benchmark."""
    idx = np.arange(len(y))
    dev, comp = train_test_split(idx, test_size=test_size, stratify=y, random_state=seed)
    return np.sort(dev), np.sort(comp)


def tuning_cv(seed: int = SEED, n_splits: int = TUNING_FOLDS) -> StratifiedKFold:
    return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)


def temporal_split(n: int, final_fraction: float = TEST_SIZE):
    """Development prefix and the future suffix, in file order."""
    cut = int(n * (1 - final_fraction))
    return np.arange(cut), np.arange(cut, n)


def expanding_window_folds(n_dev: int, edges=(0.50, 0.665, 0.83, 1.0)):
    """Expanding-window folds inside the development prefix: train on everything before, validate on the next block."""
    cuts = [int(n_dev * e) for e in edges]
    return [(np.arange(a), np.arange(a, b)) for a, b in zip(cuts[:-1], cuts[1:])]


def describe_blocks(y: np.ndarray, blocks: list[tuple[str, np.ndarray]]) -> pd.DataFrame:
    rows = []
    for name, idx in blocks:
        rows.append({"block": name, "first_row": int(idx.min()), "last_row": int(idx.max()),
                     "records": int(len(idx)), "positives": int(y[idx].sum()),
                     "prevalence": float(y[idx].mean())})
    return pd.DataFrame(rows)


def environment() -> dict:
    """Software, hardware and settings, written next to every set of results."""
    import os
    import catboost, lightgbm, sklearn, xgboost, scipy
    return {
        "python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor(),
        "logical_cpus": os.cpu_count(), "worker_threads_used": N_JOBS,
        "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__, "xgboost": xgboost.__version__,
        "lightgbm": lightgbm.__version__, "catboost": catboost.__version__,
        "seed": SEED, "tuning_folds": TUNING_FOLDS, "max_search_candidates": TUNING_CANDIDATES,
        "cost_per_contact": COST_PER_CONTACT, "value_per_subscription": VALUE_PER_SUBSCRIPTION,
    }


def write_json(name: str, obj) -> Path:
    path = ART / name
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def build_manifest() -> dict:
    """Split manifest: who is in development, comparison, future; fold sizes; feature decisions."""
    df = load_frame()
    y = (df["y"] == "yes").astype(int).to_numpy()
    dev, comp = random_split(y)
    t_dev, t_fut = temporal_split(len(y))
    folds = expanding_window_folds(len(t_dev))
    blocks = [("development (random 80%)", dev), ("comparison (random 20%)", comp),
              ("temporal development (first 80% of rows)", t_dev), ("future (last 20% of rows)", t_fut)]
    blocks += [(f"temporal fold {i + 1}: train", tr) for i, (tr, _) in enumerate(folds)]
    blocks += [(f"temporal fold {i + 1}: validate", va) for i, (_, va) in enumerate(folds)]
    manifest = {
        "environment": environment(),
        "rows": int(len(y)), "positives": int(y.sum()), "prevalence": float(y.mean()),
        "exact_duplicate_rows": int(df.duplicated().sum()),
        "blocks": describe_blocks(y, blocks).to_dict(orient="records"),
        "random_split": {"seed": SEED, "test_size": TEST_SIZE, "stratified": True,
                         "development_rows_sha1": _sha1(dev), "comparison_rows_sha1": _sha1(comp)},
        "feature_sets": FEATURE_SETS,
        "feature_table": FEATURE_TABLE.to_dict(orient="records"),
        "price_list": {"cost_per_contact": COST_PER_CONTACT, "value_per_subscription": VALUE_PER_SUBSCRIPTION,
                       "break_even_probability": BREAK_EVEN, "status": "illustrative assumption"},
    }
    return manifest


def _sha1(a: np.ndarray) -> str:
    import hashlib
    return hashlib.sha1(np.asarray(a, dtype=np.int64).tobytes()).hexdigest()


if __name__ == "__main__":
    m = build_manifest()
    write_json("protocol_manifest.json", m)
    FEATURE_TABLE.to_csv(ART / "feature_availability.csv", index=False)
    print(pd.DataFrame(m["blocks"]).to_string(index=False))
    print({k: len(v) for k, v in FEATURE_SETS.items()})
