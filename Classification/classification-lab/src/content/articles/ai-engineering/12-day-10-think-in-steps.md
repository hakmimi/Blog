---
title: "Day 10: Think in Steps"
description: "From a single prompt that has to search, choose facts and write an answer all at once, to a pipeline of small steps: analyze, retrieve, extract, compose. Each step has one prompt, one JSON schema and a logged output, so you can see and fix exactly where an answer went wrong."
series: "ai-engineering"
order: 12
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "multi-step rag", "structured outputs", "trace"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day10`](https://github.com/hakmimi/AIEngineering/tree/main/Day10). Layers touched: L2 LLM, L3 Orchestration.

## Goals

- **G1. Break one RAG call into sequential steps that share a state object.**  
  You can: draw `analyze → retrieve → extract → compose` and say what each step writes to `PipelineState`.
- **G2. Give each LLM step its own prompt and JSON schema.**  
  You can: show `ANALYZE_SCHEMA` and `EXTRACT_SCHEMA` and explain why `get_structured` raises on bad JSON.
- **G3. Make intermediate outputs visible.**  
  You can: call `/rag/multistep` and read `pipeline.search_query`, `intent`, `facts` and `trace` from the response.
- **G4. Judge the trade-off between one call and three.**  
  You can: compare timings of `/rag` and `/rag/multistep` on the same question and say when each is worth it.

## System map

A second path appears next to the Day 9 RAG path. The router and retrieval are shared; the new part is a chain of three LLM steps with retrieval in the middle.

> Query → Router → analyze (LLM) → retrieve → extract facts (LLM) → compose answer (LLM) → Response + trace

<div class="ae-map" role="img" aria-label="The client calls /rag or the new /rag/multistep. The rule router still short-circuits greetings. run_pipeline creates a PipelineState and runs four steps in order: analyze rewrites the question and classifies intent with an LLM call, retrieve uses Day 9 retrieval with a retry on the raw question, extract asks the LLM for relevant sentences, compose writes the answer from those facts. Every step records its output in the trace. All three LLM steps go through get_structured in llm.py to OpenAI. The response, including the trace, returns to the client."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 565" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · ROUTES.PY</text><text class="lane" x="508" y="18">L3 · PIPELINE.PY</text><text class="lane" x="752" y="18">L3 · STEPS</text><text class="lane" x="996" y="18">L2 · LLM + PROMPTS</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,228 C230,228 230,178 261,178" marker-end="url(#mka)"></path><path class="edge" d="M444,178 C474,178 474,174 505,174" marker-end="url(#mka)"></path><path class="edge" d="M598,216 L598,236" marker-end="url(#mka)"></path><path class="edge" d="M688,174 C718,174 718,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M842,118 L842,137" marker-end="url(#mka)"></path><path class="edge" d="M842,224 L842,243" marker-end="url(#mka)"></path><path class="edge" d="M842,330 L842,349" marker-end="url(#mka)"></path><path class="edge" d="M932,386 C962,386 962,174 993,174" marker-end="url(#mka)"></path><path class="edge" d="M1086,238 L1086,220" marker-end="url(#mka)"></path><path class="edge" d="M1176,174 C1206,174 1206,228 1237,228" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,258 V447 H110 V268" marker-end="url(#mkg)"></path><g class="node-external"><rect height="76" rx="8" width="180" x="20" y="190"></rect><text class="nt t" text-anchor="middle" x="110" y="214">Client</text><text class="ns s" text-anchor="middle" x="110" y="232">run_pipeline_demo.py</text><text class="ns s" text-anchor="middle" x="110" y="248">PowerShell</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="144"></rect><text class="nt t" text-anchor="middle" x="354" y="176">POST /rag/multistep</text><text class="ns s" text-anchor="middle" x="354" y="195">returns pipeline.trace</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="157">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="235"></rect><text class="nt t" text-anchor="middle" x="354" y="259">POST /rag</text><text class="ns s" text-anchor="middle" x="354" y="278">single-step path</text><text class="ns s" text-anchor="middle" x="354" y="293">(Day 9, unchanged)</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="132"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="164">run_pipeline()</text><text class="ns s" text-anchor="middle" x="598" y="184">router first · STEPS loop</text><text class="ns s" text-anchor="middle" x="598" y="198">stop on state.done</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="146">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="238"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="270">PipelineState</text><text class="ns s" text-anchor="middle" x="598" y="290">search_query · intent</text><text class="ns s" text-anchor="middle" x="598" y="304">chunks · facts · trace</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="252">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">analyze</text><text class="ns s" text-anchor="middle" x="842" y="85">rewrite + intent</text><text class="ns s" text-anchor="middle" x="842" y="100">(degrades to raw question)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="172">retrieve</text><text class="ns s" text-anchor="middle" x="842" y="191">Day 9 retrieval · wider</text><text class="ns s" text-anchor="middle" x="842" y="206">for comparisons · retry</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="246"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="278">extract</text><text class="ns s" text-anchor="middle" x="842" y="297">copy relevant sentences</text><text class="ns s" text-anchor="middle" x="842" y="312">with their tags</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="259">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="352"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="384">compose</text><text class="ns s" text-anchor="middle" x="842" y="403">answer from facts only</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="365">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="132"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="164">get_structured()</text><text class="ns s" text-anchor="middle" x="1086" y="184">one schema per step</text><text class="ns s" text-anchor="middle" x="1086" y="198">bad JSON → error</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="146">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="238"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="270">prompts.py</text><text class="ns s" text-anchor="middle" x="1086" y="290">ANALYZE / EXTRACT /</text><text class="ns s" text-anchor="middle" x="1086" y="304">COMPOSE_PROMPT</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="252">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="197"></rect><text class="nt t" text-anchor="middle" x="1330" y="221">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="240">3 LLM calls + 1 embedding</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="186"></rect><text class="el" text-anchor="middle" x="230" y="197">POST</text><rect class="elbg" height="15" rx="3" width="78" x="1167" y="184"></rect><text class="el" text-anchor="middle" x="1206" y="195">json_schema</text><rect class="elbg" height="15" rx="3" width="98" x="671" y="440"></rect><text class="el" text-anchor="middle" x="720" y="451">answer + trace</text><text class="lane" style="fill:var(--ghost)" x="20" y="495">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="182" x="20" y="505"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="111" y="532">Day 11 · tool usage</text></g><g class="node-ghost"><rect height="44" rx="8" width="150" x="222" y="505"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="297" y="532">Day 12 · memory</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: One prompt does everything

- `/rag` sends the user's raw words to retrieval, then one prompt with all chunks
- The model has to pick facts and write the answer in the same call
- When an answer is wrong, you can't tell if retrieval, selection or wording failed
- `llm.py` could only return the fixed `{answer, confidence, score}` shape

### After this episode: Four steps, each one visible

- `POST /rag/multistep` runs `analyze → retrieve → extract → compose` over a `PipelineState`
- Each LLM step has its own prompt in `prompts.py` and schema, via `get_structured(prompt, schema, name)`
- `state.record()` logs every step and returns it in `pipeline.trace`
- `analyze` degrades to the raw question; `retrieve` retries once; later LLM errors return the fallback

> **Why it matters:** this is the core idea behind agents: split a task into steps with clear inputs and outputs, and keep state between them. Building it by hand first, with no framework, is what makes LangGraph make sense later. The trace also turns 'the answer is bad' into 'the extract step dropped a fact', which is something you can fix.

## Code walkthrough

Four snippets from `Day10`. The state object and the loop are the whole idea; the prompts and the shared LLM call make it work.

### pipeline.py · the shared state

```python
@dataclass
class PipelineState:
    question: str
    top_k: int
    filters: dict | None
    timer: StepTimer
    route_name: str = "rag_simple"
    search_query: str = ""
    intent: str = "open"
    chunks: list[dict] = field(default_factory=list)
    facts: list[dict] = field(default_factory=list)
    ...
    trace: list[dict] = field(default_factory=list)
    done: bool = False  # a step sets this to stop the pipeline (safe refusal / failure)

    def record(self, step: str, output) -> None:
        self.trace.append({"step": step, "output": output})
        logger.info("pipeline_step step=%s output=%s", step, output)
```

**State is the contract between steps.** Each step reads what earlier steps wrote and adds its own field. `done` lets any step stop the run, like a refusal when retrieval finds nothing. `record` writes the same data to the log and the response.

### pipeline.py · analyze + retrieve

```python
def analyze(state: PipelineState) -> None:
    try:
        result = get_structured(render_analyze_prompt(state.question), ANALYZE_SCHEMA, "analyze")
        state.search_query = result["search_query"].strip() or state.question
        state.intent = result["intent"]
    except ExternalServiceError:
        logger.warning("analyze_failed - falling back to the raw question")
        state.search_query, state.intent = state.question, "open"
...
def retrieve(state: PipelineState) -> None:
    top_k = max(state.top_k, 6) if state.intent == "comparison" else state.top_k
    state.chunks = get_relevant_chunks(state.search_query, top_k, state.filters)
    if not state.chunks and state.search_query != state.question:
        # the rewrite can lose information; retry once with the user's own words
        state.chunks = get_relevant_chunks(state.question, top_k, state.filters)
```

**An optional step should degrade gracefully.** If analyze breaks, the pipeline still has the user's question. The intent it produces changes the next step: a comparison gets at least 6 chunks.

### pipeline.py · the orchestrator

```python
STEPS = [analyze, retrieve, extract, compose]
...
    state = PipelineState(question, route.top_k, filters, timer, route_name=route.name)
    try:
        for step in STEPS:
            with timer.step(step.__name__):
                step(state)
            if state.done:
                break
    except ExternalServiceError:
        logger.error("pipeline_failed at=%s", state.trace[-1]["step"] if state.trace else "start")
        state.answer, state.source = LLM_DOWN_ANSWER, "fallback_error"
```

**The flow is data: change the list, change the pipeline.** Each step is timed by name, so `timings` shows analyze, retrieve, extract and compose separately. Look closely at the highlighted log: it names the last step that **finished**, which the break-it segment exposes.

### llm.py · one call path, many schemas

```python
def _call_model(prompt: str, schema: dict, name: str) -> str:
    ...
            text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}},
...
def get_structured(prompt: str, schema: dict, name: str) -> dict:
    """Generic structured-output call used by every pipeline step. Invalid JSON -> ExternalServiceError."""
    raw = _call_model(prompt, schema, name)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("llm_returned_non_json step=%s", name)
        raise ExternalServiceError("The AI service returned an invalid response") from exc
```

**Pipeline steps can't guess at a bad reply, so bad JSON is an error.** `get_answer` still tolerates non-JSON by returning the raw text. A pipeline step needs `facts` or `intent` to continue, so it raises and lets the orchestrator decide.

## Run it

Run from `Day10` in PowerShell. Multistep requests take 4–5 seconds, so let the pauses breathe or cut them in editing.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `59 passed`, including 10 new tests in `test_pipeline.py`.

**Step 2**

```powershell
python run_pipeline_demo.py pipeline_runs_v3.json
```

**Expect:** For each of 7 queries: the rewritten query and intent, number of facts, then the multi and single answers with their times. `hello` stays at a few ms with source `smalltalk`.

**Step 3**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on port 8000; `/docs` now lists `/rag/multistep`.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/multistep" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Compare Tel Aviv and Haifa"}').results | ConvertTo-Json -Depth 6
```

**Expect:** `pipeline.intent: comparison`, a keyword `search_query`, a `facts` list with tags, four trace entries, and `timings` for analyze, retrieve, extract and compose.

**Step 5**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Compare Tel Aviv and Haifa"}').results.timings
```

**Expect:** One `llm` step and a much smaller `total_ms`. Put the two timings side by side.

### Break it on purpose

#### 1 · A model that doesn't exist, and a log that blames the wrong step

Stop uvicorn, run `$env:LLM_MODEL="gpt-does-not-exist"`, start it again and call `/rag/multistep`. `analyze` fails and degrades: the trace shows the raw question as `search_query`. Retrieval still works (embeddings use a different model). Then `extract` fails and you get `source: fallback_error` with **200**. Now read the log: `llm_call_failed step=extract`, followed by `pipeline_failed at=retrieve`. The orchestrator logs `state.trace[-1]["step"]`, the last step that **finished**. The step that raised never got recorded. On a dashboard, that sends you to debug retrieval. Run `Remove-Item Env:LLM_MODEL` afterwards.

```python
    current = "start"
    try:
        for step in STEPS:
            current = step.__name__
            with timer.step(current):
                step(state)
            if state.done:
                break
    except ExternalServiceError:
        logger.error("pipeline_failed at=%s", current)
```

#### 2 · An out-of-domain question

Ask `/rag/multistep` "What is the capital of France?". The trace has only `analyze` and `retrieve`: the retrieval gate sets `state.done`, so extract and compose never run. You paid for one LLM call instead of three, and got the safe refusal.

> When you split work into steps, error reporting has to follow the steps too. A trace that names the wrong step is worse than none, because it sends you to the wrong place with confidence.

## Cheat sheet

- **Multi-step pipeline**: A task split into ordered steps, each with its own input, output and prompt.
- **Pipeline state**: One object (`PipelineState`) that every step reads from and writes to, instead of passing many arguments.
- **Query rewriting**: Turning the user's words into a better search query. Here the `analyze` step produces a keyword query.
- **Intent classification**: Labelling a question as `lookup`, `comparison` or `open` so later steps can adapt, like a wider top_k for comparisons.
- **Fact extraction**: Asking the model to copy only the relevant sentences, with their tags, before writing the answer.
- **Structured output**: Forcing the model's reply to match a JSON schema (`json_schema`, `strict: True`), so code can read it safely.
- **Graceful degradation**: Continuing with a simpler fallback when an optional step fails, like using the raw question when analyze fails.
- **Early exit**: Stopping the pipeline when a step decides there's nothing to do, via `state.done`.
- **Trace**: The ordered list of step outputs returned in `pipeline.trace` and written to the log.
- **Latency trade-off**: Three LLM calls take 3.7–5.5 s against 1.4–2.7 s for single-step RAG. More steps, more time and cost.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why give each step its own prompt instead of one long prompt?</summary><p>Each prompt has one job and one schema, so each step can be tested, logged and fixed alone. Small prompts are also easier to keep grounded.</p></details>
<details><summary>What happens if the analyze step's LLM call fails?</summary><p>It catches <code>ExternalServiceError</code>, uses the raw question as <code>search_query</code> with intent <code>open</code>, records that in the trace, and the pipeline continues.</p></details>
<details><summary>Why does get_structured raise on invalid JSON while get_answer doesn't?</summary><p>Pipeline steps need specific fields like <code>facts</code> or <code>intent</code> to continue. <code>get_answer</code> can still return raw text as an answer, a pipeline step can't.</p></details>
<details><summary>If extract raises, what does the pipeline_failed log line say, and why?</summary><p>It says <code>at=retrieve</code>. The handler reads <code>state.trace[-1]</code>, but <code>extract</code> never reached <code>record()</code>, so the last trace entry is from <code>retrieve</code>.</p></details>
<details><summary>When is /rag/multistep worth its extra latency?</summary><p>For comparisons and multi-part questions, and when you need an audit trail of how the answer was built. For simple lookups single-step RAG gives the same answer 2–3× faster.</p></details>
</div>

**Next:** Day 11 – Give It Tools

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
