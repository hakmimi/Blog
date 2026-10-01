---
title: "Day 18: Retry, Then Fall Back"
description: "From a graph where one failing call can end the request with a 500 or a 503 to one that contains every exception at the node boundary. Transient errors are retried with backoff, everything else lands in a fallback node that gives an honest answer and still shows the best evidence it has."
series: "ai-engineering"
order: 20
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "tenacity", "safe nodes", "fallback node"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day18`](https://github.com/hakmimi/AIEngineering/tree/main/Day18). Layers touched: L3 Orchestration, L4 System.

## Goals

- **G1. Contain exceptions at node boundaries.**  
  You can: show `safe(name)` and read a `graph_node_failed` log line with its context.
- **G2. Retry only what can succeed on retry.**  
  You can: explain why a timeout is retried and a bad API key is not, using `is_retryable()`.
- **G3. Route every failure to one fallback node.**  
  You can: run the failure drill and read the trace ending in `fallback_node`.
- **G4. Avoid stacked retries.**  
  You can: explain why `OPENAI_MAX_RETRIES` went from 2 to 0 and what it did to latency.

## System map

Nothing new on the happy path. The new boxes are all about the unhappy one: a safe wrapper around each node, one retry layer, and a fallback node every failure can reach.

> Query → Node → success path \| transient failure → retry (backoff) → success \| still failing → fallback_node → honest answer (+ best evidence)

<div class="ae-map" role="img" aria-label="The client posts to /rag/graph. Every node that can fail runs inside safe(), which turns any exception into state.error and logs it with context. Retrieval and the LLM call go through retry_call, which uses tenacity to retry only ExternalServiceError with retryable=True, as decided by is_retryable in openai_client.py, with 0.5 s and 1 s waits and at most 3 attempts. The OpenAI SDK's own retries are set to 0. If a node still fails, the or_fallback conditional edge sends the run to fallback_node, which uses render_degraded_answer to return a deterministic message and, if retrieval worked, the best retrieved passage."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 368" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L3 · GRAPH.PY</text><text class="lane" x="508" y="18">L4 · RESILIENCE.PY</text><text class="lane" x="752" y="18">EXTERNAL</text><text class="lane" x="996" y="18">L3 · FAILURE PATH</text><text class="lane" x="1240" y="18">L2 · PROMPTS.PY</text><path class="edge" d="M200,129 C230,129 230,76 261,76" marker-end="url(#mka)"></path><path class="edge" d="M354,118 L354,137" marker-end="url(#mka)"></path><path class="edge" d="M444,182 C474,182 474,76 505,76" marker-end="url(#mka)"></path><path class="edge" d="M598,118 L598,137" marker-end="url(#mka)"></path><path class="edge" d="M688,76 C718,76 718,129 749,129" marker-end="url(#mka)"></path><path class="edge" d="M932,129 C962,129 962,84 993,84" marker-end="url(#mka)"></path><path class="edge" d="M1086,118 L1086,137" marker-end="url(#mka)"></path><path class="edge" d="M1176,174 C1206,174 1206,129 1237,129" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,171 V250 H110 V170" marker-end="url(#mkg)"></path><g class="node-external"><rect height="76" rx="8" width="180" x="20" y="91"></rect><text class="nt t" text-anchor="middle" x="110" y="115">Client</text><text class="ns s" text-anchor="middle" x="110" y="134">POST /rag/graph</text><text class="ns s" text-anchor="middle" x="110" y="149">scripts.failure_drill</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="34"></rect><text class="nt t" text-anchor="middle" x="354" y="66">graph nodes</text><text class="ns s" text-anchor="middle" x="354" y="85">retrieve · call_llm</text><text class="ns s" text-anchor="middle" x="354" y="100">select · run · tool_answer</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="47">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="172">safe(name)</text><text class="ns s" text-anchor="middle" x="354" y="191">exception → state.error</text><text class="ns s" text-anchor="middle" x="354" y="206">+ context log</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="153">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="66">retry_call()</text><text class="ns s" text-anchor="middle" x="598" y="85">tenacity · 3 attempts</text><text class="ns s" text-anchor="middle" x="598" y="100">waits 0.5 s, 1 s</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="172">is_retryable()</text><text class="ns s" text-anchor="middle" x="598" y="191">timeout · connection</text><text class="ns s" text-anchor="middle" x="598" y="206">429 · 5xx</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="153">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="752" y="98"></rect><text class="nt t" text-anchor="middle" x="842" y="122">OpenAI API</text><text class="ns s" text-anchor="middle" x="842" y="142">SDK max_retries 2 → 0</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="49"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="81">or_fallback()</text><text class="ns s" text-anchor="middle" x="1086" y="100">edge: error set?</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="62">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="172">fallback_node</text><text class="ns s" text-anchor="middle" x="1086" y="191">no LLM involved</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="153">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="87"></rect><text class="nt t" text-anchor="middle" x="1330" y="119">degraded answer</text><text class="ns s" text-anchor="middle" x="1330" y="138">honest message</text><text class="ns s" text-anchor="middle" x="1330" y="153">+ best passage if any</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="100">NEW</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="86"></rect><text class="el" text-anchor="middle" x="230" y="96">JSON</text><rect class="elbg" height="15" rx="3" width="46" x="602" y="116"></rect><text class="el" text-anchor="start" x="604" y="128">retry?</text><rect class="elbg" height="15" rx="3" width="91" x="917" y="89"></rect><text class="el" text-anchor="middle" x="962" y="100">still failing</text><rect class="elbg" height="15" rx="3" width="258" x="591" y="243"></rect><text class="el" text-anchor="middle" x="720" y="254">200 · source: fallback_error · error{…}</text><text class="lane" style="fill:var(--ghost)" x="20" y="298">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="335">Day 19 · memory &amp; persistence</text></g><g class="node-ghost"><rect height="44" rx="8" width="174" x="300" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="387" y="335">Day 20 · LLM judge</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: One failure, whole request down

- An embedding failure left the graph and returned **503** with no trace
- The Day 17 overflow bug in a tool returned **500**
- Only `call_llm` caught provider errors, and it never retried
- The SDK retried silently inside our code, so nobody saw it

### After this episode: Recover, don't crash

- Every failing node is wrapped by `safe()`; exceptions become `state["error"]`
- Timeouts, connection errors, 429 and 5xx are retried with backoff; auth errors are not
- Every failure path ends in `fallback_node` with an honest, deterministic answer
- The response includes `error: {node, type, message, retryable}`

> **Why it matters:** real providers time out, rate-limit and go down. A system that crashes on the first failure can't be put in front of users, and one that retries everything can hang for a minute. This episode is about choosing which failures to retry and making the rest fail politely.

## Code walkthrough

Four snippets from `Day18`. Boundary, retry policy, the retryable decision, and the fallback.

### graph.py · the node boundary

```python
def safe(name: str):
    """Node boundary: never let an exception escape the graph. Log it WITH context, store it in state."""
    def wrap(fn):
        def inner(state: RagState) -> dict:
            try:
                return fn(state)
            except Exception as exc:  # noqa: BLE001 - this is the deliberate catch-all boundary
                error = {"node": name, "type": type(exc).__name__, "message": str(exc),
                         "retryable": bool(getattr(exc, "retryable", False))}
                logger.error("graph_node_failed node=%s type=%s retryable=%s route=%s query_type=%s question_len=%s msg=%s", ...)
                return {"error": error}
```

**One catch-all, in one place, on purpose.** Inside the nodes the code stays clean. At the boundary any exception, even our own bug, becomes data in state. The log has the route and question length but not the user's text.

### resilience.py · one retry layer

```python
def _should_retry(exc: BaseException) -> bool:
    return isinstance(exc, ExternalServiceError) and exc.retryable

def retry_call(fn, *args, label: str = "call", attempts: int | None = None, base_delay: float | None = None, **kwargs):
    ...
    retrying = Retrying(
        stop=stop_after_attempt(attempts or settings.retry_attempts),
        wait=wait_exponential(multiplier=settings.retry_base_delay if base_delay is None else base_delay, max=8),
        retry=retry_if_exception(_should_retry),
        before_sleep=before_sleep,
        reraise=True,          # after the last attempt the original error surfaces (-> fallback path)
    )
    return retrying(fn, *args, **kwargs)
```

**Capped attempts, exponential waits, and only for errors that might go away.** `reraise=True` matters: after the last try the original error comes out, `safe()` catches it, and the fallback edge takes over. Every retry is logged in `before_sleep`.

### openai_client.py · what is worth retrying

```python
def is_retryable(exc: Exception) -> bool:
    """Transient provider failures are worth retrying; auth/validation errors are not."""
    return isinstance(exc, (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError))

# llm.py / embeddings.py
        raise ExternalServiceError(retryable=is_retryable(exc)) from exc
```

**The decision is made where the error is understood.** Only the code that talks to OpenAI knows what kind of failure it saw. It stamps the error with `retryable`, and the retry layer just reads the flag.

### graph.py + prompts.py · the fallback

```python
@timed("fallback_node")
def fallback_node(state: RagState) -> dict:
    error = state.get("error", {})
    ...
    return {"answer": render_degraded_answer(state.get("chunks") or [], error), "source": "fallback_error",
            "confidence": 0.0}

def render_degraded_answer(chunks: list[dict], error: dict) -> str:
    if error.get("node") in ("select_tool", "run_tool", "tool_answer"):
        return "I could not complete that calculation or lookup right now. Please try again shortly."
    if chunks:
        best = chunks[0]
        return (f"{LLM_DOWN_ANSWER} In the meantime, the most relevant information I found "
                f"({best.get('topic') or 'knowledge base'}): {best['text']}")
    return LLM_DOWN_ANSWER
```

**Degraded, but useful and never invented.** If retrieval worked and only the LLM failed, the user still sees the best passage, word for word from the knowledge base. No model is involved in writing the fallback.

## Run it

Run from `Day18` in PowerShell. The drill script calls the graph directly, so no server is needed. Remove every override after each drill.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `191 passed`, with 14 failure-injection tests in `tests/test_failures.py`.

**Step 2**

```powershell
python -m scripts.failure_drill
```

**Expect:** `source=rag`, about 3 s, `error=None`, and a normal answer about Masada.

**Step 3**

```powershell
$env:OPENAI_API_KEY="sk-invalid"; python -m scripts.failure_drill
Remove-Item Env:OPENAI_API_KEY
```

**Expect:** `source=fallback_error`, trace `… retrieve_context, fallback_node`, `error` with `type: ExternalServiceError`, `retryable: False`. About 2 s and **no** `retrying` lines.

**Step 4**

```powershell
$env:OPENAI_BASE_URL="http://127.0.0.1:9"; python -m scripts.failure_drill
Remove-Item Env:OPENAI_BASE_URL
```

**Expect:** `retrying label=retrieval attempt=1/3 next_wait_s=0.50`, then `attempt=2/3 next_wait_s=1.00`, then the fallback. About 9 s total, `retryable: True`.

**Step 5**

```powershell
python -m pytest tests/test_failures.py -q -k "degrades_to_evidence or unexpected_bug"
```

**Expect:** 2 passed: the LLM-down case that still shows the best passage, and a `ZeroDivisionError` inside a node that is contained.

### Break it on purpose

#### 1 · Stack the retries again

Run `$env:OPENAI_MAX_RETRIES="2"; $env:OPENAI_BASE_URL="http://127.0.0.1:9"` and the drill. Now the SDK retries twice inside each of our three attempts, and you can't see those inner retries in the log. The README's first drill took **25 s** this way. That's why there is one retry layer, and it's ours. Clean up with `Remove-Item Env:OPENAI_MAX_RETRIES, Env:OPENAI_BASE_URL`.

#### 2 · Replay the Day 17 crash

Run `python -m scripts.failure_drill "10^100*10^100*10^100*10^100"`. On Day 17 this was a 500. Now `safe("run_tool")` catches the `OverflowError`, the trace ends in `fallback_node`, and the answer is "I could not complete that calculation or lookup right now". The boundary works, but the root cause is still in `safe_eval`, and the message even suggests trying again, which won't help. A boundary is a safety net, not a fix.

```text
# tools.py, safe_eval: fix the cause as well
    except OverflowError as exc:
        raise ValueError("result too large") from exc
```

> Failure handling is a set of choices: which errors to retry, how many times, how long the user waits, and what they see at the end. Write the choices down, test each one, and still fix the bugs the safety net catches.

## Cheat sheet

- **Node boundary**: The wrapper around a node where exceptions are caught and turned into state. Here `safe(name)`.
- **Transient failure**: A failure that may go away on its own: a timeout, a dropped connection, a 429 or a 5xx.
- **Retryable**: A flag on `ExternalServiceError` that says whether trying again can help.
- **Exponential backoff**: Waiting longer before each retry (0.5 s, then 1 s) so a struggling service gets room to recover.
- **tenacity**: A Python library for retry policies: stop conditions, wait strategies and which exceptions to retry.
- **Fallback node**: The graph node every failure path reaches. It returns a deterministic, honest answer.
- **Graceful degradation**: Giving a smaller but still useful result when part of the system fails, like the best passage without an LLM summary.
- **Stacked retries**: Two retry layers nested inside each other. The attempts multiply, and so does the latency.
- **Latency budget**: The worst-case time a request can take: attempts × timeout + backoff, about 61 s here with the defaults.
- **Expected outcome vs failure**: A `no_context` refusal or a `1/0` tool error is normal behaviour and stays on the normal path.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why isn't an AuthenticationError retried?</summary><p>A wrong key will be wrong on every attempt. <code>is_retryable()</code> returns False, so <code>retry_call</code> gives up at once and the run goes to the fallback in about 2 seconds.</p></details>
<details><summary>Why was OPENAI_MAX_RETRIES changed from 2 to 0?</summary><p>The SDK was retrying inside each of our attempts, invisibly. One visible, logged retry layer is easier to reason about and cut the dead-server drill from 25 s to about 9 s.</p></details>
<details><summary>Retrieval worked but the LLM is down. What does the user get?</summary><p>The unavailable message plus the best retrieved passage, quoted from the knowledge base. <code>render_degraded_answer</code> builds it without calling any model.</p></details>
<details><summary>Is a no_context refusal routed to fallback_node?</summary><p>No. Weak context is an expected outcome: <code>call_llm</code> returns the refusal normally and the run ends on the success path.</p></details>
<details><summary>Why does the fallback text avoid the LLM?</summary><p>The LLM might be exactly what failed. A deterministic message always works and can't invent anything.</p></details>
</div>

**Next:** Day 19 – Memory That Persists

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
