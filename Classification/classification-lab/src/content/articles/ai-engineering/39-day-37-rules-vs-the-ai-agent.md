---
title: "Day 37: Rules vs the AI Agent"
description: "From a yardstick with a single agent on it to a side-by-side run of the rules-only baseline and the AI graph agent on 31 cases. The AI agent wins, 87.1% to 64.5%, but its four failures are fraud patterns the LLM reviewer missed too, and that finding sets the work for Day 38."
series: "ai-engineering"
order: 39
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "full evaluation", "probe cases", "failure analysis"]
readingTime: "8 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day37`](https://github.com/hakmimi/AIEngineering/tree/main/Day37). Layers touched: L2 LLM, L3 Orchestration.

## Goals

- **G1. Run both agents on the same cases with the same scorer and store the results.**  
  You can: run `python -m scripts.eval_full v1` and open the CSV, JSON and Markdown report it writes.
- **G2. Add probe cases so the evaluation can fail.**  
  You can: explain why a 100% score on the first 23 cases was not evidence of much.
- **G3. Group failures by error type and category, then find the root cause in the code.**  
  You can: point at the capped risk terms (`+0.15`, `+0.30`) that let `p03` and `p04` through.
- **G4. Turn the failure analysis into a short, ranked list of fixes.**  
  You can: name the three improvements Day 38 will implement.

## System map

The evaluation loop from Day 36 grows a second lane: one script now runs both agents on every case, scores decisions and explanations, and writes three kinds of output. The agents themselves are still unchanged.

> Eval cases → Baseline agent + AI agent → Compare → Failure analysis → Top 3 improvements

<div class="ae-map" role="img" aria-label="make_eval_cases.py now writes 31 cases, including 8 probe cases with no expected route. scripts/eval_full.py runs decide_baseline with a template explanation and run_decision_graph with the LLM on every case. evaluation.py scores each decision (a null expected route is now accepted) and the explanation. The script builds metrics per mode, groups failures by error type and category, and writes full_<label>.csv, full_<label>.json and report_<label>.md, which you read to pick the top three fixes."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 444" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CASES</text><text class="lane" x="264" y="18">L1 · DATA/EVAL</text><text class="lane" x="508" y="18">RUNNER</text><text class="lane" x="752" y="18">AGENTS (DAYS 31–35)</text><text class="lane" x="996" y="18">SCORING</text><text class="lane" x="1240" y="18">OUTPUTS</text><path class="edge" d="M200,126 C230,126 230,167 261,167" marker-end="url(#mka)"></path><path class="edge-old" d="M200,220 C352,220 352,167 505,167" marker-end="url(#mkm)"></path><path class="edge" d="M444,167 C474,167 474,167 505,167" marker-end="url(#mka)"></path><path class="edge" d="M688,167 C718,167 718,118 749,118" marker-end="url(#mka)"></path><path class="edge" d="M688,167 C718,167 718,216 749,216" marker-end="url(#mka)"></path><path class="edge" d="M932,118 C962,118 962,114 993,114" marker-end="url(#mka)"></path><path class="edge" d="M932,216 C962,216 962,114 993,114" marker-end="url(#mka)"></path><path class="edge-old" d="M1086,148 L1086,168" marker-end="url(#mkm)"></path><path class="edge" d="M1176,212 C1206,212 1206,68 1237,68" marker-end="url(#mka)"></path><path class="edge" d="M1176,212 C1206,212 1206,160 1237,160" marker-end="url(#mka)"></path><path class="edge" d="M1176,212 C1206,212 1206,258 1237,258" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,300 V326 H110 V254" marker-end="url(#mkg)"></path><g class="node-changed"><rect height="84" rx="8" width="180" x="20" y="84"></rect><text class="nt t" text-anchor="middle" x="110" y="116">make_eval_cases.py</text><text class="ns s" text-anchor="middle" x="110" y="134">+8 probe cases</text><text class="ns s" text-anchor="middle" x="110" y="150">route=None</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="96">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="190"></rect><text class="nt t" text-anchor="middle" x="110" y="214">You</text><text class="ns s" text-anchor="middle" x="110" y="232">PowerShell</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="125"></rect><text class="nt t" text-anchor="middle" x="354" y="157">decision_cases.json</text><text class="ns s" text-anchor="middle" x="354" y="176">31 cases</text><text class="ns s" text-anchor="middle" x="354" y="191">+ probe 8</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="138">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="125"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="157">eval_full.py</text><text class="ns s" text-anchor="middle" x="598" y="176">both agents · every case</text><text class="ns s" text-anchor="middle" x="598" y="191">scores explanations too</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="138">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="80"></rect><text class="nt t" text-anchor="middle" x="842" y="104">Baseline (rules)</text><text class="ns s" text-anchor="middle" x="842" y="123">decide_baseline()</text><text class="ns s" text-anchor="middle" x="842" y="138">+ template_explanation()</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="178"></rect><text class="nt t" text-anchor="middle" x="842" y="202">AI agent (graph)</text><text class="ns s" text-anchor="middle" x="842" y="221">run_decision_graph()</text><text class="ns s" text-anchor="middle" x="842" y="236">LLM review via OpenAI</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="996" y="80"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="112">evaluation.py</text><text class="ns s" text-anchor="middle" x="1086" y="130">expected route may be null</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="92">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="170"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="202">mode_metrics()</text><text class="ns s" text-anchor="middle" x="1086" y="222">pass · accuracy · p50</text><text class="ns s" text-anchor="middle" x="1086" y="236">cost · llm_status</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="184">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="1240" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="66">failure_groups()</text><text class="ns s" text-anchor="middle" x="1330" y="85">error type [category]</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="47">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="1240" y="125"></rect><text class="nt t" text-anchor="middle" x="1330" y="157">full_v1 csv + json</text><text class="ns s" text-anchor="middle" x="1330" y="176">one row per case</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="138">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="216"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="248">report_v1.md</text><text class="ns s" text-anchor="middle" x="1330" y="267">table · failures</text><text class="ns s" text-anchor="middle" x="1330" y="282">lowest 3 explanations</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="229">NEW</text></g><rect class="elbg" height="15" rx="3" width="46" x="207" y="129"></rect><text class="el" text-anchor="middle" x="230" y="140">writes</text><rect class="elbg" height="15" rx="3" width="85" x="432" y="150"></rect><text class="el" text-anchor="middle" x="474" y="161">load_cases()</text><rect class="elbg" height="15" rx="3" width="78" x="681" y="319"></rect><text class="el" text-anchor="middle" x="720" y="330">top 3 fixes</text><text class="lane" style="fill:var(--ghost)" x="20" y="374">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="246" x="20" y="384"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="143" y="411">Day 38 · fix it, re-measure</text></g><g class="node-ghost"><rect height="44" rx="8" width="214" x="286" y="384"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="393" y="411">Day 39 · latency &amp; cost</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: One agent, one score

- `eval_decisions.py` runs one agent at a time and prints a pass rate
- The AI agent passes the 23 Day 36 cases at 100%, which proves little
- Explanations are never scored in a real run
- No stored results to compare against later

### After this episode: A comparison with a verdict

- `eval_full.py` runs baseline and AI on 31 cases and writes CSV, JSON and a Markdown report
- 8 probe cases encode fraud patterns the rules never mention
- AI 87.1% vs baseline 64.5%; AI unsafe errors 4 vs 10
- Failures grouped by cause, with three ranked fixes for Day 38

> **Why it matters:** a single score says nothing about where to spend effort. The comparison shows the safety routes pay off, and the grouped failures show the LLM reviewer adds explanations but no extra safety on these cases. That's the fact Day 38 and Day 39 act on.

## Code walkthrough

Four snippets from `Day37`. Show the highlighted lines on screen and say the point in bold.

### scripts/make_eval_cases.py · a probe case

```python
# --- probes: plausible blind spots of the rules (added after the first evaluation passed 100 % on the cases above) ---
case("p03_grocery_5000", "probe", "A returning customer suddenly pays 5,000 USD for groceries (~80x the typical basket) - anomalous even if the profile is clean",
     T(amount=5000, currency="USD", country="US", merchant_category="groceries", customer_type="returning", payment_method="card", customer_age_days=500),
     ["manual_review"], route=None)
```

**Probes test the decision, not the internal path.** A probe says what a human expects, not how the graph should get there. `route=None` tells the scorer to skip the route check for that case.

### evaluation.py · the one-line change

```python
    route: str | None                   # None = the route is not part of the expectation (probe cases)
...
    route_ok = exp.route is None or actual.route == exp.route
```

**A small change in the scorer so the dataset can say "I don't care how".** Without it, every probe would fail on route for the baseline, and the failure list would be noise.

### scripts/eval_full.py · both agents, same scorer

```python
def run_baseline(case) -> tuple[Actual, object]:
    started = time.perf_counter()
    decision = decide_baseline(case.transaction).decision
    decision.explanation = template_explanation(decision)
...
def evaluate_mode(cases, runner) -> list[CaseResult]:
    results = []
    for case in cases:
        actual, decision = runner(case)
        result = score_case(case, actual)
        result.explanation_score = score_explanation(actual.explanation, decision, case.transaction)
        results.append(result)
    return results
```

**The baseline gets the template explanation, so its explanations are scored too.** `evaluate_mode` takes the runner as a parameter. That is the whole trick: the loop and the scoring are identical for both agents.

### scripts/eval_full.py · grouping failures

```python
def failure_groups(results: list[CaseResult]) -> dict:
    groups = defaultdict(list)
    for r in results:
        if r.passed:
            continue
        key = r.error_type or ("wrong_provider" if r.provider_ok is False else "wrong_route_or_reason")
        groups[f"{key} [{r.category}]"].append(r.case_id)
    return dict(groups)
```

**Group failures before you fix anything.** Four red rows look like four problems. Grouped, they are two missing pattern rules, one capped score term and one under-weighted history.

## Run it

Run from `Day37` in PowerShell. Step 2 calls OpenAI for every case; the rest is offline.

**Step 1**

```powershell
python -m scripts.make_eval_cases
```

**Expect:** `wrote 31 cases` and `{'normal': 11, 'risky': 6, 'edge': 4, 'uncertain': 2, 'probe': 8}`.

**Step 2**

```powershell
python -m scripts.eval_full v1
```

**Expect:** One line per case with `baseline=PASS/FAIL ai=PASS/FAIL`, then the Markdown table. The README run gave AI 87.1% and baseline 64.5%. The LLM makes small differences between runs possible, so read your own numbers.

**Step 3**

```powershell
Get-Content data\eval\report_v1.md
```

**Expect:** The metric table, `Errors - baseline: {'unsafe_error': 10} | AI: {'unsafe_error': 4}` (README run), the failure groups and the three lowest-scoring AI explanations.

**Step 4**

```text
Import-Csv data\eval\full_v1.csv | Where-Object { $_.ai_pass -eq 'False' } | Format-Table case_id, ai_action, ai_error
```

**Expect:** The AI failures: `p01`, `p02`, `p03`, `p04`, all `route` and `unsafe_error` in the README run.

**Step 5**

```powershell
python -m pytest -q
```

**Expect:** `221 passed` (7 new tests in `tests/test_eval_full.py`).

### Break it on purpose

#### 1 · No key at all

Run `$env:OPENAI_API_KEY=""` and then `python -m scripts.eval_full nokey`. The baseline half runs, then the graph stops with `ConfigurationError: OPENAI_API_KEY is not configured` inside `llm_explain`, and no files are written. That's the right behaviour: a missing key is a setup mistake, and a crash is better than a report. Close the terminal or run `Remove-Item Env:OPENAI_API_KEY` afterwards so `.env` is used again.

#### 2 · A wrong key: the AI column without AI

Now set `$env:OPENAI_API_KEY="sk-wrong"` and run `python -m scripts.eval_full badkey`. This time the run finishes. The auth error becomes an `ExternalServiceError`, the LLM node catches it and uses the template explanation. With the LLM out of the picture the AI column still scores 87.1% with the same four failures, because the rules and routes make every decision. Open `full_badkey.json`: the AI summary shows `"llm_status": {"unavailable": 27, "skipped": 4}` and `total_cost_usd` 0. The Markdown report doesn't show `llm_status`, so add it.

```text
# scripts/eval_full.py, in report(): make a silent fallback visible
lines += ["", f"LLM status - AI: {a['llm_status']}"]
```

> Compare agents on identical cases, then read the failures, not just the score. And make sure the report tells you when the AI part didn't run, because a graceful fallback can pass an evaluation on its own.

## Cheat sheet

- **Baseline**: The simplest agent you have (rules only). Any AI layer must beat it to be worth its cost.
- **Probe case**: A case aimed at a plausible blind spot, added so the evaluation can fail.
- **Card testing**: A fraud pattern: tiny purchases on a fresh account to check whether a stolen card works.
- **Route accuracy**: The share of cases where the graph took the expected path (`normal`, `fallback`, `uncertain`).
- **Failure grouping**: Sorting failed cases by error type and category so you fix causes, not rows.
- **Capped score term**: A risk component with a maximum (amount +0.15, chargebacks +0.30), so an extreme value can't push the score over a threshold.
- **p50 latency**: The median response time: half the decisions were faster. Rules take 0.1 ms, the AI agent about 1.7 s.
- **Cost per case**: Total LLM cost of the run divided by LLM-reviewed cases, about $0.0005 here.
- **Manual reading**: Reading the lowest-scoring outputs yourself, because a rubric score can hide wording problems.
- **llm_status**: What happened to the LLM call for a decision: `ok`, `rejected_output`, `unavailable` or `skipped`.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why add probe cases after the AI agent scored 100% on the first 23?</summary><p>Those cases were written knowing the safety routes, so passing them proved little. A useful evaluation has to be able to fail, so the probes encode fraud patterns the rules never mention.</p></details>
<details><summary>Why do probe cases use route=None?</summary><p>They test the decision, not the internal path. Checking the route would fail the baseline for a reason unrelated to the fraud pattern.</p></details>
<details><summary>p04 has four chargebacks and still gets routed. Why?</summary><p>The chargeback term in the risk score is capped at +0.30, so the score stays about 0.35, below the 0.45 review threshold.</p></details>
<details><summary>What does the comparison say about the LLM reviewer?</summary><p>It never escalated or disagreed on the four failures. It adds readable explanations but no extra safety on these cases.</p></details>
<details><summary>Why is a 87% pass rate here not "87% of real traffic is right"?</summary><p>31 hand-written, edge-heavy cases with business-judgement labels. The number says which specific patterns are missing, not how the agent does on real payments.</p></details>
</div>

**Next:** Day 38 – Fix It, Prove It

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
