---
title: "Day 15: Pipeline as a Graph"
description: "From a RAG pipeline whose order is hard-coded inside one function to the same pipeline as a LangGraph workflow: shared state, three nodes, and edges you can inspect. FastAPI stays the front door; the graph takes over the orchestration."
series: "ai-engineering"
order: 17
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "langgraph", "stategraph", "reducers"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day15`](https://github.com/hakmimi/AIEngineering/tree/main/Day15). Layers touched: L3 Orchestration, L4 System.

## Goals

- **G1. Understand state, node, edge and conditional edge.**  
  You can: point at each one in `graph.py` and define it in one sentence.
- **G2. Rebuild the RAG flow as a graph without rewriting the logic.**  
  You can: show that each node calls a module we already had: `get_relevant_chunks`, `validate_context`, `get_answer`.
- **G3. Use reducers so nodes add to state instead of overwriting it.**  
  You can: call `/rag/graph` and read `graph.trace` and per-node `timings` in the response.
- **G4. Keep FastAPI as the entry point and the graph as the orchestrator.**  
  You can: explain why `rag_graph_endpoint` only validates and calls `run_graph()`.

## System map

Same RAG behaviour as `/rag`, drawn as a graph. The new boxes are the graph itself: one state object and three nodes. The modules the nodes call are grey because they didn't change.

> Client → FastAPI (/rag/graph) → receive_query → retrieve_context → call_llm → Response

<div class="ae-map" role="img" aria-label="The client posts to /rag/graph. The route calls run_graph, which invokes the compiled StateGraph with a RagState. receive_query normalises the question and ends the run if it is blank. retrieve_context calls get_relevant_chunks, which embeds the query and searches FAISS. call_llm checks the context with validate_context and, if it is good enough, calls get_answer. The final state is shaped into the same response as /rag plus graph.trace and returned to the client."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 444" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · ROUTES.PY</text><text class="lane" x="508" y="18">L3 · GRAPH.PY</text><text class="lane" x="752" y="18">L3 · NODES</text><text class="lane" x="996" y="18">L1/L2 · MODULES</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,167 C230,167 230,118 261,118" marker-end="url(#mka)"></path><path class="edge" d="M444,118 C474,118 474,114 505,114" marker-end="url(#mka)"></path><path class="edge" d="M688,114 C718,114 718,68 749,68" marker-end="url(#mka)"></path><path class="edge" d="M842,103 L842,122" marker-end="url(#mka)"></path><path class="edge" d="M842,194 L842,213" marker-end="url(#mka)"></path><path class="edge" d="M932,160 C962,160 962,118 993,118" marker-end="url(#mka)"></path><path class="edge" d="M932,258 C962,258 962,218 993,218" marker-end="url(#mka)"></path><path class="edge-old" d="M1176,118 C1206,118 1206,167 1237,167" marker-end="url(#mkm)"></path><path class="edge-old" d="M1176,218 C1206,218 1206,167 1237,167" marker-end="url(#mkm)"></path><path class="edge-back" d="M1330,198 V326 H110 V200" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="136"></rect><text class="nt t" text-anchor="middle" x="110" y="160">Client</text><text class="ns s" text-anchor="middle" x="110" y="180">/docs · PowerShell</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="76"></rect><text class="nt t" text-anchor="middle" x="354" y="108">POST /rag/graph</text><text class="ns s" text-anchor="middle" x="354" y="127">SearchRequest</text><text class="ns s" text-anchor="middle" x="354" y="142">auth · rate limit</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="89">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="182"></rect><text class="nt t" text-anchor="middle" x="354" y="206">other endpoints</text><text class="ns s" text-anchor="middle" x="354" y="225">/ask · /rag · /chat</text><text class="ns s" text-anchor="middle" x="354" y="240">(unchanged)</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="72"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="104">run_graph()</text><text class="ns s" text-anchor="middle" x="598" y="123">invoke · shape response</text><text class="ns s" text-anchor="middle" x="598" y="138">+ graph.trace</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="85">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="178"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="210">RagState</text><text class="ns s" text-anchor="middle" x="598" y="229">TypedDict · trace appends</text><text class="ns s" text-anchor="middle" x="598" y="244">timings merge</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="191">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">receive_query</text><text class="ns s" text-anchor="middle" x="842" y="85">normalise · blank → END</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="125"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="157">retrieve_context</text><text class="ns s" text-anchor="middle" x="842" y="176">chunks into state</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="138">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="216"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="248">call_llm</text><text class="ns s" text-anchor="middle" x="842" y="267">gate first · fallback</text><text class="ns s" text-anchor="middle" x="842" y="282">on provider error</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="229">NEW</text></g><g class="node-existing"><rect height="79" rx="8" width="180" x="996" y="78"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="102">get_relevant_chun</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="120">ks</text><text class="ns s" text-anchor="middle" x="1086" y="140">embed · FAISS · siblings</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="996" y="180"></rect><text class="nt t" text-anchor="middle" x="1086" y="204">gate + prompt + LLM</text><text class="ns s" text-anchor="middle" x="1086" y="222">validate_context</text><text class="ns s" text-anchor="middle" x="1086" y="238">get_answer</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="136"></rect><text class="nt t" text-anchor="middle" x="1330" y="160">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="180">embeddings · answers</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="126"></rect><text class="el" text-anchor="middle" x="230" y="136">JSON</text><rect class="elbg" height="15" rx="3" width="91" x="673" y="74"></rect><text class="el" text-anchor="middle" x="718" y="85">invoke(state)</text><rect class="elbg" height="15" rx="3" width="181" x="630" y="319"></rect><text class="el" text-anchor="middle" x="720" y="330">{ results: …, graph.trace }</text><text class="lane" style="fill:var(--ghost)" x="20" y="374">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="254" x="20" y="384"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="147" y="411">Day 16 · conditional routing</text></g><g class="node-ghost"><rect height="44" rx="8" width="246" x="294" y="384"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="417" y="411">Day 17 · tools in the graph</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: The order lives in one function body

- `get_rag_answer()` calls retrieve, gate and LLM in a fixed sequence
- Adding a branch or a retry means editing that function
- Timing per step needs manual `StepTimer` calls
- Nothing outside the code can show you the flow

### After this episode: The order is data you can inspect

- `build_graph()` declares nodes and edges; `draw_mermaid()` can print them
- Each node returns a partial update to one shared `RagState`
- `trace` and `timings` fill up through reducers, so every node shows in the response
- `POST /rag/graph` returns the same fields as `/rag` plus `graph.trace`

> **Why it matters:** the next four days add branches, tools, retries and memory. In a single function each of those would be another nested `if`. In a graph each one is a node and an edge, and you can still see the whole flow.

## Code walkthrough

Four snippets from `Day15/graph.py`. Keep the diagram in `docs/graph.md` on screen while you read them.

### graph.py · the shared state

```python
class RagState(TypedDict, total=False):
    """Everything that travels between nodes. Keys are added as the workflow progresses."""
    question: str
    top_k: int
    chunks: list[dict]
    answer: str
    confidence: float
    source: str                                  # rag | no_context | fallback_error | invalid_input
    trace: Annotated[list[str], operator.add]    # reducer: each node APPENDS instead of overwriting
    timings: Annotated[dict, lambda old, new: {**(old or {}), **new}]  # reducer: merge per-node timings
```

**State is the contract between nodes.** Plain keys are overwritten by the last node that writes them. The two `Annotated` keys have reducers, so every node's entry is kept. That's what makes the trace possible.

### graph.py · a node

```python
@timed("call_llm")
def call_llm(state: RagState) -> dict:
    """The LLM is one node, not the system: it only runs when retrieval produced usable context."""
    chunks = state["chunks"]
    if not validate_context(chunks):
        return {"answer": NO_CONTEXT_ANSWER, "source": "no_context", "confidence": 0.0}
    try:
        result = get_answer(render_rag_prompt(build_context(chunks), state["question"]))
    except ExternalServiceError:
        return {"answer": LLM_DOWN_ANSWER, "source": "fallback_error", "confidence": 0.0}
    return {"answer": result["answer"], "confidence": result.get("confidence") or 0.0, "source": "rag"}
```

**A node reads state and returns only what it changed.** Nothing here is new logic. The gate, the prompt and `get_answer` come from earlier days. The node just gives them a place in the flow.

### graph.py · wiring the graph

```python
def _after_receive(state: RagState) -> str:
    """Conditional edge: an invalid question ends the run immediately (cheapest possible path)."""
    return END if state.get("source") == "invalid_input" else "retrieve_context"

def build_graph():
    graph = StateGraph(RagState)
    graph.add_node("receive_query", receive_query)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("call_llm", call_llm)
    graph.add_edge(START, "receive_query")
    graph.add_conditional_edges("receive_query", _after_receive, {"retrieve_context": "retrieve_context", END: END})
    graph.add_edge("retrieve_context", "call_llm")
    graph.add_edge("call_llm", END)
    return graph.compile()
```

**The flow is declared once, then compiled.** `add_edge` is a fixed next step. `add_conditional_edges` takes a function that reads state and returns a node name. Day 16 uses the same mechanism for real routing.

### routes.py · FastAPI stays the door

```python
@router.post("/rag/graph", dependencies=protected)
def rag_graph_endpoint(request: SearchRequest) -> dict:
    """Day 15: same behaviour as /rag, executed as a LangGraph workflow (FastAPI stays the entry point)."""
    return {"results": run_graph(request.query, request.top_k)}
```

**HTTP concerns in the route, orchestration in the graph.** The endpoint validates with `SearchRequest` and hands off. If we swapped LangGraph for something else tomorrow, this function wouldn't change.

## Run it

Run from `Day15` in PowerShell. Show the uvicorn logs: every node prints a `graph_node node=… ms=…` line.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `150 passed`, including 8 new tests in `tests/test_graph.py`.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** `Uvicorn running on http://127.0.0.1:8000`.

**Step 3**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Where is Masada?"}').results | Select-Object source, answer, graph, timings
```

**Expect:** `source: rag`, a grounded answer, trace `receive_query, retrieve_context, call_llm`, and a timing per node plus `total_ms`.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"What is the capital of France?"}').results | Select-Object source, graph
```

**Expect:** `source: no_context`. All three nodes ran, but `call_llm` stopped at the gate and made no LLM call.

**Step 5**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"   "}').results | Select-Object source, graph
```

**Expect:** `source: invalid_input`, trace only `receive_query`. Three spaces pass Pydantic's `min_length=1`, and the conditional edge ends the run.

**Step 6**

```powershell
python -c "from graph import rag_graph; print(rag_graph.get_graph().draw_mermaid())"
```

**Expect:** Mermaid text for the compiled graph, matching `docs/graph.md`.

### Break it on purpose

#### 1 · Remove a reducer

In `RagState`, change `trace: Annotated[list[str], operator.add]` to `trace: list[str]` and ask about Masada again. The trace now shows only `call_llm`: without a reducer the last writer wins. Put it back and show the full trace. That's the whole idea of reducers in one edit.

#### 2 · Retrieval fails and the graph can't cope

Stop uvicorn, run `$env:OPENAI_API_KEY="sk-invalid"`, start it again and ask about Masada. The embedding call inside `retrieve_context` raises `ExternalServiceError`. Only `call_llm` catches provider errors, so the exception leaves the graph and the app's error handler returns **503** `External AI service is unavailable` with no trace. Clean up with `Remove-Item Env:OPENAI_API_KEY`. That's the gap Day 18 closes with safe nodes and a fallback node.

> A graph makes the flow visible, but it doesn't make it safe by itself. Each node still needs to decide what happens when it fails, and today only one of them does.

## Cheat sheet

- **LangGraph**: A library for building LLM workflows as graphs of nodes that share a state object.
- **State**: The dict every node reads from and writes to. Here, `RagState`, a `TypedDict`.
- **Node**: A function `state → partial update`: one step with a clear input, output and failure mode.
- **Edge**: A fixed "run this next" link between two nodes.
- **Conditional edge**: A function that reads the state and returns the name of the next node.
- **Reducer**: A rule for combining a node's update with the existing value, like `operator.add` to append to a list.
- **START / END**: The special entry and exit points of a LangGraph graph.
- **compile()**: Turns the graph definition into a runnable object with `invoke()`.
- **Trace**: The list of node names a run visited, returned in `graph.trace`.
- **Orchestration**: Deciding which step runs next. Here it moved from a function body into the graph.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>What does a node return, and what happens to it?</summary><p>A dict with only the keys it changed. LangGraph merges it into the state: plain keys are overwritten, keys with a reducer are combined.</p></details>
<details><summary>Why do trace and timings need reducers?</summary><p>Every node writes them. Without a reducer each write replaces the last one, so only the final node would show.</p></details>
<details><summary>"What is the capital of France?" goes through all three nodes. Does it call the LLM?</summary><p>No. <code>call_llm</code> runs <code>validate_context</code> first, the scores are too low, and it returns the no-context refusal without a model call.</p></details>
<details><summary>Why is build_context a helper and not its own node?</summary><p>It has no I/O and no failure mode of its own. Nodes are for steps you want to time, branch around or retry.</p></details>
<details><summary>If the embedding API fails today, what does the client get?</summary><p>A 503 from the app's <code>AppError</code> handler, because <code>retrieve_context</code> doesn't catch the error and the graph stops. Only LLM errors are turned into a fallback answer inside a node.</p></details>
</div>

**Next:** Day 16 – Graphs That Choose

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
