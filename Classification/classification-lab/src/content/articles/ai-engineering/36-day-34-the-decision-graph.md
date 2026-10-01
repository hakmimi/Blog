---
title: "Day 34: The Decision Graph"
description: "The decision pipeline becomes an explicit LangGraph workflow: tools, rules and the LLM are named nodes around one shared state, joined by conditional edges. Decisions stay exactly the same, and every run now reports which nodes ran and how long each took."
series: "ai-engineering"
order: 36
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "langgraph", "stategraph", "reducers", "mermaid"]
readingTime: "9 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day34`](https://github.com/hakmimi/AIEngineering/tree/main/Day34). Layers touched: L3 Orchestration, L4 System.

## Goals

- **G1. Design the graph state: what the workflow must remember between steps.**  
  You can: walk through `DecisionState` and say which fields use reducers and why.
- **G2. Turn each pipeline step into a thin node that reuses the existing rules and tools.**  
  You can: show that `select` calls `select_provider` from `decision_engine`, not a copy.
- **G3. Control the flow with conditional edges, including a failure path.**  
  You can: show an 8-node route, a 5-node decline and a 6-node tool failure live.
- **G4. Make the graph inspectable.**  
  You can: regenerate `docs/graph.md` and read per-node timings from a live response.

## System map

The boxes from Days 31–33 come back as graph nodes. Grey ones reuse existing code unchanged; the new parts are the state, the nodes, the conditional edges and the new `/decision` endpoint.

> Transaction → LangGraph state → Tool nodes → Baseline node → LLM node → Finalize → Response

<div class="ae-map" role="img" aria-label="The client posts to POST /decision, which calls run_decision_graph. The graph starts at input, then risk_tool. After risk_tool a conditional edge goes to rules or, on failure, to tool_error. After rules, if the risk rules decided, it goes straight to llm_explain; otherwise to provider_tool, cost_tool and select, each able to divert to tool_error. llm_explain calls OpenAI and validates the review. Both llm_explain and tool_error lead to finalize, which applies the control rules. The response includes the decision, review, tool trace, node trace and per-node timings."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 459" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · ENTRY</text><text class="lane" x="508" y="18">L3 · RISK NODES</text><text class="lane" x="752" y="18">L3 · PROVIDER NODES</text><text class="lane" x="996" y="18">L3 · OUTCOME NODES</text><text class="lane" x="1240" y="18">REUSED</text><path class="edge" d="M200,174 C230,174 230,122 261,122" marker-end="url(#mka)"></path><path class="edge-old" d="M354,156 L354,175" marker-end="url(#mkm)"></path><path class="edge" d="M444,122 C474,122 474,122 505,122" marker-end="url(#mka)"></path><path class="edge" d="M598,156 L598,175" marker-end="url(#mka)"></path><path class="edge" d="M688,220 C718,220 718,84 749,84" marker-end="url(#mka)"></path><path class="edge" d="M842,118 L842,137" marker-end="url(#mka)"></path><path class="edge" d="M842,209 L842,228" marker-end="url(#mka)"></path><path class="edge" d="M688,220 C840,220 840,76 993,76" marker-end="url(#mka)"></path><path class="edge" d="M932,266 C962,266 962,76 993,76" marker-end="url(#mka)"></path><path class="edge" d="M932,84 C962,84 962,182 993,182" marker-end="url(#mka)"></path><path class="edge" d="M1086,118 L1086,243" marker-end="url(#mka)"></path><path class="edge-old" d="M1086,224 L1086,243" marker-end="url(#mkm)"></path><path class="edge-old" d="M1176,76 C1206,76 1206,216 1237,216" marker-end="url(#mkm)"></path><path class="edge-old" d="M932,266 C1084,266 1084,133 1237,133" marker-end="url(#mkm)"></path><path class="edge-back" d="M1086,315 V341 H110 V208" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="144"></rect><text class="nt t" text-anchor="middle" x="110" y="168">Client</text><text class="ns s" text-anchor="middle" x="110" y="187">PowerShell · /docs</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="87"></rect><text class="nt t" text-anchor="middle" x="354" y="119">POST /decision</text><text class="ns s" text-anchor="middle" x="354" y="138">run_decision_graph()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="100">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="178"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="210">DecisionState</text><text class="ns s" text-anchor="middle" x="354" y="229">TypedDict + reducers</text><text class="ns s" text-anchor="middle" x="354" y="244">notes · trace · timings</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="191">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="508" y="87"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="119">risk_tool</text><text class="ns s" text-anchor="middle" x="598" y="138">risk_lookup tool</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="100">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="178"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="210">rules</text><text class="ns s" text-anchor="middle" x="598" y="229">risk_rule_decision()</text><text class="ns s" text-anchor="middle" x="598" y="244">decline / review?</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="191">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="49"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="81">provider_tool</text><text class="ns s" text-anchor="middle" x="842" y="100">provider_lookup tool</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="62">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="172">cost_tool</text><text class="ns s" text-anchor="middle" x="842" y="191">cost_estimate per provider</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="231"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="263">select</text><text class="ns s" text-anchor="middle" x="842" y="282">select_provider()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="244">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="66">llm_explain</text><text class="ns s" text-anchor="middle" x="1086" y="85">review + validation</text><text class="ns s" text-anchor="middle" x="1086" y="100">≈ 2–3 s</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="172">tool_error</text><text class="ns s" text-anchor="middle" x="1086" y="191">manual_review · TOOL_ERROR</text><text class="ns s" text-anchor="middle" x="1086" y="206">no LLM call</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="153">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="246"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="278">finalize</text><text class="ns s" text-anchor="middle" x="1086" y="297">apply_control_rules()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="259">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="1240" y="102"></rect><text class="nt t" text-anchor="middle" x="1330" y="126">tools + rules</text><text class="ns s" text-anchor="middle" x="1330" y="146">Days 31–33, unchanged</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="186"></rect><text class="nt t" text-anchor="middle" x="1330" y="210">OpenAI</text><text class="ns s" text-anchor="middle" x="1330" y="228">gpt-4.1-mini</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="131"></rect><text class="el" text-anchor="middle" x="230" y="142">JSON</text><rect class="elbg" height="15" rx="3" width="91" x="673" y="135"></rect><text class="el" text-anchor="middle" x="718" y="146">need provider</text><rect class="elbg" height="15" rx="3" width="53" x="814" y="131"></rect><text class="el" text-anchor="middle" x="840" y="142">decided</text><rect class="elbg" height="15" rx="3" width="78" x="923" y="116"></rect><text class="el" text-anchor="middle" x="962" y="127">tool failed</text><rect class="elbg" height="15" rx="3" width="72" x="1048" y="182"></rect><text class="el" text-anchor="middle" x="1084" y="193">same rules</text><rect class="elbg" height="15" rx="3" width="251" x="472" y="334"></rect><text class="el" text-anchor="middle" x="598" y="345">{ decision, graph: trace, timings_ms }</text><text class="lane" style="fill:var(--ghost)" x="20" y="389">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="399"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="426">Day 35 · routing and fallback</text></g><g class="node-ghost"><rect height="44" rx="8" width="246" x="300" y="399"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="423" y="426">Day 36 · evaluation dataset</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: A pipeline inside functions

- `decide_ai()` runs tools, rules and the LLM in one function
- The flow is only visible by reading code
- No per-step timing
- Adding a branch means more `if` statements in the middle

### After this episode: An explicit, timed workflow

- Nine named nodes, four conditional edges, one `DecisionState`
- `POST /decision` returns the node `trace` and `timings_ms`
- `docs/graph.md` is generated from the compiled graph
- Same decisions as `decide_baseline` and `decide_ai` on 200 transactions; 154 tests pass

> **Why it matters:** once the flow is a graph, adding a branch is adding a node and an edge, not rewriting a function. Day 35 does exactly that for fallback and uncertainty, and later days hang evaluation, audit and async jobs off the same nodes. The timings also answer a real question today: the LLM is the latency.

## Code walkthrough

Four snippets from `Day34/decision_graph.py`: the state, one node and its edge, the wiring, and the timing wrapper.

### decision_graph.py · the shared state

```python
class DecisionState(TypedDict, total=False):
    transaction: Transaction
    risk: RiskAssessment
    candidates: list[Candidate]
    rejected: dict[str, str]
    baseline: BaselineResult
    review: LLMReview | None
    llm_status: str
    notes: Annotated[list[str], operator.add]
    decision: Decision
    error: dict                                        # {node, tool, message} when a tool failed
    tool_trace: ToolTrace
    trace: Annotated[list[str], operator.add]          # nodes visited, in order
    timings: Annotated[dict, lambda old, new: {**(old or {}), **new}]
```

**State is what the nodes agree on; reducers decide how updates merge.** Most fields are simply replaced by the node that writes them. `notes` and `trace` append, and `timings` merges dicts, so every node can add its own entry without overwriting the others.

### decision_graph.py · a node and its edge

```python
@timed("rules")
def rules_node(state: DecisionState) -> dict:
    """Risk rules: decline / review decisions that need no provider data."""
    early = risk_rule_decision(state["transaction"], state["risk"])
    if early is None:
        return {}
    return {"baseline": BaselineResult(early, state["risk"], [], {})}
...
def after_rules(state: DecisionState) -> str:
    return "llm_explain" if state.get("baseline") else "provider_tool"     # risk rules decided -> skip provider tools
```

**The node does the work; the edge only reads what the node wrote.** `rules` calls the same `risk_rule_decision` as the non-graph code. If it produced a baseline, `after_rules` skips the provider tools. That's the short circuit from Day 33, now visible as a branch.

### decision_graph.py · the wiring

```python
def build_graph():
    g = StateGraph(DecisionState)
    for name, fn in [("input", input_node), ("risk_tool", risk_tool), ("rules", rules_node), ("provider_tool", provider_tool),
                     ("cost_tool", cost_tool), ("select", select_node), ("llm_explain", llm_node),
                     ("tool_error", tool_error_node), ("finalize", finalize_node)]:
        g.add_node(name, fn)
    g.add_edge(START, "input")
    g.add_edge("input", "risk_tool")
    g.add_conditional_edges("risk_tool", after_risk_tool, {"rules": "rules", "tool_error": "tool_error"})
    g.add_conditional_edges("rules", after_rules, {"llm_explain": "llm_explain", "provider_tool": "provider_tool"})
    g.add_conditional_edges("provider_tool", after_provider_tool, {"cost_tool": "cost_tool", "tool_error": "tool_error"})
    g.add_conditional_edges("cost_tool", after_cost_tool, {"select": "select", "tool_error": "tool_error"})
    g.add_edge("select", "llm_explain")
    g.add_edge("llm_explain", "finalize")
    g.add_edge("tool_error", "finalize")
    g.add_edge("finalize", END)
    return g.compile()
```

**The whole workflow fits on one screen.** Read it top to bottom and you have the flowchart. Every tool node has a conditional edge to `tool_error`, and both endings meet at `finalize`, where the control rules run.

### decision_graph.py · timing every node

```python
def timed(name: str):
    def wrap(fn):
        def inner(state: DecisionState) -> dict:
            started = time.perf_counter()
            update = fn(state)
            ms = round((time.perf_counter() - started) * 1000, 2)
            log_event(logger, "graph_node", node=name, ms=ms, update_keys=sorted(update))
            return {**update, "timings": {name: ms}, "trace": [name]}
        inner.__name__ = fn.__name__
        return inner
    return wrap
```

**One decorator gives every node a timing and a place in the trace.** The wrapper adds `timings` and `trace` to whatever the node returns, and the reducers merge them. That's how the API response can list the path and the milliseconds per node.

## Run it

Run from `Day34` in PowerShell with a real key in `.env`. Print `$r.graph` after each call rather than the whole response.

**Step 1**

```powershell
python -m pytest
```

**Expect:** 154 tests pass, including the 200-transaction equivalence test and an exact-trace test for each path.

**Step 2**

```powershell
python -m scripts.draw_graph
```

**Expect:** `wrote ...\Day34\docs\graph.md`. Open it: `__start__ → input → risk_tool`, dotted conditional edges out of `risk_tool`, `rules`, `provider_tool` and `cost_tool`.

**Step 3**

```powershell
uvicorn main:app --reload
$tx = @{transaction_id="t-1"; timestamp="2026-01-05T09:12:00Z"; amount=85.5; currency="ILS"; country="IL"
  merchant_category="groceries"; customer_type="returning"; payment_method="card"
  customer_age_days=400; prior_chargebacks=0}
$r = Invoke-RestMethod http://127.0.0.1:8000/decision -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
$r.graph.trace; $r.graph.timings_ms; $r.decision.action
```

**Expect:** 8 nodes: `input, risk_tool, rules, provider_tool, cost_tool, select, llm_explain, finalize`. Every tool node under 1 ms; `llm_explain` around 2,000–3,000 ms. Action `route`.

**Step 4**

```text
$tx.country="NG"; $tx.merchant_category="gaming"; $tx.customer_type="new"; $tx.customer_age_days=5
$tx.prior_chargebacks=2; $tx.payment_method="wallet"; $tx.currency="USD"
$r = Invoke-RestMethod http://127.0.0.1:8000/decision -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
$r.graph.trace; $r.decision.action
```

**Expect:** 5 nodes: `input, risk_tool, rules, llm_explain, finalize`. The provider nodes never ran. Action `decline`.

**Step 5**

```powershell
python -m pytest tests/test_graph.py -v
```

**Expect:** 16 tests by name: routed, decline, review and no-provider paths, one failing-tool test per tool, and equivalence with `decide_ai`.

### Break it on purpose

#### 1 · A missing provider file becomes a path

Stop uvicorn, rename `data\providers.json` to `providers.bak`, start again and send the Israeli grocery payment (paste the first `$tx` again). The trace is `input, risk_tool, rules, provider_tool, tool_error, finalize`. The decision is `manual_review` with `TOOL_ERROR`, `llm_status` is `skipped`, and `notes` says `providers.json not found - run python -m scripts.generate_data`. Status 200, no LLM call. Rename the file back and restart.

#### 2 · The LLM node degrades, the graph doesn't

Stop uvicorn, run `$env:OPENAI_API_KEY="sk-invalid"`, start again and resend the grocery payment. All 8 nodes still run, `llm_status` is `unavailable`, the explanation is the template and `llm_explain` now takes a fraction of the time. One caveat carried over from Day 32: with no key at all, `get_client()` raises `ConfigurationError`, which `llm_node` doesn't catch, and `/decision` returns 500. Remove the variable with `Remove-Item Env:OPENAI_API_KEY`.

```text
# decision_graph.py - optional: treat a missing key like an outage
from errors import ConfigurationError, ExternalServiceError
...
    except (ExternalServiceError, ConfigurationError):
        return {"review": None, "llm_status": "unavailable", "notes": ["LLM unavailable - deterministic explanation used"]}
```

> In a graph, failure handling is part of the design you can see: a node, an edge, and a trace that shows which path a request took. The one failure that isn't on the diagram, a missing key, is the one that still crashes.

## Cheat sheet

- **LangGraph**: A library for building workflows as graphs of Python functions that share a state.
- **StateGraph**: The LangGraph builder: you add nodes and edges, then `compile()` it into something you can `invoke()`.
- **State**: The shared dictionary that flows through the graph. Here `DecisionState`, a `TypedDict`.
- **Node**: A function that takes the state and returns a partial update.
- **Conditional edge**: A function that reads the state and returns the name of the next node.
- **Reducer**: The rule for merging a node's update into a state field, like `operator.add` to append to a list.
- **START / END**: LangGraph's built-in entry and exit points of the graph.
- **Node trace**: The ordered list of node names a run visited, returned as `graph.trace`.
- **Mermaid**: A text format for diagrams. `draw_mermaid()` generates it from the compiled graph, so the picture can't go stale.
- **Thin adapter**: A node that only moves data between the state and existing code, with no business logic of its own.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why are notes, trace and timings annotated with reducers but decision is not?</summary><p>Several nodes add to notes, trace and timings, so updates must be merged. Only <code>finalize</code> writes <code>decision</code>, so a plain replace is right.</p></details>
<details><summary>Why split decide_baseline into risk_rule_decision and select_provider?</summary><p>So the graph's <code>rules</code> and <code>select</code> nodes call the same rules as the non-graph code. One definition of each rule, and the equivalence test can compare them.</p></details>
<details><summary>A payment is declined by the risk rules. Which nodes run?</summary><p><code>input</code>, <code>risk_tool</code>, <code>rules</code>, <code>llm_explain</code>, <code>finalize</code>. The provider nodes are skipped by <code>after_rules</code>.</p></details>
<details><summary>Why does tool_error go straight to finalize instead of llm_explain?</summary><p>The agent doesn't have enough facts to explain a decision, so there's nothing for the LLM to review. It skips the call, saves cost and marks <code>llm_status: skipped</code>.</p></details>
<details><summary>What did the per-node timings reveal?</summary><p>Every tool node runs in under a millisecond; the LLM node takes 2–3 seconds. The LLM is the latency, which is what Day 39's fast path will address.</p></details>
</div>

**Next:** Day 35 – Fallback to a Human

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
