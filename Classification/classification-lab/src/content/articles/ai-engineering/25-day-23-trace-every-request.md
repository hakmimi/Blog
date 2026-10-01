---
title: "Day 23: Trace Every Request"
description: "From free-text log lines that mix every request together to one JSON object per event, all tied to a request id. After this episode you can take any request id and rebuild what happened: which route, which chunks, which tool, which node was slow and why it failed."
series: "ai-engineering"
order: 25
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "json logs", "contextvar", "request id"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day23`](https://github.com/hakmimi/AIEngineering/tree/main/Day23). Layers touched: L3 Orchestration, L4 System.

## Goals

- **G1. Give every request an id that appears on every log line it produces.**  
  You can: send `X-Request-ID: my-trace-1` and show it in the response header and in every log line of that request.
- **G2. Switch to one standard, machine-readable log format.**  
  You can: explain the fixed keys `ts`, `level`, `logger`, `event`, `request_id` and filter lines with `ConvertFrom-Json`.
- **G3. Log decisions and latency, not user text.**  
  You can: read `graph_route`, `retrieval` (`embed_ms` vs `search_ms`) and `graph_done`, and show the question appears only as `<N chars>`.
- **G4. Find the real bottleneck from logs alone.**  
  You can: run `scripts.log_demo` and say which node is slowest for each of the 5 requests and why.

## System map

The request path is the same as Day 22. What's new is a second flow running alongside it: every box now emits structured events, and one id ties them together from the middleware to the last graph node.

> Client → Request ID (header or generated) → API → Graph nodes → structured JSON logs (+ timings) → Response (X-Request-ID, X-Process-Time-Ms)

<div class="ae-map" role="img" aria-label="The client sends a request, optionally with X-Request-ID. The middleware in main.py sets request_id_var, logs request_start and request_end, and returns the id and latency as headers. A logging filter in observability.py stamps the id on every record, and JsonFormatter writes one JSON object per line, redacting user text. graph.py, retrieval.py and tools.py emit graph_node, graph_route, retrieval and tool_call events. The RAG path calls OpenAI. Logs go to stdout, and log_demo.py writes five sample requests to data/logs/sample_requests.jsonl."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 459" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · MAIN.PY</text><text class="lane" x="508" y="18">L4 · OBSERVABILITY.PY</text><text class="lane" x="752" y="18">L3 · EVENTS</text><text class="lane" x="996" y="18">EXTERNAL</text><text class="lane" x="1240" y="18">LOG OUTPUT</text><path class="edge" d="M200,174 C230,174 230,122 261,122" marker-end="url(#mka)"></path><path class="edge-old" d="M354,164 L354,182" marker-end="url(#mkm)"></path><path class="edge" d="M444,122 C474,122 474,122 505,122" marker-end="url(#mka)"></path><path class="edge" d="M598,164 L598,182" marker-end="url(#mka)"></path><path class="edge" d="M444,122 C596,122 596,76 749,76" marker-end="url(#mka)"></path><path class="edge-old" d="M842,118 L842,137" marker-end="url(#mkm)"></path><path class="edge-old" d="M842,224 L842,243" marker-end="url(#mkm)"></path><path class="edge-old" d="M932,182 C962,182 962,174 993,174" marker-end="url(#mkm)"></path><path class="edge" d="M688,228 C962,228 962,120 1237,120" marker-end="url(#mka)"></path><path class="edge" d="M1330,154 L1330,174" marker-end="url(#mka)"></path><path class="edge-back" d="M1086,205 V341 H110 V208" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="144"></rect><text class="nt t" text-anchor="middle" x="110" y="168">Client</text><text class="ns s" text-anchor="middle" x="110" y="187">optional X-Request-ID</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="80"></rect><text class="nt t" text-anchor="middle" x="354" y="112">request middleware</text><text class="ns s" text-anchor="middle" x="354" y="130">id in/out · request_start</text><text class="ns s" text-anchor="middle" x="354" y="146">request_end + latency</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="92">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="186"></rect><text class="nt t" text-anchor="middle" x="354" y="218">error handlers</text><text class="ns s" text-anchor="middle" x="354" y="236">request_id in body</text><text class="ns s" text-anchor="middle" x="354" y="252">exc_info=exc fix</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="198">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="80"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="112">request_id_var</text><text class="ns s" text-anchor="middle" x="598" y="130">ContextVar +</text><text class="ns s" text-anchor="middle" x="598" y="146">RequestIdFilter</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="92">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="186"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="218">JsonFormatter</text><text class="ns s" text-anchor="middle" x="598" y="236">log_event() · redact()</text><text class="ns s" text-anchor="middle" x="598" y="252">LOG_FORMAT=text</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="198">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">graph.py</text><text class="ns s" text-anchor="middle" x="842" y="85">graph_node · graph_route</text><text class="ns s" text-anchor="middle" x="842" y="100">graph_done (all timings)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="172">retrieval.py</text><text class="ns s" text-anchor="middle" x="842" y="191">embed_ms vs search_ms</text><text class="ns s" text-anchor="middle" x="842" y="206">chunk metadata</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">CHANGED</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="752" y="246"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="278">tools.py</text><text class="ns s" text-anchor="middle" x="842" y="297">tool_call: args, ok, ms</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="259">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="996" y="144"></rect><text class="nt t" text-anchor="middle" x="1086" y="168">OpenAI</text><text class="ns s" text-anchor="middle" x="1086" y="187">embeddings + LLM</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="1240" y="86"></rect><text class="nt t" text-anchor="middle" x="1330" y="118">stdout / docker logs</text><text class="ns s" text-anchor="middle" x="1330" y="136">one JSON object per line</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="98">NEW</text></g><g class="node-new"><rect height="87" rx="8" width="180" x="1240" y="176"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="208">sample_requests.j</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="226">sonl</text><text class="ns s" text-anchor="middle" x="1330" y="246">scripts/log_demo.py</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="190">NEW</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="131"></rect><text class="el" text-anchor="middle" x="230" y="142">HTTP</text><rect class="elbg" height="15" rx="3" width="46" x="451" y="104"></rect><text class="el" text-anchor="middle" x="474" y="116">set id</text><rect class="elbg" height="15" rx="3" width="46" x="602" y="162"></rect><text class="el" text-anchor="start" x="604" y="173">stamps</text><rect class="elbg" height="15" rx="3" width="34" x="946" y="157"></rect><text class="el" text-anchor="middle" x="962" y="168">JSON</text><rect class="elbg" height="15" rx="3" width="142" x="527" y="334"></rect><text class="el" text-anchor="middle" x="598" y="345">X-Request-ID + answer</text><text class="lane" style="fill:var(--ghost)" x="20" y="389">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="399"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="426">Day 24 · token + cost tracking</text></g><g class="node-ghost"><rect height="44" rx="8" width="182" x="300" y="399"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="391" y="426">Day 25 · guardrails</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Logs you can read but not use

- `logging.basicConfig` free-text lines: `graph_route route=rag type=simple ...`
- Concurrent requests interleave, with nothing to tell them apart
- `memory_rewrite` logged the user's original and rewritten question verbatim
- `logger.exception()` in the 500 handler logged `NoneType: None` instead of the traceback

### After this episode: Every request can explain itself

- One JSON object per event with `ts`, `level`, `logger`, `event`, `request_id`
- `X-Request-ID` honoured or generated, stamped on every line, returned in headers and error bodies
- Events for routing, retrieval (with chunk metadata), tools, node latency and errors
- User text shown as `<N chars>` unless `LOG_USER_TEXT=1`; the 500 handler logs the real traceback

> **Why it matters:** once the system runs in a container or on a server, logs are the only window you have. A user saying "request 3f9a… gave a weird answer" is only useful if one filter on that id gives you the route, the chunks, the timings and the error.

## Code walkthrough

Five snippets from `Day23`. The first three are the whole mechanism; the last two show it being used.

### observability.py · the id travels by itself

```python
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
...
class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True
```

**A ContextVar plus a filter puts the id on every line without passing it around.** The ContextVar holds one value per request context. The filter runs on every record from any module and copies the id onto it. Starlette copies the context into worker threads, so sync endpoints and graph nodes see it too.

### main.py · set the id, log start and end

```python
request_id = request.headers.get("x-request-id") or new_request_id()
token = request_id_var.set(request_id)
started = time.perf_counter()
log_event(logger, "request_start", method=request.method, path=request.url.path)
try:
    response = await call_next(request)
...
response.headers["X-Request-ID"] = request_id
response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
log_event(logger, "request_end", method=request.method, path=request.url.path,
          status=response.status_code, latency_ms=elapsed_ms)
```

**Honour the caller's id, so their logs and yours line up.** If a client or gateway already has a trace id, we reuse it. Otherwise we make a 12-character one. Either way it comes back in the response header.

### observability.py · structured and readable

```python
def redact(text: str | None) -> str:
    """User-provided text is only logged when LOG_USER_TEXT=1; otherwise just its length."""
    if text is None:
        return "-"
    return text if os.getenv("LOG_USER_TEXT") == "1" else f"<{len(text)} chars>"
...
def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields) -> None:
    """Emit `event key=value ...` as text AND as structured fields for the JSON formatter."""
    message = event + "".join(f" {k}={summarize(v) if isinstance(v, (dict, list)) else v}" for k, v in fields.items())
    logger.log(level, message, extra={"event": event, "fields": fields})
```

**One call gives you a readable message and real JSON fields.** `extra` puts the fields on the log record, where `JsonFormatter` picks them up. The text message keeps pytest's `caplog` and `LOG_FORMAT=text` readable.

### main.py · the traceback bug

```python
@app.exception_handler(Exception)
def unexpected_error_handler(request: Request, exc: Exception):
    logger.error("unexpected_error path=%s", request.url.path, exc_info=exc)   # exc_info=exc: no active except block here
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id_var.get()})
```

**`logger.exception()` only works inside an `except` block.** An exception handler isn't an `except` block, so Days 5–22 logged `NoneType: None` and lost every traceback. Passing the exception explicitly fixes it, and the client gets an id it can report.

### retrieval.py · where the time goes

```python
log_event(logger, "retrieval", backend="faiss", filters=filters or {}, query_len=len(query), kept=len(kept),
          best_score=round(kept[0]["score"], 3) if kept else 0.0, embed_ms=round(embed_ms, 1), search_ms=round(search_ms, 2),
          chunks=[{"doc": c["doc_id"], "chunk": c["chunk_id"], "topic": c.get("topic"), "score": round(c["score"], 3),
                   "expanded": bool(c.get("expanded"))} for c in kept])
```

**Split the timing where the cause might hide.** `embed_ms` is the network call to OpenAI, `search_ms` is local FAISS. In the demo `retrieve_context` took about 1.5 s while `search_ms` was about 1 ms, which ends the "should we switch vector DB?" debate.

## Run it

Run from `Day23` in PowerShell. Use the default JSON format first, then show `LOG_FORMAT=text` once for comparison.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `242 passed` (20 new tests in `test_observability.py`).

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** Startup lines are JSON objects with `request_id: "-"`, since no request is running yet.

**Step 3**

```text
$r = Invoke-WebRequest http://127.0.0.1:8000/health -Headers @{"X-Request-ID"="my-trace-1"}
$r.Headers["X-Request-ID"]; $r.Headers["X-Process-Time-Ms"]
```

**Expect:** `my-trace-1` and a latency in ms. The server shows `request_start` and `request_end` with `request_id: my-trace-1`.

**Step 4**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -Headers @{"X-Request-ID"="masada-1"} -ContentType "application/json" `
  -Body '{"query":"Where is Masada?"}'
```

**Expect:** In the server log: `graph_route`, `retrieval` (with `embed_ms`, `search_ms` and chunk topics), a `graph_node` line per node, and `graph_done`. All carry `masada-1`. Search for "Masada?": the question itself isn't there.

**Step 5**

```powershell
python -m scripts.log_demo
```

**Expect:** A summary line pointing at `data/logs/sample_requests.jsonl`, then one line per `demo-1`…`demo-5` with route, status, latency and slowest node.

**Step 6**

```powershell
Get-Content data\logs\sample_requests.jsonl | ConvertFrom-Json |
  Where-Object request_id -eq "demo-3" | Format-Table event, node, ms, latency_ms
```

**Expect:** The comparison request rebuilt from its id alone. `call_llm` is the slowest node.

### Break it on purpose

#### 1 · Bring back the lost traceback

In `main.py`, change the 500 handler back to `logger.exception("unexpected_error path=%s", request.url.path)` and run `python -m pytest tests/test_observability.py -q`. `test_errors_are_logged_with_request_id_and_returned_to_client` fails: the ERROR line's `exception` field says `NoneType: None`, with no `ZeroDivisionError`. Restore `exc_info=exc` and it passes.

#### 2 · Find the user text that still leaks

`redact()` covers the rewrite event, but tool arguments are logged as-is: `graph_tool_selected` in `graph.py` logs `args=decision.arguments` and `tool_call` logs `args` too. Send `12*(3+4)` and the expression is in the log. With `LLM_ROUTING=1`, a question the LLM sends to `search_docs` gets `{"query": <the question>}` from `llm_decision`, so the full question lands in the log. Arguments are logged on purpose for debugging (a test checks it), so the fix is to redact the values, not drop the field.

```text
# graph.py, select_tool
log_event(logger, "graph_tool_selected", tool=decision.tool, decided_by=decision.decided_by,
          args={k: redact(str(v)) for k, v in decision.arguments.items()})
```

> Observability is a contract like any other: a fixed format, one id per request, and rules about what may be written. The breaks show both ways it quietly fails: the error you needed isn't recorded, or data you promised not to keep is.

## Cheat sheet

- **Structured logging**: Logging events as key/value data (here JSON) instead of free sentences, so tools can filter and aggregate them.
- **Request id**: A unique id per request, attached to every log line and returned to the client, used to find one request's logs.
- **ContextVar**: A Python variable with a separate value per execution context, like per request, safe across async tasks.
- **Logging filter**: A hook that sees every log record before it's written. Here it adds `request_id`.
- **Formatter**: Turns a log record into text. `JsonFormatter` writes one JSON object; `TextFormatter` writes a readable line.
- **Event name**: The fixed first word of each line (`graph_route`, `retrieval`, `tool_call`) that you filter on.
- **Redaction**: Replacing sensitive values in logs, here user text becomes `<N chars>` unless `LOG_USER_TEXT=1`.
- **exc_info**: The exception attached to a log record. Without an active `except`, you must pass it explicitly.
- **X-Process-Time-Ms**: A response header with the server-side latency, so the client can compare it to what it measured.
- **Bottleneck**: The one step that dominates latency. Here the embedding and LLM network calls, not FAISS.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>How does <code>retrieval.py</code> get the request id without a <code>request_id</code> parameter?</summary><p>It doesn't need it. The middleware sets <code>request_id_var</code>, and <code>RequestIdFilter</code> reads that ContextVar and stamps it on every record, whichever module logged it.</p></details>
<details><summary>Why honour an incoming <code>X-Request-ID</code> instead of always generating one?</summary><p>So a caller or gateway can correlate its own logs with ours. A user report with their id maps straight to our log slice.</p></details>
<details><summary>Why did Days 5–22 lose the traceback of unhandled errors?</summary><p><code>logger.exception()</code> reads the exception from the active <code>except</code> block. A FastAPI exception handler isn't one, so it logged <code>NoneType: None</code>. Passing <code>exc_info=exc</code> fixes it.</p></details>
<details><summary>In the demo, the RAG request took about 2.6 s and <code>retrieve_context</code> 1.5 s. Should we optimise FAISS?</summary><p>No. The retrieval event splits it: <code>search_ms</code> is about 1 ms and the rest is <code>embed_ms</code>, the network call to OpenAI. Caching embeddings would help; a faster index wouldn't.</p></details>
<details><summary>Why log user text as <code>&lt;N chars&gt;</code> by default?</summary><p>Logs are copied, shipped and kept longer than anyone plans. Length is enough for debugging most issues, and <code>LOG_USER_TEXT=1</code> exists for local debugging when you need the text.</p></details>
</div>

**Next:** Day 24 – Tokens Into Dollars

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
