"""Chapter 9: why the folds inside a calibrator must be shuffled when the file is in time order.

The Platt-scaled linear SVM is fitted on the development rows (in file order) and scored on an inner validation split.
Only the folds used *inside* the calibrator differ between the two rows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

import metrics as K
import models as M
import protocol as P


def main() -> None:
    X, y = P.load()
    dev, _ = P.random_split(y)
    fit, val = train_test_split(dev, test_size=0.25, stratify=y[dev], random_state=P.SEED)
    fit = np.sort(fit)                                           # file order, like the original data
    rows = []
    for label, cv in (("3 folds, not shuffled (contiguous blocks of the file)", StratifiedKFold(3)),
                      ("3 folds, shuffled", StratifiedKFold(3, shuffle=True, random_state=P.SEED))):
        est = CalibratedClassifierCV(Pipeline([("prep", M.make_prep(X, "linear")), ("m", LinearSVC(dual=False, max_iter=5000))]),
                                     method="sigmoid", cv=cv).fit(X.iloc[fit], y[fit])
        p = est.predict_proba(X.iloc[val])[:, 1]
        raw = Pipeline([("prep", M.make_prep(X, "linear")), ("m", LinearSVC(dual=False, max_iter=5000))]).fit(X.iloc[fit], y[fit])
        d = raw.decision_function(X.iloc[val])
        rows.append({"calibrator folds": label, "ap_calibrated": K.ap(y[val], p), "auc_calibrated": K.auc_roc(y[val], p),
                     "ap_uncalibrated_margin": K.ap(y[val], d), "auc_uncalibrated_margin": K.auc_roc(y[val], d)})
    pd.DataFrame(rows).to_csv(P.ART / "families_svm_calibration_folds.csv", index=False, float_format="%.4f")
    print(pd.DataFrame(rows).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
