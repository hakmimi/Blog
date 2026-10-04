"""Write docs/classification-changelog.md: original claims, the correction, the evidence, the affected parts.

Every number in the evidence column is read from series/classification/artifacts when this script runs, so the
change log cannot disagree with the experiments.

    python scripts/build_changelog.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "series" / "classification" / "artifacts"
sys.path.insert(0, str(ROOT / "series" / "classification" / "scripts"))


def csv(n):
    return pd.read_csv(ART / n)


def js(n):
    return json.loads((ART / n).read_text(encoding="utf-8"))


def cell(n, col, **flt):
    d = csv(n)
    for k, v in flt.items():
        d = d[d[k.replace("__", " ")].astype(str) == str(v)]
    assert len(d) == 1, (n, flt, len(d))
    return d.iloc[0][col]


def build() -> str:
    sel = csv("leaderboard_selected.csv").set_index("model")
    pol = csv("policy_by_model.csv")
    pb = pol[pol.policy.str.startswith("break")].set_index("model")
    prof = js("data_profile.json")
    obj = csv("objectives_discrepancy.csv")
    onotes = js("objectives_notes.json")
    ocmp = csv("objectives_comparison.csv").set_index("loss")
    fs = csv("data_feature_sets.csv")
    fsv = lambda s, m: fs[(fs.feature_set == s) & (fs.model == m)].cv_ap_mean.iloc[0]
    boot = js("bagging_oob.json")
    base = csv("policy_baselines.csv").set_index("policy").contribution
    tp = csv("temporal_policies.csv")
    tb = tp[tp.policy == "break-even (1/8)"]
    pick = lambda m, c: tb[(tb.model == m) & (tb.correction == c)].iloc[0]
    svm = csv("families_svm_calibration_folds.csv")
    rank = csv("calibration_rank_checks.csv")
    cands = csv("leaderboard_candidates.csv").groupby("model").candidate.nunique()
    paired = csv("uncertainty_paired_ap.csv")
    pr = paired[(paired.resampling == "rows") & (paired.reference == "Logistic regression")].set_index("model")
    spread_all = pb.contribution.max() - pb.contribution.min()
    spread_excl = pb.drop("Gaussian Naive Bayes").contribution.max() - pb.drop("Gaussian Naive Bayes").contribution.min()
    old_oracle, old_everyone = 12240, 12082

    rows = [
        ("1", "\"41,188 customers\" (parts 1, 2, 16)", "The unit is a record. The file has no client identifier, `campaign` is above 1 in many records, and the documentation describes the contact columns as attributes of the last contact.",
         f"`data_profile.json`: campaign > 1 in {prof['campaign_gt1_share']:.1%} of records, maximum {prof['campaign_max']}; {prof['exact_duplicate_rows']} exact duplicate rows.", "1, 2"),
        ("2", "\"Test set touched once\" (parts 1, 12)", "Development rows are used for every choice; the comparison split is scored for frozen pipelines and called a teaching benchmark. Earlier drafts did look at it.",
         "`protocol.py`, `protocol_manifest.json` (split hashes); every experiment script imports the protocol.", "1, 6-14"),
        ("3", "`duration` \"is a consequence of the outcome\" (part 2)", "Unavailability before the contact is the sufficient argument. The mechanism is not claimed.",
         f"CV AP of a logistic regression: {fsv('main', 'Logistic regression'):.3f} without, {fsv('main + duration (not eligible; benchmark only)', 'Logistic regression'):.3f} with `duration` (`data_feature_sets.csv`).", "2"),
        ("4", "`campaign` is \"known before dialling\" and kept (part 2)", "Its eligibility cannot be established (the contact columns describe the last contact, so the count may record when the bank stopped calling). Excluded from the main set; sensitivity run added.",
         f"Adding it changes CV AP by {fsv('main + campaign', 'Logistic regression') - fsv('main', 'Logistic regression'):+.4f} (logistic regression) and {fsv('main + campaign', 'LightGBM') - fsv('main', 'LightGBM'):+.4f} (LightGBM).", "2, all"),
        ("5", "`unknown` means the agent did not record it (part 2)", "The documentation only says missing values are coded `unknown`; no reason is claimed.", "`bank-additional-names.txt` (section 8).", "2"),
        ("6", "ROC-AUC is optimistic on imbalanced data because negatives absorb the damage (part 3)", "AUC compares class-conditional score distributions and is unchanged when positives are removed at random; AP depends on prevalence and is only comparable on the same records.",
         f"`metrics_prevalence_experiment.csv`: AUC {cell('metrics_prevalence_experiment.csv', 'roc_auc', share_of_positives_kept=1.0):.3f} to {cell('metrics_prevalence_experiment.csv', 'roc_auc', share_of_positives_kept=0.1):.3f} while AP {cell('metrics_prevalence_experiment.csv', 'average_precision', share_of_positives_kept=1.0):.3f} to {cell('metrics_prevalence_experiment.csv', 'average_precision', share_of_positives_kept=0.1):.3f}.", "3"),
        ("7", "Accuracy can improve by at most about two points (part 3)", "A perfect classifier gains 11.3 points over the do-nothing baseline.", f"`data_profile.json`: always-no accuracy {prof['always_no_accuracy']:.4f}.", "1, 3"),
        ("8", "\"There is no model that maximises both\" precision and recall (part 1)", "A better model can raise both. For one score, moving the cut-off trades them.", "Part 3 reports precision and recall at two cut-offs for one model.", "1, 3"),
        ("9", "Hand-written logistic regression differs from the library by 0.201 because of a \"long, flat valley\" (part 4)", "The 1,500-step fit had not converged. Converged fits agree to about 1e-5; rank deficiency changes coefficients, not predictions.",
         f"`objectives_discrepancy.csv`: largest probability difference {obj.iloc[0].max_abs_prob_diff_vs_reference:.3f} (1,500 steps), {obj.iloc[1].max_abs_prob_diff_vs_reference:.3f} (20,000 steps), {obj.iloc[2].max_abs_prob_diff_vs_reference:.1e} (L-BFGS); design rank deficiency {onotes['rank_deficiency']}.", "4"),
        ("10", "Class weights are equivalent to moving the threshold (part 4)", "Equivalence needs conditions (unpenalised, correctly specified model). With a penalty and a finite sample the solutions differ.",
         f"`objectives_notes.json`: largest probability difference {onotes['weight_vs_intercept_shift']['max_abs_prob_diff_weighted_vs_shifted_intercept']:.3f}; re-weighted fit selects every validation record at 1/8 (contribution {ocmp.loc['weighted log', 'contribution_at_break_even']:.0f}).", "4"),
        ("11", "Log loss and Brier compared by size (part 4)", "Compared by shape; an objective-function map covers log loss, Brier, hinge, exponential and focal losses.", "Part 4 table.", "4"),
        ("12", "Per-dummy odds ratios with full one-hot encoding (part 5)", "Odds ratios against a stated reference level, with bootstrap intervals; coefficients are conditional associations.", "`linear_odds_ratios.csv` (100 refits).", "5"),
        ("13", "Naive Bayes \"has no objective\" (part 4); Gaussian NB as the Naive Bayes (parts 5, 11, 12)", "It estimates parameters by maximum likelihood. The Gaussian-on-one-hot variant is labelled a deliberately imperfect baseline and a categorical variant is compared.", "`linear_naive_bayes.csv`.", "4, 5"),
        ("14", "Leaves of 1 record and `k` below 50 are wrong (parts 6, 9)", "Presented as dataset-specific bias-variance behaviour measured on development data.", "`trees_sweeps.csv`, `families_knn.csv`.", "6, 9"),
        ("15", "`n_estimators` is not a hyperparameter (part 7)", "Treated as a resource and stability setting; more trees need not improve every finite-sample metric.", "`bagging_n_estimators.csv` (5 seeds per size).", "7"),
        ("16", "Out-of-bag gap explained by fewer trees per prediction (part 7)", "Tested and not supported by the evidence.", f"`bagging_oob.json`: validation AP {boot['val_ap_300_trees']:.3f} with 300 trees, {boot['val_ap_random_100_of_300_mean']:.3f} with random 100-tree subsets, OOB {boot['oob_ap']:.3f}.", "7"),
        ("17", "k-NN scaling matters because `nr.employed` is near 5,000 (part 9)", "Distance depends on variation, not a constant offset; measured effect of scaling and of recoding `pdays`.", "`families_knn.csv`, `families_notes_std.csv`.", "9"),
        ("18", "Report helper clipped all scores, so AP changed after calibration (part 11)", "Ranking metrics use unclipped scores; clipping is only inside log loss. A sigmoid map leaves AP identical; isotonic maps create ties.",
         f"`calibration_rank_checks.csv`: sigmoid AP unchanged in {int((rank[rank['map'] == 'sigmoid'].ap_raw == rank[rank['map'] == 'sigmoid'].ap_after_map).sum())} of {int((rank['map'] == 'sigmoid').sum())} rows; isotonic leaves between {rank[rank['map'] == 'isotonic'].distinct_scores_after_map.min()} and {rank[rank['map'] == 'isotonic'].distinct_scores_after_map.max()} distinct scores.", "11"),
        ("19", "Calibration folds fitted preprocessing outside the calibrator; unshuffled folds on time-ordered data", "The calibrator wraps the complete pipeline with shuffled folds.",
         f"`families_svm_calibration_folds.csv`: calibrated AP {svm.iloc[0].ap_calibrated:.3f} (unshuffled) against {svm.iloc[1].ap_calibrated:.3f} (shuffled).", "9, 11, 12"),
        ("20", "RBF SVM does not scale past ~50k rows (part 9)", "Excluded for measured cost under this protocol.", "`families_svm_timing.csv`.", "9, 12"),
        ("21", "CatBoost \"cannot be cloned\" (parts 12)", "Tested: constructing with `cat_features` makes `sklearn.clone` raise a `RuntimeError`; the adapter finds string columns at fit time.", "`models.py` (`CatBoostES`).", "12"),
        ("22", "Eight random candidates for every model; budget justified by a study that scored on the comparison split (part 10)", "Default plus up to seven distinct draws per model; measured counts; the budget study scores on rows outside the search and limits the inference to three models.",
         f"`leaderboard_candidates.csv`: candidates per model {int(cands.min())} to {int(cands.max())}; `budget_curve.csv`.", "10, 12"),
        ("23", "A single timing per model (part 12)", "Final fit, search cost, batch throughput and single-record latency are separate; environment recorded.", "`timing.csv`, `timing_environment.json`.", "12"),
        ("24", "\"Thirteen classifiers\" (parts 1, 12, 14)", "Twelve predictive models plus one no-model baseline: thirteen entries.", f"`leaderboard_selected.csv`: {len(sel)} rows, one baseline.", "1, 12-14"),
        ("25", "Top models are \"statistically tied\"; P(LightGBM worse) = 0.25 (part 13)", "No equality or non-inferiority claim; \"share of resamples above zero\" is an empirical proportion; simultaneous intervals added; four-decimal endpoints.",
         f"`uncertainty_paired_ap.csv`: against logistic regression, random forest marginal interval [{pr.loc['Random forest', 'ci95_lo']:+.4f}, {pr.loc['Random forest', 'ci95_hi']:+.4f}], simultaneous [{pr.loc['Random forest', 'simultaneous95_lo']:+.4f}, {pr.loc['Random forest', 'simultaneous95_hi']:+.4f}].", "13"),
        ("26", "Stability study reused hyperparameters chosen on the original split (part 13)", "Every split re-tunes from scratch.", "`stability_runs.csv`.", "13"),
        ("27", "Highest minus lowest learned-model contribution is 200 (part 14)", "The old table's 3,377 and 3,040 differ by 337. The new text names its subset.",
         f"New: {spread_all:.0f} across all twelve, {spread_excl:.0f} excluding Naive Bayes (`policy_by_model.csv`).", "14"),
        ("28", "The threshold is worth ~100% of profit and the model ~3% (part 14)", "Scoped to these prices and policies.", f"Default 0.5 against break-even for the same scores (`policy_by_model.csv`); best break-even contribution {pb.contribution.max():.0f}.", "14"),
        ("29", "\"Best possible profit\" (parts 14, 16)", "\"Best observed threshold on this sample\"; selected on out-of-fold development scores.", "`metrics.best_observed_threshold`.", "11, 14, 16"),
        ("30", "Profit as incremental value (part 14)", "Retrospective policy simulation; expected versus incremental contribution formulas; no uplift is identified.", "Part 14 section 1.", "14"),
        ("31", "Capacity must be filled (part 14)", "Capacity is a ceiling; guarded policy compared with unguarded.", "`policy_capacity.csv`.", "11, 14"),
        ("32", "Importance upper bound and \"no personalisation\" (part 15)", "Four importance questions kept apart; grouped permutation is not a bound; profile ablation is scoped to this pipeline.", "`importance_groups.csv`.", "15"),
        ("33", "Missed subscribers shown as extremes (part 15)", "Policy-based false negatives, three rank groups, segment rates with intervals.", "`errors_*.csv`.", "15"),
        ("34", "Segments \"within noise\" (part 15)", "Wilson intervals; segments listed with counts.", "`errors_segments.csv`.", "15"),
        ("35", "Chronological run reused random-split hyperparameters; AP compared across populations (part 16)", "Past-only development with expanding-window folds; AP compared only within the same test population with the prevalence baseline.", "`temporal_candidates.csv`, `temporal_policies.csv`.", "16"),
        ("36", f"Corrected model earns {old_oracle:,} against call-everyone {old_everyone:,} (part 16)",
         "Recomputed with past-only development, a feasible EM correction and an oracle correction labelled as such.",
         f"`temporal_policies.csv`: call-everyone {base_everyone(tb):,.0f}; LightGBM {pick('LightGBM', 'none').contribution:,.0f} uncorrected, {pick('LightGBM', 'EM on unlabelled scores').contribution:,.0f} with EM, {pick('LightGBM', 'oracle prevalence (diagnostic)').contribution:,.0f} with the oracle.", "16"),
    ]
    out = ["# Classification series: technical change log", "",
           "Generated by `scripts/build_changelog.py` from the experiment artifacts. Original claims refer to the first published edition.", "",
           "| # | Original claim | Correction | Evidence | Parts |", "|---|---|---|---|---|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/") for c in r) + " |")
    return "\n".join(out) + "\n"


def base_everyone(tb) -> float:
    return float(tb.call_everyone.iloc[0])


if __name__ == "__main__":
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "classification-changelog.md").write_text(build(), encoding="utf-8")
    print("wrote docs/classification-changelog.md")
