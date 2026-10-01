---
title: "Day 35: Fallback to a Human"
description: "The decision graph learns when not to decide alone. Untrustworthy inputs skip straight to manual review, and routed decisions the reviewer doubts are escalated with a note that tells the human what to check."
series: "ai-engineering"
order: 37
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "langgraph routing", "fallback", "uncertainty review"]
readingTime: "9 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day35`](https://github.com/hakmimi/AIEngineering/tree/main/Day35). Layers touched: L2 LLM, L3 Orchestration.

## Goals

- **G1. Route schema-valid but untrustworthy inputs to a human before any tool or LLM runs.**  
  You can: show country `ZZ` and a 20-day-old VIP taking the 4-node fallback path with their own reason codes.
- **G2. Detect uncertain routed decisions from the LLM review and from the risk margin.**  
  You can: trigger `borderline_risk_new_customer` live and show `LOW_CONFIDENCE` in the reason codes.
- **G3. Keep branching logic in nodes and let edges only read state.**  
  You can: explain why computing uncertainty inside `after_llm` loses the value.
- **G4. Prove the new routes only ever add oversight.**  
  You can: show that an unavailable LLM doesn't create uncertainty and that review/decline are never touched.

## System map

The Day 34 graph is the grey middle. New today: a router at the start that can divert to `fallback`, and a branch after `llm_explain` that sends doubtful routed decisions to `uncertainty_review` before `finalize`.

> Transaction → route_input ─ normal → tools → rules → LLM review ─ confident → finalize · fallback → manual review · uncertain → uncertainty_review → manual review

<div class="ae-map" role="img" aria-label="The client posts to POST /decision. After input, route_input calls classify_input. Unknown country, extreme amount or an inconsistent profile go to the fallback node, which makes a manual_review with a specific reason code and no tools or LLM, then finalize. Normal inputs run the Day 34 path: risk and provider tools, rules, select and llm_explain. llm_explain now also computes uncertainty signals. If there are any, after_llm sends the run to uncertainty_review, which asks the LLM for a two-sentence note for the human reviewer, with a template fallback. finalize escalates uncertain routed decisions to manual_review with LOW_CONFIDENCE. The response reports graph.route and route_reason."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 466" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L3 · ROUTING.PY</text><text class="lane" x="508" y="18">L3 · DAY 34 PATH</text><text class="lane" x="752" y="18">L2 · REVIEW</text><text class="lane" x="996" y="18">L3 · OUTCOME</text><path class="edge" d="M200,178 C230,178 230,118 261,118" marker-end="url(#mka)"></path><path class="edge" d="M354,160 L354,178" marker-end="url(#mka)"></path><path class="edge" d="M444,118 C474,118 474,178 505,178" marker-end="url(#mka)"></path><path class="edge-old" d="M688,178 C718,178 718,76 749,76" marker-end="url(#mkm)"></path><path class="edge" d="M842,118 L842,137" marker-end="url(#mka)"></path><path class="edge-old" d="M842,118 L842,243" marker-end="url(#mkm)"></path><path class="edge" d="M932,76 C962,76 962,118 993,118" marker-end="url(#mka)"></path><path class="edge" d="M932,182 C962,182 962,118 993,118" marker-end="url(#mka)"></path><path class="edge" d="M444,231 C718,231 718,118 993,118" marker-end="url(#mka)"></path><path class="edge-old" d="M1086,160 L1086,178" marker-end="url(#mkm)"></path><path class="edge-back" d="M1086,280 V348 H110 V212" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="148"></rect><text class="nt t" text-anchor="middle" x="110" y="172">Client</text><text class="ns s" text-anchor="middle" x="110" y="190">POST /decision</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="76"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="108">route_input</text><text class="ns s" text-anchor="middle" x="354" y="126">classify_input()</text><text class="ns s" text-anchor="middle" x="354" y="142">normal or fallback</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="88">NEW</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="264" y="182"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="214">fallback</text><text class="ns s" text-anchor="middle" x="354" y="232">UNKNOWN_COUNTRY</text><text class="ns s" text-anchor="middle" x="354" y="248">EXTREME_AMOUNT</text><text class="ns s" text-anchor="middle" x="354" y="262">INCONSISTENT_PROFILE</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="194">NEW</text></g><g class="node-existing"><rect height="94" rx="8" width="180" x="508" y="131"></rect><text class="nt t" text-anchor="middle" x="598" y="155">tools → rules →</text><text class="nt t" text-anchor="middle" x="598" y="173">select</text><text class="ns s" text-anchor="middle" x="598" y="192">risk · providers · cost</text><text class="ns s" text-anchor="middle" x="598" y="207">tool_error on failure</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">llm_explain</text><text class="ns s" text-anchor="middle" x="842" y="85">review +</text><text class="ns s" text-anchor="middle" x="842" y="100">uncertainty_signals</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="140"></rect><text class="nt t" text-anchor="middle" x="842" y="172">uncertainty_review</text><text class="ns s" text-anchor="middle" x="842" y="191">note for the human</text><text class="ns s" text-anchor="middle" x="842" y="206">template if LLM fails</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">NEW</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="752" y="246"></rect><text class="nt t" text-anchor="middle" x="842" y="270">OpenAI</text><text class="ns s" text-anchor="middle" x="842" y="289">review + uncertainty</text><text class="ns s" text-anchor="middle" x="842" y="304">prompts</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="76"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="108">finalize</text><text class="ns s" text-anchor="middle" x="1086" y="126">AI_ESCALATION or</text><text class="ns s" text-anchor="middle" x="1086" y="142">LOW_CONFIDENCE</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="88">CHANGED</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="996" y="182"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="214">graph.route</text><text class="ns s" text-anchor="middle" x="1086" y="232">normal · fallback ·</text><text class="ns s" text-anchor="middle" x="1086" y="248">uncertain</text><text class="ns s" text-anchor="middle" x="1086" y="262">+ route_reason</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="194">NEW</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="131"></rect><text class="el" text-anchor="middle" x="230" y="142">JSON</text><rect class="elbg" height="15" rx="3" width="59" x="358" y="158"></rect><text class="el" text-anchor="start" x="360" y="169">fallback</text><rect class="elbg" height="15" rx="3" width="46" x="451" y="131"></rect><text class="el" text-anchor="middle" x="474" y="142">normal</text><rect class="elbg" height="15" rx="3" width="66" x="846" y="116"></rect><text class="el" text-anchor="start" x="848" y="128">uncertain</text><rect class="elbg" height="15" rx="3" width="66" x="930" y="80"></rect><text class="el" text-anchor="middle" x="962" y="91">confident</text><rect class="elbg" height="15" rx="3" width="110" x="663" y="157"></rect><text class="el" text-anchor="middle" x="718" y="168">no tools, no LLM</text><rect class="elbg" height="15" rx="3" width="219" x="488" y="341"></rect><text class="el" text-anchor="middle" x="598" y="352">{ decision, graph: route, trace }</text><text class="lane" style="fill:var(--ghost)" x="20" y="396">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="246" x="20" y="406"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="143" y="433">Day 36 · evaluation dataset</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="286" y="406"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="416" y="433">Day 37 · baseline vs AI evaluation</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: One path for every payment

- Every input runs tools, rules and the LLM
- An unknown country is scored with a guessed risk of 0.40
- A routed decision the LLM doubts is still routed unless it sets the escalation flag
- The human reviewer gets no note on why a case is theirs

### After this episode: Three routes, all toward safety

- `fallback`: unknown country, amount over 50,000 USD or inconsistent profile go to manual review with no tools or LLM
- `uncertain`: disagreement, confidence under 0.5 or a borderline new customer escalate with `LOW_CONFIDENCE`
- An LLM-written, grounded note tells the reviewer what to check
- `graph.route` and `route_reason` in every response; 181 tests pass

> **Why it matters:** production agents get inputs nobody planned for. Sending those to a person with a precise reason is cheaper than a wrong automatic decision, and the invariants tested today mean the new routes can only add human oversight. The evaluation set on Day 36 will measure how often that oversight is needed.

## Code walkthrough

Four snippets from `Day35`: the router, the uncertainty rules, where the signals are computed, and how `finalize` uses them.

### routing.py · the fallback route

```python
def classify_input(tx: Transaction) -> RouteChoice:
    if tx.country not in load_risk_tables()["country_risk"]:
        return RouteChoice(FALLBACK, ReasonCode.UNKNOWN_COUNTRY, f"country '{tx.country}' is not in the risk tables, so risk cannot be assessed")
    if amount_in_usd(tx) > EXTREME_AMOUNT_USD:
        return RouteChoice(FALLBACK, ReasonCode.EXTREME_AMOUNT, f"amount exceeds the automatic limit of {EXTREME_AMOUNT_USD:,} USD")
    if tx.customer_type is CustomerType.RETURNING and tx.customer_age_days < RETURNING_MIN_AGE_DAYS:
        return RouteChoice(FALLBACK, ReasonCode.INCONSISTENT_PROFILE, "a 'returning' customer with an account younger than 7 days is inconsistent")
    if tx.customer_type is CustomerType.VIP and tx.customer_age_days < VIP_MIN_AGE_DAYS:
        return RouteChoice(FALLBACK, ReasonCode.INCONSISTENT_PROFILE, "a 'vip' customer with an account younger than 180 days is inconsistent")
    return RouteChoice(NORMAL)
```

**Some inputs pass the schema and still shouldn't be decided automatically.** Missing reference data, out-of-policy size and a profile that contradicts itself. Each gets its own reason code, so the reviewer knows the problem before opening the case. Pure function, no I/O beyond the cached tables, easy to test.

### routing.py · uncertainty signals

```python
def uncertainty_signals(tx: Transaction, baseline_action: Action, risk_score: float, agrees: bool | None, confidence: float | None) -> list[str]:
    """Reasons to doubt a ROUTED decision. Empty list = not uncertain. Only routed decisions can be uncertain (others are already safe)."""
    if baseline_action is not Action.ROUTE:
        return []
    signals = []
    if agrees is False:
        signals.append("llm_disagrees")
    if confidence is not None and confidence < LOW_CONFIDENCE_BELOW:
        signals.append("llm_low_confidence")
    if tx.customer_type is CustomerType.NEW and settings.risk_review - BORDERLINE_MARGIN <= risk_score < settings.risk_review:
        signals.append("borderline_risk_new_customer")
    return signals
```

**Only a routed decision can be uncertain, because only a routed payment moves money.** Two signals come from the LLM review, one from the rules: a new customer just under the 0.45 review threshold. `agrees is False` is deliberate, so a missing review (`None`) is not a signal.

### decision_graph.py · compute in the node, read in the edge

```python
    # Uncertainty is decided here, where the review is at hand, and stored in state for the conditional edge to read.
    signals = uncertainty_signals(tx, baseline.decision.action, baseline.risk.score,
                                  review.agrees_with_baseline if review else None, review.confidence if review else None)
    return {"review": review, "llm_status": status, "notes": notes, "uncertainty": signals}
...
def after_llm(state: DecisionState) -> str:
    """Uncertain routed decisions go to the uncertainty node; everything else straight to finalize."""
    return "uncertainty_review" if state.get("uncertainty") else "finalize"
```

**The node writes the signals into state; the edge only reads them.** The first version computed this inside the edge function and the value vanished, because edges get a copy of the state. The break-it segment reproduces that.

### decision_graph.py · finalize with a new code

```python
def finalize_node(state: DecisionState) -> dict:
    review = state.get("review")
    code = ReasonCode.AI_ESCALATION
    if state.get("uncertainty"):                       # uncertainty always escalates a routed decision (toward a human)
        code = ReasonCode.LOW_CONFIDENCE
        review = LLMReview(state["uncertainty_text"], review.agrees_with_baseline if review else True,
                           review.concerns if review else [], True, review.confidence if review else 0.0)
    decision, control_notes = apply_control_rules(state["baseline"].decision, review, code)
    return {"decision": decision, "notes": control_notes}
```

**Uncertainty reuses the one escalation path the LLM already had.** `finalize` builds a review with `escalate_to_review=True` and the uncertainty note, then calls the same `apply_control_rules`. Route becomes manual review with `LOW_CONFIDENCE`; anything else is left alone.

## Run it

Run from `Day35` in PowerShell with a real key in `.env`. After each call print `$r.graph.route`, `$r.graph.route_reason`, `$r.graph.trace` and `$r.decision.reason_codes`.

**Step 1**

```powershell
python -m pytest
python -m scripts.draw_graph
```

**Expect:** 181 tests pass. `docs/graph.md` now shows `route_input` branching to `fallback` or `risk_tool`, and `llm_explain` branching to `uncertainty_review` or `finalize`.

**Step 2**

```powershell
uvicorn main:app --reload
$tx = @{transaction_id="t-1"; timestamp="2026-01-05T09:12:00Z"; amount=85.5; currency="ILS"; country="IL"
  merchant_category="groceries"; customer_type="returning"; payment_method="card"
  customer_age_days=400; prior_chargebacks=0}
$tx.country="ZZ"
$r = Invoke-RestMethod http://127.0.0.1:8000/decision -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
$r.graph; $r.decision.reason_codes; $r.usage.llm_calls
```

**Expect:** `route: fallback`, `route_reason: country 'ZZ' is not in the risk tables, so risk cannot be assessed`, trace `input, route_input, fallback, finalize`, reason `UNKNOWN_COUNTRY`, 0 LLM calls.

**Step 3**

```text
$tx.country="IL"; $tx.customer_type="vip"; $tx.customer_age_days=20
$r = Invoke-RestMethod http://127.0.0.1:8000/decision -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
$r.graph.route_reason; $r.decision.reason_codes
```

**Expect:** `a 'vip' customer with an account younger than 180 days is inconsistent` and `INCONSISTENT_PROFILE`.

**Step 4**

```text
$tx.country="BR"; $tx.merchant_category="gaming"; $tx.customer_type="new"; $tx.customer_age_days=10
$tx.amount=100; $tx.currency="USD"
$r = Invoke-RestMethod http://127.0.0.1:8000/decision -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
$r.graph; $r.decision.action; $r.decision.reason_codes; $r.decision.explanation
```

**Expect:** Risk 0.4436, just under 0.45. `route: uncertain`, `route_reason: borderline_risk_new_customer`, trace ends `llm_explain, uncertainty_review, finalize`. Action `manual_review`, first reason `LOW_CONFIDENCE`, and a two-sentence note for the reviewer. `usage` shows 2 LLM calls.

**Step 5**

```text
$tx = @{transaction_id="t-1"; timestamp="2026-01-05T09:12:00Z"; amount=85.5; currency="ILS"; country="IL"
  merchant_category="groceries"; customer_type="returning"; payment_method="card"
  customer_age_days=400; prior_chargebacks=0}
$r = Invoke-RestMethod http://127.0.0.1:8000/decision -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
$r.graph.route; $r.graph.trace.Count; $r.decision.action
```

**Expect:** `normal`, 9 nodes (Day 34's 8 plus `route_input`), `route`.

### Break it on purpose

#### 1 · An LLM outage is not uncertainty

Stop uvicorn, set `$env:OPENAI_API_KEY="sk-invalid"`, restart. The normal grocery payment still routes: `llm_status: unavailable`, no uncertainty, because a missing review is not a doubt. The borderline BR payment is still `uncertain`, since that signal comes from the rules, and the note falls back to the template: `Sent to manual review because the automatic decision is uncertain: borderline risk new customer.` Remove the variable afterwards.

#### 2 · The edge that forgot

Reproduce the bug from the README. In `llm_node`, drop `"uncertainty": signals` from the return. In `after_llm`, compute the signals yourself, write `state["uncertainty"] = signals`, and return the route. Send the borderline payment: the edge chooses `uncertainty_review`, but that node then fails with `KeyError: 'uncertainty'` and the API returns 500. The edge wrote to a copy of the state, so nothing downstream ever saw it. Put the code back.

```text
# decision_graph.py - the node computes and returns; the edge only reads
    signals = uncertainty_signals(tx, baseline.decision.action, baseline.risk.score,
                                  review.agrees_with_baseline if review else None, review.confidence if review else None)
    return {"review": review, "llm_status": status, "notes": notes, "uncertainty": signals}
...
def after_llm(state: DecisionState) -> str:
    return "uncertainty_review" if state.get("uncertainty") else "finalize"
```

> Every branch added today leads toward a human, and each one is decided by a node and recorded in state. In LangGraph, only what a node returns becomes state. Anything an edge writes is lost.

## Cheat sheet

- **Routing (in a graph)**: Choosing which path a request takes, based on the state. Here normal, fallback or uncertain.
- **Fallback route**: A path that skips automation and sends the case to a human, with a specific reason code.
- **Router node**: A node whose only job is to classify the input and write the route into state (`route_input`).
- **Uncertainty signal**: A reason to doubt a routed decision: LLM disagreement, low confidence or a borderline risk.
- **Borderline margin**: How close to a threshold counts as "too close": 0.05 below the 0.45 review threshold.
- **LOW_CONFIDENCE**: Reason code for a routed decision escalated to manual review because it was uncertain.
- **Human-in-the-loop**: A design where people make the calls the system isn't sure about.
- **Invariant**: A property that must hold for every input. Here: the final action is never more permissive than the baseline.
- **Schema-valid vs trustworthy**: An input can pass every type check and still be unusable, like a country with no risk data.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why does an unknown country go to fallback instead of using the 0.40 default risk?</summary><p>The agent has no data for that country, so any score is a guess. A human with a precise reason code is safer than a routed payment based on an invented number.</p></details>
<details><summary>The LLM is down. Does that make a routed decision uncertain?</summary><p>No. A missing review gives <code>agrees=None</code> and <code>confidence=None</code>, which are not signals. Only the borderline-risk rule can still fire.</p></details>
<details><summary>Why can't a decline become uncertain?</summary><p>Uncertainty can only escalate toward a human. A decline or manual review is already at least that safe, so <code>uncertainty_signals</code> returns an empty list for them.</p></details>
<details><summary>Why is the uncertainty computed in llm_explain rather than in after_llm?</summary><p>Conditional edges get a copy of the state, so anything they write is lost. The node returns the signals as a state update, and the edge just reads them.</p></details>
<details><summary>A fallback decision's explanation says "risk score 0.50". Was the risk assessed?</summary><p>No. Fallback skips the tools, and 0.5 is <code>UNKNOWN_RISK_SCORE</code>, a placeholder. The template prints it anyway, so a reviewer should read the reason code, not the number.</p></details>
</div>

**Next:** Day 36 – Build the Yardstick First

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
