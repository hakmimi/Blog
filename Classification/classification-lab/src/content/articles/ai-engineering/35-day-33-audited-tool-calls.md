---
title: "Day 33: Audited Tool Calls"
description: "The agent stops reading reference data directly: risk, provider eligibility and cost now come from validated tool calls that are logged and traced. The rules and decisions stay identical, while the LLM and the API caller see exactly which lookups a decision rests on."
series: "ai-engineering"
order: 35
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "tool layer", "pydantic i/o contracts", "tool trace"]
readingTime: "12 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day33`](https://github.com/hakmimi/AIEngineering/tree/main/Day33). Layers touched: L1 Data, L2 LLM, L3 Orchestration.

## Business problem

Any system that makes decisions about money gets asked the same question sooner or later: *why did it do that?* A payment-routing agent chooses a provider, a fee and a risk level for each transaction, and risk teams, auditors and support staff all need to see which facts that choice rested on.

If those facts are computed inline and pasted into an LLM prompt, there is no record of where a number came from, and a broken data file shows up as a crash in the middle of a customer's payment. Production decision systems separate **fact gathering** from **decision logic**: facts come from small, well-defined lookups with validated inputs and outputs, and every lookup is logged. That gives you an audit trail, lets you test each lookup alone, and lets you replace one with a real service later without touching the rules.

## Goals

- **G1. Decide which steps should be tools and define them with input and output contracts.**  
  You can: show a tool call rejected for a bad `merchant_category` before it runs.
- **G2. Route all data access through one `execute_tool()` that logs and traces every call.**  
  You can: show the six-call `tool_trace` for a routed payment and the one-call trace for a decline.
- **G3. Prove that the tool pipeline makes exactly the same decisions as the direct baseline.**  
  You can: explain the 300-transaction equivalence test and run it.
- **G4. Turn a failing tool into a manual review instead of an error.**  
  You can: break a tool and show `TOOL_ERROR` with the failure in `tool_failure`.

## System map

Decision logic from Day 31 is unchanged and grey. The new layer sits between the rules and the data: three tools behind one `execute_tool` door, a trace that records every call, and a pipeline that turns tool failures into manual reviews.

> Transaction → Tool calls (risk_lookup → provider_lookup → cost_estimate…) → Baseline rules → LLM explanation → Response + tool trace

<div class="ae-map" role="img" aria-label="The client posts to POST /decision/tools (no LLM) or POST /decision/ai. decide_with_tools runs the unchanged baseline rules with a ToolGatherer, which calls execute_tool for risk_lookup, provider_lookup and one cost_estimate per eligible provider. execute_tool validates arguments with Pydantic, runs the tool over data_loader, checks the output, logs the call and adds it to the ToolTrace. A failed tool raises ToolFailure, which becomes manual_review with TOOL_ERROR. For /decision/ai the trace is added to the review prompt, and grounding now accepts rounded numbers. The response includes the decision and the tool trace."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 474" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · MAIN.PY</text><text class="lane" x="508" y="18">L3 · PIPELINE</text><text class="lane" x="752" y="18">L1 · TOOLS.PY</text><text class="lane" x="996" y="18">DATA + LLM</text><path class="edge" d="M200,182 C230,182 230,136 261,136" marker-end="url(#mka)"></path><path class="edge-old" d="M200,182 C230,182 230,228 261,228" marker-end="url(#mkm)"></path><path class="edge" d="M444,136 C474,136 474,136 505,136" marker-end="url(#mka)"></path><path class="edge" d="M444,228 C474,228 474,136 505,136" marker-end="url(#mka)"></path><path class="edge-old" d="M598,178 L598,198" marker-end="url(#mkm)"></path><path class="edge" d="M688,235 C718,235 718,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M842,118 L842,137" marker-end="url(#mka)"></path><path class="edge" d="M932,190 C962,190 962,88 993,88" marker-end="url(#mka)"></path><path class="edge-old" d="M842,118 L842,258" marker-end="url(#mkm)"></path><path class="edge" d="M932,296 C962,296 962,182 993,182" marker-end="url(#mka)"></path><path class="edge-old" d="M1086,224 L1086,243" marker-end="url(#mkm)"></path><path class="edge-back" d="M842,330 V356 H110 V216" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="152"></rect><text class="nt t" text-anchor="middle" x="110" y="176">Client</text><text class="ns s" text-anchor="middle" x="110" y="194">PowerShell · /docs</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="102"></rect><text class="nt t" text-anchor="middle" x="354" y="134">POST /decision/tools</text><text class="ns s" text-anchor="middle" x="354" y="153">rules + trace, no LLM</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="115">NEW</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="264" y="193"></rect><text class="nt t" text-anchor="middle" x="354" y="225">POST /decision/ai</text><text class="ns s" text-anchor="middle" x="354" y="244">now returns tool_trace</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="206">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="94"></rect><text class="nt t" text-anchor="middle" x="598" y="126">decide_with_tools()</text><text class="ns s" text-anchor="middle" x="598" y="146">ToolGatherer</text><text class="ns s" text-anchor="middle" x="598" y="160">failure → TOOL_ERROR</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="108">NEW</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="508" y="200"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="232">decide_baseline()</text><text class="ns s" text-anchor="middle" x="598" y="252">same rules, gatherer param</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="214">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">execute_tool()</text><text class="ns s" text-anchor="middle" x="842" y="85">validate → run → check</text><text class="ns s" text-anchor="middle" x="842" y="100">log → trace</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="752" y="140"></rect><text class="nt t" text-anchor="middle" x="842" y="172">3 tools</text><text class="ns s" text-anchor="middle" x="842" y="191">risk_lookup ·</text><text class="ns s" text-anchor="middle" x="842" y="206">provider_lookup</text><text class="ns s" text-anchor="middle" x="842" y="221">cost_estimate</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="261"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="293">ToolTrace</text><text class="ns s" text-anchor="middle" x="842" y="312">tool · args · result · ms</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="274">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="996" y="57"></rect><text class="nt t" text-anchor="middle" x="1086" y="81">data_loader</text><text class="ns s" text-anchor="middle" x="1086" y="100">providers · risk tables</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="140"></rect><text class="nt t" text-anchor="middle" x="1086" y="172">LLM review</text><text class="ns s" text-anchor="middle" x="1086" y="191">prompt + "Tool results"</text><text class="ns s" text-anchor="middle" x="1086" y="206">grounding allows rounding</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="153">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="996" y="246"></rect><text class="nt t" text-anchor="middle" x="1086" y="270">OpenAI</text><text class="ns s" text-anchor="middle" x="1086" y="289">gpt-4.1-mini</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="142"></rect><text class="el" text-anchor="middle" x="230" y="153">JSON</text><rect class="elbg" height="15" rx="3" width="59" x="689" y="138"></rect><text class="el" text-anchor="middle" x="718" y="150">gatherer</text><rect class="elbg" height="15" rx="3" width="85" x="920" y="222"></rect><text class="el" text-anchor="middle" x="962" y="233">for_prompt()</text><rect class="elbg" height="15" rx="3" width="162" x="395" y="349"></rect><text class="el" text-anchor="middle" x="476" y="360">{ decision, tool_trace }</text><text class="lane" style="fill:var(--ghost)" x="20" y="404">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="414"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="441">Day 34 · decision workflow in LangGraph</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="300" y="414"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="430" y="441">Day 35 · routing and fallback</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Facts hidden in a prompt

- `decide_baseline()` reads loaders and computes inline
- The LLM gets numbers pasted into the prompt, with no record of where they came from
- A broken data file surfaces as a crash
- Grounding rejects "92%" for 0.9235

### After this episode: Facts from traced tool calls

- `risk_lookup`, `provider_lookup`, `cost_estimate` with Pydantic inputs and output checks
- `POST /decision/tools` returns the decision plus every call's arguments, result and ms
- A tool that fails with a known error becomes `manual_review` + `TOOL_ERROR`
- Decisions identical to the baseline on 300 transactions; 138 tests pass

> **Why it matters:** an explanation you can't check is only a story. With a trace, anyone can compare the LLM's words with the lookups that actually ran, and each tool can be tested, replaced or moved to a real service without touching the rules. Day 34's graph turns these same calls into nodes.

## Design decisions

- **Same decisions, new plumbing.** The rules do not change. A 300-transaction equivalence test proves the tool-based path produces exactly the same decisions as the direct baseline, so the refactor can't hide a behaviour change.
- **One door for every call.** All lookups go through a single `execute_tool()`, which validates input, runs the tool, checks the output and records the call. Logging and tracing live in one place instead of being sprinkled across the code.
- **Failure becomes a human decision.** A tool that fails with a known error produces `manual_review` with a `TOOL_ERROR` reason, not a crash. For payments, "ask a person" is a safer default than "guess".
- **The LLM explains from the trace.** The prompt now carries the tool results and says to base the explanation on them. The cost is real (about 37% more per decision, measured), and the benefit is an explanation anyone can check against the trace.

## Code walkthrough

Four snippets from `Day33`: the tool contract, the one door every call goes through, the gatherer that swaps the data path, and the failure rule.

### tools.py · the tool contract

```python
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable[[BaseModel], dict]
    check_output: Callable[[dict], None]


TOOLS: dict[str, Tool] = {t.name: t for t in (
    Tool("risk_lookup", "Risk score and components for a customer/transaction profile", RiskLookupInput, _risk_lookup, _check_risk),
    Tool("provider_lookup", "Providers that can carry a payment, and why the others cannot", ProviderLookupInput, _provider_lookup, _check_providers),
    Tool("cost_estimate", "Fee, approval probability and score for one provider", CostEstimateInput, _cost_estimate, _check_cost),
)}
```

**A tool is a name, a description, an input model, a function and an output check.** The same shape a function-calling LLM would need, but here code calls the tools. The output checks catch garbage, like a risk of 7.0 or a provider listed as both eligible and rejected.

### tools.py · one door for every call

```python
def execute_tool(name: str, arguments: dict, trace: ToolTrace | None = None) -> ToolResult:
    """Validate the arguments, run the tool, validate the output, log and trace the call. Never raises."""
    started = time.perf_counter()
    tool = TOOLS.get(name)
    try:
        if tool is None:
            raise KeyError(f"unknown tool '{name}'")
        output = tool.fn(tool.input_model(**arguments))
        tool.check_output(output)
        result = ToolResult(True, output)
    except ValidationError as exc:
        result = ToolResult(False, error=f"invalid arguments: {exc.errors()[0]['loc'][0]}: {exc.errors()[0]['msg']}")
    except (KeyError, ValueError, DataStoreError) as exc:
        result = ToolResult(False, error=str(exc.args[0]) if isinstance(exc, KeyError) else str(exc))
    ms = (time.perf_counter() - started) * 1000
    log_event(logger, "tool_call", tool=name, args=arguments, ok=result.ok, error=result.error,
              output=summarize(result.output, 100) if result.ok else None, ms=round(ms, 2))
    if trace is not None:
        trace.add(name, arguments, result, ms)
    return result
```

**Validate, run, check, log, trace, and return a result instead of raising.** Bad arguments come back as `invalid arguments: <field>: <reason>`. Every call is logged as `tool_call` and added to the trace. Look at the highlighted `except` line: it's the setup for the break-it segment.

### tool_pipeline.py · same rules, new data path

```python
def _run(self, name: str, args: dict) -> dict:
    result = execute_tool(name, args, self.trace)
    if not result.ok:
        raise ToolFailure(name, result.error or "unknown error")
    return result.output

def risk(self, tx: Transaction) -> RiskAssessment:
    out = self._run("risk_lookup", {"country": tx.country, "merchant_category": tx.merchant_category, "customer_type": tx.customer_type,
                                    "amount": tx.amount, "currency": tx.currency, "prior_chargebacks": tx.prior_chargebacks})
    return RiskAssessment(out["risk_score"], out["components"], [ReasonCode(r) for r in out["reason_codes"]])
```

**The gatherer changes how facts are fetched, not what the rules do with them.** `ToolGatherer` overrides `risk()` and `eligible()` from `DirectGatherer`. A failed result is turned back into an exception here, so the rules never see half an answer.

### tool_pipeline.py · failure becomes a human

```python
def decide_with_tools(tx: Transaction) -> ToolDecisionResult:
    """Baseline rules over tool-fetched data. A failing tool never crashes the decision: it becomes a manual review."""
    trace = ToolTrace()
    try:
        return ToolDecisionResult(decide_baseline(tx, ToolGatherer(trace)), trace)
    except ToolFailure as failure:
        risk = RiskAssessment(UNKNOWN_RISK_SCORE, {}, [])
        decision = Decision(transaction_id=tx.transaction_id, action=Action.MANUAL_REVIEW, reason_codes=[ReasonCode.TOOL_ERROR],
                            risk_score=UNKNOWN_RISK_SCORE)
        return ToolDecisionResult(BaselineResult(decision, risk, [], {}), trace, tool_failure=str(failure.message))
```

**When a lookup fails, the agent doesn't guess. It asks a person.** Risk is assumed to be 0.5 and the action is `manual_review` with `TOOL_ERROR`. The failure message is returned in `tool_failure`, so the reviewer knows which lookup broke.

## Run it

Run from `Day33` in PowerShell. Most steps need no key; only the `/decision/ai` step calls OpenAI.

**Step 1**

```powershell
python -m pytest
```

**Expect:** 138 tests pass, including the 300-transaction equivalence test.

**Step 2**

```powershell
uvicorn main:app --reload
$tx = @{transaction_id="t-1"; timestamp="2026-01-05T09:12:00Z"; amount=85.5; currency="ILS"; country="IL"
  merchant_category="groceries"; customer_type="returning"; payment_method="card"
  customer_age_days=400; prior_chargebacks=0}
$r = Invoke-RestMethod http://127.0.0.1:8000/decision/tools -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
$r.decision; $r.tool_trace | Format-Table tool, ok, ms
```

**Expect:** The same decision as `/decision/baseline` (route to `epsilon_local_il`, fee 1.72). Six trace rows: `risk_lookup`, `provider_lookup`, then four `cost_estimate`, all `ok`, each well under a millisecond.

**Step 3**

```text
$tx.country="NG"; $tx.merchant_category="gaming"; $tx.customer_type="new"; $tx.customer_age_days=5
$tx.prior_chargebacks=2; $tx.payment_method="wallet"; $tx.currency="USD"
(Invoke-RestMethod http://127.0.0.1:8000/decision/tools -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)).tool_trace | Format-Table tool, ok
```

**Expect:** One row: `risk_lookup`. The risk rules decided (decline), so no provider tool was called.

**Step 4**

```powershell
python -c 'from tools import execute_tool; print(execute_tool(''cost_estimate'', {''provider_id'': ''alpha_pay'', ''amount'': 100, ''risk'': 0.0}))'
```

**Expect:** `ToolResult(ok=True, output={'provider_id': 'alpha_pay', 'expected_cost': 3.2, 'expected_approval_probability': 0.9291, ...})`. 2.9 % of 100 plus 0.30.

**Step 5**

```text
$r = Invoke-RestMethod http://127.0.0.1:8000/decision/ai -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
$r.llm_status; $r.decision.explanation; $r.tool_trace.Count; $r.usage
```

**Expect:** `ok`, the decline explained from the tool results, a trace count of 1 (only `risk_lookup` ran), and usage for one LLM call. The README measured about 37 % more cost per decision than Day 32 because of the trace in the prompt.

### Break it on purpose

#### 1 · Bad arguments never run

Call the risk tool with a category that doesn't exist:
`python -c 'from tools import execute_tool; print(execute_tool(''risk_lookup'', {''country'': ''IL'', ''merchant_category'': ''weapons'', ''customer_type'': ''new'', ''amount'': 1, ''currency'': ''USD''}))'`
You get `ok=False` and `invalid arguments: merchant_category: Input should be 'groceries', ...`. No exception, no half-computed result.

#### 2 · The real bug: "never raises" has a gap

`execute_tool` only catches `ValidationError`, `KeyError`, `ValueError` and `DataStoreError`. Stop uvicorn, open `data\risk_tables.json`, set `"ILS": 0` under `currency_per_usd`, restart, and send the Israeli grocery payment in ILS. `amount_in_usd` divides by zero inside `risk_lookup`, the `ZeroDivisionError` passes straight through `execute_tool` and `decide_with_tools`, and `/decision/tools` returns **500**. The tests only break tools with `ValueError`, so they never saw this. The same payment in USD still works. Any unexpected error type (a locked file on Windows, a `TypeError` from a bad JSON value) takes this path. Restore the file with `python -m scripts.generate_data 1000 42`.

```text
# tools.py - keep the promise: an unexpected error is a failed tool call, not a crash
    except (KeyError, ValueError, DataStoreError) as exc:
        result = ToolResult(False, error=str(exc.args[0]) if isinstance(exc, KeyError) else str(exc))
    except Exception as exc:
        logger.exception("tool_crashed tool=%s", name)
        result = ToolResult(False, error=f"{type(exc).__name__}: {exc}")
```

> A fallback only protects you from the failures it catches. Test failure handling with the error types that really happen, not only the one you raised in the test.

## What went wrong

The promise was "`execute_tool` never raises", and it didn't hold. The function caught only `ValidationError`, `KeyError`, `ValueError` and `DataStoreError`. Setting `"ILS": 0` in the currency table made `amount_in_usd` divide by zero, the `ZeroDivisionError` passed straight through, and `/decision/tools` returned a 500. The tests had only ever broken tools with `ValueError`, so they never saw it.

The lesson is about test design: test failure handling with the error types that actually occur (a locked file on Windows, a bad JSON value), not just the one you chose to raise. The fix is a final `except Exception` that turns any unexpected error into a failed tool call.

## Cheat sheet

- **Tool**: A function with a name, description, validated input and checked output that the agent calls to get an exact fact.
- **Input model**: A Pydantic class that validates a tool's arguments before the tool runs.
- **Output contract**: A check on the tool's result, like risk between 0 and 1, applied before anything uses it.
- **Tool trace**: The ordered list of tool calls for one decision: tool, arguments, result or error, and duration.
- **Gatherer**: The object that fetches facts for the rules. `DirectGatherer` calls functions; `ToolGatherer` calls tools.
- **Equivalence test**: A test that two implementations give the same output on many inputs. Here tools vs direct baseline on 300 payments.
- **Short circuit**: Stopping early when the answer is known. A declined payment never calls the provider tools.
- **TOOL_ERROR**: The reason code for a decision sent to a human because a lookup failed.
- **Rounding-aware grounding**: Day 33's grounding check: a number is fine if it equals a source value after rounding to the text's precision.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why compute cost with a tool instead of letting the LLM work it out?</summary><p>LLMs approximate arithmetic. A tool computes the exact fee every time, and the LLM only narrates the result.</p></details>
<details><summary>How many tool calls does a routed payment with four eligible providers make?</summary><p>Six: one <code>risk_lookup</code>, one <code>provider_lookup</code>, and one <code>cost_estimate</code> per eligible provider.</p></details>
<details><summary>What does the equivalence test protect against?</summary><p>A refactor that changes decisions. Fetching data through tools must give the same decision, rejections and candidate order as the direct baseline on 300 transactions.</p></details>
<details><summary>provider_lookup fails with a DataStoreError. What does the caller get?</summary><p>A 200 with <code>manual_review</code>, reason <code>TOOL_ERROR</code>, risk 0.5, and the error in <code>tool_failure</code>. The trace shows the failed call last.</p></details>
<details><summary>Why does the prompt now say "base your explanation on these"?</summary><p>So the explanation can be checked against the lookups that actually ran. The grounding check uses the same text, tool results included.</p></details>
</div>

**Next:** Day 34 – The Decision Graph

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
