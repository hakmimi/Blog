---
title: "Day 21: Package the Milestone"
description: "From six days of features stacked on top of each other to one milestone you can explain, prove and defend. No new features today: a clean graph module, a diagram generated from the running code, a live end-to-end smoke test and an architecture write-up with the evidence behind every trade-off."
series: "ai-engineering"
order: 23
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "langgraph", "mermaid", "e2e smoke", "docs"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day21`](https://github.com/hakmimi/AIEngineering/tree/main/Day21). Layers touched: L3 Orchestration, L4 System.

## Goals

- **G1. Clean the Week 3 code so one file describes the whole workflow.**  
  You can: open `graph.py` and walk the header diagram and its four design rules without scrolling.
- **G2. Generate the workflow diagram from the compiled graph instead of drawing it by hand.**  
  You can: run `python -m scripts.draw_graph` and show `docs/graph.md` rendering in Mermaid.
- **G3. Prove the whole system works through the real API, not only through mocked tests.**  
  You can: run `python -m scripts.e2e_smoke` and read out 12/12, including the 3-turn memory scenario.
- **G4. Explain the design as trade-offs backed by numbers.**  
  You can: tell the 2-minute story and name three trade-offs with the measurement behind each.

## System map

This is the whole Week 3 system in one picture. Almost everything is grey because no runtime behaviour changed. The new boxes are the tools that prove and explain it: the smoke test, the generated diagram and the architecture doc.

> Client → /rag/graph → LangGraph (route → direct \| tool \| rag \| fallback) → memory → Response, plus: compiled graph → graph.md, e2e_smoke → real API → 12/12

<div class="ae-map" role="img" aria-label="A client and the new e2e_smoke script both call POST /rag/graph. FastAPI checks auth, rate limit and input, then runs the LangGraph workflow in graph.py, whose header was rewritten. The graph routes to direct answers, tools, retrieval plus the LLM, or a fallback node, and reads and writes SQLite memory. The retrieval and LLM path calls OpenAI. The answer returns to the client. draw_graph.py turns the compiled graph into docs/graph.md, which feeds the new ARCHITECTURE.md and the 2-minute story."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 444" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CALLERS</text><text class="lane" x="264" y="18">L4 · API</text><text class="lane" x="508" y="18">L3 · GRAPH.PY</text><text class="lane" x="752" y="18">PATHS · DAYS 15–20</text><text class="lane" x="996" y="18">EXTERNAL</text><text class="lane" x="1240" y="18">DOCS · EVIDENCE</text><path class="edge" d="M200,114 C230,114 230,167 261,167" marker-end="url(#mka)"></path><path class="edge" d="M200,208 C230,208 230,167 261,167" marker-end="url(#mka)"></path><path class="edge" d="M444,167 C474,167 474,122 505,122" marker-end="url(#mka)"></path><path class="edge" d="M598,164 L598,182" marker-end="url(#mka)"></path><path class="edge-old" d="M688,122 C718,122 718,76 749,76" marker-end="url(#mkm)"></path><path class="edge-old" d="M688,122 C718,122 718,160 749,160" marker-end="url(#mkm)"></path><path class="edge-old" d="M688,122 C718,122 718,250 749,250" marker-end="url(#mkm)"></path><path class="edge-old" d="M932,76 C962,76 962,167 993,167" marker-end="url(#mkm)"></path><path class="edge" d="M688,220 C962,220 962,68 1237,68" marker-end="url(#mka)"></path><path class="edge" d="M1330,103 L1330,122" marker-end="url(#mka)"></path><path class="edge" d="M1330,209 L1330,228" marker-end="url(#mka)"></path><path class="edge-back" d="M1086,198 V326 H110 V148" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="84"></rect><text class="nt t" text-anchor="middle" x="110" y="108">Client</text><text class="ns s" text-anchor="middle" x="110" y="126">/docs · PowerShell</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="20" y="166"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="198">e2e_smoke.py</text><text class="ns s" text-anchor="middle" x="110" y="218">12 live scenarios</text><text class="ns s" text-anchor="middle" x="110" y="232">temp SQLite memory</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="180">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="264" y="136"></rect><text class="nt t" text-anchor="middle" x="354" y="160">POST /rag/graph</text><text class="ns s" text-anchor="middle" x="354" y="180">API key · rate limit · 422</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="80"></rect><text class="nt t" text-anchor="middle" x="598" y="112">LangGraph workflow</text><text class="ns s" text-anchor="middle" x="598" y="130">header = one description</text><text class="ns s" text-anchor="middle" x="598" y="146">imports sorted, ruff clean</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="92">CHANGED</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="508" y="186"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="218">draw_graph.py</text><text class="ns s" text-anchor="middle" x="598" y="236">compiled graph → Mermaid</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="198">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="752" y="46"></rect><text class="nt t" text-anchor="middle" x="842" y="70">direct · tool · rag</text><text class="ns s" text-anchor="middle" x="842" y="89">rules first, FAISS, tools</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="752" y="129"></rect><text class="nt t" text-anchor="middle" x="842" y="153">SQLite memory</text><text class="ns s" text-anchor="middle" x="842" y="172">history + user facts</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="212"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="236">fallback_node</text><text class="ns s" text-anchor="middle" x="842" y="255">one retry layer, then</text><text class="ns s" text-anchor="middle" x="842" y="270">an honest degraded answer</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="996" y="136"></rect><text class="nt t" text-anchor="middle" x="1086" y="160">OpenAI</text><text class="ns s" text-anchor="middle" x="1086" y="180">embeddings + gpt-4.1-mini</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="1240" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="66">docs/graph.md</text><text class="ns s" text-anchor="middle" x="1330" y="85">generated, never edited</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="125"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="157">ARCHITECTURE.md</text><text class="ns s" text-anchor="middle" x="1330" y="176">flow · node table</text><text class="ns s" text-anchor="middle" x="1330" y="191">trade-offs with numbers</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="138">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="1240" y="231"></rect><text class="nt t" text-anchor="middle" x="1330" y="263">2-minute story</text><text class="ns s" text-anchor="middle" x="1330" y="282">README · gaps for Week 4</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="244">NEW</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="124"></rect><text class="el" text-anchor="middle" x="230" y="134">JSON</text><rect class="elbg" height="15" rx="3" width="72" x="194" y="171"></rect><text class="el" text-anchor="middle" x="230" y="182">TestClient</text><rect class="elbg" height="15" rx="3" width="78" x="602" y="162"></rect><text class="el" text-anchor="start" x="604" y="173">get_graph()</text><rect class="elbg" height="15" rx="3" width="53" x="936" y="127"></rect><text class="el" text-anchor="middle" x="962" y="138">Mermaid</text><rect class="elbg" height="15" rx="3" width="110" x="543" y="319"></rect><text class="el" text-anchor="middle" x="598" y="330">{ "results": … }</text><text class="lane" style="fill:var(--ghost)" x="20" y="374">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="230" x="20" y="384"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="135" y="411">Day 22 · Docker packaging</text></g><g class="node-ghost"><rect height="44" rx="8" width="246" x="270" y="384"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="393" y="411">Day 23 · request-id logging</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Six days of features, no single story

- The `graph.py` header was a stack of per-day patch notes (Day 16, 18, 19)
- The ASCII diagram in the docstring was drawn by hand and already out of date
- Proof of correctness was 222 offline tests with mocked OpenAI calls
- Days 18–20 carried a duplicated `is_retryable()` and duplicated retry settings

### After this episode: One milestone you can defend

- One header in `graph.py`: the flow plus four design rules
- `docs/graph.md` is generated from `rag_graph.get_graph()`, so it can't go stale
- `scripts/e2e_smoke.py` runs 12 live scenarios through the real API: **12/12**
- `docs/ARCHITECTURE.md` lists every trade-off next to the measurement behind it, and the README lists 8 gaps for Week 4

> **Why it matters:** a system you can't explain is a system nobody else can trust or extend. Packaging turns three weeks of experiments into something a reviewer, an interviewer or future-you can read in ten minutes, and the gap list becomes the plan for Week 4.

## Code walkthrough

Four snippets from `Day21`. This episode is about structure and proof, so the code is short.

### graph.py · the single description

```python
"""The assistant as a LangGraph workflow (Week 3 result).
...
Design rules
* Nodes are plain functions `state -> partial update`; helpers (retrieval, LLM, tools, memory) live in
  their own modules so they can be tested without LangGraph.
* Decision and branching are separate: `route_query` *writes* route/query_type/reason to state, the
  conditional edges only *read* it.
* Failure handling is uniform: `safe()` turns an exception into `state["error"]`, `or_fallback()` edges
  send the run to `fallback_node`. Memory is an enhancement and never fails a request.
* `trace` (append) and `timings` (merge) use reducers so every node adds information.
```

**The header says what the system is, not how it got here.** Before today this docstring was three layers of Day 16, 18 and 19 notes. Four design rules are easier to remember and easier to check against the code.

### scripts/draw_graph.py · diagram from code

````python
from graph import rag_graph
from config import settings

mermaid = rag_graph.get_graph().draw_mermaid()
out = settings.base_dir / "docs" / "graph.md"
out.write_text(
    "# Workflow graph (generated - do not edit; run `python -m scripts.draw_graph`)\n\n"
    "```mermaid\n" + mermaid + "\n```\n", encoding="utf8")
````

**A diagram generated from the compiled graph can't lie.** LangGraph already knows every node and edge. Dotted arrows in the output are conditional edges, solid ones are fixed. Add a node tomorrow, rerun one command, and the doc is right again.

### scripts/e2e_smoke.py · real API, throwaway memory

```python
memory_module.memory = memory_module.SqliteMemoryStore(Path(tempfile.mkdtemp()) / "smoke.db")   # never touch data/memory.db
import routes  # noqa: E402
...
client = TestClient(app)


def post(query: str, session: str | None = None, path: str = "/rag/graph") -> dict:
    body = {"query": query, **({"session_id": session} if session else {})}
    resp = client.post(path, json=body)
    assert resp.status_code == 200, (query, resp.status_code, resp.text)
    return resp.json()["results"]
```

**Live test, real services, but never your real data.** The memory store is swapped for a temp SQLite file before the routes are imported. OpenAI and FAISS are real; your `data/memory.db` is never touched.

### scripts/e2e_smoke.py · scenarios as data

```python
SCENARIOS = [
    ("smalltalk costs nothing",       lambda: post("hello"),                       lambda r: r["source"] == "direct"),
    ("out of domain -> refusal",      lambda: post("What is the capital of France?"), lambda r: r["source"] == "no_context"),
    ("calculator tool",               lambda: post("12*(3+4)"),                    lambda r: r["tool"]["output"] == 84.0),
    ...
    ("memory: follow-up resolves 'it'", lambda: post("How do visitors reach it?", "smoke"),
     lambda r: "Masada" in r["session"]["standalone_question"] and "cable car" in r["answer"].lower()),
    ...
]
```

**Each scenario checks behaviour, not exact wording.** Live model text changes between runs, so the checks look at `source`, the tool output and key words. The memory scenario checks the rewritten question, which is the part memory is responsible for.

## Run it

Run from `Day21` in PowerShell with the venv active. The smoke test makes real OpenAI calls, so it costs a few cents.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `222 passed`. Offline, no key needed.

**Step 2**

```text
ruff check --select F,E9,E7 .
```

**Expect:** `All checks passed!` The cleanup removed every unused import.

**Step 3**

```powershell
python -m scripts.draw_graph
code docs/graph.md
```

**Expect:** `wrote ...docs\graph.md (N lines)`. Open the Mermaid preview and trace one path: `route_query` → `retrieve_context` → `call_llm` → `finish`.

**Step 4**

```powershell
python -m scripts.e2e_smoke
```

**Expect:** Twelve `OK` lines, then `12/12 scenarios passed`. Exit code 0.

**Step 5**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on `http://127.0.0.1:8000`. Leave it running for the next step.

**Step 6**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Where is Masada?"}' | ConvertTo-Json -Depth 6
```

**Expect:** `source: rag`, an answer mentioning the Dead Sea, and `graph.trace`: `receive_query`, `route_query`, `retrieve_context`, `call_llm`. Match it against the diagram.

### Break it on purpose

#### 1 · Run the smoke test with no key

Set `$env:OPENAI_API_KEY=""` and rerun `python -m scripts.e2e_smoke`. `load_dotenv` doesn't override a variable that already exists, so the app sees an empty key and `get_client()` raises `ConfigurationError`. `safe()` catches it inside the graph. Smalltalk, clarify, the tool outputs and both validation cases still pass; the RAG and memory scenarios print `FAIL`, and the script exits with code 1. Nothing crashes. Remove the variable afterwards.

```powershell
Remove-Item Env:OPENAI_API_KEY
```

#### 2 · Make the diagram disagree with the code

Add one line to the old hand-drawn docstring, for example a fake `cache` node. Nothing complains, because a comment can say anything. Then rerun `draw_graph`: `docs/graph.md` still shows only the real nodes. That's the whole argument for generating diagrams.

> Passing unit tests and a working system aren't the same claim. Today adds the missing proof: one live end-to-end run, a diagram that comes from the code, and a written list of what's still weak. That list is the plan for Days 22–28.

## Cheat sheet

- **Milestone packaging**: Stopping feature work to clean, document and verify what exists so someone else can understand and run it.
- **Mermaid**: A text format for diagrams that GitHub and most editors render as a flowchart.
- **Generated documentation**: Docs produced from the code itself, like `get_graph().draw_mermaid()`, so they can't drift from reality.
- **Conditional edge**: A graph edge chosen at runtime by a function that reads state. Shown as a dotted arrow in `graph.md`.
- **End-to-end smoke test**: A small set of live requests through the real API that checks the main paths work together.
- **TestClient**: FastAPI's in-process HTTP client. It runs the real app without starting a server.
- **ruff**: A fast Python linter. `--select F,E9,E7` limits it to real errors like unused imports and syntax problems.
- **Trade-off**: A design choice written as benefit plus cost, backed by a measurement.
- **Known gaps**: An explicit list of what the system doesn't handle yet. It turns weaknesses into a plan.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why generate <code>docs/graph.md</code> instead of drawing the diagram by hand?</summary><p>The generated version comes from <code>rag_graph.get_graph()</code>, the same object that runs requests. A hand-drawn diagram is a comment, and comments go stale without anyone noticing.</p></details>
<details><summary>Why does <code>e2e_smoke.py</code> replace <code>memory_module.memory</code> before importing <code>routes</code>?</summary><p>So every module that grabs the store at import time gets the temp SQLite file. The live test then never reads or writes your real <code>data/memory.db</code>.</p></details>
<details><summary>The smoke checks look for "Dead Sea" or <code>source == "rag"</code> instead of exact answers. Why?</summary><p>Live model text varies between runs. Checking behaviour (route, source, tool output, key facts) keeps the test stable while still catching real breakage.</p></details>
<details><summary>222 tests passed on Day 20. What did the smoke test prove that they didn't?</summary><p>That the real pieces work together: real OpenAI calls, the real FAISS index, real SQLite memory and the real HTTP layer. The unit tests mock most of those.</p></details>
<details><summary>Name one trade-off from <code>ARCHITECTURE.md</code> and its cost.</summary><p>For example, refusing before the LLM when retrieval is weak gave 0 % hallucination on 12 trap cases, but the threshold needs recalibration whenever the embeddings change.</p></details>
</div>

**Next:** Day 22 – Ship It in Docker

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
