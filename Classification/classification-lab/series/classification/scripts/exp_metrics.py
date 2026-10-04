"""Chapter 3: grading one frozen model several ways.

A logistic regression (library defaults) is fitted on the development rows and scored once on the comparison
split. No choice is made from these numbers; they illustrate what each metric measures.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import classification_report, confusion_matrix

import metrics as K
import models as M
import protocol as P


def run() -> None:
    X, y = P.load()
    dev, comp = P.random_split(y)
    spec = [s for s in M.registry(X) if s.name == "Logistic regression"][0]
    model = clone(spec.build()).fit(X.iloc[dev], y[dev])
    p = model.predict_proba(X.iloc[comp])[:, 1]
    yc = y[comp]
    n, pos = len(yc), int(yc.sum())
    pd.DataFrame({"row": comp, "y": yc, "p": p}).to_csv(P.ART / "metrics_scores.csv", index=False)

    cm_rows, rep_rows = [], []
    for t in (0.5, 0.25, 0.125):
        tn, fp, fn, tp = confusion_matrix(yc, p >= t).ravel()
        cm_rows.append({"threshold": t, "tn": tn, "fp": fp, "fn": fn, "tp": tp, "records_selected": tp + fp,
                        "accuracy": (tp + tn) / n, "precision": tp / (tp + fp), "recall": tp / (tp + fn),
                        "specificity": tn / (tn + fp), "false_positive_rate": fp / (fp + tn),
                        "f1": 2 * tp / (2 * tp + fp + fn), "balanced_accuracy": (tp / (tp + fn) + tn / (tn + fp)) / 2})
        rep = classification_report(yc, p >= t, target_names=["no", "yes"], output_dict=True, digits=3)
        for k, v in rep.items():
            if isinstance(v, dict):
                rep_rows.append({"threshold": t, "row": k, **{kk: vv for kk, vv in v.items()}})
            else:
                rep_rows.append({"threshold": t, "row": k, "precision": np.nan, "recall": np.nan, "f1-score": v, "support": n})
    pd.DataFrame(cm_rows).to_csv(P.ART / "metrics_confusion.csv", index=False, float_format="%.5f")
    pd.DataFrame(rep_rows).to_csv(P.ART / "metrics_report.csv", index=False, float_format="%.5f")

    # --- ranking metrics, and what changes when the number of positives changes but the scoring does not
    rng = np.random.default_rng(P.SEED)
    rows = []
    for keep in (1.0, 0.5, 0.2, 0.1):
        aucs, aps, prev = [], [], []
        for _ in range(200 if keep < 1 else 1):
            m = (yc == 0) | (rng.random(n) < keep)
            aucs.append(K.auc_roc(yc[m], p[m])); aps.append(K.ap(yc[m], p[m])); prev.append(yc[m].mean())
        rows.append({"share_of_positives_kept": keep, "prevalence": np.mean(prev), "roc_auc": np.mean(aucs), "roc_auc_sd": np.std(aucs),
                     "average_precision": np.mean(aps), "ap_sd": np.std(aps), "ap_over_prevalence": np.mean(aps) / np.mean(prev)})
    pd.DataFrame(rows).to_csv(P.ART / "metrics_prevalence_experiment.csv", index=False, float_format="%.5f")

    order = np.argsort(-p)
    top = []
    for frac in (0.05, 0.10, 0.20):
        k = int(frac * n)
        hit = yc[order[:k]]
        top.append({"top_share": frac, "records": k, "precision": hit.mean(), "recall": hit.sum() / pos, "lift": hit.mean() / yc.mean()})
    pd.DataFrame(top).to_csv(P.ART / "metrics_top_k.csv", index=False, float_format="%.5f")
    P.write_json("metrics_notes.json", {"records": n, "positives": pos, "prevalence": float(yc.mean()),
                                         "roc_auc": K.auc_roc(yc, p), "average_precision": K.ap(yc, p),
                                         "pr_auc_trapezoid": K.pr_auc_trapezoid(yc, p),
                                         "always_no_accuracy": float(1 - yc.mean()), "perfect_accuracy_gain_points": float(100 * yc.mean()),
                                         "negatives": int(n - pos)})
    pd.set_option("display.width", 200)
    print(pd.DataFrame(cm_rows).round(4).to_string(index=False)); print(pd.DataFrame(rep_rows).round(3).to_string(index=False))
    print(pd.DataFrame(rows).round(4).to_string(index=False)); print(pd.DataFrame(top).round(3)); print(K.auc_roc(yc, p), K.ap(yc, p), K.pr_auc_trapezoid(yc, p))


if __name__ == "__main__":
    run()
