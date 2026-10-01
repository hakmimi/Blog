---
title: "Day 7: Refactor Without Fear"
description: "From a working RAG API where the OpenAI client, the prompts and every endpoint are tangled across a few big files, to a codebase where each module has one job. Same routes, same answers, same logs; the offline tests prove nothing changed."
series: "ai-engineering"
order: 9
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "fastapi apirouter", "clean modules", "pytest"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day7`](https://github.com/hakmimi/AIEngineering/tree/main/Day7). Layers touched: L2 LLM, L4 System.

## Goals

- **G1. Split the app by responsibility: wiring, endpoints, schemas, pipeline, prompts, provider access.**  
  You can: open the module map and say in one sentence what each file does.
- **G2. Remove duplication: one OpenAI client and one missing-key check.**  
  You can: show `get_client()` and point at the two callers that used to build their own client.
- **G3. Make the pipeline read top to bottom.**  
  You can: read `get_rag_answer` out loud in six lines: route, then answer directly or from context.
- **G4. Use the test suite as the safety net for a no-behaviour-change refactor.**  
  You can: run `pytest` and get 34 passing tests, then explain why two mock targets had to move.

## System map

Same system as Day 6, redrawn by file. The boxes that moved or were created today are highlighted. The request path did not change at all.

> Client → main.py (middleware) → routes.py → rag.py → router / retrieval / prompts → llm.py → openai_client → OpenAI → Response

<div class="ae-map" role="img" aria-label="The client calls main.py, which only wires middleware and error handlers and includes routes.py. routes.py validates with schemas.py and calls get_rag_answer in rag.py. rag.py uses router.py, retrieval.py and prompts.py, then llm.py. llm.py and embeddings.py both get their client from openai_client.py, which calls the OpenAI API. The response returns to the client."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 466" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · WIRING</text><text class="lane" x="508" y="18">L4 · ENDPOINTS</text><text class="lane" x="752" y="18">L3 · PIPELINE</text><text class="lane" x="996" y="18">L2 · PROVIDER ACCESS</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,178 C230,178 230,136 261,136" marker-end="url(#mka)"></path><path class="edge-old" d="M354,178 L354,198" marker-end="url(#mkm)"></path><path class="edge" d="M444,136 C474,136 474,132 505,132" marker-end="url(#mka)"></path><path class="edge" d="M598,174 L598,194" marker-end="url(#mka)"></path><path class="edge" d="M688,132 C718,132 718,76 749,76" marker-end="url(#mka)"></path><path class="edge-old" d="M842,118 L842,137" marker-end="url(#mkm)"></path><path class="edge" d="M842,216 L842,235" marker-end="url(#mka)"></path><path class="edge" d="M932,76 C962,76 962,125 993,125" marker-end="url(#mka)"></path><path class="edge" d="M1086,167 L1086,186" marker-end="url(#mka)"></path><path class="edge" d="M1176,231 C1206,231 1206,178 1237,178" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,216 V348 H110 V212" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="148"></rect><text class="nt t" text-anchor="middle" x="110" y="172">Client</text><text class="ns s" text-anchor="middle" x="110" y="190">PowerShell · /docs</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="94"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="126">main.py</text><text class="ns s" text-anchor="middle" x="354" y="146">middleware · error handlers</text><text class="ns s" text-anchor="middle" x="354" y="160">includes the router</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="108">CHANGED</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="264" y="200"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="224">security.py</text><text class="ns s" text-anchor="middle" x="354" y="244">API key · rate limit</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="90"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="122">routes.py</text><text class="ns s" text-anchor="middle" x="598" y="142">/health /ready /docs-count</text><text class="ns s" text-anchor="middle" x="598" y="156">/search /rag</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="104">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="508" y="196"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="228">schemas.py</text><text class="ns s" text-anchor="middle" x="598" y="248">SearchRequest</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="210">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">rag.py</text><text class="ns s" text-anchor="middle" x="842" y="85">get_rag_answer → 3 small</text><text class="ns s" text-anchor="middle" x="842" y="100">functions + build_response</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">CHANGED</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="140"></rect><text class="nt t" text-anchor="middle" x="842" y="164">router + retrieval</text><text class="ns s" text-anchor="middle" x="842" y="183">Day 5–6 rules, scoring,</text><text class="ns s" text-anchor="middle" x="842" y="198">filters (unchanged)</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="238"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="270">prompts.py</text><text class="ns s" text-anchor="middle" x="842" y="289">RAG_PROMPT · fixed answers</text><text class="ns s" text-anchor="middle" x="842" y="304">with_json_schema()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="251">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="83"></rect><text class="nt t" text-anchor="middle" x="1086" y="115">llm + embeddings</text><text class="ns s" text-anchor="middle" x="1086" y="134">_call_model + get_answer</text><text class="ns s" text-anchor="middle" x="1086" y="149">get_embedding</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="96">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="189"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="221">openai_client.py</text><text class="ns s" text-anchor="middle" x="1086" y="240">get_client(): one lazy</text><text class="ns s" text-anchor="middle" x="1086" y="255">shared client</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="202">NEW</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="1240" y="140"></rect><text class="nt t" text-anchor="middle" x="1330" y="164">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="183">gpt-4.1-mini</text><text class="ns s" text-anchor="middle" x="1330" y="198">text-embedding-3-small</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="140"></rect><text class="el" text-anchor="middle" x="230" y="151">HTTP</text><rect class="elbg" height="15" rx="3" width="72" x="1170" y="188"></rect><text class="el" text-anchor="middle" x="1206" y="198">one client</text><rect class="elbg" height="15" rx="3" width="98" x="671" y="341"></rect><text class="el" text-anchor="middle" x="720" y="352">{ results: … }</text><text class="lane" style="fill:var(--ghost)" x="20" y="396">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="238" x="20" y="406"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="139" y="433">Day 8 · FAISS vector index</text></g><g class="node-ghost"><rect height="44" rx="8" width="230" x="278" y="406"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="393" y="433">Day 9 · retrieval quality</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: It works, but it's hard to explain

- `llm.py` and `embeddings.py` each built their own `OpenAI` client and checked the key twice
- Prompt text, the refusal sentence and the JSON suffix were scattered across `rag.py` and `llm.py`
- `main.py` held app setup, the request schema and every endpoint
- `get_rag_answer` was one 30-line function full of early returns

### After this episode: One job per module

- `openai_client.get_client()` is the only place a client is built, lazily on first use
- Every string the user or the model sees lives in `prompts.py`
- `main.py` is wiring, `routes.py` is endpoints, `schemas.py` is request models
- `get_rag_answer` routes to `_answer_directly` or `_answer_from_context`, and `build_response` shapes every result

> **Why it matters:** the next three weeks add a vector index, evaluation, tools, memory and an agent loop. Each of those lands in one module now. If you can't point at the file a feature belongs in, you can't explain the system on camera either.

## Code walkthrough

Four snippets from `Day7`. Show the highlighted lines and land the bold sentence.

### openai_client.py · one lazy client

```python
_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Lazily create one shared client; fail clearly if the key is missing."""
    global _client
    if not settings.openai_api_key:
        raise ConfigurationError("OPENAI_API_KEY is not configured")
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key,
                         timeout=settings.openai_timeout_seconds,
                         max_retries=settings.openai_max_retries)
    return _client
```

**The client is built once, the first time someone needs it.** Day 6 created a client at import time in two files and checked for `None` in each. Now the key check exists once, and a smalltalk request that never calls OpenAI works even with no key.

### prompts.py · every sentence in one place

```python
NO_CONTEXT_ANSWER = "I don't have enough information in my knowledge base to answer that."
LLM_DOWN_ANSWER = "The answer service is temporarily unavailable. Please try again shortly."
...
JSON_SUFFIX = "\n\nReturn only valid JSON matching this schema:\n{schema}"


def render_rag_prompt(context: str, question: str) -> str:
    return RAG_PROMPT.format(no_context=NO_CONTEXT_ANSWER, context=context, question=question)


def with_json_schema(prompt: str, schema: dict) -> str:
    return prompt + JSON_SUFFIX.format(schema=json.dumps(schema))
```

**Prompts are product copy. Keep them where you can review them together.** The refusal sentence appears both in the prompt and as a canned answer. With one constant, the model and the fallback can never drift apart.

### rag.py · the pipeline reads top to bottom

```python
def get_rag_answer(question: str, top_k: int = 4) -> dict:
    timer = StepTimer()
    question = (question or "").strip()

    with timer.step("routing"):
        route = route_query(question, top_k)
    logger.info("decision=route name=%s reason=%s top_k=%s", route.name, route.reason, route.top_k)

    if route.name in (SKIP, CLARIFY):
        return _answer_directly(question, route, timer)
    return _answer_from_context(question, route, timer)
```

**The top-level function only decides. The named helpers do the work.** Compare it with Day 6, where retrieval, validation, prompting and the LLM call were all inline. Every result now goes through `build_response`, so the response shape and the log line live in one place.

### llm.py · network vs parsing

```python
def _call_model(prompt: str) -> str:
    """One LLM round-trip; any provider error becomes ExternalServiceError."""
    client = get_client()
    try:
        response = client.responses.create(
            model=settings.llm_model,
            input=with_json_schema(prompt, ANSWER_SCHEMA),
            ...
    except OpenAIError as exc:  # timeout, rate limit, connection, ...
        logger.error("llm_call_failed type=%s", type(exc).__name__)
        raise ExternalServiceError() from exc
    return response.output_text


def get_answer(prompt: str) -> dict:
    raw = _call_model(prompt)
```

**Split the part that can time out from the part that can be unit tested.** `_call_model` is the only function that touches the network. `get_answer` only parses JSON, so its fallback for non-JSON output can be tested with a fake string.

## Run it

Run from `Day7` in PowerShell. The point of the demo is that the outputs look exactly like Day 6.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `34 passed`. Run it before touching anything and again at the end.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on `http://127.0.0.1:8000`. `/docs` lists the same routes as Day 6, now coming from `routes.py`.

**Step 3**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready
```

**Expect:** `status: ready` and a `checks` object. If a data file or the key is missing, `degraded`.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"hello there"}').results
```

**Expect:** `route: skip`, `source: smalltalk`, the canned hello, and `timings` with only `routing` and `total_ms`. Zero API calls.

**Step 5**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Why is Jerusalem important to three religions?"}').results
```

**Expect:** `route: rag_complex`, a cited answer, `retrieved_chunks`, and timings for `routing`, `retrieval`, `prompt`, `llm`. Same shape as Day 6.

### Break it on purpose

#### 1 · Patch the old location in a test

In `tests/test_reliability.py`, change `test_api_unexpected_error_is_safe` back to Day 6's `import main` and `monkeypatch.setattr(main, "get_rag_answer", ...)`. Run `pytest`: it fails, because `main` no longer has `get_rag_answer`. The endpoint moved to `routes.py`, so the mock must patch where the name is **looked up**. This is exactly one of the two test changes the refactor needed.

```python
import routes
monkeypatch.setattr(routes, "get_rag_answer", lambda q, k: 1 / 0)
```

#### 2 · Run without OPENAI_API_KEY

Rename `.env` and restart uvicorn. `hello there` still returns the canned answer with **200**, because the client is only built when it's needed. A real question returns **500** with `{"detail": "OPENAI_API_KEY is not configured"}`, raised once by `get_client()` and turned into JSON by the `AppError` handler in `main.py`. The new test `test_missing_api_key_raises_configuration_error` locks this in.

> A refactor is only safe when behaviour is pinned down by tests first. Moving code changes where names live, and tests that reach into internals are the first thing to break. Treat that as a signal.

## Cheat sheet

- **Refactor**: Changing the structure of code without changing what it does from the outside.
- **Single responsibility**: Each module has one reason to change. `prompts.py` changes when wording changes, `routes.py` when the HTTP API changes.
- **Lazy initialisation**: Creating an object the first time it's used instead of at import time. `get_client()` does this for the OpenAI client.
- **Dependency direction**: Imports flow one way: `routes → rag → router, retrieval, llm, prompts`. Lower layers never import higher ones.
- **APIRouter**: A FastAPI object that groups endpoints in their own file. `main.py` attaches it with `app.include_router(router)`.
- **Route dependencies**: Functions FastAPI runs before an endpoint, like `require_api_key` and `rate_limit` in the `protected` list.
- **Re-export**: Importing a name into a module so old imports keep working. `rag.py` re-exports `RAG_PROMPT` and the fixed answers from `prompts.py`.
- **Mock target**: The module attribute a test replaces. You patch where the name is looked up, so moving code can move the target.
- **Over-refactoring**: Adding layers or frameworks the code doesn't need yet. Day 7 moves code and names things, nothing more.
- **Regression test**: A test that proves existing behaviour still works after a change.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why can a smalltalk request succeed with no OPENAI_API_KEY after this refactor?</summary><p>The router answers <code>skip</code> before any retrieval or LLM call, and <code>get_client()</code> is only called inside <code>get_embedding</code> and <code>_call_model</code>. Nothing builds a client at import time any more.</p></details>
<details><summary>Where would you change the sentence the model must use when it has no context?</summary><p><code>NO_CONTEXT_ANSWER</code> in <code>prompts.py</code>. It feeds both <code>RAG_PROMPT</code> and the canned <code>no_context</code> response, so one edit updates both.</p></details>
<details><summary>Why did the unexpected-error test change from patching main to patching routes?</summary><p><code>monkeypatch</code> replaces a name in the module that uses it. The <code>/rag</code> endpoint now lives in <code>routes.py</code> and looks up <code>get_rag_answer</code> there, so patching <code>main</code> has no effect (or fails because the name is gone).</p></details>
<details><summary>What's the benefit of splitting _call_model from get_answer?</summary><p>Network errors and parsing are separate concerns. <code>_call_model</code> is the only place that can time out and turns provider errors into <code>ExternalServiceError</code>; <code>get_answer</code> can be tested with fake strings.</p></details>
<details><summary>How do you know the refactor changed no behaviour?</summary><p>The Day 5 and Day 6 tests ran unchanged except for two moved mock targets, and all 34 pass. Routes, response fields, thresholds and log lines are the same.</p></details>
</div>

**Next:** Day 8 – A Real Vector Index

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
