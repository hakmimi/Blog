---
title: "Day 4+: Hardening Your RAG"
description: "Day 4's RAG works on friendly input, on your laptop, from the right folder. This episode wraps it in what a service needs before anyone else calls it: config from the environment, an API key, a rate limit, input bounds, typed errors, a readiness check and timeouts on every OpenAI call."
series: "ai-engineering"
order: 6
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "config", "auth", "rate limit", "error handling"]
readingTime: "10 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day4ProductionUpgrade`](https://github.com/hakmimi/AIEngineering/tree/main/Day4ProductionUpgrade). Layers touched: L1 Data, L2 LLM, L4 System.

## Goals

- **G1. Move every setting and path into one config object.**  
  You can: open `config.py`, change `MAX_TOP_K` in `.env`, restart, and show `/search` enforcing the new limit.
- **G2. Protect the paid endpoints with an API key and a rate limit.**  
  You can: get a 401 without the `X-API-Key` header and a normal answer with it.
- **G3. Reject bad input before it costs an embedding call.**  
  You can: send `top_k: 999` and an empty query and show two 422s with no OpenAI call in the log.
- **G4. Turn failures into clear status codes.**  
  You can: explain the `AppError` classes, the two exception handlers, and why a provider failure maps to 503.

## System map

Same RAG pipeline as Day 4, with gates in front and error handling around it. New boxes are the guards; dashed boxes are Day 4 code that now reads from `config.py` and raises typed errors.

> Client → key → rate limit → bounds → /rag → RAG → LLM (timeout) → answer or typed error

<div class="ae-map" role="img" aria-label="A client request passes require_api_key (401 on a wrong key) and rate_limit (429 over 60 per minute), then the SearchRequest bounds (422). The /rag and /search routes call the Day 4 pipeline, which now loads chunks once through an lru_cache and an absolute path, wraps context in tags, and calls OpenAI with a timeout and retries. Provider failures become ExternalServiceError (503), and exception handlers turn every AppError into a JSON status. config.py reads all limits from .env. A new /ready endpoint reports whether data files and keys are present."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 565" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT · CONFIG</text><text class="lane" x="264" y="18">L4 · SECURITY.PY</text><text class="lane" x="508" y="18">L4 · MAIN.PY</text><text class="lane" x="752" y="18">L3 · L1 RAG + RETRIEVAL</text><text class="lane" x="996" y="18">L2 · LLM + EMBEDDINGS</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,280 C230,280 230,182 261,182" marker-end="url(#mka)"></path><path class="edge-old" d="M200,186 C230,186 230,182 261,182" marker-end="url(#mkm)"></path><path class="edge" d="M354,216 L354,236" marker-end="url(#mka)"></path><path class="edge" d="M444,273 C474,273 474,76 505,76" marker-end="url(#mka)"></path><path class="edge" d="M598,118 L598,137" marker-end="url(#mka)"></path><path class="edge" d="M688,182 C718,182 718,174 749,174" marker-end="url(#mka)"></path><path class="edge-old" d="M842,216 L842,236" marker-end="url(#mkm)"></path><path class="edge" d="M932,174 C962,174 962,174 993,174" marker-end="url(#mka)"></path><path class="edge" d="M932,280 C962,280 962,280 993,280" marker-end="url(#mka)"></path><path class="edge" d="M1176,174 C1206,174 1206,228 1237,228" marker-end="url(#mka)"></path><path class="edge" d="M1176,280 C1206,280 1206,228 1237,228" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,258 V447 H110 V314" marker-end="url(#mkg)"></path><g class="node-new"><rect height="84" rx="8" width="180" x="20" y="144"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="176">config.py</text><text class="ns s" text-anchor="middle" x="110" y="195">Settings from .env</text><text class="ns s" text-anchor="middle" x="110" y="210">paths from __file__</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="157">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="250"></rect><text class="nt t" text-anchor="middle" x="110" y="274">Client</text><text class="ns s" text-anchor="middle" x="110" y="293">sends X-API-Key</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="148"></rect><text class="nt t" text-anchor="middle" x="354" y="180">require_api_key()</text><text class="ns s" text-anchor="middle" x="354" y="198">wrong key → 401</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="160">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="238"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="270">rate_limit()</text><text class="ns s" text-anchor="middle" x="354" y="290">60 / min per IP → 429</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="252">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="66">SearchRequest</text><text class="ns s" text-anchor="middle" x="598" y="85">query 1–1000 · top_k 1–10</text><text class="ns s" text-anchor="middle" x="598" y="100">→ 422</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="47">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="140"></rect><text class="nt t" text-anchor="middle" x="598" y="172">POST /rag · /search</text><text class="ns s" text-anchor="middle" x="598" y="191">dependencies=</text><text class="ns s" text-anchor="middle" x="598" y="206">protected_endpoint</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="153">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="246"></rect><text class="nt t" text-anchor="middle" x="598" y="278">exception handlers</text><text class="ns s" text-anchor="middle" x="598" y="297">AppError → its status</text><text class="ns s" text-anchor="middle" x="598" y="312">anything else → 500</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="259">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="508" y="352"></rect><text class="nt t" text-anchor="middle" x="598" y="384">GET /ready</text><text class="ns s" text-anchor="middle" x="598" y="403">files + keys present?</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="365">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="132"></rect><text class="nt t" text-anchor="middle" x="842" y="164">get_rag_answer()</text><text class="ns s" text-anchor="middle" x="842" y="184">&lt;context&gt; tags</text><text class="ns s" text-anchor="middle" x="842" y="198">max 6000 chars</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="146">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="238"></rect><text class="nt t" text-anchor="middle" x="842" y="270">load_embedded_chunks</text><text class="ns s" text-anchor="middle" x="842" y="290">lru_cache · absolute path</text><text class="ns s" text-anchor="middle" x="842" y="304">DataStoreError</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="252">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="132"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="164">get_answer()</text><text class="ns s" text-anchor="middle" x="1086" y="184">strict json_schema</text><text class="ns s" text-anchor="middle" x="1086" y="198">timeout 20s · 2 retries</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="146">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="238"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="270">get_embedding()</text><text class="ns s" text-anchor="middle" x="1086" y="290">OpenAIError →</text><text class="ns s" text-anchor="middle" x="1086" y="304">ExternalServiceError 503</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="252">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="197"></rect><text class="nt t" text-anchor="middle" x="1330" y="221">OpenAI</text><text class="ns s" text-anchor="middle" x="1330" y="240">embeddings · Responses API</text></g><rect class="elbg" height="15" rx="3" width="53" x="204" y="214"></rect><text class="el" text-anchor="middle" x="230" y="225">request</text><rect class="elbg" height="15" rx="3" width="78" x="191" y="167"></rect><text class="el" text-anchor="middle" x="230" y="178">APP_API_KEY</text><rect class="elbg" height="15" rx="3" width="46" x="939" y="158"></rect><text class="el" text-anchor="middle" x="962" y="168">prompt</text><rect class="elbg" height="15" rx="3" width="40" x="942" y="264"></rect><text class="el" text-anchor="middle" x="962" y="274">query</text><rect class="elbg" height="15" rx="3" width="168" x="636" y="440"></rect><text class="el" text-anchor="middle" x="720" y="451">results · or 4xx/5xx JSON</text><text class="lane" style="fill:var(--ghost)" x="20" y="495">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="214" x="20" y="505"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="127" y="532">Day 5 · RAG reliability</text></g><g class="node-ghost"><rect height="44" rx="8" width="230" x="254" y="505"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="369" y="532">Day 6 · routing + latency</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: A prototype on one laptop

- Anyone who can reach the port can spend your OpenAI credits
- `top_k` and `query` accept anything, including -1 and 50,000 characters
- `data/...` paths only work when you start from the project folder
- An OpenAI error or a missing file becomes an unexplained 500

### After this episode: A service that can say no

- `require_api_key` and `rate_limit` guard `/search` and `/rag`
- `SearchRequest` enforces `min_length`, `max_length`, `ge` and `le`
- `config.py` owns every path, model name, limit and timeout
- `AppError` subclasses map to 500 or 503, and `/ready` reports missing pieces

> **Why it matters:** an AI endpoint costs money on every call, so an open, unbounded endpoint is a billing risk as well as a security risk. Everything added today is plain web-service engineering, and it is what separates a demo from something you can hand to a team.

## Code walkthrough

Five snippets from `Day4ProductionUpgrade`. Each one is a guard; say what it prevents.

### config.py · one source of settings

```python
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

@dataclass(frozen=True)
class Settings:
    base_dir: Path = BASE_DIR
    docs_path: Path = BASE_DIR / "data" / "docs.json"
    ...
    max_top_k: int = int(os.getenv("MAX_TOP_K", "10"))
    retrieval_threshold: float = float(os.getenv("RETRIEVAL_THRESHOLD", "0.55"))
    openai_timeout_seconds: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
```

**Paths come from the code's location, limits come from the environment.** This fixes Day 3's wrong-folder bug for good. The 0.55 threshold from Day 4 is now a setting, so you can tune it without touching `rag.py`.

### security.py · lock and speed limit

```python
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.app_api_key and not secrets.compare_digest(x_api_key or "", settings.app_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

def rate_limit(request: Request) -> None:
    ...
    while window and now - window[0] > 60:
        window.popleft()

    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

**Auth is off until you set APP_API_KEY, then every protected call needs the header.** `compare_digest` compares in constant time, so timing can't leak the key. The rate limit keeps a deque of timestamps per client IP and drops those older than 60 seconds. It's per process: two workers means two separate counters.

### main.py · gates on the route

```python
class SearchRequest(BaseModel):
    query : str = Field(..., min_length=1, max_length=settings.max_query_length)
    top_k : int = Field(default=4, ge=1, le=settings.max_top_k)

protected_endpoint = [Depends(require_api_key), Depends(rate_limit)]

@app.post('/rag', dependencies=protected_endpoint)
def get_rag_llm(request : SearchRequest) -> dict:
```

**Two dependencies and four numbers close the doors Day 4 left open.** `top_k: -1` from Day 3 is now a 422. Note the order FastAPI uses: the dependencies run before the body is validated, which matters in the break-it.

### errors.py + main.py · typed failures

```python
class ExternalServiceError(AppError):
    def __init__(self, message: str = "External AI service is unavailable"):
        super().__init__(message, status_code=503)
...
@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    logger.warning("Application error on %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
```

**The error type decides the status code, in one place.** 503 says our dependency is down, 500 says our code is broken. The client and the on-call person can tell them apart. The catch-all handler returns a generic 500 so stack traces never leak to callers.

### llm.py · structured output

```python
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "score": {"type": ["number", "null"]},
    },
    "required": ["answer", "confidence"],
    "additionalProperties": False,
}
...
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "rag_answer",
                        "schema": ANSWER_SCHEMA,
                        "strict": True,
                    }
                },
```

**Structured output replaces 'please return JSON' with a schema the API enforces.** Compare the highlighted `properties` and `required`. In strict mode they must list the same keys. Hold that thought for the break-it.

## Run it

Run from `Day4ProductionUpgrade` in PowerShell. Replace `demo-key-123` with whatever throwaway value you put in `APP_API_KEY`.

**Step 1**

```powershell
uvicorn main:app --reload
# second terminal
Invoke-RestMethod http://127.0.0.1:8000/ready | ConvertTo-Json
```

**Expect:** `status: ready` and four checks, with `api_key_auth_enabled: true`. Rename `data` for a moment to see `degraded`.

**Step 2**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/search" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Jerusalem","top_k":4}'
```

**Expect:** PowerShell throws: **401 Invalid API key**. No embedding call in the log.

**Step 3**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/search" -Method Post `
  -Headers @{ "X-API-Key" = "demo-key-123" } `
  -ContentType "application/json" `
  -Body '{"query":"Jerusalem","top_k":999}'
```

**Expect:** **422**: `top_k` must be at most 10.

**Step 4**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/search" -Method Post `
  -Headers @{ "X-API-Key" = "demo-key-123" } `
  -ContentType "application/json" `
  -Body '{"query":"Jerusalem","top_k":4}' | ConvertTo-Json -Depth 4
```

**Expect:** Four chunks with scores. The log shows `Search query received: length=9`; the query text itself is no longer logged.

**Step 5**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag" -Method Post `
  -Headers @{ "X-API-Key" = "demo-key-123" } `
  -ContentType "application/json" `
  -Body '{"query":"Why is Jerusalem so important?"}'
```

**Expect:** **503 External AI service is unavailable**. `/search` works and `/rag` doesn't. Go to Break it 1.

**Step 6**

```powershell
python -m pytest tests\test_api_hardening.py -q
```

**Expect:** With `APP_API_KEY` set: **1 passed, 2 failed** (401 instead of 422). Go to Break it 2.

### Break it on purpose

#### 1 · Every /rag call returns 503

Read the log after step 5: `OpenAI LLM request failed`, and inside it a **400 BadRequestError** saying the schema is invalid because `score` is missing from `required`. In strict structured-output mode, every key in `properties` must also be in `required`. The `except TypeError` fallback never runs, because this is an API error, not a TypeError. The error handling worked perfectly: it turned our own schema bug into a clean 503. That's also why `/ready` said `ready`: it checks files and keys, not whether a real call succeeds.

```text
# llm.py: list every property; the null type keeps score optional in practice
"required": ["answer", "confidence", "score"],
```

#### 2 · Turning auth on breaks the tests

`test_search_rejects_empty_query_before_openai_call` expects 422, but with `APP_API_KEY` in `.env` it gets **401**. FastAPI runs the route's dependencies before it validates the body, so `require_api_key` rejects the request first. The tests only pass when auth is off, which is the opposite of production. Also note that the catch-all handler logs `NoneType: None` instead of a stack trace: it's a sync function, so FastAPI runs it in a worker thread where `logger.exception` can't see the exception.

```text
# tests/test_api_hardening.py
from config import settings

HEADERS = {"X-API-Key": settings.app_api_key or ""}

response = client.post("/search", json={"query": "", "top_k": 4}, headers=HEADERS)

# main.py: keep the traceback in the catch-all handler
logger.error("Unexpected error on %s", request.url.path, exc_info=exc)
```

> Hardening code is code, and it needs the same live testing as the feature it protects. A clean 503 can hide a bug in your own request, and tests written with auth off prove nothing about the service with auth on.

## Cheat sheet

- **Configuration**: Values that change between environments (paths, limits, model names) read from `.env` instead of written in code.
- **API key auth**: The client sends a shared secret in a header (`X-API-Key`); a wrong or missing key gets 401.
- **Rate limiting**: Capping how many requests a client can make per time window; over the cap returns 429.
- **Dependency (FastAPI)**: A function listed in `Depends(...)` that runs before the endpoint and can reject the request.
- **Input bounds**: Limits like `ge=1, le=10` and `max_length` that reject bad values before any work is done.
- **401 / 422 / 429 / 503**: Not authorized / invalid input / too many requests / a service we depend on is down.
- **Readiness check**: `/ready` asks whether the service has what it needs to work; `/health` only asks whether it's running.
- **Timeout and retries**: The OpenAI client gives up after 20 seconds and retries twice, so one slow call can't hang a request forever.
- **Structured output**: Passing a JSON schema to the model API so the reply must match it; strict mode requires every property in `required`.
- **lru_cache**: Remembers a function's result. Here the chunks file is read once, so a new file needs a server restart.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why are paths built from Path(__file__) instead of 'data/...'?</summary><p>A relative path depends on the folder you start from. <code>__file__</code> is the location of <code>config.py</code>, so the path is right no matter where uvicorn or a script is launched.</p></details>
<details><summary>APP_API_KEY is empty. Is /rag protected?</summary><p>No. <code>require_api_key</code> only checks when <code>settings.app_api_key</code> is set. Auth is opt-in, and <code>/ready</code> shows it as <code>api_key_auth_enabled: false</code>.</p></details>
<details><summary>Why does a failed OpenAI call return 503 and not 500?</summary><p><code>get_embedding</code> and <code>get_answer</code> convert <code>OpenAIError</code> into <code>ExternalServiceError</code>, which carries 503. It tells the caller that a dependency failed, not our code.</p></details>
<details><summary>Why does every /rag call fail in this folder while /search works?</summary><p><code>ANSWER_SCHEMA</code> is sent with <code>strict: True</code>, but <code>score</code> is in <code>properties</code> and missing from <code>required</code>. OpenAI rejects the request with 400, and the code maps it to 503. <code>/search</code> never calls the LLM.</p></details>
<details><summary>Why do the 422 tests get 401 when APP_API_KEY is set?</summary><p>Route dependencies run before body validation, so <code>require_api_key</code> rejects the request before Pydantic sees the empty query or large <code>top_k</code>.</p></details>
</div>

**Next:** Day 5 – RAG That Fails Safely

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
