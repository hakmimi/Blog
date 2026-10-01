---
title: "Day 36: Build the Yardstick First"
description: "From a decision agent that looks right because nobody has measured it to a labelled set of 23 cases with expected decisions, expected routes and a scoring function. Today we build the yardstick before we touch the agent, and the first run already shows where the rules alone are unsafe."
series: "ai-engineering"
order: 38
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "evaluation dataset", "deterministic scoring", "runner"]
readingTime: "7 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day36`](https://github.com/hakmimi/AIEngineering/tree/main/Day36). Layers touched: L1 Data, L3 Orchestration.

## Goals

- **G1. Write evaluation cases whose expected outcome comes from business reasoning, not from the agent.**  
  You can: open `make_eval_cases.py` and explain why `n06` accepts two providers and `r03` accepts review or decline.
- **G2. Score a decision on action, provider, route and reason codes.**  
  You can: show `score_case()` and say what makes a case pass.
- **G3. Classify wrong answers by direction: too permissive or too cautious.**  
  You can: point at the 5 `unsafe_error`s in the rules-only run and say why they cost more than an over-cautious error.
- **G4. Run the evaluation repeatably and test the measuring stick itself.**  
  You can: run `eval_decisions run all` live and get 17/23, then run the 33 dataset and scoring tests.

## System map

Today the map gets a second loop next to the API. Cases go into a runner, the runner calls the agent we already have, and a scorer compares actual with expected. The agent itself does not change.

> Eval dataset → Decision agent → Actual decision → Expected decision → Score

<div class="ae-map" role="img" aria-label="make_eval_cases.py writes 23 labelled cases to data/eval/decision_cases.json; the explanation rubric sits next to it. scripts/eval_decisions.py loads the cases and runs either decide_baseline (rules only, route always normal) or run_decision_graph (the Day 35 graph with the LLM). evaluation.py scores each result on action, provider, route and reason codes, classifies wrong actions as unsafe_error, over_cautious or wrong_action, and summarize() builds pass rates. The runner prints PASS/FAIL lines and saves decisions_<label>.json."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 368" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">AUTHOR</text><text class="lane" x="264" y="18">L1 · DATA/EVAL</text><text class="lane" x="508" y="18">RUNNER</text><text class="lane" x="752" y="18">AGENTS (DAYS 31–35)</text><text class="lane" x="996" y="18">EVALUATION.PY</text><text class="lane" x="1240" y="18">RESULTS</text><path class="edge-old" d="M200,182 C230,182 230,84 261,84" marker-end="url(#mkm)"></path><path class="edge" d="M200,88 C230,88 230,84 261,84" marker-end="url(#mka)"></path><path class="edge" d="M444,84 C474,84 474,129 505,129" marker-end="url(#mka)"></path><path class="edge-old" d="M444,190 C718,190 718,182 993,182" marker-end="url(#mkm)"></path><path class="edge" d="M688,129 C718,129 718,80 749,80" marker-end="url(#mka)"></path><path class="edge" d="M688,129 C718,129 718,170 749,170" marker-end="url(#mka)"></path><path class="edge" d="M932,80 C962,80 962,84 993,84" marker-end="url(#mka)"></path><path class="edge" d="M932,170 C962,170 962,84 993,84" marker-end="url(#mka)"></path><path class="edge" d="M1176,84 C1206,84 1206,84 1237,84" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,126 V250 H110 V216" marker-end="url(#mkg)"></path><g class="node-new"><rect height="84" rx="8" width="180" x="20" y="46"></rect><text class="nt t" text-anchor="middle" x="110" y="78">make_eval_cases.py</text><text class="ns s" text-anchor="middle" x="110" y="96">one line of business</text><text class="ns s" text-anchor="middle" x="110" y="112">reasoning per case</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="58">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="152"></rect><text class="nt t" text-anchor="middle" x="110" y="176">You</text><text class="ns s" text-anchor="middle" x="110" y="194">PowerShell</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="264" y="34"></rect><text class="nt t" text-anchor="middle" x="354" y="66">decision_cases.json</text><text class="ns s" text-anchor="middle" x="354" y="85">23 cases</text><text class="ns s" text-anchor="middle" x="354" y="100">normal 11 · risky 6</text><text class="ns s" text-anchor="middle" x="354" y="115">edge 4 · uncertain 2</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="47">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="155"></rect><text class="nt t" text-anchor="middle" x="354" y="187">Explanation rubric</text><text class="ns s" text-anchor="middle" x="354" y="206">5 criteria × 0–2 · pass ≥ 8</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="168">NEW</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="508" y="80"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="112">eval_decisions.py</text><text class="ns s" text-anchor="middle" x="598" y="130">run &lt;label&gt;</text><text class="ns s" text-anchor="middle" x="598" y="146">--mode baseline|graph</text><text class="ns s" text-anchor="middle" x="598" y="160">--limit N</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="92">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="752" y="50"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="74">decide_baseline()</text><text class="ns s" text-anchor="middle" x="842" y="92">rules only · no routes</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="132"></rect><text class="nt t" text-anchor="middle" x="842" y="156">run_decision_graph()</text><text class="ns s" text-anchor="middle" x="842" y="176">fallback + uncertain routes</text><text class="ns s" text-anchor="middle" x="842" y="190">LLM via OpenAI</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="42"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="74">score_case()</text><text class="ns s" text-anchor="middle" x="1086" y="92">action · provider · route</text><text class="ns s" text-anchor="middle" x="1086" y="108">reasons + error direction</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="54">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="148"></rect><text class="nt t" text-anchor="middle" x="1086" y="180">score_explanation()</text><text class="ns s" text-anchor="middle" x="1086" y="198">rubric as code</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="160">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="42"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="74">summarize()</text><text class="ns s" text-anchor="middle" x="1330" y="92">pass rate · by category</text><text class="ns s" text-anchor="middle" x="1330" y="108">error counts</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="54">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="1240" y="148"></rect><text class="nt t" text-anchor="middle" x="1330" y="180">test_evaluation.py</text><text class="ns s" text-anchor="middle" x="1330" y="198">33 tests · 214 in total</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="160">NEW</text></g><rect class="elbg" height="15" rx="3" width="46" x="207" y="68"></rect><text class="el" text-anchor="middle" x="230" y="80">writes</text><rect class="elbg" height="15" rx="3" width="85" x="432" y="89"></rect><text class="el" text-anchor="middle" x="474" y="100">load_cases()</text><rect class="elbg" height="15" rx="3" width="59" x="689" y="88"></rect><text class="el" text-anchor="middle" x="718" y="98">baseline</text><rect class="elbg" height="15" rx="3" width="40" x="698" y="133"></rect><text class="el" text-anchor="middle" x="718" y="144">graph</text><rect class="elbg" height="15" rx="3" width="46" x="939" y="65"></rect><text class="el" text-anchor="middle" x="962" y="76">Actual</text><rect class="elbg" height="15" rx="3" width="110" x="665" y="243"></rect><text class="el" text-anchor="middle" x="720" y="254">PASS/FAIL + JSON</text><text class="lane" style="fill:var(--ghost)" x="20" y="298">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="335">Day 37 · baseline vs AI, full run</text></g><g class="node-ghost"><rect height="44" rx="8" width="222" x="300" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="411" y="335">Day 38 · fix what failed</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: An agent nobody has measured

- Day 35 added `fallback` and `uncertain` routes, but only unit tests say they work
- No list of cases with an agreed right answer
- No way to say whether a change made decisions better or worse
- A wrong decision is just wrong: letting fraud through and blocking a good customer look the same

### After this episode: A yardstick you can rerun

- 23 labelled cases in `data/eval/decision_cases.json`, each with a written reason
- `score_case()` checks action, provider, route and required reason codes
- Wrong actions are split into `unsafe_error`, `over_cautious` and `wrong_action`
- `python -m scripts.eval_decisions run <label>` prints a table and saves the result as JSON

> **Why it matters:** Month 1 taught us to build the evaluation before optimising (Day 13). From Day 37 on, every change to the decision agent is judged by this set, so the set has to be fair, repeatable and tested itself.

## Code walkthrough

Four snippets from `Day36`. Show the highlighted lines on screen and say the point in bold.

### scripts/make_eval_cases.py · a case is business reasoning

```python
case("n06_il_bank_transfer", "normal", "Israeli bank transfer - either the bank-transfer specialist or the local provider is fine",
     T(amount=3000, currency="ILS", country="IL", merchant_category="utilities", customer_type="returning", payment_method="bank_transfer", customer_age_days=500),
     ["route"], ["beta_bank", "epsilon_local_il"])
...
case("r03_ng_electronics_new_cb", "risky", "New customer in a high-risk country with a chargeback, buying electronics",
     T(amount=700, currency="USD", country="NG", merchant_category="electronics", customer_type="new", payment_method="card", customer_age_days=5, prior_chargebacks=1),
     ["manual_review", "decline"])
```

**When several answers are fine, the case lists all of them.** Forcing one right answer would punish the agent for a choice a human would accept. The description is the reason, written before running anything.

### evaluation.py · error direction

```python
PERMISSIVENESS = {Action.DECLINE: 0, Action.MANUAL_REVIEW: 1, Action.ROUTE: 2}      # higher = more permissive
...
    if not action_ok:
        most_permissive = max(PERMISSIVENESS[a] for a in exp.acceptable_actions)
        least_permissive = min(PERMISSIVENESS[a] for a in exp.acceptable_actions)
        if PERMISSIVENESS[actual.action] > most_permissive:
            error_type = "unsafe_error"
        elif PERMISSIVENESS[actual.action] < least_permissive:
            error_type = "over_cautious"
        else:
            error_type = "wrong_action"
```

**Actions are ordered, so a wrong answer has a direction.** More permissive than any acceptable answer is an unsafe error. Stricter than any is over-cautious. In payments the first one loses money, the second one loses a customer.

### evaluation.py · what a pass means

```python
    route_ok = actual.route == exp.route
    reasons_ok = all(code in actual.reason_codes for code in exp.must_include_reason_codes)
...
    passed = action_ok and provider_ok is not False and reasons_ok and route_ok
```

**A pass needs the right action, an acceptable provider, the right route and the required reasons.** `provider_ok` is `None` when the agent didn't route, so it only counts when a provider was chosen. The rules-only agent always reports route `normal`, which is why it fails every edge case.

### scripts/eval_decisions.py · the runner

```python
def run_agent(case, mode: str) -> Actual:
    started = time.perf_counter()
    if mode == "baseline":
        actual = actual_from_baseline(decide_baseline(case.transaction).decision)
    else:                                   # "graph": the full workflow with the LLM
        from decision_graph import run_decision_graph
        result = run_decision_graph(case.transaction)
```

**Same cases, same scorer, swappable agent.** That is what makes a comparison fair. Day 37 uses exactly this idea to put the baseline and the AI agent side by side.

## Run it

Run from `Day36` in PowerShell. Only step 4 calls OpenAI; everything else is offline and instant.

**Step 1**

```powershell
python -m scripts.make_eval_cases
```

**Expect:** `wrote 23 cases to ...\data\eval\decision_cases.json` and `{'normal': 11, 'risky': 6, 'edge': 4, 'uncertain': 2}`.

**Step 2**

```powershell
python -m scripts.eval_decisions run first5 --limit 5
```

**Expect:** Five `PASS` lines (`epsilon_local_il`, `alpha_pay`, `beta_bank`, `alpha_pay`, `alpha_pay`) and `"pass_rate": 1.0`.

**Step 3**

```powershell
python -m scripts.eval_decisions run all
```

**Expect:** `"pass_rate": 0.739`, `"errors": {"unsafe_error": 5}`, `edge 0.0`, `uncertain 0.0`. The FAIL lines say `route normal != expected fallback`.

**Step 4**

```powershell
python -m scripts.eval_decisions run mine --mode graph
```

**Expect:** Live LLM calls, a second or two per routed case. The edge cases now show `route=fallback` and the uncertain ones `route=uncertain`.

**Step 5**

```powershell
python -m pytest tests/test_evaluation.py -q
```

**Expect:** `33 passed`. Then `python -m pytest -q` for `214 passed`.

### Break it on purpose

#### 1 · A duplicate case id

In `make_eval_cases.py` rename `n02_us_grocery_card` to `n01_il_grocery_card`, regenerate and run again. `load_cases()` stops with `ValueError: duplicate case id n01_il_grocery_card` before any agent runs. Results keyed by id would silently overwrite each other otherwise.

#### 2 · Label the case from the agent's answer

Change `e01_unknown_country` to accept `["route"]`, the answer the rules-only agent gives. The pass rate goes up, which is the trap. Now run `python -m pytest tests/test_evaluation.py -q`: the dataset test fails because a `fallback` case must expect `manual_review`. The tests on the dataset stop you from copying the agent's mistakes into the answer key.

```text
# the check that catches it (tests/test_evaluation.py)
if c.expected.route in ("fallback", "uncertain"):
    assert c.expected.acceptable_actions == [Action.MANUAL_REVIEW], c.id
```

> An evaluation is only as good as its labels. Write the expected outcome from business reasoning, allow every acceptable answer, and test the dataset like code. Then a low score is information, not an insult.

## Cheat sheet

- **Evaluation dataset**: A fixed list of inputs with the outcome a human expects, used to score an agent the same way every time.
- **Acceptable actions**: The set of actions a case accepts (`route`, `manual_review`, `decline`). A case can accept more than one.
- **Expected route**: Which path the graph should take: `normal`, `fallback` or `uncertain`.
- **Required reason codes**: Codes that must appear in the decision, so the agent is right for the right reason.
- **unsafe_error**: The agent was more permissive than any acceptable answer, for example it routed a payment that needed a human.
- **over_cautious**: The agent was stricter than any acceptable answer, for example it sent a routine payment to review.
- **wrong_action**: A wrong action that sits between two acceptable ones, like `manual_review` when only `route` or `decline` were acceptable.
- **Rubric**: A written scoring scheme. Here: five criteria for explanations, 0–2 each, pass at 8 of 10.
- **Baseline**: The rules-only agent (`decide_baseline`). It is the reference any AI layer has to beat.
- **Pass rate by category**: The share of passing cases per group (normal, risky, edge, uncertain), so one weak group can't hide in an average.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why are expected outcomes written from business reasoning before running the agent?</summary><p>If you label cases from the agent's output, the evaluation copies the agent's bugs and scores them as correct. The labels must come from what a human would expect.</p></details>
<details><summary>The rules-only agent routes e01_unknown_country. Which error type is that, and why?</summary><p><code>unsafe_error</code>. The only acceptable action is <code>manual_review</code>, and <code>route</code> is more permissive than that.</p></details>
<details><summary>Why does n02 list two acceptable providers?</summary><p>Both <code>alpha_pay</code> and <code>gamma_wallet</code> are commercially fine for a small US card payment. Forcing one would punish a reasonable choice.</p></details>
<details><summary>The baseline scores 0% on edge and uncertain cases. Is the dataset too hard?</summary><p>No. Those cases need the <code>fallback</code> and <code>uncertain</code> routes, which only the graph has. The failures show the dataset measures the safety routes and does not reward doing nothing.</p></details>
<details><summary>Why is provider_ok None instead of False when the agent sends a case to review?</summary><p>No provider was chosen, so there is nothing to check. Counting it as a failure would punish a correct review decision.</p></details>
</div>

**Next:** Day 37 – Rules vs the AI Agent

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
