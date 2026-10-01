---
title: "Day 38: Fix It, Prove It"
description: "From a failure report with four unsafe errors to three explicit pattern rules, a version tag and a before/after comparison that proves the fix. The AI agent goes from 87.1% to 100% with zero regressions, and a hold-out set checks that the rules generalise instead of memorising the probes."
series: "ai-engineering"
order: 40
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "pattern rules", "versioned evaluation", "hold-out cases"]
readingTime: "9 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day38`](https://github.com/hakmimi/AIEngineering/tree/main/Day38). Layers touched: L1 Data, L3 Orchestration.

## Goals

- **G1. Trace the Day 37 failures to their root cause and choose a fix that doesn't shift every other decision.**  
  You can: explain why explicit pattern rules beat re-weighting the capped risk score.
- **G2. Add card-testing, amount-anomaly and chargeback-history rules with their own reason codes.**  
  You can: walk `_pattern_reason()` and show where it sits in `risk_rule_decision()`.
- **G3. Version the agent so every result says which logic produced it.**  
  You can: show `AGENT_VERSION = "v2"` in `version.py`, in a `decision_made` log line and in the report header.
- **G4. Prove the fix: fixed, regressed and still-failing cases, plus a hold-out set written after the fix.**  
  You can: run `eval_compare v1 v2` and read 4 fixed, 0 regressed.

## System map

Today the change is inside the rules. The evaluation loop from Days 36–37 stays, and gets a version tag and a compare script so we can say what the fix did.

> Failure report → Logic fix → Re-evaluation (versioned) → Improvement report

<div class="ae-map" role="img" aria-label="decision_cases.json grows to 39 cases with 8 hold-out cases. eval_full.py runs the graph agent, which calls risk_rule_decision in decision_engine.py. After the decline rule, the new _pattern_reason checks card testing, amount anomaly and chargeback history using thresholds from config.py, and sends matches to manual review with new reason codes. version.py tags decisions and results as v2. eval_compare.py reads two stored runs and reports fixed, regressed and still-failing cases back to you."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 405" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">EVAL</text><text class="lane" x="264" y="18">RUNNERS</text><text class="lane" x="508" y="18">AGENT (DAYS 31–37)</text><text class="lane" x="752" y="18">DECISION_ENGINE.PY</text><text class="lane" x="996" y="18">CONTRACTS</text><text class="lane" x="1240" y="18">RESULTS</text><path class="edge-old" d="M200,190 C230,190 230,84 261,84" marker-end="url(#mkm)"></path><path class="edge" d="M200,95 C230,95 230,84 261,84" marker-end="url(#mka)"></path><path class="edge" d="M444,84 C474,84 474,76 505,76" marker-end="url(#mka)"></path><path class="edge" d="M688,76 C718,76 718,84 749,84" marker-end="url(#mka)"></path><path class="edge" d="M688,186 C718,186 718,190 749,190" marker-end="url(#mka)"></path><path class="edge" d="M932,190 C962,190 962,84 993,84" marker-end="url(#mka)"></path><path class="edge" d="M932,84 C962,84 962,197 993,197" marker-end="url(#mka)"></path><path class="edge" d="M1176,84 C1206,84 1206,136 1237,136" marker-end="url(#mka)"></path><path class="edge" d="M1176,197 C1206,197 1206,136 1237,136" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,178 V265 H354 V227" marker-end="url(#mkg)"></path><path class="edge-back" d="M354,224 V287 H110 V223" marker-end="url(#mkg)"></path><g class="node-changed"><rect height="84" rx="8" width="180" x="20" y="53"></rect><text class="nt t" text-anchor="middle" x="110" y="85">decision_cases.json</text><text class="ns s" text-anchor="middle" x="110" y="104">39 cases</text><text class="ns s" text-anchor="middle" x="110" y="119">+ 8 hold-out (4 guards)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="66">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="159"></rect><text class="nt t" text-anchor="middle" x="110" y="183">You</text><text class="ns s" text-anchor="middle" x="110" y="202">PowerShell</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="264" y="49"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="81">eval_full.py</text><text class="ns s" text-anchor="middle" x="354" y="100">agent_version in results</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="62">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="172">eval_compare.py</text><text class="ns s" text-anchor="middle" x="354" y="191">fixed · regressed</text><text class="ns s" text-anchor="middle" x="354" y="206">still failing · hold-out</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="153">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="508" y="38"></rect><text class="nt t" text-anchor="middle" x="598" y="62">Decision graph</text><text class="ns s" text-anchor="middle" x="598" y="81">tools · LLM review</text><text class="ns s" text-anchor="middle" x="598" y="96">fallback + uncertain</text></g><g class="node-changed"><rect height="99" rx="8" width="180" x="508" y="136"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="168">config.py</text><text class="ns s" text-anchor="middle" x="598" y="187">card test ≤ 5 USD</text><text class="ns s" text-anchor="middle" x="598" y="202">anomaly ≥ 30× typical</text><text class="ns s" text-anchor="middle" x="598" y="217">review at 3 chargebacks</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="149">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="42"></rect><text class="nt t" text-anchor="middle" x="842" y="74">risk_rule_decision()</text><text class="ns s" text-anchor="middle" x="842" y="92">decline → patterns →</text><text class="ns s" text-anchor="middle" x="842" y="108">review thresholds</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="54">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="148"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="180">_pattern_reason()</text><text class="ns s" text-anchor="middle" x="842" y="198">card testing · anomaly</text><text class="ns s" text-anchor="middle" x="842" y="214">≥ 3 chargebacks</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="160">NEW</text></g><g class="node-changed"><rect height="99" rx="8" width="180" x="996" y="34"></rect><text class="nt t" text-anchor="middle" x="1086" y="66">Reason codes</text><text class="ns s" text-anchor="middle" x="1086" y="85">+ CARD_TESTING_PATTERN</text><text class="ns s" text-anchor="middle" x="1086" y="100">+ AMOUNT_ANOMALY</text><text class="ns s" text-anchor="middle" x="1086" y="115">+ explanation text</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="47">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="155"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="187">version.py</text><text class="ns s" text-anchor="middle" x="1086" y="206">AGENT_VERSION = "v2"</text><text class="ns s" text-anchor="middle" x="1086" y="221">changelog</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="168">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="94"></rect><text class="nt t" text-anchor="middle" x="1330" y="126">full_v2 + report_v2</text><text class="ns s" text-anchor="middle" x="1330" y="146">AI 100% · 0 unsafe</text><text class="ns s" text-anchor="middle" x="1330" y="160">hold-out 8/8</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="108">NEW</text></g><rect class="elbg" height="15" rx="3" width="59" x="201" y="72"></rect><text class="el" text-anchor="middle" x="230" y="83">39 cases</text><rect class="elbg" height="15" rx="3" width="72" x="682" y="170"></rect><text class="el" text-anchor="middle" x="718" y="182">thresholds</text><rect class="elbg" height="15" rx="3" width="91" x="917" y="123"></rect><text class="el" text-anchor="middle" x="962" y="134">decision_made</text><rect class="elbg" height="15" rx="3" width="91" x="1161" y="150"></rect><text class="el" text-anchor="middle" x="1206" y="161">agent_version</text><rect class="elbg" height="15" rx="3" width="59" x="812" y="258"></rect><text class="el" text-anchor="middle" x="842" y="269">v1 vs v2</text><rect class="elbg" height="15" rx="3" width="142" x="161" y="280"></rect><text class="el" text-anchor="middle" x="232" y="291">4 fixed · 0 regressed</text><text class="lane" style="fill:var(--ghost)" x="20" y="335">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="345"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="372">Day 39 · latency, cost, fast path</text></g><g class="node-ghost"><rect height="44" rx="8" width="190" x="300" y="345"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="395" y="372">Day 40 · audit trail</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Four fraud patterns slip through

- `p01`/`p02` card testing, `p03` 5,000 USD of groceries, `p04` four chargebacks: all routed
- The amount term is capped at +0.15 and the chargeback term at +0.30
- No version on decisions or results, so "did the fix help?" has no clean answer
- Only the cases that exposed the problem, nothing to test generalisation

### After this episode: Fixed, versioned and proven

- `_pattern_reason()` sends the three patterns to manual review with specific reason codes
- Thresholds live in `config.py` and can be tuned by environment variable
- `AGENT_VERSION = "v2"` in logs and in every stored evaluation
- AI 100% on all 39 cases, 0 unsafe errors, 0 regressions, hold-out 8/8

> **Why it matters:** a fix you can't measure is a guess. Using the same evaluation before and after, tagging the version, and adding cases written after the fix is the loop you'll use for every change to an AI system.

## Code walkthrough

Four snippets from `Day38`. Show the highlighted lines on screen and say the point in bold.

### decision_engine.py · the pattern rules

```python
def _pattern_reason(tx: Transaction) -> ReasonCode | None:
    """Patterns the additive risk score cannot express because its terms are capped."""
    usd = amount_in_usd(tx)
    if tx.customer_type is CustomerType.NEW and usd <= settings.card_test_max_usd and tx.merchant_category.value in CARD_TEST_CATEGORIES:
        return ReasonCode.CARD_TESTING_PATTERN                        # tiny purchase on a fresh account: probing stolen cards
    if usd >= settings.amount_anomaly_multiple * load_risk_tables()["category_median_usd"][tx.merchant_category.value]:
        return ReasonCode.AMOUNT_ANOMALY                              # e.g. 5,000 USD of groceries
    if tx.prior_chargebacks >= settings.chargeback_review_count:
        return ReasonCode.PRIOR_CHARGEBACKS                           # history alone stops automatic approval
    return None
```

**Each rule reads like the fraud pattern it catches.** The amount rule compares against the category's typical amount, so 5,000 USD of travel is fine and 5,000 USD of groceries is not. All three thresholds come from `settings`.

### decision_engine.py · where the rules sit

```python
    if risk.score >= settings.risk_decline:
        return _decision(tx, Action.DECLINE, [ReasonCode.HIGH_RISK, *risk.reason_codes], risk)
    # v2 pattern rules - specific, explainable reasons that a capped risk score would otherwise hide (Day 37 findings)
    pattern = _pattern_reason(tx)
    if pattern is not None:
        return _decision(tx, Action.MANUAL_REVIEW, [pattern, *[r for r in risk.reason_codes if r is not pattern]], risk)
    if risk.score >= settings.risk_review:
        return _decision(tx, Action.MANUAL_REVIEW, [ReasonCode.MEDIUM_RISK, *risk.reason_codes], risk)
```

**After the decline rule, before the generic review rule.** A decline still wins, so the patterns can only add review. And because they come before `MEDIUM_RISK`, the first reason code is the specific one a reviewer needs.

### version.py · the version tag

```python
AGENT_VERSION = "v2"

CHANGELOG = {
    "v1": "Day 31-35: risk rules, eligibility, scoring, LLM review, fallback + uncertainty routes",
    "v2": "Day 38: card-testing rule, amount-anomaly rule, chargeback-history rule (fixes found by the Day 37 evaluation)",
}
```

**Bump it whenever rules, thresholds or prompts change.** It goes into every `decision_made` log line and into `full_*.json`, so months later you can still tell which logic produced a result.

### scripts/eval_compare.py · fixed and regressed

```python
    old_rows = {r["case_id"]: r for r in ra["rows"]}
    common = [r for r in rb["rows"] if r["case_id"] in old_rows]                 # only cases both runs saw are comparable
...
        out[f"{mode}_fixed"] = [r["case_id"] for r in common if r[f"{mode}_pass"] and not old_rows[r["case_id"]][f"{mode}_pass"]]
        out[f"{mode}_regressed"] = [r["case_id"] for r in common if not r[f"{mode}_pass"] and old_rows[r["case_id"]][f"{mode}_pass"]]
```

**Compare case by case, not only the averages.** A pass rate can stay flat while two cases get fixed and two others break. The regressed list is the one to read first.

## Run it

Run from `Day38` in PowerShell. Steps 1, 2, 4 and 5 are offline; step 3 calls OpenAI.

**Step 1**

```powershell
python -m scripts.make_eval_cases
```

**Expect:** `wrote 39 cases` and `{... 'probe': 8, 'holdout': 8}`.

**Step 2**

```powershell
python -m scripts.eval_decisions run base_v2
```

**Expect:** Rules only, offline: `pass_rate 0.821`, `probe 0.88` (only `p07` still fails, the graph's uncertainty route catches it), `holdout 1.0`.

**Step 3**

```powershell
python -m scripts.eval_full v3
```

**Expect:** Live run of both agents. The report header says `(agent version v2)`; the README run had the AI agent at 100% with no unsafe errors.

**Step 4**

```powershell
python -m scripts.eval_compare v1 v2
```

**Expect:** `v1 (agent v1 (untagged)) -> v2 (agent v2)`, the metric deltas, the 8 hold-out case ids, and for `ai`: `fixed=['p01_card_testing_digital', 'p02_card_testing_gaming', 'p03_grocery_5000', 'p04_four_chargebacks'] regressed=[]`.

**Step 5**

```powershell
python -m pytest tests/test_rules_v2.py -q
```

**Expect:** `33 passed` (one test reads the stored v1/v2 results). Then `python -m pytest -q` for `254 passed`.

### Break it on purpose

#### 1 · Switch the card-testing rule off by config

Run `$env:CARD_TEST_MAX_USD="0"` and then `python -m scripts.eval_decisions run broken`. No code changed, but `p01`, `p02`, `h01` and `h02` fail again, the pass rate drops from 0.821 to 0.718 and unsafe errors go from 6 to 10. Config is logic too, and the evaluation catches it. `Remove-Item Env:CARD_TEST_MAX_USD` when done.

#### 2 · The real bug in eval_compare

The "before" common-case pass rate is computed over **all** rows of the first run, while "after" uses only the cases both runs share. Comparing forward (`v1 v2`) hides it because every v1 case is also in v2. Compare backwards, `python -m scripts.eval_compare v2 v1`: "before" is averaged over 39 cases while the output says `cases: 31`. With a small made-up pair of runs (3 cases vs 2) it reports 0.667 before where the right answer on the shared cases is 0.5.

```text
# scripts/eval_compare.py: compute 'before' on the same common cases
before = [old_rows[r["case_id"]] for r in common]
out[f"{mode}_common_pass_rate"] = {"before": round(sum(r[f"{mode}_pass"] for r in before) / len(before), 3),
                                   "after": round(sum(r[f"{mode}_pass"] for r in common) / len(common), 3), "cases": len(common)}
```

> Measure the fix with the same yardstick, compare case by case, and add cases after the fix to test generalisation. And check the comparison code as carefully as the agent, because a wrong "before" makes any "after" look good.

## Cheat sheet

- **Root cause**: The reason in the code a case fails, here the capped risk terms, as opposed to the symptom (a routed fraud).
- **Pattern rule**: An explicit rule for a known fraud shape that sends matching payments to review with its own reason code.
- **Card testing**: Tiny purchases on a new account in digital goods or gaming, used to check whether a stolen card works.
- **Amount anomaly**: An amount at least 30 times the category's typical amount.
- **Agent version**: A tag (`v2`) stored with every decision log and evaluation result, so results can be traced to the logic that made them.
- **Regression**: A case that passed before the change and fails after it.
- **Hold-out case**: A case written after the fix and never used to design it, to test whether the fix generalises.
- **Guard case**: A case that must NOT be flagged, so a new rule doesn't over-block good customers.
- **Overfitting to the eval**: Tuning the agent to the exact test cases so the score rises but real behaviour doesn't improve.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why add pattern rules instead of raising the caps in the risk score?</summary><p>Changing the score's weights shifts every decision in the population. A pattern rule changes only the cases that match it, and it gives a specific reason code.</p></details>
<details><summary>Why do the pattern rules run after the decline rule and before the MEDIUM_RISK rule?</summary><p>A decline must still win, so patterns can only add review. Running before <code>MEDIUM_RISK</code> makes the specific reason code the first one.</p></details>
<details><summary>What do the four guard cases in the hold-out set protect against?</summary><p>Over-blocking: an established customer paying 1 USD, 400 USD of groceries, two old chargebacks, a new customer paying 20 USD. The new rules must leave them alone.</p></details>
<details><summary>Why does the README warn about the 100% result?</summary><p>The fixes were designed from these probes and the hold-out variants were written by the same person knowing the fix. It shows the known gaps are closed, not that unknown fraud patterns are covered.</p></details>
<details><summary>What does eval_compare report that a pass-rate delta can't?</summary><p>Which cases were fixed, which regressed and which still fail, compared only on cases both runs share.</p></details>
</div>

**Next:** Day 39

<style>
.ae-map{--accent:var(--teal);--accent-soft:color-mix(in srgb,var(--teal) 14%,var(--card));--surface:var(--card);--ghost:var(--muted);--ok:var(--teal);margin:1.2rem 0;overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card);padding:.8rem}
.ae-map svg{display:block;min-width:900px;width:100%;height:auto}
.ae-map .node-new rect{fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.6}
.ae-map .node-changed rect{fill:var(--surface);stroke:var(--accent);stroke-width:1.6;stroke-dasharray:6 3}
.ae-map .node-existing rect{fill:var(--surface);stroke:var(--line);stroke-width:1.2}
.ae-map .node-external rect{fill:var(--surface);stroke:var(--ink);stroke-width:1.2}
.ae-map .node-ghost rect{fill:none;stroke:var(--ghost);stroke-width:1.2;stroke-dasharray:5 4}
.ae-map .node-existing .t{fill:var(--muted)}.ae-map .node-ghost .t,.ae-map .node-ghost .s{fill:var(--ghost)}
.ae-map .nt{font-size:14px;font-weight:600;fill:var(--ink)}.ae-map .ns{font-size:11.5px;fill:var(--muted)}
.ae-map .lane,.ae-map .el{font-family:ui-monospace,Consolas,monospace;fill:var(--muted)}.ae-map .lane{font-size:11px;letter-spacing:1.2px}.ae-map .el{font-size:10.5px}
.ae-map .edge{fill:none;stroke:var(--accent);stroke-width:1.5}.ae-map .edge-old{fill:none;stroke:var(--muted);stroke-width:1.2}
.ae-map .edge-back{fill:none;stroke:var(--ok);stroke-width:1.5}.ae-map .edge-ghost{fill:none;stroke:var(--ghost);stroke-width:1.1;stroke-dasharray:3 3}
.ae-map .elbg{fill:var(--surface)}
.ae-legend{display:flex;flex-wrap:wrap;gap:.4rem 1.1rem;font-size:.84rem;color:var(--muted);--accent:var(--teal);--accent-soft:color-mix(in srgb,var(--teal) 14%,var(--card));--ghost:var(--muted)}
.ae-legend i{display:inline-block;width:18px;height:12px;border-radius:3px;vertical-align:-1px;margin-right:6px}
.ae-quiz details{border:1px solid var(--line);border-radius:8px;background:var(--card);padding:.7rem 1rem;margin:.6rem 0}
.ae-quiz summary{cursor:pointer;font-weight:600;color:var(--ink)}
.ae-quiz details[open] summary{margin-bottom:.4rem}
.ae-quiz p{margin:.3rem 0;color:var(--text)}
</style>
