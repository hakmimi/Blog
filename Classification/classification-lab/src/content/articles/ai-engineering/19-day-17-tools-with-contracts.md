---
title: "Day 17: Tools With Contracts"
description: "From a graph that can only retrieve and answer to one with a tool branch: select a tool, run it, and let the LLM phrase only the validated result. Every tool now has a contract for what may go in, what may come out, and how it fails."
series: "ai-engineering"
order: 19
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "langgraph", "tool contracts", "pydantic"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day17`](https://github.com/hakmimi/AIEngineering/tree/main/Day17). Layers touched: L2 LLM, L3 Orchestration.

## Goals

- **G1. Define a tool contract: input schema, output check, error behaviour.**  
  You can: read one `Tool(...)` line in `TOOLS` and name its four parts.
- **G2. Add a tool branch to the graph.**  
  You can: send `12*(3+4)` and read the trace `select_tool → run_tool → tool_answer`.
- **G3. Decide who picks the tool: rules first, LLM second.**  
  You can: show `decided_by: rule` for arithmetic and `decided_by: llm` for a weighted score in LLM mode.
- **G4. Validate tool output before the LLM sees it.**  
  You can: explain what `check_output` blocks and show a tool error reaching the user politely.

## System map

The router from Day 16 gets a fourth route: `tool`. Three new nodes form the branch, and `tools.py` gains output contracts. The RAG path is grey because it didn't change.

> Query → Router → tool → select_tool → run_tool → tool_answer → Response (or rag → retrieve_context → call_llm)

<div class="ae-map" role="img" aria-label="The client posts to /rag/graph. receive_query and route_query run first; classify in intent.py now returns a tool route for obvious arithmetic or list-topics requests, and the LLM classifier can choose it too. select_tool picks the tool with rule_decision, or llm_decision if no rule matches. search_docs or none continue on the existing retrieval path. Other tools go to run_tool, which calls execute_tool in tools.py: Pydantic validates the input, the function runs, and check_output validates the output. tool_answer asks the LLM to phrase only the tool result, or returns the raw result if the LLM is down. The answer returns to the client with a tool object."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 368" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L3 · ROUTING</text><text class="lane" x="508" y="18">L3 · SELECT</text><text class="lane" x="752" y="18">L1 · TOOLS.PY</text><text class="lane" x="996" y="18">L2 · ANSWER</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,129 C230,129 230,76 261,76" marker-end="url(#mka)"></path><path class="edge-old" d="M354,106 L354,126" marker-end="url(#mkm)"></path><path class="edge" d="M444,170 C474,170 474,80 505,80" marker-end="url(#mka)"></path><path class="edge-old" d="M444,170 C474,170 474,182 505,182" marker-end="url(#mkm)"></path><path class="edge" d="M598,122 L598,141" marker-end="url(#mka)"></path><path class="edge" d="M688,80 C718,80 718,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M842,118 L842,137" marker-end="url(#mka)"></path><path class="edge" d="M932,76 C962,76 962,129 993,129" marker-end="url(#mka)"></path><path class="edge" d="M1176,129 C1206,129 1206,129 1237,129" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,167 V250 H110 V162" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="98"></rect><text class="nt t" text-anchor="middle" x="110" y="122">Client</text><text class="ns s" text-anchor="middle" x="110" y="142">POST /rag/graph</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="264" y="46"></rect><text class="nt t" text-anchor="middle" x="354" y="70">receive + route_query</text><text class="ns s" text-anchor="middle" x="354" y="88">Days 15–16 nodes</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="128"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="160">classify()</text><text class="ns s" text-anchor="middle" x="354" y="180">new route: tool</text><text class="ns s" text-anchor="middle" x="354" y="194">rules or LLM</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="142">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="38"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="70">select_tool</text><text class="ns s" text-anchor="middle" x="598" y="89">rule_decision →</text><text class="ns s" text-anchor="middle" x="598" y="104">llm_decision</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="51">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="508" y="144"></rect><text class="nt t" text-anchor="middle" x="598" y="168">retrieve → call_llm</text><text class="ns s" text-anchor="middle" x="598" y="187">RAG path (unchanged)</text><text class="ns s" text-anchor="middle" x="598" y="202">also for search_docs</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">run_tool</text><text class="ns s" text-anchor="middle" x="842" y="85">execute_tool()</text><text class="ns s" text-anchor="middle" x="842" y="100">never raises (in theory)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="140"></rect><text class="nt t" text-anchor="middle" x="842" y="172">tool contracts</text><text class="ns s" text-anchor="middle" x="842" y="191">input model · fn</text><text class="ns s" text-anchor="middle" x="842" y="206">· check_output</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="87"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="119">tool_answer</text><text class="ns s" text-anchor="middle" x="1086" y="138">LLM phrases ONLY</text><text class="ns s" text-anchor="middle" x="1086" y="153">the tool result</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="100">NEW</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="1240" y="91"></rect><text class="nt t" text-anchor="middle" x="1330" y="115">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="134">phrase result</text><text class="ns s" text-anchor="middle" x="1330" y="149">(+ tool choice in LLM mode)</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="86"></rect><text class="el" text-anchor="middle" x="230" y="96">JSON</text><rect class="elbg" height="15" rx="3" width="34" x="458" y="108"></rect><text class="el" text-anchor="middle" x="474" y="119">tool</text><rect class="elbg" height="15" rx="3" width="27" x="461" y="159"></rect><text class="el" text-anchor="middle" x="474" y="170">rag</text><rect class="elbg" height="15" rx="3" width="78" x="602" y="120"></rect><text class="el" text-anchor="start" x="604" y="132">search_docs</text><rect class="elbg" height="15" rx="3" width="130" x="898" y="86"></rect><text class="el" text-anchor="middle" x="962" y="96">{ok, output, error}</text><rect class="elbg" height="15" rx="3" width="142" x="649" y="243"></rect><text class="el" text-anchor="middle" x="720" y="254">{ answer, tool: {…} }</text><text class="lane" style="fill:var(--ghost)" x="20" y="298">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="230" x="20" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="135" y="335">Day 18 · retry &amp; fallback</text></g><g class="node-ghost"><rect height="44" rx="8" width="254" x="270" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="397" y="335">Day 19 · memory in the graph</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Tools lived outside the graph

- The graph could only retrieve and answer; `12*(3+4)` went to RAG and was refused
- Tools ran only through `/ask/tools` and `/ask`, outside the workflow
- Tool inputs were validated, but outputs went straight to the LLM
- No tool for weighted scores

### After this episode: A controlled tool branch

- `route: tool` → `select_tool → run_tool → tool_answer` inside the graph
- Rules pick obvious tools for free; the LLM picks from an enum of registered tools
- Every tool has `check_output`: a garbage result becomes an error before the LLM sees it
- New `calculate_score` tool; the response includes a `tool` object

> **Why it matters:** an agent is only as safe as the tools it can call. Putting tools inside the graph, behind contracts and a logged selection step, is what separates "the model can do things" from "the model can do the things we allow, the way we allow them".

## Code walkthrough

Four snippets from `Day17`. Start with the contract, end with the graph wiring.

### tools.py · the contract

```python
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable[[BaseModel], object]
    check_output: Callable[[object], None] = lambda output: None   # raises ValueError if the output is unusable
...
TOOLS: dict[str, Tool] = {t.name: t for t in (
    Tool("search_docs", "Search the knowledge base for facts", SearchDocsInput, _search_docs, _check_hits),
    Tool("calculate", "Evaluate an arithmetic expression", CalculateInput, _calculate, _check_number),
    Tool("calculate_score", "Weighted score of numbers", CalculateScoreInput, _calculate_score, _check_number),
    Tool("list_topics", "List topics, optionally for one category", ListTopicsInput, _list_topics, _check_topics),
)}
```

**A tool is data: name, input schema, function, output check.** Tools live in `tools.py`, outside the graph. The graph only calls `execute_tool`, so every tool is testable without LangGraph.

### tools.py · validate, run, check

```python
def execute_tool(name: str, arguments: dict) -> ToolResult:
    """Validate arguments, run the tool, log the call. Never raises."""
    started = time.perf_counter()
    tool = TOOLS.get(name)
    try:
        if tool is None:
            raise KeyError(f"unknown tool '{name}'")
        output = tool.fn(tool.input_model(**arguments))
        tool.check_output(output)
        result = ToolResult(True, output)
    except ValidationError as exc:
        result = ToolResult(False, error=f"invalid arguments: {exc.errors()[0]['msg']}")
    except (KeyError, ValueError) as exc:
        result = ToolResult(False, error=str(exc).strip("'\""))
```

**Errors come back as data, not exceptions.** Bad input, unknown tool, a domain error like `1/0`: all become `ToolResult(ok=False, error=…)`. Remember the highlighted `except` line. It only lists two exception types.

### graph.py · select and run

```python
@timed("select_tool")
def select_tool(state: RagState) -> dict:
    """Who picks the tool? Rules first (free, exact); the LLM only for what the rules can't recognise."""
    decision = rule_decision(state["question"]) or llm_decision(state["question"])
    ...

def _after_select(state: RagState) -> str:
    """search_docs / none = the retrieval path we already have; every other tool is executed."""
    return "retrieve_context" if state["tool_name"] in ("search_docs", "none") else "run_tool"
```

**Rules first, LLM second, and search goes back to the path we already trust.** `llm_decision` uses a JSON schema whose `tool` field is an enum of registered tools plus `none`. If that call fails it defaults to `search_docs`.

### graph.py · the LLM only phrases

```python
@timed("tool_answer")
def tool_answer(state: RagState) -> dict:
    result = state["tool_result"]
    shown = str(result["output"]) if result["ok"] else f"ERROR: {result['error']}"
    try:
        text = get_answer(render_tool_answer_prompt(state["tool_name"], shown, state["question"]))
        answer, confidence = text["answer"], text.get("confidence") or 0.0
    except ExternalServiceError:
        answer, confidence = (shown if result["ok"] else LLM_DOWN_ANSWER), 0.0
    return {"answer": answer, "confidence": confidence, "source": "tool" if result["ok"] else "tool_error"}
```

**Reasoning and execution stay separate.** The prompt says "using ONLY the tool result". If the LLM is down, the raw number is still a useful answer, so we return it.

## Run it

Run from `Day17` in PowerShell. Every tool call logs `tool_call name=… args=… ok=… error=… ms=…` in the uvicorn terminal.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `177 passed`, with 19 new tests in `tests/test_graph_tools.py`.

**Step 2**

```powershell
python -c "from tools import execute_tool; print(execute_tool('calculate_score', {'values': [80, 90, 100], 'weights': [1, 1]}))"
```

**Expect:** `ToolResult(ok=False, output=None, error='values and weights must have the same length')`. The contract, with no server and no LLM.

**Step 3**

```powershell
uvicorn main:app --reload
```

**Expect:** `Uvicorn running on http://127.0.0.1:8000`.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"12*(3+4)"}').results | Select-Object route, source, answer, tool, graph
```

**Expect:** `route: tool`, `tool.name: calculate`, `decided_by: rule`, `output: 84.0`, answer "12\*(3+4) equals 84."; trace ends `select_tool, run_tool, tool_answer`.

**Step 5**

```text
foreach ($q in "List the history topics", "10/0") {
  (Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
    -ContentType "application/json" -Body (@{query=$q} | ConvertTo-Json)).results |
    Select-Object source, answer, tool
}
```

**Expect:** Topics: `source: tool`, output Akko, Archaeology, Caesarea, Masada. Division: `source: tool_error`, `error: division by zero`, and a polite answer.

**Step 6**

```powershell
$env:LLM_ROUTING="1"; uvicorn main:app --reload
# second terminal:
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"weighted score of 80, 90, 100 with weights 1, 1, 2"}').results.tool
```

**Expect:** `name: calculate_score`, `decided_by: llm`, `output: 92.5`. Stop the server and run `Remove-Item Env:LLM_ROUTING`.

### Break it on purpose

#### 1 · A tool error is not a crash

The `10/0` call above is the designed failure: `safe_eval` turns `ZeroDivisionError` into `ValueError("division by zero")`, `execute_tool` returns `ok=False`, and the LLM is told `ERROR: division by zero`. Status 200, honest answer. That's the contract working.

#### 2 · The real bug: a number too big for a float

Send \*\*`10^100*10^100*10^100*10^100`**. The rules route it to `calculate`, the exponent cap allows each `10^100`, and Python multiplies the integers fine. Then `safe_eval` does `float(result)`, which raises**OverflowError**. `execute_tool` only catches `ValidationError`, `KeyError` and `ValueError`, so the exception escapes the "never raises" function, leaves the graph, and the client gets**500\*\* `Internal server error`. `(10.0^100)^4` does the same through float power. The same bug hits `/ask` and `/ask/tools`.

```text
# tools.py, safe_eval
    try:
        result = ev(ast.parse(cleaned.strip(), mode="eval"))
        return round(float(result), 10)
    except ZeroDivisionError as exc:
        raise ValueError("division by zero") from exc
    except OverflowError as exc:
        raise ValueError("result too large") from exc
    except SyntaxError as exc:
        raise ValueError("could not parse expression") from exc
```

> A contract is a promise, and promises need tests at the edges. The calculator guarded exponents and division, but not the size of the result. Day 18 adds a second line of defence: a node boundary that catches whatever a tool forgot to.

## Cheat sheet

- **Tool**: A plain Python function the system can run on the model's behalf, with a name and a description.
- **Tool contract**: Input schema, output schema and error behaviour: what may go in, what may come out, how it fails.
- **Input validation**: The Pydantic model checks arguments before the tool runs, like `values` having 1 to 20 numbers.
- **Output validation**: `check_output` rejects unusable results, like a non-finite number or an empty topic list, before the LLM sees them.
- **ToolResult**: `{ok, output, error}`. Tools report failure as data instead of raising.
- **Tool selection**: Deciding which tool to call. Here rules first, then an LLM restricted to an enum of registered tools.
- **Reasoning vs execution**: The LLM chooses and phrases; deterministic Python code executes.
- **Weighted score**: `sum(value × weight) / sum(weight)`, the new `calculate_score` tool.
- **safe_eval**: A calculator that walks the Python AST and allows only numbers and arithmetic operators, never names or calls.
- **OverflowError**: Raised when a number is too large for a float. Not a subclass of `ValueError`, which is why it slipped through today.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why does the LLM never execute a tool directly?</summary><p>Execution is deterministic Python in <code>tools.py</code>, behind validation. The LLM only picks a tool from an enum and later phrases the result, so it can't run anything we didn't register.</p></details>
<details><summary>What does check_output add on top of the Pydantic input model?</summary><p>It validates what the tool returned: a finite number, a non-empty list of topic strings, well-formed search hits. A broken result becomes <code>ok=False</code> before the LLM sees it.</p></details>
<details><summary>The LLM selects search_docs. What runs next?</summary><p><code>_after_select</code> sends it to <code>retrieve_context</code> and <code>call_llm</code>, the existing RAG path. No duplicate search code in the tool branch.</p></details>
<details><summary>In default rules mode, what happens to "What is 15% of 240?"</summary><p>No rule recognises it, so it routes to RAG, which refuses. It only works with <code>LLM_ROUTING=1</code>, where the LLM picks <code>calculate</code> and builds <code>0.15*240</code>.</p></details>
<details><summary>Why does 10/0 return 200 but a huge product returns 500?</summary><p>Division by zero is converted to <code>ValueError</code>, which <code>execute_tool</code> catches. <code>OverflowError</code> from <code>float()</code> isn't a <code>ValueError</code>, so it escapes the tool, the node and the graph.</p></details>
</div>

**Next:** Day 18 – Retry, Then Fall Back

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
