---
title: "Day 16: Graphs That Choose"
description: "From a graph that runs the same straight line for every message to one with a router node and conditional edges: small talk, vague input, simple questions and comparisons each take their own path. Then we settle \"rules or LLM for routing?\" with 22 labelled messages instead of opinions."
series: "ai-engineering"
order: 18
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "langgraph", "router node", "conditional edges"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day16`](https://github.com/hakmimi/AIEngineering/tree/main/Day16). Layers touched: L2 LLM, L3 Orchestration.

## Goals

- **G1. Separate deciding from branching.**  
  You can: show that `route_query_node` writes the decision and `_after_route` only reads it.
- **G2. Give each kind of message its cheapest path.**  
  You can: send "hello", "ok" and a real question and read three different traces.
- **G3. Size retrieval by question type.**  
  You can: explain why simple questions get `top_k ≤ 3` and comparisons get `top_k ≥ 6` with the wide margin.
- **G4. Choose rules or an LLM for routing with data.**  
  You can: run `scripts.routing_eval` and read route and complexity accuracy for both.

## System map

The straight line from Day 15 now forks after a new router node. Three new nodes, one changed node, and a new `intent.py` that decides. The dashed box is `router.py`, whose rules we tuned today.

> Query → Router node → direct \| fallback \| rag (simple → small context, complex → wide context) → LLM → Response

<div class="ae-map" role="img" aria-label="The client posts to /rag/graph. receive_query normalises the question and passes it to the new route_query node, which calls classify in intent.py. classify uses the rules in router.py by default, or an LLM classifier when LLM_ROUTING=1, which falls back to rules on failure. The node writes route, query_type, route_reason and routed_by into state. A conditional edge sends direct messages to direct_answer and unclear ones to fallback_response, both with zero API calls, and information requests to retrieve_context, which uses top_k at most 3 for simple and at least 6 with a wide margin for complex questions, then call_llm. The answer returns to the client."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 459" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L3 · GRAPH ENTRY</text><text class="lane" x="508" y="18">L3 · INTENT.PY</text><text class="lane" x="752" y="18">L3 · BRANCHES</text><text class="lane" x="996" y="18">L2 · ANSWER</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,174 C230,174 230,122 261,122" marker-end="url(#mka)"></path><path class="edge" d="M354,152 L354,171" marker-end="url(#mka)"></path><path class="edge" d="M444,216 C474,216 474,122 505,122" marker-end="url(#mka)"></path><path class="edge" d="M688,122 C718,122 718,68 749,68" marker-end="url(#mka)"></path><path class="edge" d="M688,122 C718,122 718,167 749,167" marker-end="url(#mka)"></path><path class="edge" d="M688,122 C718,122 718,273 749,273" marker-end="url(#mka)"></path><path class="edge" d="M932,273 C962,273 962,174 993,174" marker-end="url(#mka)"></path><path class="edge-old" d="M1176,174 C1206,174 1206,174 1237,174" marker-end="url(#mkm)"></path><path class="edge-back" d="M1330,212 V341 H110 V208" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="144"></rect><text class="nt t" text-anchor="middle" x="110" y="168">Client</text><text class="ns s" text-anchor="middle" x="110" y="187">POST /rag/graph</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="264" y="91"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="115">receive_query</text><text class="ns s" text-anchor="middle" x="354" y="134">normalise · blank → END</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="174"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="206">route_query node</text><text class="ns s" text-anchor="middle" x="354" y="225">writes route · query_type</text><text class="ns s" text-anchor="middle" x="354" y="240">· reason · routed_by</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="187">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="80"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="112">classify()</text><text class="ns s" text-anchor="middle" x="598" y="130">rules by default</text><text class="ns s" text-anchor="middle" x="598" y="146">LLM when LLM_ROUTING=1</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="92">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="186"></rect><text class="nt t" text-anchor="middle" x="598" y="218">router.py rules</text><text class="ns s" text-anchor="middle" x="598" y="236">how/why no longer</text><text class="ns s" text-anchor="middle" x="598" y="252">"complex"</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="198">CHANGED</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">direct_answer</text><text class="ns s" text-anchor="middle" x="842" y="85">greetings · 0 API calls</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="125"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="157">fallback_response</text><text class="ns s" text-anchor="middle" x="842" y="176">"please rephrase"</text><text class="ns s" text-anchor="middle" x="842" y="191">0 API calls</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="138">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="231"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="263">retrieve_context</text><text class="ns s" text-anchor="middle" x="842" y="282">simple: top_k ≤ 3</text><text class="ns s" text-anchor="middle" x="842" y="297">complex: ≥ 6 + wide</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="244">CHANGED</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="996" y="144"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="168">call_llm</text><text class="ns s" text-anchor="middle" x="1086" y="187">gate · prompt · LLM</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="1240" y="136"></rect><text class="nt t" text-anchor="middle" x="1330" y="160">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="180">embed · answer</text><text class="ns s" text-anchor="middle" x="1330" y="194">(+ intent if LLM mode)</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="131"></rect><text class="el" text-anchor="middle" x="230" y="142">JSON</text><rect class="elbg" height="15" rx="3" width="46" x="695" y="78"></rect><text class="el" text-anchor="middle" x="718" y="89">direct</text><rect class="elbg" height="15" rx="3" width="59" x="689" y="127"></rect><text class="el" text-anchor="middle" x="718" y="138">fallback</text><rect class="elbg" height="15" rx="3" width="27" x="705" y="180"></rect><text class="el" text-anchor="middle" x="718" y="191">rag</text><rect class="elbg" height="15" rx="3" width="200" x="620" y="334"></rect><text class="el" text-anchor="middle" x="720" y="345">{ route, graph.query_type, … }</text><text class="lane" style="fill:var(--ghost)" x="20" y="389">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="246" x="20" y="399"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="143" y="426">Day 17 · tools in the graph</text></g><g class="node-ghost"><rect height="44" rx="8" width="230" x="286" y="399"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="401" y="426">Day 18 · retry &amp; fallback</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: One path for every message

- "hello" went through retrieval and the gate like any question
- Every question used the same `top_k`, simple or comparison
- The response said `route: graph`, which tells you nothing
- "How" and "why" questions were wrongly marked complex

### After this episode: Each message takes its cheapest path

- Greetings and vague input end in 0 API calls
- Simple questions retrieve at most 3 chunks; comparisons at least 6 with the wide margin
- The response returns `route`, `query_type`, `route_reason` and `routed_by`
- Rules route 100 % correctly on 22 labelled messages; LLM routing is opt-in

> **Why it matters:** routing is the first real decision the system makes, and every later branch hangs off it. Tools on Day 17 are just another route. Keeping the decision in state makes it visible in logs, the API response and tests.

## Code walkthrough

Four snippets from `Day16`. The first two are the heart of it: decide in a node, branch in an edge.

### graph.py · the router node

```python
@timed("route_query")
def route_query_node(state: RagState) -> dict:
    """Decide the path and remember why (state enrichment). Never raises: the LLM classifier fails safe."""
    d = classify(state["question"])
    logger.info("graph_route route=%s type=%s reason=%s by=%s", d.route, d.query_type, d.reason, d.by)
    update = {"route": d.route, "query_type": d.query_type, "route_reason": d.reason, "routed_by": d.by}
    if d.answer:
        update["answer"] = d.answer          # canned reply for direct/fallback, used by those nodes
    return update
```

**The router node writes its decision into state.** Route, type, reason and who decided all stay in state. That's why they show up in the logs, in the API response, and in tests that never run the whole graph.

### graph.py · the edge only reads

```python
def _after_route(state: RagState) -> str:
    return {DIRECT: "direct_answer", FALLBACK: "fallback_response", RAG: "retrieve_context"}[state["route"]]
...
    g.add_conditional_edges("route_query", _after_route, {
        "direct_answer": "direct_answer", "fallback_response": "fallback_response", "retrieve_context": "retrieve_context"})
```

**A conditional edge is a lookup, not a decision.** All the thinking happened in the node. The edge maps a route name to a node name. That keeps the scattered `if/else` of earlier days out of the graph.

### graph.py · retrieval sized by type

```python
@timed("retrieve_context")
def retrieve_context(state: RagState) -> dict:
    complex_query = state.get("query_type") == "complex"
    top_k = max(state["top_k"], 6) if complex_query else min(state["top_k"], 3)
    return {"chunks": get_relevant_chunks(state["question"], top_k, None, wide=complex_query)}
```

**State enrichment pays off downstream.** The router wrote `query_type`, and retrieval uses it. Comparisons get more chunks and the wide score margin from Day 13, so both sides of the comparison make it into the context.

### intent.py · two classifiers, one Decision

```python
def llm_classify(question: str) -> Decision:
    try:
        out = get_structured(render_intent_prompt(question), INTENT_SCHEMA, "intent")
    except ExternalServiceError:
        logger.warning("intent_llm_failed - using rules")
        return rule_classify(question)
    answer = {DIRECT: DIRECT_DEFAULT, FALLBACK: FALLBACK_ANSWER}.get(out["route"])
    return Decision(out["route"], out["query_type"], out["reason"], "llm", answer)

def classify(question: str) -> Decision:
    return llm_classify(question) if settings.llm_routing else rule_classify(question)
```

**Both classifiers return the same `Decision`, so the graph doesn't care who decided.** The LLM path uses a strict JSON schema with enums for `route` and `query_type`. If the call fails, it quietly uses the rules. `LLM_ROUTING` defaults to off.

## Run it

Run from `Day16` in PowerShell. Keep the uvicorn log visible: each request prints `graph_route route=… type=… reason=… by=…`.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `158 passed`, with 9 new routing tests in `tests/test_graph.py`.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** `Uvicorn running on http://127.0.0.1:8000`.

**Step 3**

```text
foreach ($q in "hello", "ok") {
  (Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
    -ContentType "application/json" -Body (@{query=$q} | ConvertTo-Json)).results |
    Select-Object route, source, answer, graph
}
```

**Expect:** "hello": `route: direct`, trace `receive_query, route_query, direct_answer`. "ok": `route: fallback`, "Could you rephrase…". Both in milliseconds.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Compare Tel Aviv and Haifa"}').results | Select-Object route, source, graph
```

**Expect:** `route: rag`, `graph.query_type: complex`, `route_reason: complex_query`, `routed_by: rule`, and an answer covering both cities.

**Step 5**

```powershell
python -m scripts.routing_eval
```

**Expect:** `rules: route_accuracy=1.0 type_accuracy_on_rag=0.929`, then the `llm:` line with its wrong cases. Results saved to `data/routing_eval.json`.

### Break it on purpose

#### 1 · A complex question the rules call simple

Send **"Why is Jerusalem holy to three religions?"**. No marker word matches, so the rules say `simple` and retrieval is capped at 3 chunks. It's the one complexity miss in the routing eval. Now run `$env:LLM_ROUTING="1"`, restart uvicorn and send it again: `routed_by: llm`, `query_type: complex`, wider retrieval, and about a second more latency. That's the trade-off in one question.

#### 2 · One word, two opinions

Still in LLM mode, send **"Jerusalem"**. The LLM routes it to `rag`; the rules send it to `fallback` because it's under `MIN_QUERY_WORDS`. Neither is clearly wrong, which is why the eval labels it and the README calls the LLM's choice "arguably fine". Finish with `Remove-Item Env:LLM_ROUTING` and restart.

> Routing decisions have a cost on both sides: rules are free and predictable but miss nuance, an LLM gets nuance but adds latency and money to every request. Measure on labelled messages, pick a default, and keep the other as an option.

## Cheat sheet

- **Router node**: A graph node that classifies the message and writes the decision into state.
- **Conditional edge**: A function that reads state and returns the next node's name. Here `_after_route`.
- **Route**: The processing path: `direct`, `rag` or `fallback`.
- **Query type**: `simple` (one fact or topic) or `complex` (comparison, several topics). It sets how much context to retrieve.
- **State enrichment**: Storing a decision and its reason in state so later nodes, logs and the response can use it.
- **Rule-based routing**: Regex and word-count checks in `router.py`. Free, deterministic, testable.
- **LLM-based routing**: A structured-output LLM call that classifies the message. Better on nuance, costs a call per request.
- **Fail safe**: When a component fails, fall back to a known-good behaviour. Here the LLM classifier falls back to rules.
- **Wide margin**: The looser score cutoff (`COMPLEX_SCORE_MARGIN`, 0.30) that keeps lower-scoring chunks for comparisons.
- **Labelled routing set**: Messages with the expected route and type, used to score routers. Here 22 in `scripts/routing_eval.py`.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why does the router node write route_reason and routed_by into state?</summary><p>So the decision is visible: it's logged, returned in the API response under <code>graph</code>, and testable without running the whole graph.</p></details>
<details><summary>"What is the capital of France?" routes to rag. Isn't that wrong?</summary><p>No. The router decides how to process a message, not whether the topic is covered. Retrieval and the score gate turn it into a <code>no_context</code> refusal.</p></details>
<details><summary>Why were how and why removed from the complex markers?</summary><p>Most how/why questions ask for one fact ("How high is Mount Hermon?"). As markers they pushed complexity accuracy down to 78.6 %; without them it rose to 92.9 %.</p></details>
<details><summary>What happens in LLM mode if the OpenAI call for classification fails?</summary><p><code>llm_classify</code> catches <code>ExternalServiceError</code>, logs <code>intent_llm_failed</code>, and returns the rules' decision. The request carries on.</p></details>
<details><summary>Why are rules the default when the LLM was more accurate on complexity?</summary><p>Rules were already 100 % on the route itself, cost nothing and add under a millisecond. The LLM adds about a second and a paid call to every request for a small gain.</p></details>
</div>

**Next:** Day 17 – Tools With Contracts

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
