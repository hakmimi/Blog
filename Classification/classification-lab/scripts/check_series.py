"""Consistency checks for the Classification series. Fails loudly (exit 1) when something drifted.

    python scripts/check_series.py

Groups
  protocol     development / comparison / future rows never overlap; every temporal step stays in the past
  alignment    all models were scored on the same comparison records, in the same order
  policy       contribution arithmetic, matched baselines, capacity ceilings
  ranking      a strictly increasing transform of a fixed score vector leaves AP and AUC unchanged
  counts       candidate counts are the realised ones; twelve models plus one baseline make thirteen entries
  articles     rendered numbers match the artifacts, internal links resolve, figures referenced exist
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "series" / "classification" / "scripts"))
import metrics as K  # noqa: E402
import protocol as P  # noqa: E402

ART, FIG = P.ART, P.FIG
ARTICLES = ROOT / "src" / "content" / "articles" / "classification"
failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("ok    " if cond else "FAIL  ") + msg)
    if not cond:
        failures.append(msg)


def protocol_checks() -> None:
    _, y = P.load()
    dev, comp = P.random_split(y)
    check(len(set(dev) & set(comp)) == 0 and len(dev) + len(comp) == len(y), "random split: development and comparison are disjoint and cover every record")
    check(abs(y[dev].mean() - y[comp].mean()) < 5e-4, "random split is stratified (prevalence equal to three decimals)")
    t_dev, t_fut = P.temporal_split(len(y))
    check(t_dev.max() < t_fut.min(), "temporal split: every development row precedes every future row")
    for i, (tr, va) in enumerate(P.expanding_window_folds(len(t_dev))):
        check(tr.max() < va.min() and va.max() <= t_dev.max(), f"temporal fold {i + 1}: training precedes validation and stays inside the development prefix")
    manifest = json.loads((ART / "protocol_manifest.json").read_text(encoding="utf-8"))
    check(manifest["random_split"]["comparison_rows_sha1"] == P._sha1(comp), "manifest hash matches the comparison rows")
    check("duration" not in P.MAIN and "campaign" not in P.MAIN, "main feature set excludes duration and campaign")


def alignment_checks() -> None:
    pred = pd.read_csv(ART / "leaderboard_predictions.csv")
    _, y = P.load()
    _, comp = P.random_split(y)
    check(np.array_equal(pred["row"].to_numpy(), comp), "leaderboard predictions are in comparison-row order")
    check(np.array_equal(pred["y"].to_numpy(), y[comp]), "labels in the predictions file match the data")
    for name in ("leaderboard_predictions_default.csv",):
        other = pd.read_csv(ART / name)
        check(np.array_equal(other["row"].to_numpy(), pred["row"].to_numpy()), f"{name} is aligned with the tuned predictions")
    tl = json.loads((ART / "threshold_lab.json").read_text(encoding="utf-8"))
    check(len(tl["y"]) == len(pred) and int(sum(tl["y"])) == int(pred["y"].sum()), "threshold widget data has the same records as the leaderboard")
    fut = pd.read_csv(ART / "temporal_future_scores.csv")
    _, t_fut = P.temporal_split(len(y))
    check(np.array_equal(fut["row"].to_numpy(), t_fut), "temporal future scores cover exactly the future rows")


def policy_checks() -> None:
    y = np.array([1, 0, 1, 0, 0])
    sel = np.array([True, True, False, False, True])
    check(K.contribution(y, sel) == P.VALUE_PER_SUBSCRIPTION * 1 - P.COST_PER_CONTACT * 3, "contribution = value * positives - cost * selected (worked example)")
    p = np.array([0.9, 0.5, 0.3, 0.1, 0.05])
    check(K.capacity_policy(p, 2, None).sum() == 2 and K.capacity_policy(p, 4, 0.2).sum() == 3, "capacity is a ceiling and the break-even guard never admits a lower score")
    pred = pd.read_csv(ART / "leaderboard_predictions.csv"); yc = pred["y"].to_numpy()
    base = pd.read_csv(ART / "policy_baselines.csv").set_index("policy").contribution
    check(base["call everyone"] == K.contribution(yc, np.ones(len(yc), dtype=bool)), "call-everyone baseline equals the arithmetic on the comparison labels")
    check(base["call nobody"] == 0, "call-nobody baseline is zero")
    by = pd.read_csv(ART / "policy_by_model.csv")
    row = by[(by.model == "Logistic regression") & by.policy.str.startswith("break")].iloc[0]
    check(row.contribution == K.contribution(yc, pred["Logistic regression"].to_numpy() >= P.BREAK_EVEN), "policy table reproduces from the frozen predictions (logistic regression, break-even)")
    t = pd.read_csv(ART / "temporal_policies.csv")
    fut = pd.read_csv(ART / "temporal_future_scores.csv")
    check(float(t.call_everyone.iloc[0]) == K.contribution(fut["y"].to_numpy(), np.ones(len(fut), dtype=bool)), "temporal call-everyone baseline reproduces")


def ranking_checks() -> None:
    rng = np.random.default_rng(0)
    z = rng.normal(size=3000); y = (rng.random(3000) < 1 / (1 + np.exp(-z))).astype(int)
    f = lambda s: 1 / (1 + np.exp(-(3 * s + 1)))
    check(K.ap(y, z) == K.ap(y, f(z)) and K.auc_roc(y, z) == K.auc_roc(y, f(z)), "AP and AUC are invariant to a strictly increasing transform of a fixed score vector")
    ties = np.round(z, 1)
    check(len(np.unique(ties)) < len(np.unique(z)), "rounding creates ties (so a staircase map is not strictly increasing)")
    cal = pd.read_csv(ART / "calibration_rank_checks.csv")
    s = cal[cal["map"] == "sigmoid"]
    check(bool((s.ap_raw == s.ap_after_map).all()), "sigmoid maps leave AP unchanged in every calibration experiment")


def count_checks() -> None:
    sel = pd.read_csv(ART / "leaderboard_selected.csv")
    cand = pd.read_csv(ART / "leaderboard_candidates.csv")
    check(len(sel) == 13 and (sel.family == "baseline").sum() == 1, "thirteen entries: twelve models plus one no-model baseline")
    realised = cand.groupby("model").candidate.nunique()
    check(bool((realised == sel.set_index("model").loc[realised.index, "candidates_evaluated"]).all()), "reported candidate counts equal the candidates actually evaluated")
    check(bool((realised <= P.TUNING_CANDIDATES).all()) and bool(cand.groupby("model").is_default.sum().eq(1).all()), "at most 8 candidates per model and the default is always one of them")
    check(bool(cand[~cand.is_default].groupby("model").params.nunique().eq(cand[~cand.is_default].groupby("model").size()).all()), "the random candidates of each model are distinct")


def article_checks() -> None:
    files = sorted(ARTICLES.glob("[0-9][0-9]-*.md"))
    check(len(files) == 16, "sixteen rendered parts")
    slugs = {f.name[:2]: f.stem for f in files}
    for f in files:
        text = f.read_text(encoding="utf-8")
        check("@@" not in text, f"{f.name[:2]}: no unrendered tokens")
        check("(filled in by the build)" not in text, f"{f.name[:2]}: every output block was filled")
        for m in re.finditer(r"\]\(/series/classification/(\d\d-[^/)]+)/\)", text):
            check(m.group(1) in {s for s in slugs.values()}, f"{f.name[:2]}: link to part {m.group(1)[:2]} resolves")
        for m in re.finditer(r"/series/classification/figures/([\w.-]+\.png)", text):
            check((FIG / m.group(1)).exists(), f"{f.name[:2]}: figure {m.group(1)} exists")
        m = re.search(r'^order: (\d+)', text, re.M)
        check(m is not None and int(m.group(1)) == int(f.name[:2]), f"{f.name[:2]}: order matches file number")
    bad = re.compile(r"\b(thirteen (?:classifiers|models) )", re.I)
    for f in files:
        t = f.read_text(encoding="utf-8")
        check(not bad.search(t), f"{f.name[:2]}: no 'thirteen classifiers/models' wording")


def main() -> int:
    for group in (protocol_checks, alignment_checks, policy_checks, ranking_checks, count_checks, article_checks):
        print("==", group.__name__)
        group()
    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
